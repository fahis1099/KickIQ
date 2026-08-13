import csv
import os

from django.core.management.base import BaseCommand, CommandError
from core.models import Club


class Command(BaseCommand):
    help = "Validate and import clubs from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the clubs CSV file"
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        # Check whether the file exists
        if not os.path.isfile(csv_file):
            raise CommandError(
                f"File not found: {csv_file}"
            )

        required_columns = {
            "ClubName",
            "Country",
            "LogoPath",
            "isActive",
        }

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        seen_clubs = set()

        try:
            with open(
                csv_file,
                mode="r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                # Check CSV columns
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
                    club_name = row["ClubName"].strip()
                    country = row["Country"].strip()
                    logo_path = row["LogoPath"].strip()
                    is_active_value = row["isActive"].strip().upper()

                    # -----------------------------
                    # Validation
                    # -----------------------------

                    if not club_name:
                        errors.append(
                            f"Row {row_number}: ClubName is empty"
                        )
                        continue

                    if not country:
                        errors.append(
                            f"Row {row_number}: Country is empty"
                        )
                        continue

                    if not logo_path:
                        errors.append(
                            f"Row {row_number}: LogoPath is empty"
                        )
                        continue

                    if is_active_value not in {"TRUE", "FALSE"}:
                        errors.append(
                            f"Row {row_number}: "
                            f"Invalid isActive value "
                            f"'{is_active_value}'"
                        )
                        continue

                    # Check duplicate within CSV
                    club_key = club_name.lower()

                    if club_key in seen_clubs:
                        errors.append(
                            f"Row {row_number}: "
                            f"Duplicate club '{club_name}'"
                        )
                        continue

                    seen_clubs.add(club_key)

                    is_active = (
                        is_active_value == "TRUE"
                    )

                    # -----------------------------
                    # Create / Update
                    # -----------------------------

                    try:
                        club = Club.objects.filter(
                            name__iexact=club_name
                        ).first()

                        if club:
                            # Update existing club
                            club.name = club_name
                            club.country = country
                            club.logo_path = logo_path

                            # IMPORTANT:
                            # Do not overwrite is_active
                            # for an existing club.
                            club.save()

                            updated_count += 1

                        else:
                            # Create new club
                            Club.objects.create(
                                name=club_name,
                                country=country,
                                logo_path=logo_path,
                                is_active=is_active,
                            )

                            created_count += 1

                    except Exception as e:
                        errors.append(
                            f"Row {row_number}: "
                            f"Could not import '{club_name}': {e}"
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
                "========== CLUB IMPORT REPORT =========="
            )
        )

        self.stdout.write(
            f"Created clubs : {created_count}"
        )

        self.stdout.write(
            f"Updated clubs : {updated_count}"
        )

        self.stdout.write(
            f"Skipped rows  : {skipped_count}"
        )

        self.stdout.write(
            f"Errors        : {len(errors)}"
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
                    "All clubs imported successfully."
                )
            )