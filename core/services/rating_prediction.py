
from functools import lru_cache
from pathlib import Path
import shap
import numpy as np
import joblib
import pandas as pd

from django.conf import settings
from django.utils.timezone import localdate

from core.models import Match, Player, PlayerStatistics
from core.services.ffi import calculate_ffi


HISTORY_WINDOW = 5
FIXTURE_WINDOW = 7
MINIMUM_APPEARANCES = 3
RECENT_AVAILABILITY_WINDOW = 3

STAT_FIELDS = [
    "minutes_played", "started", "goals", "assists",
    "penalty_goals", "penalty_attempts", "shots",
    "shots_on_target", "passes_completed", "passes_attempted",
    "key_passes", "crosses", "dribbles_completed",
    "dribbles_attempted", "tackles_won", "interceptions",
    "yellow_cards", "red_cards", "fouls_committed",
    "fouls_drawn", "offsides", "own_goals", "penalty_won",
    "penalty_conceded", "shots_faced", "saves",
    "penalty_faced", "penalty_saved",
]



@lru_cache(maxsize=1)
def get_rating_model():
    """Load the trained model once per Django process."""
    model_path = (
        Path(settings.BASE_DIR)
        / "models"
        / "kickiq_rating_model.joblib"
    )

    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained rating model not found: {model_path}"
        )

    return joblib.load(model_path)


def explain_rating_prediction(model, input_data, top_n=8):
    """
    Explain a single prediction using SHAP values from
    the Random Forest inside the saved sklearn pipeline.

    Contributions are measured in predicted-rating points.
    """
    preprocessor = model.named_steps["preprocessor"]
    regressor = model.named_steps["regressor"]

    transformed_data = preprocessor.transform(input_data)

    # Recover readable names, including one-hot encoded categories.
    feature_names = preprocessor.get_feature_names_out()

    explainer = shap.TreeExplainer(regressor)
    shap_values = explainer.shap_values(transformed_data)

    values = np.asarray(shap_values)

    # For single-row regression, SHAP normally returns (1, features).
    values = values.reshape(-1, len(feature_names))[0]

    contributions = []

    for name, contribution in zip(feature_names, values):
        # Remove preprocessing prefixes such as numeric__ and
        # categorical__ from the displayed feature name.
        readable_name = str(name).replace("numeric__", "")
        readable_name = readable_name.replace("categorical__", "")

        contributions.append({
            "feature": readable_name,
            "contribution": round(float(contribution), 4),
        })

    contributions.sort(
        key=lambda item: abs(item["contribution"]),
        reverse=True,
    )

    top_contributions = contributions[:top_n]

    for item in top_contributions:
        item["direction"] = (
            "positive"
            if item["contribution"] > 0
            else "negative"
            if item["contribution"] < 0
            else "neutral"
        )

    return top_contributions



def _mean(values):
    values = [float(value) for value in values if value is not None]
    return sum(values) / len(values) if values else None


def _sum(values):
    values = [float(value) for value in values if value is not None]
    return sum(values) if values else None


