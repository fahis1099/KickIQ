from rest_framework import serializers
from .models import Club, Player, Match


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