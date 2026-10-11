
from datetime import date
from math import isfinite

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone

from core.models import Match, Player, PlayerStatistics
from core.services.ffi import calculate_ffi


class Command(BaseCommand):
    help = "Audit FFI calculations and database integrity without modifying data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Test only the first N players; 0 means all players.",
        )
        parser.add_argument(
            "--before-date",
            type=str,
            default=None,
            help="Historical cutoff date in YYYY-MM-DD format.",
        )
        parser.add_argument(
            "--season",
            type=str,
            default=None,
            help="Optional season, e.g. 2023/24.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        season = options["season"]

        if limit < 0:
            self.stderr.write("--limit cannot be negative.")
            return

        try:
            before_date = (
                date.fromisoformat(options["before_date"])
                if options["before_date"]
                else timezone.localdate() + __import__(
                    "datetime"
                ).timedelta(days=1)
            )
        except ValueError:
            self.stderr.write(
                "Invalid date. Use YYYY-MM-DD, e.g. 2024-03-10."
            )
            return

        errors = []
        warnings = []
        valid_count = 0
        insufficient_count = 0
        tested_count = 0
        formula_checks = 0
        cutoff_checks = 0
        fixture_checks = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            "KICKIQ FFI VALIDATION"
        ))
        self.stdout.write(f"Cutoff date: {before_date}")
        self.stdout.write(f"Season filter: {season or 'All seasons'}")

        # Database-level integrity checks.
        status_counts = list(
            Match.objects.values("status")
            .annotate(total=Count("id"))
            .order_by("status")
        )

        non_completed_stats = (
            PlayerStatistics.objects
            .exclude(match__status="COMPLETED")
            .count()
        )

        non_completed_ratings = (
            PlayerStatistics.objects
            .filter(rating__isnull=False)
            .exclude(match__status="COMPLETED")
            .count()
        )

        invalid_ratings = (
            PlayerStatistics.objects
            .filter(rating__isnull=False)
            .filter(Q(rating__lt=0) | Q(rating__gt=10))
            .count()
        )

        duplicate_pairs = list(
            PlayerStatistics.objects
            .values("player_id", "match_id")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
        )

        self.stdout.write(f"Match statuses: {status_counts}")
        self.stdout.write(
            f"Statistics on non-completed matches: {non_completed_stats}"
        )
        self.stdout.write(
            f"Rated records on non-completed matches: "
            f"{non_completed_ratings}"
        )
        self.stdout.write(f"Ratings outside 0-10: {invalid_ratings}")
        self.stdout.write(
            f"Duplicate player-match pairs: {len(duplicate_pairs)}"
        )

        if non_completed_stats:
            errors.append(
                f"{non_completed_stats} statistics records belong "
                "to non-completed matches."
            )

        if invalid_ratings:
            errors.append(
                f"{invalid_ratings} ratings fall outside 0-10."
            )

        if duplicate_pairs:
            errors.append(
                f"{len(duplicate_pairs)} duplicate player-match pairs."
            )

        players = Player.objects.order_by("id")

        if limit:
            players = players[:limit]

        for player in players.iterator() if not limit else players:
            tested_count += 1

            try:
                result = calculate_ffi(
                    player.id,
                    before_date=before_date,
                    season=season,
                )
            except Exception as exc:
                errors.append(
                    f"Player {player.id} ({player.name}): "
                    f"{type(exc).__name__}: {exc}"
                )
                continue

            ffi = result.get("ffi")
            matches_used = result.get("matches_used", 0)
            continuity = result.get("continuity") or {}

            # A missing score is valid only when insufficient data
            # explains why the calculation could not be completed.
            if ffi is None:
                insufficient_count += 1

                if matches_used >= 3:
                    errors.append(
                        f"Player {player.id}: FFI is None despite "
                        f"{matches_used} usable ratings."
                    )

                continue

            valid_count += 1

            if not isinstance(ffi, (int, float)) or not isfinite(ffi):
                errors.append(
                    f"Player {player.id}: FFI is not a finite number."
                )
                continue

            if not 0 <= ffi <= 100:
                errors.append(
                    f"Player {player.id}: FFI outside 0-100: {ffi}."
                )

            if not 3 <= matches_used <= 5:
                errors.append(
                    f"Player {player.id}: unexpected matches_used="
                    f"{matches_used}."
                )

            # Check component bounds and recompute final FFI.
            components = [
                result.get("performance_score"),
                result.get("trend_score"),
                result.get("consistency_score"),
            ]

            if all(value is not None for value in components):
                performance, trend, consistency = components

                for label, value in zip(
                    ("performance", "trend", "consistency"),
                    components,
                ):
                    if not 0 <= value <= 100:
                        errors.append(
                            f"Player {player.id}: {label} score "
                            f"outside 0-100: {value}."
                        )

                recomputed = (
                    0.70 * performance
                    + 0.15 * trend
                    + 0.15 * consistency
                )

                if abs(ffi - recomputed) > 0.03:
                    errors.append(
                        f"Player {player.id}: FFI formula mismatch; "
                        f"returned={ffi}, recomputed={recomputed:.4f}."
                    )
                else:
                    formula_checks += 1
            else:
                errors.append(
                    f"Player {player.id}: missing FFI component scores."
                )

            # Inspect fixture dates for leakage.
            fixture_sequence = continuity.get("fixture_sequence", [])

            for fixture in fixture_sequence:
                fixture_date = date.fromisoformat(fixture["date"])

                if fixture_date >= before_date:
                    errors.append(
                        f"Player {player.id}: fixture {fixture['match_id']} "
                        f"on {fixture_date} is not before cutoff."
                    )
                else:
                    cutoff_checks += 1

            if len(fixture_sequence) > 7:
                errors.append(
                    f"Player {player.id}: more than seven fixtures "
                    "were analyzed."
                )

            fixture_checks += 1

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            "VALIDATION SUMMARY"
        ))
        self.stdout.write(f"Players tested: {tested_count}")
        self.stdout.write(f"Valid FFI results: {valid_count}")
        self.stdout.write(
            f"Insufficient-data results: {insufficient_count}"
        )
        self.stdout.write(f"Formula checks passed: {formula_checks}")
        self.stdout.write(f"Fixture cutoff checks: {cutoff_checks}")
        self.stdout.write(f"Players with fixture checks: {fixture_checks}")
        self.stdout.write(f"Errors: {len(errors)}")

        if errors:
            self.stdout.write(self.style.ERROR(
                "\nVALIDATION FAILED — review these findings:"
            ))
            for error in errors:
                self.stdout.write(f"- {error}")
        else:
            self.stdout.write(self.style.SUCCESS(
                "\nNo errors detected by the implemented checks."
            ))

        self.stdout.write(
            "\nNote: passing these checks does not prove that the "
            "formula is scientifically optimal or that the source "
            "data is factually accurate."
        )
