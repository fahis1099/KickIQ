from django.db.models import Q

from core.models import Match, Player, PlayerStatistics


def analyze_player_continuity(
    player_id,
    club_id,
    before_date,
    window=7,
    recent_appearance_count=5,
    season=None,
):
    """
    Analyze player appearances across the latest completed fixtures
    played by a club before a target date.

    An appearance requires minutes_played > 0.
    The target date itself is excluded.

    The default window is seven club fixtures.
    """

    if window < 1:
        raise ValueError("window must be at least 1.")

    if recent_appearance_count < 1:
        raise ValueError(
            "recent_appearance_count must be at least 1."
        )

    player = Player.objects.get(pk=player_id)

    fixture_queryset = Match.objects.filter(
        Q(home_club_id=club_id) | Q(away_club_id=club_id),
        status="COMPLETED",
        match_date__lt=before_date,
    )

    if season is not None:
        fixture_queryset = fixture_queryset.filter(
            season=season
        )

    fixtures = list(
        fixture_queryset
        .select_related("home_club", "away_club")
        .order_by("-match_date", "-id")[:window]
    )

    fixture_ids = [match.id for match in fixtures]

    appearance_records = list(
        PlayerStatistics.objects.filter(
            player_id=player_id,
            club_id=club_id,
            match_id__in=fixture_ids,
            minutes_played__gt=0,
        )
        .select_related("match")
        .order_by("-match__match_date", "-match_id")
    )

    records_by_match = {
        record.match_id: record
        for record in appearance_records
    }

    # Index 0 represents the most recent club fixture.
    fixture_index = {
        match.id: index
        for index, match in enumerate(fixtures)
    }

    fixture_sequence = []

    for match in fixtures:
        record = records_by_match.get(match.id)

        opponent = (
            match.away_club.name
            if match.home_club_id == club_id
            else match.home_club.name
        )

        fixture_sequence.append({
            "match_id": match.id,
            "date": match.match_date.isoformat(),
            "opponent": opponent,
            "venue": (
                "Home"
                if match.home_club_id == club_id
                else "Away"
            ),
            "appeared": record is not None,
            "minutes_played": (
                record.minutes_played if record else 0
            ),
            "rating": (
                float(record.rating)
                if record and record.rating is not None
                else None
            ),
        })

    recent_appearances = appearance_records[
        :recent_appearance_count
    ]

    # Count consecutive appearances from the latest fixture backwards.
    consecutive_appearances = 0

    for fixture in fixture_sequence:
        if not fixture["appeared"]:
            break

        consecutive_appearances += 1

    # Fixtures missed between successive appearances.
    appearance_gaps = []

    for newer, older in zip(
        recent_appearances,
        recent_appearances[1:],
    ):
        newer_index = fixture_index[newer.match_id]
        older_index = fixture_index[older.match_id]

        appearance_gaps.append({
            "newer_match_date": (
                newer.match.match_date.isoformat()
            ),
            "older_match_date": (
                older.match.match_date.isoformat()
            ),
            "missed_team_fixtures_between": max(
                0,
                older_index - newer_index - 1,
            ),
        })

    appearances_in_window = len(appearance_records)
    fixtures_analyzed = len(fixtures)

    latest_appearance = (
        appearance_records[0]
        if appearance_records
        else None
    )

    return {
        "player": player.name,
        "club_id": club_id,
        "before_date": before_date.isoformat(),
        "season": season,
        "fixture_window": window,
        "fixtures_analyzed": fixtures_analyzed,
        "appearances_in_window": appearances_in_window,
        "missed_fixtures_in_window": (
            fixtures_analyzed - appearances_in_window
        ),
        "appearance_percentage": (
            round(
                100 * appearances_in_window / fixtures_analyzed,
                2,
            )
            if fixtures_analyzed
            else None
        ),
        "consecutive_appearances_at_end": (
            consecutive_appearances
        ),
        "latest_appearance_date": (
            latest_appearance.match.match_date.isoformat()
            if latest_appearance
            else None
        ),
        "recent_appearances": [
            {
                "date": record.match.match_date.isoformat(),
                "match_id": record.match_id,
                "rating": (
                    float(record.rating)
                    if record.rating is not None
                    else None
                ),
                "minutes_played": record.minutes_played,
                "fixture_index": fixture_index[record.match_id],
            }
            for record in recent_appearances
        ],
        "gaps_between_recent_appearances": appearance_gaps,
        "fixture_sequence": fixture_sequence,
    }