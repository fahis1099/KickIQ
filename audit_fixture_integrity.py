from django.db.models import Q, Count
from core.models import Match, Player, PlayerStatistics
from datetime import date

CUTOFF = date.fromisoformat("2026-09-20")
PLAYER_ID = 169
CLUB_ID = 15

print("=== KICKIQ FIXTURE INTEGRITY AUDIT ===")
print("Target cutoff:", CUTOFF)

# 1. Verify the seven latest completed club fixtures.
fixtures = list(
    Match.objects.filter(
        Q(home_club_id=CLUB_ID) | Q(away_club_id=CLUB_ID),
        status="COMPLETED",
        match_date__lt=CUTOFF,
    )
    .select_related("home_club", "away_club")
    .order_by("-match_date", "-id")[:7]
)

print("\n--- Latest 7 completed club fixtures ---")
dates = [m.match_date for m in fixtures]
ordering_ok = dates == sorted(dates, reverse=True)
cutoff_ok = all(d < CUTOFF for d in dates)

for index, match in enumerate(fixtures):
    print(
        f"{index}: ID={match.id} | Date={match.match_date} | "
        f"{match.home_club.name} {match.home_goals}-{match.away_goals} "
        f"{match.away_club.name}"
    )

print("Fixture count:", len(fixtures))
print("Newest-first ordering:", ordering_ok)
print("All dates before cutoff:", cutoff_ok)
print("Unique fixture IDs:", len({m.id for m in fixtures}) == len(fixtures))

# 2. Inspect player records against those fixtures.
player = Player.objects.get(pk=PLAYER_ID)
fixture_ids = [m.id for m in fixtures]

records = list(
    PlayerStatistics.objects.filter(
        player=player,
        club_id=CLUB_ID,
        match_id__in=fixture_ids,
    ).select_related("match", "club")
)

records_by_match = {}
for record in records:
    records_by_match.setdefault(record.match_id, []).append(record)

print(f"\n--- {player.name}: fixture-by-fixture statistics ---")
for match in fixtures:
    matching = records_by_match.get(match.id, [])
    if not matching:
        status = "NO PLAYER STATISTICS RECORD"
    elif len(matching) > 1:
        status = f"DUPLICATE RECORDS: {len(matching)}"
    else:
        record = matching[0]
        status = (
            f"minutes={record.minutes_played}, "
            f"rating={record.rating}"
        )
    print(
        f"Match {match.id} | {match.match_date} | {status}"
    )

# 3. Find duplicate player-match pairs across all statistics.
duplicates = list(
    PlayerStatistics.objects.values(
        "player_id", "match_id"
    )
    .annotate(total=Count("id"))
    .filter(total__gt=1)
)

print("\n--- Duplicate player-match pairs ---")
print("Duplicate pairs:", len(duplicates))
for item in duplicates[:10]:
    print(item)

# 4. Check whether statistics' recorded club participated in the match.
bad_club_records = PlayerStatistics.objects.exclude(
    Q(club_id=__import__("django").db.models.F("match__home_club_id"))
    | Q(club_id=__import__("django").db.models.F("match__away_club_id"))
)

print("\n--- Statistics linked to a non-participating club ---")
print("Invalid club-fixture records:", bad_club_records.count())
for record in bad_club_records.select_related(
    "player", "club", "match"
)[:10]:
    print(
        f"Player={record.player.name} | Match={record.match_id} | "
        f"Statistics club={record.club_id}"
    )

print("\n=== AUDIT COMPLETE ===")
