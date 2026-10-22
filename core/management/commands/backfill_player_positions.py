
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Club, Match, Player, PlayerStatistics


class Command(BaseCommand):
    help = "Backfill only missing PlayerStatistics positions from CSV files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--directory",
            default="dataset/statistics",
            help="Directory containing statistics CSV files.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually update missing positions. Without this, runs a dry-run.",
        )

    def handle(self, *args, **options):
        directory = Path(options["directory"])
        apply_changes = options["apply"]
        valid_positions = {"GK", "DF", "MF", "FW"}

        if not directory.is_dir():
            self.stderr.write(self.style.ERROR(
                f"Directory not found: {directory}"
            ))
            return

        files = sorted(directory.glob("*.csv"))
        if not files:
            self.stderr.write(self.style.ERROR(
                f"No CSV files found in {directory}"
            ))
            return

        # Collect proposed positions without modifying the database.
        proposals = defaultdict(set)
        errors = 0
        rows_read = 0

        for file_path in files:
            self.stdout.write(f"Reading: {file_path.name}")

            try:
                with file_path.open(
    		    "r", encoding="utf-8-sig", errors="replace", newline=""
		) as csvfile:
                    reader = csv.DictReader(csvfile)

                    required = {
                        "PlayerName",
                        "MatchDate",
                        "HomeClub",
                        "AwayClub",
                        "Position",
                    }

                    missing = required - set(reader.fieldnames or [])
                    if missing:
                        self.stderr.write(self.style.ERROR(
                            f"{file_path.name}: missing columns "
                            f"{', '.join(sorted(missing))}"
                        ))
                        errors += 1
                        continue

                    for row_number, row in enumerate(reader, start=2):
                        rows_read += 1

                        try:
                            player_name = row["PlayerName"].strip()
                            home_name = row["HomeClub"].strip()
                            away_name = row["AwayClub"].strip()
                            position = row["Position"].strip().upper()

                            if position not in valid_positions:
                                raise ValueError(
                                    f"Invalid position {position!r}"
                                )

                            match_date = datetime.strptime(
                                row["MatchDate"].strip(), "%Y-%m-%d"
                            ).date()

                            players = Player.objects.filter(
                                name__iexact=player_name
                            )
                            if players.count() != 1:
                                raise ValueError(
                                    f"Player match is missing or ambiguous: "
                                    f"{player_name}"
                                )
                            player = players.first()

                            home_clubs = Club.objects.filter(
                                name__iexact=home_name
                            )
                            away_clubs = Club.objects.filter(
                                name__iexact=away_name
                            )

                            if home_clubs.count() != 1:
                                raise ValueError(
                                    f"Home club missing or ambiguous: {home_name}"
                                )
                            if away_clubs.count() != 1:
                                raise ValueError(
                                    f"Away club missing or ambiguous: {away_name}"
                                )

                            matches = Match.objects.filter(
                                match_date=match_date,
                                home_club=home_clubs.first(),
                                away_club=away_clubs.first(),
                            )

                            if matches.count() != 1:
                                raise ValueError(
                                    f"Match missing or ambiguous: "
                                    f"{home_name} vs {away_name} ({match_date})"
                                )

                            stat = PlayerStatistics.objects.filter(
                                player=player,
                                match=matches.first(),
                            ).first()

                            if stat is None:
                                # Never create statistics from this command.
                                continue

                            if stat.position:
                                # Preserve all existing populated positions.
                                continue

                            proposals[stat.pk].add(position)

                        except Exception as exc:
                            errors += 1
                            self.stderr.write(
                                f"{file_path.name}, row {row_number}: {exc}"
                            )

            except (OSError, csv.Error) as exc:
                errors += 1
                self.stderr.write(self.style.ERROR(
                    f"Could not read {file_path.name}: {exc}"
                ))

        # Conflicting source positions must never be applied automatically.
        conflicts = {
            stat_id: positions
            for stat_id, positions in proposals.items()
            if len(positions) > 1
        }

        safe_updates = {
            stat_id: next(iter(positions))
            for stat_id, positions in proposals.items()
            if len(positions) == 1
        }

        self.stdout.write("")
        self.stdout.write(f"CSV files scanned: {len(files)}")
        self.stdout.write(f"CSV rows read: {rows_read}")
        self.stdout.write(f"Missing-position records proposed: {len(proposals)}")
        self.stdout.write(f"Conflicting records skipped: {len(conflicts)}")
        self.stdout.write(f"Errors: {errors}")

        if conflicts:
            for stat_id, positions in list(conflicts.items())[:20]:
                self.stderr.write(
                    f"Conflict for PlayerStatistics ID {stat_id}: "
                    f"{', '.join(sorted(positions))}"
                )

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                "DRY RUN: no database changes were made. "
                "Review the results before using --apply."
            ))
            self.stdout.write(
                f"Records eligible for update: {len(safe_updates)}"
            )
            return

        updated = 0
        skipped = 0

        with transaction.atomic():
            for stat_id, position in safe_updates.items():
                # Recheck the record to avoid overwriting a position
                # populated after the CSV scan.
                changed = PlayerStatistics.objects.filter(
                    pk=stat_id,
                    position__isnull=True,
                ).update(position=position)

                if changed:
                    updated += changed
                    continue

                # Also handle empty-string positions, if present.
                changed = PlayerStatistics.objects.filter(
                    pk=stat_id,
                    position="",
                ).update(position=position)

                if changed:
                    updated += changed
                else:
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Backfill complete. Positions updated: {updated}; "
            f"skipped because already populated or changed: {skipped}."
        ))
