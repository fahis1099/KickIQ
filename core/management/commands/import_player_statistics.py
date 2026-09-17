import csv
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand

from core.models import (
    Player,
    Club,
    Match,
    PlayerStatistics,
)


class Command(BaseCommand):

    help = "Import player match statistics from CSV"

    def add_arguments(self, parser):

        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to the player statistics CSV file",
        )

    def handle(self, *args, **options):

        file_path = Path(options["file"])

        # =====================================================
        # CHECK FILE
        # =====================================================

        if not file_path.exists():

            self.stdout.write(
                self.style.ERROR(
                    f"CSV file not found: {file_path}"
                )
            )

            return

        created_count = 0
        updated_count = 0
        error_count = 0

        self.stdout.write("")

        self.stdout.write(
            self.style.WARNING(
                "=============================================="
            )
        )

        self.stdout.write(
            self.style.WARNING(
                "KickIQ Player Statistics Import"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                "=============================================="
            )
        )

        self.stdout.write(
            f"File: {file_path}"
        )

        self.stdout.write("")

        # =====================================================
        # OPEN CSV
        # =====================================================

        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as csvfile:

            reader = csv.DictReader(csvfile)

            # =================================================
            # REQUIRED COLUMNS
            # =================================================

            required_columns = [

                "PlayerName",
                "ClubName",
                "MatchDate",
                "HomeClub",
                "AwayClub",

                "Started",
                "MinutesPlayed",

                "Goals",
                "Assists",

                "PenaltyGoals",
                "PenaltyAttempts",

                "Shots",
                "ShotsOnTarget",

                "PassesCompleted",
                "PassAttempted",

                "KeyPasses",
                "Crosses",

                "DribbleSuccess",
                "DribblesAttempted",

                "TacklesWon",
                "Interceptions",

                "YellowCards",
                "RedCards",

                "FoulsCommitted",
                "FoulsDrawn",

                "Offsides",
                "OwnGoals",

                "PenaltyWon",
                "PenaltyConceded",

                "ShotsFaced",
                "Saves",

                "PenaltyFaced",
                "PenaltySaved",

                "Rating",
            ]

            missing_columns = [
                column
                for column in required_columns
                if column not in reader.fieldnames
            ]

            if missing_columns:

                self.stdout.write(
                    self.style.ERROR(
                        "CSV is missing required columns:"
                    )
                )

                for column in missing_columns:

                    self.stdout.write(
                        f"  - {column}"
                    )

                return

            # =================================================
            # PROCESS EACH ROW
            # =================================================

            for row_number, row in enumerate(
                reader,
                start=2
            ):

                try:

                    # =========================================
                    # BASIC VALUES
                    # =========================================

                    player_name = (
                        row["PlayerName"]
                        .strip()
                    )

                    club_name = (
                        row["ClubName"]
                        .strip()
                    )

                    match_date = datetime.strptime(
                        row["MatchDate"].strip(),
                        "%Y-%m-%d"
                    ).date()

                    home_club_name = (
                        row["HomeClub"]
                        .strip()
                    )

                    away_club_name = (
                        row["AwayClub"]
                        .strip()
                    )

                    # =========================================
                    # FIND PLAYER
                    # =========================================

                    try:

                        player = Player.objects.get(
                            name__iexact=player_name
                        )

                    except Player.DoesNotExist:

                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_number}: "
                                f"Player not found: "
                                f"{player_name}"
                            )
                        )

                        error_count += 1

                        continue

                    # =========================================
                    # FIND CLUB
                    # =========================================

                    try:

                        club = Club.objects.get(
                            name__iexact=club_name
                        )

                    except Club.DoesNotExist:

                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_number}: "
                                f"Club not found: "
                                f"{club_name}"
                            )
                        )

                        error_count += 1

                        continue

                    # =========================================
                    # FIND HOME CLUB
                    # =========================================

                    try:

                        home_club = Club.objects.get(
                            name__iexact=home_club_name
                        )

                    except Club.DoesNotExist:

                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_number}: "
                                f"Home club not found: "
                                f"{home_club_name}"
                            )
                        )

                        error_count += 1

                        continue

                    # =========================================
                    # FIND AWAY CLUB
                    # =========================================

                    try:

                        away_club = Club.objects.get(
                            name__iexact=away_club_name
                        )

                    except Club.DoesNotExist:

                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_number}: "
                                f"Away club not found: "
                                f"{away_club_name}"
                            )
                        )

                        error_count += 1

                        continue

                    # =========================================
                    # FIND MATCH
                    # =========================================

                    try:

                        match = Match.objects.get(
                            match_date=match_date,
                            home_club=home_club,
                            away_club=away_club,
                        )

                    except Match.DoesNotExist:

                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_number}: "
                                f"Match not found: "
                                f"{home_club_name} vs "
                                f"{away_club_name} "
                                f"({match_date})"
                            )
                        )

                        error_count += 1

                        continue

                    # =========================================
                    # HELPER FUNCTIONS
                    # =========================================

                    def int_value(
                        field,
                        default=0
                    ):

                        value = row.get(
                            field,
                            ""
                        )

                        if (
                            value is None
                            or value.strip() == ""
                        ):

                            return default

                        return int(
                            float(value)
                        )

                    def nullable_int(field):

                        value = row.get(
                            field,
                            ""
                        )

                        if (
                            value is None
                            or value.strip() == ""
                        ):

                            return None

                        return int(
                            float(value)
                        )

                    def bool_value(field):

                        value = row.get(
                            field,
                            ""
                        ).strip().lower()

                        return value in (
                            "true",
                            "1",
                            "yes",
                            "y",
                        )

                    def decimal_value(field):

                        value = row.get(
                            field,
                            ""
                        )

                        if (
                            value is None
                            or value.strip() == ""
                        ):

                            return None

                        return value.strip()

                    # =========================================
                    # VALIDATE VALUES
                    # =========================================

                    minutes = int_value(
                        "MinutesPlayed"
                    )

                    shots = int_value(
                        "Shots"
                    )

                    shots_on_target = int_value(
                        "ShotsOnTarget"
                    )

                    passes_completed = nullable_int(
                        "PassesCompleted"
                    )

                    passes_attempted = nullable_int(
                        "PassAttempted"
                    )

                    dribbles_completed = nullable_int(
                        "DribbleSuccess"
                    )

                    dribbles_attempted = nullable_int(
                        "DribblesAttempted"
                    )

                    penalty_goals = int_value(
                        "PenaltyGoals"
                    )

                    penalty_attempts = int_value(
                        "PenaltyAttempts"
                    )

                    penalty_saved = int_value(
                        "PenaltySaved"
                    )

                    penalty_faced = int_value(
                        "PenaltyFaced"
                    )

                    # -----------------------------------------
                    # MINUTES
                    # -----------------------------------------

                    if minutes < 0 or minutes > 90:

                        raise ValueError(
                            f"Invalid minutes: {minutes}"
                        )

                    # -----------------------------------------
                    # SHOTS
                    # -----------------------------------------

                    if shots_on_target > shots:

                        raise ValueError(
                            f"Shots on target "
                            f"({shots_on_target}) "
                            f"cannot exceed shots "
                            f"({shots})"
                        )

                    # -----------------------------------------
                    # PASSING
                    # -----------------------------------------

                    if (
                        passes_completed is not None
                        and passes_attempted is not None
                        and passes_completed > passes_attempted
                    ):

                        raise ValueError(
                            f"Passes completed "
                            f"({passes_completed}) "
                            f"cannot exceed passes "
                            f"attempted "
                            f"({passes_attempted})"
                        )

                    # -----------------------------------------
                    # DRIBBLING
                    # -----------------------------------------

                    if (
                        dribbles_completed is not None
                        and dribbles_attempted is not None
                        and dribbles_completed > dribbles_attempted
                    ):

                        raise ValueError(
                            f"Dribble success "
                            f"({dribbles_completed}) "
                            f"cannot exceed dribbles "
                            f"attempted "
                            f"({dribbles_attempted})"
                        )

                    # -----------------------------------------
                    # PENALTIES
                    # -----------------------------------------

                    if penalty_goals > penalty_attempts:

                        raise ValueError(
                            f"Penalty goals "
                            f"({penalty_goals}) "
                            f"cannot exceed penalty attempts "
                            f"({penalty_attempts})"
                        )

                    if penalty_saved > penalty_faced:

                        raise ValueError(
                            f"Penalty saved "
                            f"({penalty_saved}) "
                            f"cannot exceed penalty faced "
                            f"({penalty_faced})"
                        )

                    # =========================================
                    # CREATE / UPDATE STATISTICS
                    # =========================================

                    statistics, created = (
                        PlayerStatistics.objects
                        .update_or_create(

                            player=player,

                            match=match,

                            defaults={

                                "club": club,

                                "started": bool_value(
                                    "Started"
                                ),

                                "minutes_played": minutes,

                                "goals": int_value(
                                    "Goals"
                                ),

                                "assists": int_value(
                                    "Assists"
                                ),

                                "penalty_goals":
                                    penalty_goals,

                                "penalty_attempts":
                                    penalty_attempts,

                                "shots": shots,

                                "shots_on_target":
                                    shots_on_target,

                                "passes_completed":
                                    passes_completed,

                                "passes_attempted":
                                    passes_attempted,

                                "key_passes":
                                    nullable_int(
                                        "KeyPasses"
                                    ),

                                "crosses":
                                    int_value(
                                        "Crosses"
                                    ),

                                "dribbles_completed":
                                    dribbles_completed,

                                "dribbles_attempted":
                                    dribbles_attempted,

                                "tackles_won":
                                    int_value(
                                        "TacklesWon"
                                    ),

                                "interceptions":
                                    int_value(
                                        "Interceptions"
                                    ),

                                "yellow_cards":
                                    int_value(
                                        "YellowCards"
                                    ),

                                "red_cards":
                                    int_value(
                                        "RedCards"
                                    ),

                                "fouls_committed":
                                    int_value(
                                        "FoulsCommitted"
                                    ),

                                "fouls_drawn":
                                    int_value(
                                        "FoulsDrawn"
                                    ),

                                "offsides":
                                    int_value(
                                        "Offsides"
                                    ),

                                "own_goals":
                                    int_value(
                                        "OwnGoals"
                                    ),

                                "penalty_won":
                                    int_value(
                                        "PenaltyWon"
                                    ),

                                "penalty_conceded":
                                    int_value(
                                        "PenaltyConceded"
                                    ),

                                "shots_faced":
                                    int_value(
                                        "ShotsFaced"
                                    ),

                                "saves":
                                    int_value(
                                        "Saves"
                                    ),

                                "penalty_faced":
                                    penalty_faced,

                                "penalty_saved":
                                    penalty_saved,

                                "rating":
                                    decimal_value(
                                        "Rating"
                                    ),
                            },
                        )
                    )

                    # =========================================
                    # COUNT RESULT
                    # =========================================

                    if created:

                        created_count += 1

                    else:

                        updated_count += 1

                # =============================================
                # ERROR
                # =============================================

                except Exception as e:

                    error_count += 1

                    self.stdout.write(
                        self.style.ERROR(
                            f"Row {row_number}: {e}"
                        )
                    )

        # =====================================================
        # FINAL SUMMARY
        # =====================================================

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "=============================================="
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Player statistics import completed."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "=============================================="
            )
        )

        self.stdout.write(
            f"Created : {created_count}"
        )

        self.stdout.write(
            f"Updated : {updated_count}"
        )

        self.stdout.write(
            f"Errors  : {error_count}"
        )

        self.stdout.write("")