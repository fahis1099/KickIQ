
from datetime import timedelta
from statistics import pstdev

from django.utils import timezone

from core.models import PlayerStatistics
from core.services.ffi_analysis import analyze_player_continuity


def calculate_ffi(
    player_id,
    before_date=None,
    season=None,
    window=5,
    fixture_window=7,
    minimum_appearances=3,
):
    """
    Calculate the Football Form Index on a 0-100 scale.

    Selection rules:
    - Analyse the latest completed fixtures involving the player's
      historical club.
    - Use up to five recent rated appearances within that fixture window.
    - Require at least three rated appearances by default.
    - Exclude matches on or after before_date.
    - Optionally restrict analysis to a single season.

    FFI components:
    - 70%: recency-weighted performance
    - 15%: form trend
    - 15%: rating consistency

    This function does not modify database records.
    """

    # Validate parameters.
    if window < 1:
        raise ValueError("window must be at least 1.")

    if fixture_window < 1:
        raise ValueError("fixture_window must be at least 1.")

    if minimum_appearances < 1:
        raise ValueError("minimum_appearances must be at least 1.")

    if minimum_appearances > window:
        raise ValueError(
            "minimum_appearances cannot exceed window."
        )

    if before_date is None:
        before_date = timezone.localdate() + timedelta(days=1)

    # Find the latest eligible historical appearance.
    # Only completed matches before the cutoff can determine the club.
    appearances_query = PlayerStatistics.objects.filter(
        player_id=player_id,
        minutes_played__gt=0,
        match__status="COMPLETED",
        match__match_date__lt=before_date,
    )

    if season is not None:
        appearances_query = appearances_query.filter(
            match__season=season
        )

    latest_record = (
        appearances_query
        .select_related("match")
        .order_by("-match__match_date", "-match_id")
        .first()
    )

    if latest_record is None:
        return {
            "ffi": None,
            "matches_used": 0,
            "minimum_appearances": minimum_appearances,
            "message": "No eligible previous appearances.",
        }

    # Use the historical club from the selected appearance,
    # not Player.current_club.
    club_id = latest_record.club_id

    # Analyse the club's recent completed fixture sequence.
    continuity = analyze_player_continuity(
        player_id=player_id,
        club_id=club_id,
        before_date=before_date,
        window=fixture_window,
        recent_appearance_count=window,
        season=season,
    )

    eligible_match_ids = [
        fixture["match_id"]
        for fixture in continuity["fixture_sequence"]
    ]

    # Select actual rated appearances only.
    # A missed fixture must never be treated as a zero rating.
    recent_records = list(
        PlayerStatistics.objects.filter(
            player_id=player_id,
            club_id=club_id,
            match_id__in=eligible_match_ids,
            match__status="COMPLETED",
            match__match_date__lt=before_date,
            rating__isnull=False,
            minutes_played__gt=0,
        )
        .select_related("match")
        .order_by("-match__match_date", "-match_id")[:window]
    )

    matches_used = len(recent_records)

    # Return no score if there is insufficient recent history.
    if matches_used < minimum_appearances:
        return {
            "ffi": None,
            "matches_used": matches_used,
            "minimum_appearances": minimum_appearances,
            "preferred_window": window,
            "fixture_window": fixture_window,
            "club_id": club_id,
            "continuity": continuity,
            "message": (
                "Insufficient recent data: at least "
                f"{minimum_appearances} rated appearances are required "
                f"within the last {fixture_window} club fixtures."
            ),
        }

    ratings = [
        float(record.rating)
        for record in recent_records
    ]

    # Defensive validation: database constraints alone do not guarantee
    # that imported ratings are meaningful for this calculation.
    if any(rating < 0 or rating > 10 for rating in ratings):
        raise ValueError(
            "FFI cannot be calculated: ratings must be between 0 and 10."
        )

    # Component 1: recency-weighted performance score.
    # Newest rating gets the highest weight.
    weights = list(range(matches_used, 0, -1))

    weighted_average_rating = (
        sum(
            rating * weight
            for rating, weight in zip(ratings, weights)
        )
        / sum(weights)
    )

    performance_score = weighted_average_rating * 10.0

    # Component 2: compare the newest two ratings with the older ratings.
    # Ratings are ordered newest first.
    newest_ratings = ratings[:2]
    older_ratings = ratings[2:]

    if older_ratings:
        recent_average = (
            sum(newest_ratings) / len(newest_ratings)
        )
        older_average = (
            sum(older_ratings) / len(older_ratings)
        )

        rating_change = recent_average - older_average

        # A one-point improvement maps to a 25-point trend increase.
        trend_score = max(
            0.0,
            min(100.0, 50.0 + rating_change * 25.0),
        )
    else:
        # Neutral trend when there is no older group to compare.
        rating_change = 0.0
        trend_score = 50.0

    # Component 3: consistency.
    # Population standard deviation measures rating variation.
    rating_std_dev = pstdev(ratings)

    consistency_score = max(
        0.0,
        min(100.0, 100.0 - rating_std_dev * 25.0),
    )

    # Final FFI: 70% performance, 15% trend, 15% consistency.
    ffi = (
        performance_score * 0.70
        + trend_score * 0.15
        + consistency_score * 0.15
    )

    latest_appearance_date = recent_records[0].match.match_date

    days_since_latest_appearance = (
        before_date - latest_appearance_date
    ).days

    if matches_used == window:
        message = "Calculated successfully."
    else:
        message = (
            "Calculated using available recent appearances; "
            "fewer than the preferred number of five were available."
        )

    return {
        "ffi": round(ffi, 2),
        "matches_used": matches_used,
        "preferred_window": window,
        "fixture_window": fixture_window,
        "minimum_appearances": minimum_appearances,
        "club_id": club_id,
        "weighted_average_rating": round(
            weighted_average_rating, 2
        ),
        "performance_score": round(performance_score, 2),
        "rating_change": round(rating_change, 2),
        "trend_score": round(trend_score, 2),
        "rating_standard_deviation": round(rating_std_dev, 3),
        "consistency_score": round(consistency_score, 2),
        "days_since_latest_appearance": (
            days_since_latest_appearance
        ),
        "continuity": continuity,
        "message": message,
    }
