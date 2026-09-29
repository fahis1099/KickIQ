import csv
import io
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Player


class Command(BaseCommand):
    help = "Update preferred foot for existing players from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to the player CSV file.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        self.stdout.write(
            self.style.SUCCESS(
                "KickIQ Player Preferred Foot Update"
            )
        )
        self.stdout.write(f"File: {file_path}")

        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"File not found: {file_path}"
                )
            )
            return

        # ---------------------------------------------------------
        # Read CSV with UTF-8 first, then CP1252 fallback
        # ---------------------------------------------------------
        try:
            raw_data = file_path.read_bytes()

            try:
                text = raw_data.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw_data.decode("cp1252")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Unable to read CSV: {e}"
                )
            )
            return

        reader = csv.DictReader(io.StringIO(text))

        required_columns = {
            "PlayerName",
            "PreferredFoot",
        }

        if not reader.fieldnames:
            self.stdout.write(
                self.style.ERROR("CSV has no header row.")
            )
            return

        missing_columns = required_columns - set(reader.fieldnames)

        if missing_columns:
            self.stdout.write(
                self.style.ERROR(
                    "Missing required column(s): "
                    + ", ".join(sorted(missing_columns))
                )
            )
            return

        # ---------------------------------------------------------
        # Read and validate CSV
        # ---------------------------------------------------------
        valid_feet = {"Right", "Left", "Both"}

        rows = []
        csv_names = set()

        for row_number, row in enumerate(reader, start=2):
            player_name = (row.get("PlayerName") or "").strip()
            preferred_foot = (row.get("PreferredFoot") or "").strip()

            if not player_name:
                self.stdout.write(
                    self.style.WARNING(
                        f"Row {row_number}: PlayerName is empty. Skipping."
                    )
                )
                continue

            if preferred_foot not in valid_feet:
                self.stdout.write(
                    self.style.ERROR(
                        f"Row {row_number}: Invalid PreferredFoot "
                        f"'{preferred_foot}' for {player_name}. "
                        f"Expected Right, Left, or Both."
                    )
                )
                continue

            rows.append(
                {
                    "row_number": row_number,
                    "player_name": player_name,
                    "preferred_foot": preferred_foot,
                }
            )

            csv_names.add(player_name)

        self.stdout.write(
            f"Players in CSV: {len(rows)}"
        )

        # ---------------------------------------------------------
        # Update existing players only
        # ---------------------------------------------------------
        updated = 0
        unchanged = 0
        not_found = []

        with transaction.atomic():

            for item in rows:
                player_name = item["player_name"]
                preferred_foot = item["preferred_foot"]

                try:
                    player = Player.objects.get(
                        name__iexact=player_name
                    )
                except Player.DoesNotExist:
                    not_found.append(
                        (
                            item["row_number"],
                            player_name,
                            "Player not found",
                        )
                    )
                    continue
                except Player.MultipleObjectsReturned:
                    not_found.append(
                        (
                            item["row_number"],
                            player_name,
                            "Multiple players found",
                        )
                    )
                    continue

                if player.preferred_foot == preferred_foot:
                    unchanged += 1
                    continue

                player.preferred_foot = preferred_foot
                player.save(
                    update_fields=["preferred_foot"]
                )

                updated += 1

        # ---------------------------------------------------------
        # Find database players missing from CSV
        # ---------------------------------------------------------
        database_names = set(
            Player.objects.values_list("name", flat=True)
        )

        missing_from_csv = sorted(
            database_names - csv_names
        )

        # ---------------------------------------------------------
        # Summary
        # ---------------------------------------------------------
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Preferred foot update completed."
            )
        )

        self.stdout.write(
            f"Players updated: {updated}"
        )

        self.stdout.write(
            f"Players already correct: {unchanged}"
        )

        self.stdout.write(
            f"Players not found: {len(not_found)}"
        )

        self.stdout.write(
            f"Database players missing from CSV: "
            f"{len(missing_from_csv)}"
        )

        if not_found:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Players not found / ambiguous:"
                )
            )

            for row_number, name, reason in not_found:
                self.stdout.write(
                    f"  Row {row_number}: {name} - {reason}"
                )

        if missing_from_csv:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Database players missing from CSV:"
                )
            )

            for name in missing_from_csv:
                self.stdout.write(
                    f"  {name}"
                )

        # ---------------------------------------------------------
        # Final database count
        # ---------------------------------------------------------
        foot_counts = {
            "Right": Player.objects.filter(
                preferred_foot="Right"
            ).count(),
            "Left": Player.objects.filter(
                preferred_foot="Left"
            ).count(),
            "Both": Player.objects.filter(
                preferred_foot="Both"
            ).count(),
        }

        self.stdout.write("")
        self.stdout.write("Database preferred-foot counts:")

        for foot, count in foot_counts.items():
            self.stdout.write(
                f"  {foot}: {count}"
            )

        self.stdout.write(
            f"  Total: {sum(foot_counts.values())}"
        )