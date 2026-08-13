from django.contrib import admin
from .models import (
    Club,
    Player,
    Match,
    PlayerStatistics,
    Prediction,
)


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "is_active")
    list_filter = ("country", "is_active")
    search_fields = ("name", "country")


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "current_club",
        "position",
        "nationality",
        "is_active",
    )
    list_filter = ("position", "is_active", "current_club")
    search_fields = ("name", "nationality")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "season",
        "match_date",
        "home_club",
        "away_club",
        "home_goals",
        "away_goals",
        "status",
    )
    list_filter = ("season", "competition", "status")
    search_fields = (
        "home_club__name",
        "away_club__name",
    )


@admin.register(PlayerStatistics)
class PlayerStatisticsAdmin(admin.ModelAdmin):
    list_display = (
        "player",
        "club",
        "match",
        "minutes_played",
        "goals",
        "assists",
        "rating",
    )
    list_filter = (
        "club",
        "match__season",
        "player__position",
    )
    search_fields = (
        "player__name",
        "club__name",
    )


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = (
        "player",
        "match",
        "predicted_rating",
        "actual_rating",
        "prediction_error",
        "status",
        "predicted_at",
    )
    list_filter = ("status",)
    search_fields = (
        "player__name",
        "match__home_club__name",
        "match__away_club__name",
    )