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
            default="dataset/manchester_city_2025-26.csv",
            help="Path to the player statistics CSV file",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"CSV file not found: {file_path}"
                )
            )
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        self.stdout.write(
            self.style.WARNING(
                f"Importing player statistics from: {file_path}"
            )
        )

        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as csvfile:

            reader = csv.DictReader(csvfile)

            for row_number, row in enumerate(reader, start=2):

                try:
                    # --------------------------------------------------
                    # Read basic CSV values
                    # --------------------------------------------------

                    player_name = row["PlayerName"].strip()
                    club_name = row["ClubName"].strip()

                    match_date = datetime.strptime(
                        row["MatchDate"].strip(),
                        "%Y-%m-%d"
                    ).date()

                    home_club_name = row["HomeClub"].strip()
                    away_club_name = row["AwayClub"].strip()

                    # --------------------------------------------------
                    # Find Player
                    # --------------------------------------------------

                    try:
                        player = Player.objects.get(
                            name__iexact=player_name
                        )
                    except Player.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_number}: "
                                f"Player not found: {player_name}"
                            )
                        )
                        error_count += 1
                        continue

                    # --------------------------------------------------
                    # Find Club represented in this match
                    # --------------------------------------------------

                    try:
                        club = Club.objects.get(
                            name__iexact=club_name
                        )
                    except Club.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_number}: "
                                f"Club not found: {club_name}"
                            )
                        )
                        error_count += 1
                        continue

                    # --------------------------------------------------
                    # Find Home and Away clubs
                    # --------------------------------------------------

                    try:
                        home_club = Club.objects.get(
                            name__iexact=home_club_name
                        )
                        away_club = Club.objects.get(
                            name__iexact=away_club_name
                        )
                    except Club.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_number}: "
                                f"Match club not found: "
                                f"{home_club_name} vs {away_club_name}"
                            )
                        )
                        error_count += 1
                        continue

                    # --------------------------------------------------
                    # Find Match
                    # --------------------------------------------------

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

                    # --------------------------------------------------
                    # Helper functions
                    # --------------------------------------------------

                    def int_value(field, default=0):
                        value = row.get(field, "")

                        if value is None or value.strip() == "":
                            return default

                        return int(float(value))

                    def nullable_int(field):
                        value = row.get(field, "")

                        if value is None or value.strip() == "":
                            return None

                        return int(float(value))

                    def bool_value(field):
                        value = row.get(field, "").strip().lower()

                        return value in (
                            "true",
                            "1",
                            "yes",
                            "y",
                        )

                    def decimal_value(field):
                        value = row.get(field, "")

                        if value is None or value.strip() == "":
                            return None

                        return value.strip()

                    # --------------------------------------------------
                    # Create or update PlayerStatistics
                    # --------------------------------------------------

                    statistics, created = (
                        PlayerStatistics.objects.update_or_create(
                            player=player,
                            match=match,
                            defaults={
                                "club": club,

                                "started": bool_value(
                                    "Started"
                                ),

                                "minutes_played": int_value(
                                    "MinutesPlayed"
                                ),

                                "goals": int_value(
                                    "Goals"
                                ),

                                "assists": int_value(
                                    "Assists"
                                ),

                                "penalty_goals": int_value(
                                    "PenaltyGoals"
                                ),

                                "penalty_attempts": int_value(
                                    "PenaltyAttempts"
                                ),

                                "shots": int_value(
                                    "Shots"
                                ),

                                "shots_on_target": int_value(
                                    "ShotsOnTarget"
                                ),

                                "passes_completed": nullable_int(
                                    "PassesCompleted"
                                ),

                                "passes_attempted": nullable_int(
                                    "PassAttempted"
                                ),

                                "key_passes": nullable_int(
                                    "KeyPasses"
                                ),

                                "crosses": int_value(
                                    "Crosses"
                                ),

                                "dribbles_completed": nullable_int(
                                    "DribbleSuccess"
                                ),

                                "dribbles_attempted": nullable_int(
                                    "DribblesAttempted"
                                ),

                                "tackles_won": int_value(
                                    "TacklesWon"
                                ),

                                "interceptions": int_value(
                                    "Interceptions"
                                ),

                                "yellow_cards": int_value(
                                    "YellowCards"
                                ),

                                "red_cards": int_value(
                                    "RedCards"
                                ),

                                "fouls_committed": int_value(
                                    "FoulsCommitted"
                                ),

                                "fouls_drawn": int_value(
                                    "FoulsDrawn"
                                ),

                                "offsides": int_value(
                                    "Offsides"
                                ),

                                "own_goals": int_value(
                                    "OwnGoals"
                                ),

                                "penalty_won": int_value(
                                    "PenaltyWon"
                                ),

                                "penalty_conceded": int_value(
                                    "PenaltyConceded"
                                ),

                                "shots_faced": int_value(
                                    "ShotsFaced"
                                ),

                                "saves": int_value(
                                    "Saves"
                                ),

                                "penalty_faced": int_value(
                                    "PenaltyFaced"
                                ),

                                "penalty_saved": int_value(
                                    "PenaltySaved"
                                ),

                                "rating": decimal_value(
                                    "Rating"
                                ),
                            },
                        )
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    error_count += 1

                    self.stdout.write(
                        self.style.ERROR(
                            f"Row {row_number}: {e}"
                        )
                    )

        # --------------------------------------------------
        # Final summary
        # --------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Player statistics import completed."
            )
        )

        self.stdout.write(
            f"Created: {created_count}"
        )

        self.stdout.write(
            f"Updated: {updated_count}"
        )

        self.stdout.write(
            f"Errors: {error_count}"
        )