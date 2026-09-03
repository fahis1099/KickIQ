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


# =========================================================
# KICKIQ ADMIN BRANDING
# =========================================================

admin.site.site_header = "KickIQ Administration"
admin.site.site_title = "KickIQ Admin"
admin.site.index_title = "Football Performance Management"
admin.site.logout_template = "admin/logout.html"


# =========================================================
# CLUB ADMIN
# =========================================================

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "country",
        "is_active",
    )

    list_filter = (
        "country",
        "is_active",
    )

    search_fields = (
        "name",
        "country",
    )

    ordering = (
        "name",
    )

    list_per_page = 20


# =========================================================
# PLAYER ADMIN
# =========================================================

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "current_club",
        "position",
        "nationality",
        "is_active",
    )

    list_filter = (
        "position",
        "current_club",
        "nationality",
        "is_active",
    )

    search_fields = (
        "name",
        "nationality",
        "current_club__name",
    )

    ordering = (
        "name",
    )

    list_per_page = 25


# =========================================================
# MATCH ADMIN
# =========================================================

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

    list_filter = (
        "season",
        "competition",
        "status",
        "home_club",
        "away_club",
    )

    search_fields = (
        "home_club__name",
        "away_club__name",
        "competition",
        "season",
    )

    ordering = (
        "-match_date",
    )

    list_per_page = 25


# =========================================================
# PLAYER STATISTICS ADMIN
# =========================================================

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
        "started",
    )

    search_fields = (
        "player__name",
        "club__name",
        "match__home_club__name",
        "match__away_club__name",
    )

    ordering = (
        "-match__match_date",
    )

    list_per_page = 25


# =========================================================
# PREDICTION ADMIN
# =========================================================

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

    list_filter = (
        "status",
    )

    search_fields = (
        "player__name",
        "match__home_club__name",
        "match__away_club__name",
    )

    ordering = (
        "-predicted_at",
    )

    list_per_page = 25


# =========================================================
# CUSTOM ADMIN URL
# =========================================================

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

# =========================================================
# KICKIQ ADMIN DASHBOARD DATA
# =========================================================

original_each_context = admin.site.each_context


def kickiq_each_context(request):
    context = original_each_context(request)

    context["kickiq_stats"] = {
        "clubs": Club.objects.count(),
        "players": Player.objects.count(),
        "matches": Match.objects.count(),
        "statistics": PlayerStatistics.objects.count(),
        "active_players": Player.objects.filter(is_active=True).count(),
        "upcoming_matches": Match.objects.filter(status="UPCOMING").count(),
        "completed_matches": Match.objects.filter(status="COMPLETED").count(),
    }

    return context


admin.site.each_context = kickiq_each_context


# --------------------------------------------------
# KickIQ Admin Branding
# --------------------------------------------------

admin.site.site_header = "KickIQ Administration"
admin.site.site_title = "KickIQ Admin"
admin.site.index_title = "Football Performance Management"