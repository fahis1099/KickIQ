import csv
import os

from django.core.management.base import BaseCommand, CommandError
from core.models import Match, Club


class Command(BaseCommand):
    help = "Update existing match results from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the match results CSV file"
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        # ----------------------------------------
        # Check file
        # ----------------------------------------

        if not os.path.isfile(csv_file):
            raise CommandError(
                f"File not found: {csv_file}"
            )

        required_columns = {
            "Season",
            "MatchDate",
            "HomeClub",
            "AwayClub",
            "HomeGoals",
            "AwayGoals",
            "Status",
        }

        updated_count = 0
        not_found_count = 0
        error_count = 0

        errors = []

        seen_matches = set()

        valid_statuses = {
            "COMPLETED",
            "POSTPONED",
            "CANCELLED",
        }

        # ----------------------------------------
        # Open CSV
        # ----------------------------------------

        try:
            with open(
                csv_file,
                mode="r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                # ----------------------------------------
                # Check headers
                # ----------------------------------------

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
                        + ", ".join(
                            sorted(missing_columns)
                        )
                    )

                # ----------------------------------------
                # Process each row
                # ----------------------------------------

                for row_number, row in enumerate(
                    reader,
                    start=2
                ):

                    season = row["Season"].strip()
                    date_value = row["MatchDate"].strip()
                    home_name = row["HomeClub"].strip()
                    away_name = row["AwayClub"].strip()
                    home_goals_value = row["HomeGoals"].strip()
                    away_goals_value = row["AwayGoals"].strip()
                    status = row["Status"].strip().upper()

                    # ----------------------------------------
                    # Basic validation
                    # ----------------------------------------

                    if not season:
                        errors.append(
                            f"Row {row_number}: "
                            "Season is empty."
                        )
                        error_count += 1
                        continue

                    if not date_value:
                        errors.append(
                            f"Row {row_number}: "
                            "MatchDate is empty."
                        )
                        error_count += 1
                        continue

                    if not home_name:
                        errors.append(
                            f"Row {row_number}: "
                            "HomeClub is empty."
                        )
                        error_count += 1
                        continue

                    if not away_name:
                        errors.append(
                            f"Row {row_number}: "
                            "AwayClub is empty."
                        )
                        error_count += 1
                        continue

                    if (
                        home_name.lower()
                        == away_name.lower()
                    ):
                        errors.append(
                            f"Row {row_number}: "
                            f"HomeClub and AwayClub "
                            f"cannot be the same."
                        )
                        error_count += 1
                        continue

                    # ----------------------------------------
                    # Validate status
                    # ----------------------------------------

                    if status not in valid_statuses:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid Status '{status}'. "
                            f"Use COMPLETED, POSTPONED "
                            f"or CANCELLED."
                        )
                        error_count += 1
                        continue

                    # ----------------------------------------
                    # Validate date
                    # ----------------------------------------

                    try:
                        from datetime import datetime

                        match_date = datetime.strptime(
                            date_value,
                            "%Y-%m-%d"
                        ).date()

                    except ValueError:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid MatchDate "
                            f"'{date_value}'. "
                            f"Expected YYYY-MM-DD."
                        )
                        error_count += 1
                        continue

                    # ----------------------------------------
                    # Validate goals
                    # ----------------------------------------

                    home_goals = None
                    away_goals = None

                    if status == "COMPLETED":

                        if (
                            not home_goals_value
                            or not away_goals_value
                        ):
                            errors.append(
                                f"Row {row_number}: "
                                "Completed match must "
                                "have both HomeGoals "
                                "and AwayGoals."
                            )
                            error_count += 1
                            continue

                        try:
                            home_goals = int(
                                home_goals_value
                            )
                            away_goals = int(
                                away_goals_value
                            )

                            if (
                                home_goals < 0
                                or away_goals < 0
                            ):
                                raise ValueError

                        except ValueError:
                            errors.append(
                                f"Row {row_number}: "
                                "Goals must be "
                                "non-negative integers."
                            )
                            error_count += 1
                            continue

                    else:
                        # Postponed/cancelled matches
                        # don't require a score.
                        if (
                            home_goals_value
                            or away_goals_value
                        ):
                            errors.append(
                                f"Row {row_number}: "
                                f"{status} match should "
                                "not contain a score."
                            )
                            error_count += 1
                            continue

                    # ----------------------------------------
                    # Find clubs
                    # ----------------------------------------

                    home_club = Club.objects.filter(
                        name__iexact=home_name
                    ).first()

                    if not home_club:
                        errors.append(
                            f"Row {row_number}: "
                            f"Home club '{home_name}' "
                            "does not exist."
                        )
                        error_count += 1
                        continue

                    away_club = Club.objects.filter(
                        name__iexact=away_name
                    ).first()

                    if not away_club:
                        errors.append(
                            f"Row {row_number}: "
                            f"Away club '{away_name}' "
                            "does not exist."
                        )
                        error_count += 1
                        continue

                    # ----------------------------------------
                    # Check duplicate rows in CSV
                    # ----------------------------------------

                    match_key = (
                        season.lower(),
                        match_date,
                        home_club.id,
                        away_club.id,
                    )

                    if match_key in seen_matches:
                        errors.append(
                            f"Row {row_number}: "
                            f"Duplicate match in CSV: "
                            f"{home_name} vs "
                            f"{away_name} "
                            f"({season})."
                        )
                        error_count += 1
                        continue

                    seen_matches.add(match_key)

                    # ----------------------------------------
                    # Find existing match
                    # ----------------------------------------

                    match = Match.objects.filter(
                        season=season,
                        match_date=match_date,
                        home_club=home_club,
                        away_club=away_club,
                    ).first()

                    # IMPORTANT:
                    # This command NEVER creates a new match.
                    if not match:
                        not_found_count += 1

                        errors.append(
                            f"Row {row_number}: "
                            f"Match not found: "
                            f"{home_name} vs "
                            f"{away_name} "
                            f"({season}, {date_value})."
                        )

                        continue

                    # ----------------------------------------
                    # Update existing match
                    # ----------------------------------------

                    try:
                        match.home_goals = home_goals
                        match.away_goals = away_goals
                        match.status = status

                        match.save()

                        updated_count += 1

                    except Exception as e:
                        error_count += 1

                        errors.append(
                            f"Row {row_number}: "
                            f"Could not update "
                            f"{home_name} vs "
                            f"{away_name}: {e}"
                        )

        except UnicodeDecodeError:
            raise CommandError(
                "Could not read the CSV as UTF-8."
            )

        # ----------------------------------------
        # Final report
        # ----------------------------------------

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "========== MATCH RESULT UPDATE =========="
            )
        )

        self.stdout.write(
            f"Updated matches : {updated_count}"
        )

        self.stdout.write(
            f"Not found       : {not_found_count}"
        )

        self.stdout.write(
            f"Errors          : {error_count}"
        )

        # ----------------------------------------
        # Display errors
        # ----------------------------------------

        if errors:

            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR("DETAILS:")
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
                    "All match results updated successfully."
                )
            )