from core.models import Player, PlayerStatistics
from core.services.ffi import calculate_ffi

player = Player.objects.get(name="Eberechi Eze")
print("Player:", player.name)
print("Current club:", player.current_club)

club_ids = list(
    PlayerStatistics.objects.filter(
        player=player,
        minutes_played__gt=0,
        club__isnull=False,
    ).values_list("club_id", flat=True).distinct()
)

for club_id in club_ids:
    records = list(
        PlayerStatistics.objects.filter(
            player=player,
            club_id=club_id,
            minutes_played__gt=0,
            match__status="COMPLETED",
        ).select_related("club", "match").order_by(
            "-match__match_date", "-match_id"
        )
    )

    if not records:
        continue

    latest = records[0]
    club = latest.club

    print("\n" + "=" * 50)
    print("Historical club:", club.name, "| ID:", club_id)
    print("Appearance records:", len(records))
    print("Latest appearance:", latest.match.match_date)
    print("Latest match ID:", latest.match_id)

    result = calculate_ffi(
        player.id,
        before_date=latest.match.match_date,
        club_id=club_id,
    )

    print("FFI:", result.get("ffi"))
    print("Club used by FFI:", result.get("club_id"))
    print("Matches used:", result.get("matches_used"))
    print("Message:", result.get("message"))
