
import csv
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import Match, PlayerStatistics
from core.services.ffi import calculate_ffi


# Every numeric or boolean performance-statistic field in PlayerStatistics.
# The target rating is deliberately handled separately.
STAT_FIELDS = [
    "minutes_played",
    "started",
    "goals",
    "assists",
    "penalty_goals",
    "penalty_attempts",
    "shots",
    "shots_on_target",
    "passes_completed",
    "passes_attempted",
    "key_passes",
    "crosses",
    "dribbles_completed",
    "dribbles_attempted",
    "tackles_won",
    "interceptions",
    "yellow_cards",
    "red_cards",
    "fouls_committed",
    "fouls_drawn",
    "offsides",
    "own_goals",
    "penalty_won",
    "penalty_conceded",
    "shots_faced",
    "saves",
    "penalty_faced",
    "penalty_saved",
]

DEFAULT_HISTORY_WINDOW = 5
DEFAULT_FIXTURE_WINDOW = 7
DEFAULT_MINIMUM_APPEARANCES = 3
DEFAULT_RECENT_AVAILABILITY_WINDOW = 3


class Command(BaseCommand):
    help = (
        "Build a leakage-safe, historical player-match training dataset "
        "for KickIQ."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="datasets/kickiq_training_dataset.csv",
            help="CSV output path, relative to BASE_DIR or absolute.",
        )
        parser.add_argument(
            "--history-window",
            type=int,
            default=DEFAULT_HISTORY_WINDOW,
            help="Number of previous appearances used for rolling statistics.",
        )
        parser.add_argument(
            "--fixture-window",
            type=int,
            default=DEFAULT_FIXTURE_WINDOW,
            help="Number of recent club fixtures used for FFI eligibility.",
        )
        parser.add_argument(
            "--minimum-appearances",
            type=int,
            default=DEFAULT_MINIMUM_APPEARANCES,
            help="Minimum rated appearances required for FFI.",
        )
        parser.add_argument(
            "--recent-availability-window",
            type=int,
            default=DEFAULT_RECENT_AVAILABILITY_WINDOW,
            help="Require an appearance in at least one of the last N fixtures.",
        )
        parser.add_argument(
            "--season",
            default=None,
            help="Optional target-match season filter, e.g. 2023/24.",
        )

    def handle(self, *args, **options):
        history_window = options["history_window"]
        fixture_window = options["fixture_window"]
        minimum_appearances = options["minimum_appearances"]
        recent_window = options["recent_availability_window"]

        if history_window < 1:
            raise CommandError("--history-window must be at least 1.")

        if fixture_window < 1:
            raise CommandError("--fixture-window must be at least 1.")

        if minimum_appearances < 1:
            raise CommandError("--minimum-appearances must be at least 1.")

        if minimum_appearances > history_window:
            raise CommandError(
                "--minimum-appearances cannot exceed --history-window."
            )

        if recent_window < 1 or recent_window > fixture_window:
            raise CommandError(
                "--recent-availability-window must be between 1 "
                "and --fixture-window."
            )

        output_path = Path(options["output"])

        if not output_path.is_absolute():
            output_path = Path(settings.BASE_DIR) / output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)

        summary_path = output_path.with_name(
            output_path.stem + "_summary.txt"
        )

        targets = PlayerStatistics.objects.filter(
            match__status="COMPLETED",
            minutes_played__gt=0,
            rating__isnull=False,
        ).select_related(
            "player",
            "match",
            "club",
            "match__home_club",
            "match__away_club",
        ).order_by(
            "match__match_date",
            "match_id",
            "player_id",
        )

        if options["season"]:
            targets = targets.filter(match__season=options["season"])

        target_count = targets.count()

        if target_count == 0:
            raise CommandError(
                "No completed, rated, positive-minute player appearances "
                "were found for the selected filters."
            )

        # Statistics that have minutes but no rating cannot be used as
        # supervised-learning targets.
        missing_target_ratings = PlayerStatistics.objects.filter(
            match__status="COMPLETED",
            minutes_played__gt=0,
            rating__isnull=True,
        )

        if options["season"]:
            missing_target_ratings = missing_target_ratings.filter(
                match__season=options["season"]
            )

        counters = Counter()
        counters["rated_target_candidates"] = target_count
        counters["unrated_appearances_not_targetable"] = (
            missing_target_ratings.count()
        )

        self.stdout.write("KICKIQ TRAINING DATASET GENERATOR")
        self.stdout.write(f"Rated target candidates: {target_count}")
        self.stdout.write(f"History window: {history_window} appearances")
        self.stdout.write(f"FFI fixture window: {fixture_window}")
        self.stdout.write(f"Minimum rated appearances: {minimum_appearances}")
        self.stdout.write(
            f"Recent availability window: {recent_window} fixtures"
        )
        self.stdout.write(
            "Historical features will use completed appearances "
            "strictly before each target match date."
        )

        headers = self.get_headers(history_window)
        included_rows = 0

        # Write incrementally so the full dataset does not need to be
        # retained in memory.
        with output_path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=headers,
                extrasaction="raise",
            )
            writer.writeheader()

            for index, target in enumerate(targets.iterator(chunk_size=200), 1):
                match = target.match
                player = target.player
                target_club = target.club

                # A player's historical club must be one of the clubs
                # participating in the target match.
                if target_club.id == match.home_club_id:
                    opponent = match.away_club
                    is_home = 1
                elif target_club.id == match.away_club_id:
                    opponent = match.home_club
                    is_home = 0
                else:
                    counters["invalid_target_club_association"] += 1
                    continue

                # Strictly before the target date: this excludes the target
                # match and all other matches on that same date.
                history = list(
                    PlayerStatistics.objects.filter(
                        player_id=player.id,
                        club_id=target_club.id,
                        match__status="COMPLETED",
                        match__match_date__lt=match.match_date,
                        minutes_played__gt=0,
                    )
                    .select_related("match")
                    .order_by(
                        "-match__match_date",
                        "-match_id",
                    )[:history_window]
                )

                if not history:
                    counters["excluded_no_history"] += 1
                    continue

                # Apply the exact FFI service used by the application.
                # No season restriction is applied to historical FFI, so
                # eligible earlier-season appearances may be used.
                ffi_result = calculate_ffi(
                    player_id=player.id,
                    before_date=match.match_date,
                    season=None,
                    window=history_window,
                    fixture_window=fixture_window,
                    minimum_appearances=minimum_appearances,
                    club_id=target_club.id,
                    recent_availability_window=recent_window,
                )

                if ffi_result.get("ffi") is None:
                    message = ffi_result.get(
                        "message",
                        "FFI unavailable for an unspecified reason.",
                    )

                    if "last 3 completed club fixtures" in message:
                        counters["excluded_recent_availability"] += 1
                    elif "Insufficient recent data" in message:
                        counters["excluded_insufficient_rated_history"] += 1
                    elif "No eligible previous appearances" in message:
                        counters["excluded_no_eligible_club_history"] += 1
                    else:
                        counters["excluded_ffi_unavailable"] += 1

                    continue

                row = self.build_row(
                    target=target,
                    opponent=opponent,
                    is_home=is_home,
                    history=history,
                    ffi_result=ffi_result,
                    history_window=history_window,
                )

                writer.writerow(row)
                included_rows += 1
                counters["included_rows"] += 1

                if index % 500 == 0:
                    self.stdout.write(
                        f"Processed {index}/{target_count} candidates; "
                        f"included {included_rows}."
                    )

        excluded_rows = target_count - included_rows

        summary_lines = [
            "KICKIQ TRAINING DATASET SUMMARY",
            "=" * 36,
            f"Rated target candidates: {target_count}",
            f"Included rows: {included_rows}",
            f"Excluded rated candidates: {excluded_rows}",
            (
                "Unrated appearances not usable as targets: "
                f"{counters['unrated_appearances_not_targetable']}"
            ),
            "",
            "EXCLUSION BREAKDOWN",
            "-" * 24,
        ]

        exclusion_keys = [
            "excluded_no_history",
            "excluded_recent_availability",
            "excluded_insufficient_rated_history",
            "excluded_no_eligible_club_history",
            "excluded_ffi_unavailable",
            "invalid_target_club_association",
        ]

        for key in exclusion_keys:
            summary_lines.append(f"{key}: {counters[key]}")

        summary_lines.extend([
            "",
            f"History window: {history_window}",
            f"FFI fixture window: {fixture_window}",
            f"Minimum rated appearances: {minimum_appearances}",
            f"Recent availability window: {recent_window}",
            "Historical lookback: all seasons, strictly before target date",
            f"CSV path: {output_path}",
        ])

        summary_path.write_text(
            "\n".join(summary_lines) + "\n",
            encoding="utf-8",
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("DATASET GENERATION COMPLETE"))
        self.stdout.write(f"Candidates: {target_count}")
        self.stdout.write(f"Included: {included_rows}")
        self.stdout.write(f"Excluded: {excluded_rows}")
        self.stdout.write(f"CSV: {output_path}")
        self.stdout.write(f"Summary: {summary_path}")

    @staticmethod
    def get_headers(history_window):
        """Return a stable column list for every exported row."""

        headers = [
            # Identifiers and target metadata; do not feed IDs directly
            # into the model without an explicit modelling decision.
            "player_id",
            "match_id",
            "match_date",
            "season",
            "competition",
            "club",
            "opponent",
            "is_home",
            "position",
            "preferred_foot",
        ]

        headers.extend([
            "history_appearances_used",
            "history_rated_appearances",
            "history_latest_rating",
            f"history_rating_mean_{history_window}",
            f"history_rating_std_{history_window}",
        ])

        # For every PlayerStatistics performance field, export historical
        # mean, sum and observed-value count. The target rating is handled
        # separately as a historical feature and target.
        for field in STAT_FIELDS:
            headers.extend([
                f"history_{field}_mean_{history_window}",
                f"history_{field}_sum_{history_window}",
                f"history_{field}_observed_{history_window}",
            ])

        headers.extend([
            "ffi",
            "ffi_matches_used",
            "ffi_weighted_average_rating",
            "ffi_performance_score",
            "ffi_rating_change",
            "ffi_trend_score",
            "ffi_rating_standard_deviation",
            "ffi_consistency_score",
            "ffi_days_since_latest_appearance",
            "ffi_appearance_percentage",
            "ffi_consecutive_appearances",
            "ffi_appearances_in_window",
            "ffi_missed_fixtures_in_window",
            "target_rating",
        ])

        return headers

    @staticmethod
    def numeric_value(value):
        """Convert database numeric values to CSV-friendly numbers."""

        if value is None:
            return None

        if isinstance(value, bool):
            return int(value)

        return float(value)

    def build_row(
        self,
        target,
        opponent,
        is_home,
        history,
        ffi_result,
        history_window,
    ):
        player = target.player
        match = target.match
        club = target.club

        row = {
            "player_id": player.id,
            "match_id": match.id,
            "match_date": match.match_date.isoformat(),
            "season": match.season,
            "competition": match.competition,
            "club": club.name,
            "opponent": opponent.name,
            "is_home": is_home,
            "position": target.position,
            "preferred_foot": player.preferred_foot,
            "history_appearances_used": len(history),
            "history_rated_appearances": sum(
                record.rating is not None for record in history
            ),
            "history_latest_rating": self.numeric_value(
                history[0].rating
            ),
            f"history_rating_mean_{history_window}": self.mean_of(
                [record.rating for record in history]
            ),
            f"history_rating_std_{history_window}": self.population_std(
                [record.rating for record in history]
            ),
        }

        # Compute every historical statistic from prior appearances only.
        for field in STAT_FIELDS:
            values = [
                getattr(record, field)
                for record in history
                if getattr(record, field) is not None
            ]

            row[f"history_{field}_mean_{history_window}"] = (
                self.mean_of(values)
            )
            row[f"history_{field}_sum_{history_window}"] = (
                self.sum_of(values)
            )
            row[f"history_{field}_observed_{history_window}"] = len(values)

        continuity = ffi_result.get("continuity", {})

        row.update({
            "ffi": ffi_result["ffi"],
            "ffi_matches_used": ffi_result["matches_used"],
            "ffi_weighted_average_rating": ffi_result.get(
                "weighted_average_rating"
            ),
            "ffi_performance_score": ffi_result.get("performance_score"),
            "ffi_rating_change": ffi_result.get("rating_change"),
            "ffi_trend_score": ffi_result.get("trend_score"),
            "ffi_rating_standard_deviation": ffi_result.get(
                "rating_standard_deviation"
            ),
            "ffi_consistency_score": ffi_result.get("consistency_score"),
            "ffi_days_since_latest_appearance": ffi_result.get(
                "days_since_latest_appearance"
            ),
            "ffi_appearance_percentage": continuity.get(
                "appearance_percentage"
            ),
            "ffi_consecutive_appearances": continuity.get(
                "consecutive_appearances_at_end"
            ),
            "ffi_appearances_in_window": continuity.get(
                "appearances_in_window"
            ),
            "ffi_missed_fixtures_in_window": continuity.get(
                "missed_fixtures_in_window"
            ),
            "target_rating": self.numeric_value(target.rating),
        })

        return row

    @classmethod
    def mean_of(cls, values):
        numeric_values = [
            cls.numeric_value(value)
            for value in values
            if value is not None
        ]

        if not numeric_values:
            return None

        return sum(numeric_values) / len(numeric_values)

    @classmethod
    def sum_of(cls, values):
        numeric_values = [
            cls.numeric_value(value)
            for value in values
            if value is not None
        ]

        if not numeric_values:
            return None

        return sum(numeric_values)

    @classmethod
    def population_std(cls, values):
        numeric_values = [
            cls.numeric_value(value)
            for value in values
            if value is not None
        ]

        if not numeric_values:
            return None

        if len(numeric_values) == 1:
            return 0.0

        mean = sum(numeric_values) / len(numeric_values)
        variance = sum(
            (value - mean) ** 2
            for value in numeric_values
        ) / len(numeric_values)

        return variance ** 0.5