def _population_std(values):
    values = [float(value) for value in values if value is not None]

    if not values:
        return None

    mean_value = sum(values) / len(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return variance ** 0.5


def predict_next_match_rating(player_id):
    player = Player.objects.select_related("current_club").get(pk=player_id)

    club = player.current_club
    if not club:
        raise ValueError("This player has no current club assigned.")

    # Find the next scheduled fixture for the player's current club.
    upcoming_matches = Match.objects.filter(
        status="UPCOMING",
        match_date__gte=localdate(),
    ).filter(
        home_club_id=club.id
    ) | Match.objects.filter(
        status="UPCOMING",
        match_date__gte=localdate(),
        away_club_id=club.id,
    )

    match = upcoming_matches.select_related(
        "home_club", "away_club"
    ).order_by("match_date", "id").first()

    if not match:
        raise ValueError("No upcoming fixture was found for this player's club.")

    if match.home_club_id == club.id:
        opponent = match.away_club
        is_home = 1
    else:
        opponent = match.home_club
        is_home = 0

    # Use only completed appearances strictly before the target fixture date.
    history = list(
        PlayerStatistics.objects.filter(
            player_id=player.id,
            club_id=club.id,
            match__status="COMPLETED",
            match__match_date__lt=match.match_date,
            minutes_played__gt=0,
        ).select_related("match").order_by(
            "-match__match_date", "-match_id"
        )[:HISTORY_WINDOW]
    )

    if not history:
        raise ValueError("There is no eligible historical performance for this player.")

    ffi_result = calculate_ffi(
        player_id=player.id,
        before_date=match.match_date,
        season=None,
        window=HISTORY_WINDOW,
        fixture_window=FIXTURE_WINDOW,
        minimum_appearances=MINIMUM_APPEARANCES,
        club_id=club.id,
        recent_availability_window=RECENT_AVAILABILITY_WINDOW,
    )

    if ffi_result.get("ffi") is None:
        raise ValueError(
            ffi_result.get("message", "Historical FFI is unavailable.")
        )

    row = {
        "is_home": is_home,
        "position": player.position or history[0].position,
        "preferred_foot": player.preferred_foot,
        "history_appearances_used": len(history),
        "history_rated_appearances": sum(
            record.rating is not None for record in history
        ),
        "history_latest_rating": (
            float(history[0].rating)
            if history[0].rating is not None else None
        ),
        f"history_rating_mean_{HISTORY_WINDOW}": _mean(
            [record.rating for record in history]
        ),
        f"history_rating_std_{HISTORY_WINDOW}": _population_std(
            [record.rating for record in history]
        ),
    }

    # Rolling statistics for the same previous appearances used in training.
    for field in STAT_FIELDS:
        values = [getattr(record, field) for record in history]
        row[f"history_{field}_mean_{HISTORY_WINDOW}"] = _mean(values)
        row[f"history_{field}_sum_{HISTORY_WINDOW}"] = _sum(values)
        row[f"history_{field}_observed_{HISTORY_WINDOW}"] = sum(
            value is not None for value in values
        )

    continuity = ffi_result.get("continuity") or {}
    row.update({
        "ffi": ffi_result.get("ffi"),
        "ffi_matches_used": ffi_result.get("matches_used"),
        "ffi_weighted_average_rating": ffi_result.get("weighted_average_rating"),
        "ffi_performance_score": ffi_result.get("performance_score"),
        "ffi_rating_change": ffi_result.get("rating_change"),
        "ffi_trend_score": ffi_result.get("trend_score"),
        "ffi_rating_standard_deviation": ffi_result.get(
            "rating_standard_deviation"
        ),
        "ffi_consistency_score": ffi_result.get("consistency_score"),
        "ffi_days_since_latest_appearance": ffi_result.get(
            "days_since_latest_appearance"
        ),
        "ffi_appearance_percentage": continuity.get("appearance_percentage"),
        "ffi_consecutive_appearances": continuity.get(
            "consecutive_appearances_at_end"
        ),
        "ffi_appearances_in_window": continuity.get("appearances_in_window"),
        "ffi_missed_fixtures_in_window": continuity.get(
            "missed_fixtures_in_window"
        ),
    })

    model = get_rating_model()

    # Use the exact feature names and order learned by the saved pipeline.
    feature_names = list(model.feature_names_in_)
    missing = [name for name in feature_names if name not in row]
    if missing:
        raise ValueError(
            "Prediction input is missing model features: "
            + ", ".join(missing)
        )

    input_data = pd.DataFrame(
        [[row[name] for name in feature_names]],
        columns=feature_names,
    )

    if input_data.isna().any().any():
        missing_values = input_data.columns[
            input_data.isna().any()
        ].tolist()
        raise ValueError(
            "Historical data is incomplete for: "
            + ", ".join(missing_values)
        )

    prediction = float(model.predict(input_data)[0])
    prediction = max(0.0, min(10.0, prediction))
    
    explanations = explain_rating_prediction(
        model=model,
        input_data=input_data,
        top_n=8,
    )

    return {
        "player_id": player.id,
        "player_name": player.name,
        "predicted_rating": round(prediction, 2),
        "explanations": explanations,
        "fixture": {
            "match_id": match.id,
            "date": match.match_date.isoformat(),
            "club": club.name,
            "opponent": opponent.name,
            "venue": "Home" if is_home else "Away",
        },
        "message": "Predicted rating for the next eligible fixture.",
    }
