from rest_framework import serializers
from .models import (
    Club, Player, Match, PlayerStatistics,
)

class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "country",
            "logo_path",
            "is_active",
        ]

class PlayerSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(
        source="current_club.name",
        read_only=True
    )

    class Meta:
        model = Player
        fields = [
            "id",
            "name",
            "club_name",
            "position",
            "nationality",
            "date_of_birth",
            "height",
            "jersey_number",
            "photo_path",
            "is_active",
        ]


class MatchSerializer(serializers.ModelSerializer):
    home_club_name = serializers.CharField(
        source="home_club.name",
        read_only=True
    )

    away_club_name = serializers.CharField(
        source="away_club.name",
        read_only=True
    )

    class Meta:
        model = Match
        fields = [
            "id",
            "season",
            "competition",
            "match_date",
            "home_club_name",
            "away_club_name",
            "home_goals",
            "away_goals",
            "status",
        ]
class PlayerStatisticsSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(
        source="player.name",
        read_only=True
    )

    club_name = serializers.CharField(
        source="club.name",
        read_only=True
    )

    match_date = serializers.DateField(
        source="match.match_date",
        read_only=True
    )

    home_club_name = serializers.CharField(
        source="match.home_club.name",
        read_only=True
    )

    away_club_name = serializers.CharField(
        source="match.away_club.name",
        read_only=True
    )

    class Meta:
        model = PlayerStatistics
        fields = [
            "id",

            # Related information
            "player",
            "player_name",
            "club",
            "club_name",
            "match",
            "match_date",
            "home_club_name",
            "away_club_name",

            # General
            "started",
            "minutes_played",

            # Attacking
            "goals",
            "assists",
            "penalty_goals",
            "penalty_attempts",
            "shots",
            "shots_on_target",

            # Passing
            "passes_completed",
            "passes_attempted",
            "key_passes",

            # Crossing / Dribbling
            "crosses",
            "dribbles_completed",
            "dribbles_attempted",

            # Defensive
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

            # Goalkeeper
            "shots_faced",
            "saves",
            "penalty_faced",
            "penalty_saved",

            # ML target
            "rating",
        ]