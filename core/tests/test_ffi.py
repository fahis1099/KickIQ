from datetime import date, timedelta
from decimal import Decimal
from statistics import pstdev

from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Club, Match, Player, PlayerStatistics
from core.services.ffi import calculate_ffi
from core.services.ffi_analysis import analyze_player_continuity


class FFITestCase(TestCase):
    def setUp(self):
        self.club = Club.objects.create(
            name="Test FC",
            country="England",
        )

        self.opponent = Club.objects.create(
            name="Opponent FC",
            country="England",
        )

        self.player = Player.objects.create(
            name="Test Player",
            current_club=self.club,
            position="MF",
        )

        self.cutoff = date(2024, 3, 10)

    def create_match(
        self,
        days_before_cutoff,
        rating=Decimal("7.00"),
        minutes=90,
        status="COMPLETED",
        season="2023/24",
        club=None,
    ):
        """Create a match and an optional player-statistics record."""
        match_date = self.cutoff - timedelta(
            days=days_before_cutoff
        )

        match = Match.objects.create(
            season=season,
            competition="Premier League",
            match_date=match_date,
            home_club=self.club,
            away_club=self.opponent,
            status=status,
        )

        # Always create the statistics record, even if rating is None.
        PlayerStatistics.objects.create(
            player=self.player,
            match=match,
            club=club or self.club,
            minutes_played=minutes,
            started=minutes >= 60,
            rating=rating,
        )

        return match

    def create_recent_appearances(self, ratings=None):
        """Create appearances in descending chronological order."""
        if ratings is None:
            ratings = [
                Decimal("8.00"),
                Decimal("7.50"),
                Decimal("7.00"),
                Decimal("6.50"),
                Decimal("6.00"),
            ]

        for index, rating in enumerate(ratings, start=1):
            self.create_match(
                days_before_cutoff=index * 2,
                rating=rating,
            )

    def test_valid_ffi_is_within_zero_and_hundred(self):
        self.create_recent_appearances()

        result = calculate_ffi(
            self.player.id,
            before_date=self.cutoff,
            season="2023/24",
        )

        self.assertIsNotNone(result["ffi"])
        self.assertGreaterEqual(result["ffi"], 0)
        self.assertLessEqual(result["ffi"], 100)
        self.assertEqual(result["matches_used"], 5)

    def test_ffi_matches_the_agreed_formula(self):
        ratings = [
            Decimal("8.00"),
            Decimal("7.50"),
            Decimal("7.00"),
            Decimal("6.50"),
            Decimal("6.00"),
        ]

        self.create_recent_appearances(ratings)

        result = calculate_ffi(
            self.player.id,
            before_date=self.cutoff,
            season="2023/24",
        )

        values = [float(value) for value in ratings]
        weights = [5, 4, 3, 2, 1]

        weighted_average = sum(
            value * weight
            for value, weight in zip(values, weights)
        ) / sum(weights)

        performance = weighted_average * 10

        recent_average = sum(values[:2]) / 2
        older_average = sum(values[2:]) / 3

        trend = max(
            0,
            min(
                100,
                50 + (recent_average - older_average) * 25,
            ),
        )

        consistency = max(
            0,
            min(
                100,
                100 - pstdev(values) * 25,
            ),
        )

        expected_ffi = round(
            performance * 0.70
            + trend * 0.15
            + consistency * 0.15,
            2,
        )

        self.assertEqual(result["ffi"], expected_ffi)

    def test_fewer_than_minimum_appearances_returns_no_ffi(self):
        self.create_recent_appearances(
            [Decimal("8.00"), Decimal("7.00")]
        )

        result = calculate_ffi(
            self.player.id,
            before_date=self.cutoff,
            season="2023/24",
        )

        self.assertIsNone(result["ffi"])
        self.assertEqual(result["matches_used"], 2)

    def test_match_on_cutoff_date_is_excluded(self):
        self.create_recent_appearances(
            [
                Decimal("8.00"),
                Decimal("7.50"),
                Decimal("7.00"),
            ]
        )

        cutoff_match = Match.objects.create(
            season="2023/24",
            competition="Premier League",
            match_date=self.cutoff,
            home_club=self.club,
            away_club=self.opponent,
            status="COMPLETED",
        )

        PlayerStatistics.objects.create(
            player=self.player,
            match=cutoff_match,
            club=self.club,
            minutes_played=90,
            rating=Decimal("10.00"),
        )

        result = calculate_ffi(
            self.player.id,
            before_date=self.cutoff,
            season="2023/24",
        )

        self.assertEqual(result["matches_used"], 3)

        eligible_ids = [
            item["match_id"]
            for item in result["continuity"]["fixture_sequence"]
        ]

        self.assertNotIn(cutoff_match.id, eligible_ids)

    def test_upcoming_match_is_excluded(self):
        self.create_recent_appearances(
            [
                Decimal("8.00"),
                Decimal("7.50"),
                Decimal("7.00"),
            ]
        )

        upcoming = Match.objects.create(
            season="2023/24",
            competition="Premier League",
            match_date=self.cutoff - timedelta(days=1),
            home_club=self.club,
            away_club=self.opponent,
            status="UPCOMING",
        )

        PlayerStatistics.objects.create(
            player=self.player,
            match=upcoming,
            club=self.club,
            minutes_played=90,
            rating=Decimal("10.00"),
        )

        result = calculate_ffi(
            self.player.id,
            before_date=self.cutoff,
            season="2023/24",
        )

        self.assertEqual(result["matches_used"], 3)

        eligible_ids = [
            item["match_id"]
            for item in result["continuity"]["fixture_sequence"]
        ]

        self.assertNotIn(upcoming.id, eligible_ids)

    def test_zero_minute_record_does_not_count_as_appearance(self):
        self.create_recent_appearances(
            [
                Decimal("8.00"),
                Decimal("7.50"),
                Decimal("7.00"),
            ]
        )

        unused = self.create_match(
            days_before_cutoff=1,
            rating=Decimal("9.00"),
            minutes=0,
        )

        result = calculate_ffi(
            self.player.id,
            before_date=self.cutoff,
            season="2023/24",
        )

        self.assertEqual(result["matches_used"], 3)

        self.assertNotEqual(
            result["continuity"]["latest_appearance_date"],
            unused.match_date.isoformat(),
        )

    def test_missing_rating_is_not_counted_as_zero(self):
        self.create_recent_appearances(
            [
                Decimal("8.00"),
                Decimal("7.50"),
                Decimal("7.00"),
            ]
        )

        self.create_match(
            days_before_cutoff=1,
            rating=None,
            minutes=90,
        )

        result = calculate_ffi(
            self.player.id,
            before_date=self.cutoff,
            season="2023/24",
        )

        self.assertEqual(result["matches_used"], 3)
        self.assertIsNotNone(result["ffi"])

    def test_existing_statistics_with_missing_rating_is_not_zero(self):
        self.create_recent_appearances(
            [
                Decimal("8.00"),
                Decimal("7.50"),
                Decimal("7.00"),
            ]
        )

        missing_rating_match = self.create_match(
            days_before_cutoff=1,
            rating=None,
            minutes=90,
        )

        result = calculate_ffi(
            self.player.id,
            before_date=self.cutoff,
            season="2023/24",
        )

        self.assertEqual(result["matches_used"], 3)
        self.assertIsNotNone(result["ffi"])

        latest_fixture = result["continuity"]["fixture_sequence"][0]

        self.assertEqual(
            latest_fixture["match_id"],
            missing_rating_match.id,
        )
        self.assertIsNone(latest_fixture["rating"])

    def test_season_filter_excludes_other_seasons(self):
        self.create_recent_appearances(
            [
                Decimal("8.00"),
                Decimal("7.50"),
            ]
        )

        self.create_match(
            days_before_cutoff=3,
            rating=Decimal("7.00"),
            season="2022/23",
        )

        result = calculate_ffi(
            self.player.id,
            before_date=self.cutoff,
            season="2023/24",
        )

        self.assertIsNone(result["ffi"])
        self.assertEqual(result["matches_used"], 2)

    def test_fixture_window_is_limited_to_seven(self):
        self.create_recent_appearances(
            [
                Decimal("8.00"),
                Decimal("7.50"),
                Decimal("7.00"),
                Decimal("6.50"),
                Decimal("6.00"),
            ]
        )

        self.create_match(
            days_before_cutoff=20,
            rating=Decimal("5.00"),
        )

        self.create_match(
            days_before_cutoff=22,
            rating=Decimal("5.00"),
        )

        self.create_match(
            days_before_cutoff=24,
            rating=Decimal("5.00"),
        )

        result = analyze_player_continuity(
            player_id=self.player.id,
            club_id=self.club.id,
            before_date=self.cutoff,
            window=7,
            season="2023/24",
        )

        self.assertEqual(result["fixtures_analyzed"], 7)

    def test_invalid_rating_raises_value_error(self):
        self.create_recent_appearances(
            [
                Decimal("11.00"),
                Decimal("8.00"),
                Decimal("7.00"),
            ]
        )

        with self.assertRaises(ValueError):
            calculate_ffi(
                self.player.id,
                before_date=self.cutoff,
                season="2023/24",
            )

    def test_invalid_window_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_ffi(
                self.player.id,
                before_date=self.cutoff,
                window=0,
            )

        with self.assertRaises(ValueError):
            calculate_ffi(
                self.player.id,
                before_date=self.cutoff,
                fixture_window=0,
            )

        with self.assertRaises(ValueError):
            calculate_ffi(
                self.player.id,
                before_date=self.cutoff,
                window=3,
                minimum_appearances=4,
            )

    def test_duplicate_player_match_statistics_are_rejected(self):
        match = self.create_match(
            days_before_cutoff=1,
            rating=Decimal("7.00"),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlayerStatistics.objects.create(
                    player=self.player,
                    match=match,
                    club=self.club,
                    minutes_played=90,
                    rating=Decimal("8.00"),
                )