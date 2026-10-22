from django.db.models import Q
from core.models import Player, Match, PlayerStatistics
from core.services.ffi import calculate_ffi

CUTOFF = "2026-10-13"

case1 = []
case2 = []
case3 = []

print("=== KICKIQ FFI EDGE-CASE AUDIT ===")
print("Cutoff:", CUTOFF)

for player in Player.objects.all().select_related("current_club"):
    club_ids = list(
        PlayerStatistics.objects.filter(
            player=player,
            minutes_played__gt=0,
            club__isnull=False,
        ).values_list("club_id", flat=True).distinct()
    )

    if len(club_ids) > 1:
        case3.append((player, club_ids))

    for club_id in club_ids:
        fixtures = list(
            Match.objects.filter(
                Q(home_club_id=club_id) | Q(away_club_id=club_id),
                status="COMPLETED",
                match_date__lt=CUTOFF,
            ).order_by("-match_date", "-id")[:7]
        )

        if len(fixtures) < 7:
            continue

        fixture_ids = [m.id for m in fixtures]
        records = {
            s.match_id: s
            for s in PlayerStatistics.objects.filter(
                player=player,
                club_id=club_id,
                match_id__in=fixture_ids,
                minutes_played__gt=0,
            )
        }

        appeared = [m.id in records for m in fixtures]
        rated = [
            m.id in records and records[m.id].rating is not None
            for m in fixtures
        ]

        if not appeared[0] and not appeared[1] and appeared[2]:
            if sum(rated) >= 3:
                case1.append((player, club_id, fixtures, appeared))

        if any(appeared[:3]) and sum(rated) == 2:
            case2.append((player, club_id, fixtures, appeared, rated))

print("\n=== CASE 1: MISSED LATEST TWO, APPEARED IN THIRD ===")
for player, club_id, fixtures, appeared in case1[:5]:
    result = calculate_ffi(
        player.id, before_date=fixtures[0].match_date, club_id=club_id
    )
    print(
        player.name, "| club:", club_id,
        "| appearances:", sum(appeared),
        "| FFI:", result.get("ffi"),
        "| message:", result.get("message"),
    )
if not case1:
    print("No matching candidate found.")

print("\n=== CASE 2: ONLY TWO RATED APPEARANCES ===")
for player, club_id, fixtures, appeared, rated in case2[:5]:
    result = calculate_ffi(
        player.id, before_date=fixtures[0].match_date, club_id=club_id
    )
    print(
        player.name, "| club:", club_id,
        "| appearances:", sum(appeared),
        "| rated:", sum(rated),
        "| FFI:", result.get("ffi"),
        "| message:", result.get("message"),
    )
if not case2:
    print("No matching candidate found.")

print("\n=== CASE 3: MULTIPLE HISTORICAL CLUBS ===")
for player, club_ids in case3[:10]:
    print(
        player.name,
        "| current club:", player.current_club,
        "| historical club IDs:", club_ids,
    )
if not case3:
    print("No multiple-club candidates found.")

print("\n=== CANDIDATE COUNTS ===")
print("Case 1:", len(case1))
print("Case 2:", len(case2))
print("Case 3:", len(case3))
