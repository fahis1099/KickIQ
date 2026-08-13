import csv
import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from core.models import Player, Club


class Command(BaseCommand):
    help = "Validate and import players from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the players CSV file"
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        if not os.path.isfile(csv_file):
            raise CommandError(f"File not found: {csv_file}")

        required_columns = {
            "PlayerName",
            "ClubName",
            "Position",
            "Nationality",
            "DateOfBirth",
            "Height",
            "JerseyNumber",
            "PhotoPath",
            "IsActive",
        }

        created_count = 0
        updated_count = 0
        errors = []

        seen_players = set()

        valid_positions = {"GK", "DF", "MF", "FW"}

        try:
            with open(
                csv_file,
                mode="r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                if not reader.fieldnames:
                    raise CommandError(
                        "CSV file has no header row."
                    )

                missing_columns = (
                    required_columns
                    - set(reader.fieldnames)
                )

                if missing_columns:
                    raise CommandError(
                        "Missing columns: "
                        + ", ".join(sorted(missing_columns))
                    )

                for row_number, row in enumerate(
                    reader,
                    start=2
                ):
                    # -----------------------------
                    # Read and clean values
                    # -----------------------------

                    player_name = row["PlayerName"].strip()
                    club_name = row["ClubName"].strip()
                    position = row["Position"].strip().upper()
                    nationality = row["Nationality"].strip()
                    dob_value = row["DateOfBirth"].strip()
                    height_value = row["Height"].strip()
                    jersey_value = row["JerseyNumber"].strip()
                    photo_path = row["PhotoPath"].strip()
                    is_active_value = row["IsActive"].strip().upper()

                    # -----------------------------
                    # Basic validation
                    # -----------------------------

                    if not player_name:
                        errors.append(
                            f"Row {row_number}: PlayerName is empty"
                        )
                        continue

                    if not club_name:
                        errors.append(
                            f"Row {row_number}: ClubName is empty"
                        )
                        continue

                    if position not in valid_positions:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid position '{position}' "
                            f"for {player_name}"
                        )
                        continue

                    if not nationality:
                        errors.append(
                            f"Row {row_number}: "
                            f"Nationality is empty "
                            f"for {player_name}"
                        )
                        continue

                    if not dob_value:
                        errors.append(
                            f"Row {row_number}: "
                            f"DateOfBirth is empty "
                            f"for {player_name}"
                        )
                        continue

                    if not height_value:
                        errors.append(
                            f"Row {row_number}: "
                            f"Height is empty "
                            f"for {player_name}"
                        )
                        continue

                    if not jersey_value:
                        errors.append(
                            f"Row {row_number}: "
                            f"JerseyNumber is empty "
                            f"for {player_name}"
                        )
                        continue

                    if not photo_path:
                        errors.append(
                            f"Row {row_number}: "
                            f"PhotoPath is empty "
                            f"for {player_name}"
                        )
                        continue

                    if is_active_value not in {"TRUE", "FALSE"}:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid IsActive value "
                            f"'{is_active_value}' "
                            f"for {player_name}"
                        )
                        continue

                    # -----------------------------
                    # Validate date
                    # -----------------------------

                    try:
                        date_of_birth = datetime.strptime(
                            dob_value,
                            "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid DateOfBirth "
                            f"'{dob_value}' "
                            f"for {player_name}. "
                            f"Expected YYYY-MM-DD."
                        )
                        continue

                    # -----------------------------
                    # Validate height
                    # -----------------------------

                    try:
                        height = float(height_value)

                        if height <= 0:
                            raise ValueError

                    except ValueError:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid Height "
                            f"'{height_value}' "
                            f"for {player_name}"
                        )
                        continue

                    # -----------------------------
                    # Validate jersey number
                    # -----------------------------

                    try:
                        jersey_number = int(jersey_value)

                        if jersey_number < 0:
                            raise ValueError

                    except ValueError:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid JerseyNumber "
                            f"'{jersey_value}' "
                            f"for {player_name}"
                        )
                        continue

                    # -----------------------------
                    # Duplicate check in CSV
                    # -----------------------------

                    player_key = player_name.lower()

                    if player_key in seen_players:
                        errors.append(
                            f"Row {row_number}: "
                            f"Duplicate player "
                            f"'{player_name}'"
                        )
                        continue

                    seen_players.add(player_key)

                    # -----------------------------
                    # Find club
                    # -----------------------------

                    club = Club.objects.filter(
                        name__iexact=club_name
                    ).first()

                    if not club:
                        errors.append(
                            f"Row {row_number}: "
                            f"Club '{club_name}' "
                            f"not found for "
                            f"player '{player_name}'"
                        )
                        continue

                    is_active = (
                        is_active_value == "TRUE"
                    )

                    # -----------------------------
                    # Create / Update Player
                    # -----------------------------

                    try:
                        player = Player.objects.filter(
                            name__iexact=player_name
                        ).first()

                        if player:
                            player.name = player_name
                            player.current_club = club
                            player.position = position
                            player.nationality = nationality
                            player.date_of_birth = date_of_birth
                            player.height = height
                            player.jersey_number = jersey_number
                            player.photo_path = photo_path
                            player.is_active = is_active

                            player.save()

                            updated_count += 1

                        else:
                            Player.objects.create(
                                name=player_name,
                                current_club=club,
                                position=position,
                                nationality=nationality,
                                date_of_birth=date_of_birth,
                                height=height,
                                jersey_number=jersey_number,
                                photo_path=photo_path,
                                is_active=is_active,
                            )

                            created_count += 1

                    except Exception as e:
                        errors.append(
                            f"Row {row_number}: "
                            f"Could not import "
                            f"'{player_name}': {e}"
                        )

        except UnicodeDecodeError:
            raise CommandError(
                "Could not read the CSV as UTF-8."
            )

        # -----------------------------
        # Final report
        # -----------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "========== PLAYER IMPORT REPORT =========="
            )
        )

        self.stdout.write(
            f"Created players : {created_count}"
        )

        self.stdout.write(
            f"Updated players : {updated_count}"
        )

        self.stdout.write(
            f"Errors          : {len(errors)}"
        )

        if errors:
            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR("ERRORS:")
            )

            for error in errors:
                self.stdout.write(
                    self.style.ERROR(
                        f" - {error}"
                    )
                )

        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "All players imported successfully."
                )
            )