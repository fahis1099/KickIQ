from django.contrib import admin
from django.urls import path
from .admin_views import match_result_update
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
    ordering = ("name",)


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
    ordering = ("name",)


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
        "competition",
    )
    ordering = ("-match_date",)


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
    
# --------------------------------------------------
# Custom Admin URLs
# --------------------------------------------------

original_get_urls = admin.site.get_urls


def custom_admin_urls():
    urls = original_get_urls()

    custom_urls = [
        path(
            "match-result-update/",
            admin.site.admin_view(match_result_update),
            name="match-result-update",
        ),
    ]

    return custom_urls + urls


admin.site.get_urls = custom_admin_urls