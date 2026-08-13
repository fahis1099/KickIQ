import csv
from datetime import datetime

from django.db import transaction

from core.models import Match, Club


VALID_STATUSES = {
    "COMPLETED",
    "POSTPONED",
    "CANCELLED",
}

REQUIRED_COLUMNS = {
    "Season",
    "MatchDate",
    "HomeClub",
    "AwayClub",
    "HomeGoals",
    "AwayGoals",
    "Status",
}


def update_match_results(csv_file):
    updated_count = 0
    not_found_count = 0
    error_count = 0

    errors = []
    seen_matches = set()

    try:
        reader = csv.DictReader(
            csv_file
        )

        if not reader.fieldnames:
            return {
                "updated": 0,
                "not_found": 0,
                "errors": 1,
                "details": ["CSV file has no header row."],
            }

        missing_columns = (
            REQUIRED_COLUMNS
            - set(reader.fieldnames)
        )

        if missing_columns:
            return {
                "updated": 0,
                "not_found": 0,
                "errors": 1,
                "details": [
                    "Missing columns: "
                    + ", ".join(
                        sorted(missing_columns)
                    )
                ],
            }

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

            # -------------------------
            # Basic validation
            # -------------------------

            if not season:
                errors.append(
                    f"Row {row_number}: Season is empty."
                )
                error_count += 1
                continue

            if not date_value:
                errors.append(
                    f"Row {row_number}: MatchDate is empty."
                )
                error_count += 1
                continue

            if not home_name:
                errors.append(
                    f"Row {row_number}: HomeClub is empty."
                )
                error_count += 1
                continue

            if not away_name:
                errors.append(
                    f"Row {row_number}: AwayClub is empty."
                )
                error_count += 1
                continue

            if home_name.lower() == away_name.lower():
                errors.append(
                    f"Row {row_number}: "
                    "HomeClub and AwayClub cannot be the same."
                )
                error_count += 1
                continue

            # -------------------------
            # Validate status
            # -------------------------

            if status not in VALID_STATUSES:
                errors.append(
                    f"Row {row_number}: "
                    f"Invalid Status '{status}'."
                )
                error_count += 1
                continue

            # -------------------------
            # Validate date
            # -------------------------

            try:
                match_date = datetime.strptime(
                    date_value,
                    "%Y-%m-%d"
                ).date()

            except ValueError:
                errors.append(
                    f"Row {row_number}: "
                    f"Invalid MatchDate '{date_value}'."
                )
                error_count += 1
                continue

            # -------------------------
            # Validate goals
            # -------------------------

            home_goals = None
            away_goals = None

            if status == "COMPLETED":

                if (
                    not home_goals_value
                    or not away_goals_value
                ):
                    errors.append(
                        f"Row {row_number}: "
                        "Completed match must have both goals."
                    )
                    error_count += 1
                    continue

                try:
                    home_goals = int(home_goals_value)
                    away_goals = int(away_goals_value)

                    if (
                        home_goals < 0
                        or away_goals < 0
                    ):
                        raise ValueError

                except ValueError:
                    errors.append(
                        f"Row {row_number}: "
                        "Goals must be non-negative integers."
                    )
                    error_count += 1
                    continue

            else:

                if home_goals_value or away_goals_value:
                    errors.append(
                        f"Row {row_number}: "
                        f"{status} match should not contain a score."
                    )
                    error_count += 1
                    continue

            # -------------------------
            # Find clubs
            # -------------------------

            home_club = Club.objects.filter(
                name__iexact=home_name
            ).first()

            if not home_club:
                errors.append(
                    f"Row {row_number}: "
                    f"Home club '{home_name}' does not exist."
                )
                error_count += 1
                continue

            away_club = Club.objects.filter(
                name__iexact=away_name
            ).first()

            if not away_club:
                errors.append(
                    f"Row {row_number}: "
                    f"Away club '{away_name}' does not exist."
                )
                error_count += 1
                continue

            # -------------------------
            # Duplicate CSV row
            # -------------------------

            match_key = (
                season.lower(),
                match_date,
                home_club.id,
                away_club.id,
            )

            if match_key in seen_matches:
                errors.append(
                    f"Row {row_number}: "
                    f"Duplicate match: "
                    f"{home_name} vs {away_name}."
                )
                error_count += 1
                continue

            seen_matches.add(match_key)

            # -------------------------
            # Find existing match
            # -------------------------

            match = Match.objects.filter(
                season=season,
                match_date=match_date,
                home_club=home_club,
                away_club=away_club,
            ).first()

            if not match:
                not_found_count += 1

                errors.append(
                    f"Row {row_number}: "
                    f"Match not found: "
                    f"{home_name} vs {away_name} "
                    f"({season}, {date_value})."
                )

                continue

            # -------------------------
            # Update
            # -------------------------

            try:
                with transaction.atomic():

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
                    f"{home_name} vs {away_name}: {e}"
                )

    except UnicodeDecodeError:

        return {
            "updated": 0,
            "not_found": 0,
            "errors": 1,
            "details": [
                "Could not read CSV as UTF-8."
            ],
        }

    return {
        "updated": updated_count,
        "not_found": not_found_count,
        "errors": error_count,
        "details": errors,
    }