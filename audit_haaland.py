from core.models import Player, PlayerStatistics
from core.services.ffi import calculate_ffi

player = Player.objects.get(pk=169)
print(f"Player: {player.name} | Current club: {player.current_club}")

club_ids = list(
    PlayerStatistics.objects.filter(
        player=player,
        minutes_played__gt=0,
        match__status="COMPLETED",
    ).values_list("club_id", flat=True).distinct()
)

for club_id in club_ids:
    if club_id is None:
        continue

    records = list(
        PlayerStatistics.objects.filter(
            player=player,
            club_id=club_id,
            minutes_played__gt=0,
            match__status="COMPLETED",
        ).select_related("match", "club").order_by(
            "-match__match_date", "-match_id"
        )[:10]
    )

    if not records:
        continue

    print(f"\nHistorical club: {records[0].club.name} (ID {club_id})")
    for r in records:
        print(
            f"Match={r.match_id} | Date={r.match.match_date} | "
            f"Minutes={r.minutes_played} | Rating={r.rating}"
        )

    cutoff = records[0].match.match_date
    result = calculate_ffi(
        player.id, before_date=cutoff, club_id=club_id
    )
    print(f"\nFFI before {cutoff}: {result}")
