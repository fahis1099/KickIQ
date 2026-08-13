import csv
import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from core.models import Match, Club


class Command(BaseCommand):
    help = "Validate and import matches from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the matches CSV file"
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        if not os.path.isfile(csv_file):
            raise CommandError(f"File not found: {csv_file}")

        required_columns = {
            "Season",
            "Competition",
            "MatchDate",
            "HomeClub",
            "AwayClub",
            "HomeGoals",
            "AwayGoals",
            "Status",
        }

        created_count = 0
        updated_count = 0
        errors = []

        seen_matches = set()

        valid_statuses = {
            "UPCOMING",
            "COMPLETED",
            "POSTPONED",
            "CANCELLED",
        }

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
                    season = row["Season"].strip()
                    competition = row["Competition"].strip()
                    date_value = row["MatchDate"].strip()
                    home_name = row["HomeClub"].strip()
                    away_name = row["AwayClub"].strip()
                    home_goals_value = row["HomeGoals"].strip()
                    away_goals_value = row["AwayGoals"].strip()
                    status = row["Status"].strip().upper()

                    # -----------------------------
                    # Basic validation
                    # -----------------------------

                    if not season:
                        errors.append(
                            f"Row {row_number}: Season is empty"
                        )
                        continue

                    if not competition:
                        errors.append(
                            f"Row {row_number}: Competition is empty"
                        )
                        continue

                    if not date_value:
                        errors.append(
                            f"Row {row_number}: MatchDate is empty"
                        )
                        continue

                    if not home_name or not away_name:
                        errors.append(
                            f"Row {row_number}: "
                            "HomeClub or AwayClub is empty"
                        )
                        continue

                    if home_name.lower() == away_name.lower():
                        errors.append(
                            f"Row {row_number}: "
                            f"HomeClub and AwayClub are the same "
                            f"({home_name})"
                        )
                        continue

                    if status not in valid_statuses:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid Status '{status}'"
                        )
                        continue

                    # -----------------------------
                    # Validate date
                    # -----------------------------

                    try:
                        match_date = datetime.strptime(
                            date_value,
                            "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid MatchDate '{date_value}'. "
                            "Expected YYYY-MM-DD."
                        )
                        continue

                    # -----------------------------
                    # Validate goals
                    # -----------------------------

                    home_goals = None
                    away_goals = None

                    if status == "COMPLETED":
                        if (
                            not home_goals_value
                            or not away_goals_value
                        ):
                            errors.append(
                                f"Row {row_number}: "
                                "Completed match must have "
                                "HomeGoals and AwayGoals."
                            )
                            continue

                        try:
                            home_goals = int(home_goals_value)
                            away_goals = int(away_goals_value)

                            if home_goals < 0 or away_goals < 0:
                                raise ValueError

                        except ValueError:
                            errors.append(
                                f"Row {row_number}: "
                                "Goals must be non-negative integers."
                            )
                            continue

                    else:
                        # Upcoming/postponed/cancelled matches
                        # should not have a score yet.
                        if home_goals_value or away_goals_value:
                            errors.append(
                                f"Row {row_number}: "
                                f"{status} match should not have "
                                "HomeGoals/AwayGoals."
                            )
                            continue

                    # -----------------------------
                    # Find clubs
                    # -----------------------------

                    home_club = Club.objects.filter(
                        name__iexact=home_name
                    ).first()

                    if not home_club:
                        errors.append(
                            f"Row {row_number}: "
                            f"Home club '{home_name}' "
                            "not found in Club table."
                        )
                        continue

                    away_club = Club.objects.filter(
                        name__iexact=away_name
                    ).first()

                    if not away_club:
                        errors.append(
                            f"Row {row_number}: "
                            f"Away club '{away_name}' "
                            "not found in Club table."
                        )
                        continue

                    # -----------------------------
                    # Duplicate check in CSV
                    # -----------------------------

                    match_key = (
                        season.lower(),
                        match_date,
                        home_club.id,
                        away_club.id,
                    )

                    if match_key in seen_matches:
                        errors.append(
                            f"Row {row_number}: "
                            f"Duplicate match "
                            f"{home_name} vs {away_name} "
                            f"({season})"
                        )
                        continue

                    seen_matches.add(match_key)

                    # -----------------------------
                    # Create / update
                    # -----------------------------

                    try:
                        match = Match.objects.filter(
                            season=season,
                            match_date=match_date,
                            home_club=home_club,
                            away_club=away_club,
                        ).first()

                        if match:
                            match.competition = competition

                            # Update score/status from CSV.
                            match.home_goals = home_goals
                            match.away_goals = away_goals
                            match.status = status

                            match.save()

                            updated_count += 1

                        else:
                            Match.objects.create(
                                season=season,
                                competition=competition,
                                match_date=match_date,
                                home_club=home_club,
                                away_club=away_club,
                                home_goals=home_goals,
                                away_goals=away_goals,
                                status=status,
                            )

                            created_count += 1

                    except Exception as e:
                        errors.append(
                            f"Row {row_number}: "
                            f"Could not import match "
                            f"{home_name} vs {away_name}: {e}"
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
                "========== MATCH IMPORT REPORT =========="
            )
        )

        self.stdout.write(
            f"Created matches : {created_count}"
        )

        self.stdout.write(
            f"Updated matches : {updated_count}"
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
                    "All matches imported successfully."
                )
            )