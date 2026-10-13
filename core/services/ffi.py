
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
    club_id=None,
    recent_availability_window=3,
):
    """
    Calculate FFI using only eligible historical appearances.

    Eligibility requirements:
    - At least minimum_appearances rated appearances within fixture_window
      completed club fixtures.
    - At least one appearance in the most recent
      recent_availability_window club fixtures.
    - All historical fixtures must be strictly before before_date.

    If club_id is supplied, evaluate the player for that club.
    Otherwise, use the club associated with the player's latest
    eligible appearance.
    """

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

    if recent_availability_window < 1:
        raise ValueError(
            "recent_availability_window must be at least 1."
        )

    if recent_availability_window > fixture_window:
        raise ValueError(
            "recent_availability_window cannot exceed fixture_window."
        )

    if before_date is None:
        before_date = timezone.localdate() + timedelta(days=1)

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

    # If a target club is supplied, do not use another club's history.
    if club_id is not None:
        appearances_query = appearances_query.filter(
            club_id=club_id
        )

    latest_record = (
        appearances_query
        .select_related("match")
        .order_by("-match__match_date", "-match_id")
        .first()
    )

    if latest_record is None:
        message = (
            "No eligible previous appearances for the target club."
            if club_id is not None
            else "No eligible previous appearances."
        )

        return {
            "ffi": None,
            "matches_used": 0,
            "minimum_appearances": minimum_appearances,
            "preferred_window": window,
            "fixture_window": fixture_window,
            "recent_availability_window": recent_availability_window,
            "club_id": club_id,
            "message": message,
        }

    # Without an explicit target club, use the latest historical club.
    effective_club_id = (
        club_id if club_id is not None else latest_record.club_id
    )

    continuity = analyze_player_continuity(
        player_id=player_id,
        club_id=effective_club_id,
        before_date=before_date,
        window=fixture_window,
        recent_appearance_count=window,
        season=season,
    )

    fixture_sequence = continuity["fixture_sequence"]

    # RULE 1: Require an appearance in at least one of the last 3
    # completed fixtures (or the configured recent window).
    recent_fixtures = fixture_sequence[:recent_availability_window]

    appeared_recently = any(
        fixture["appeared"]
        for fixture in recent_fixtures
    )

    if not appeared_recently:
        return {
            "ffi": None,
            "matches_used": 0,
            "minimum_appearances": minimum_appearances,
            "preferred_window": window,
            "fixture_window": fixture_window,
            "recent_availability_window": recent_availability_window,
            "club_id": effective_club_id,
            "continuity": continuity,
            "message": (
                "FFI unavailable: the player has not appeared in any "
                f"of the last {recent_availability_window} completed "
                "club fixtures."
            ),
        }

    eligible_match_ids = [
        fixture["match_id"]
        for fixture in fixture_sequence
    ]

    # Only rated appearances with positive minutes count toward FFI.
    recent_records = list(
        PlayerStatistics.objects.filter(
            player_id=player_id,
            club_id=effective_club_id,
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

    # RULE 2: Require at least 3 rated appearances within the window.
    if matches_used < minimum_appearances:
        return {
            "ffi": None,
            "matches_used": matches_used,
            "minimum_appearances": minimum_appearances,
            "preferred_window": window,
            "fixture_window": fixture_window,
            "recent_availability_window": recent_availability_window,
            "club_id": effective_club_id,
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

    if any(rating < 0 or rating > 10 for rating in ratings):
        raise ValueError(
            "FFI cannot be calculated: ratings must be between 0 and 10."
        )

    # More recent ratings receive higher weights.
    weights = list(range(matches_used, 0, -1))

    weighted_average_rating = (
        sum(rating * weight for rating, weight in zip(ratings, weights))
        / sum(weights)
    )

    performance_score = weighted_average_rating * 10.0

    # Compare the two newest ratings with the older ratings.
    newest_ratings = ratings[:2]
    older_ratings = ratings[2:]

    if older_ratings:
        recent_average = sum(newest_ratings) / len(newest_ratings)
        older_average = sum(older_ratings) / len(older_ratings)

        rating_change = recent_average - older_average

        trend_score = max(
            0.0,
            min(100.0, 50.0 + rating_change * 25.0),
        )
    else:
        rating_change = 0.0
        trend_score = 50.0

    rating_std_dev = pstdev(ratings)

    consistency_score = max(
        0.0,
        min(100.0, 100.0 - rating_std_dev * 25.0),
    )

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
            f"{matches_used} rated appearances were available."
        )

    return {
        "ffi": round(ffi, 2),
        "matches_used": matches_used,
        "preferred_window": window,
        "fixture_window": fixture_window,
        "minimum_appearances": minimum_appearances,
        "recent_availability_window": recent_availability_window,
        "club_id": effective_club_id,
        "weighted_average_rating": round(weighted_average_rating, 2),
        "performance_score": round(performance_score, 2),
        "rating_change": round(rating_change, 2),
        "trend_score": round(trend_score, 2),
        "rating_standard_deviation": round(rating_std_dev, 3),
        "consistency_score": round(consistency_score, 2),
        "days_since_latest_appearance": days_since_latest_appearance,
        "continuity": continuity,
        "message": message,
    }
