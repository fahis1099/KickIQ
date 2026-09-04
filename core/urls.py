from django.urls import path

from .views import (
    ClubListAPIView,
    PlayerListAPIView,
    PlayerDetailAPIView,
    MatchListAPIView,
    MatchDetailAPIView,
    UpcomingMatchListAPIView,
    CompletedMatchListAPIView,
    PlayerStatisticsListAPIView,
    PlayerStatisticsDetailAPIView,
    PlayerStatisticsByPlayerAPIView,
    DashboardAPIView,
)

from .auth_views import (
    login_view,
    register_view,
    logout_view,
    profile_view,
)


urlpatterns = [

    # ------------------------------------------
    # Dashboard
    # ------------------------------------------

    path(
        "dashboard/",
        DashboardAPIView.as_view(),
        name="dashboard-api"
    ),


    # ------------------------------------------
    # Authentication
    # ------------------------------------------

    path(
        "auth/login/",
        login_view,
        name="api-login"
    ),

    path(
        "auth/register/",
        register_view,
        name="api-register"
    ),

    path(
        "auth/logout/",
        logout_view,
        name="api-logout"
    ),

    path(
        "auth/profile/",
        profile_view,
        name="api-profile"
    ),


    # ------------------------------------------
    # Clubs
    # ------------------------------------------

    path(
        "clubs/",
        ClubListAPIView.as_view(),
        name="club-list"
    ),


    # ------------------------------------------
    # Players
    # ------------------------------------------

    path(
        "players/",
        PlayerListAPIView.as_view(),
        name="player-list"
    ),

    path(
        "players/<int:pk>/",
        PlayerDetailAPIView.as_view(),
        name="player-detail"
    ),

    path(
        "players/<int:player_id>/statistics/",
        PlayerStatisticsByPlayerAPIView.as_view(),
        name="player-statistics"
    ),


    # ------------------------------------------
    # Matches
    # ------------------------------------------

    path(
        "matches/",
        MatchListAPIView.as_view(),
        name="match-list"
    ),

    path(
        "matches/upcoming/",
        UpcomingMatchListAPIView.as_view(),
        name="upcoming-matches"
    ),

    path(
        "matches/completed/",
        CompletedMatchListAPIView.as_view(),
        name="completed-matches"
    ),

    path(
        "matches/<int:pk>/",
        MatchDetailAPIView.as_view(),
        name="match-detail"
    ),


    # ------------------------------------------
    # Player Statistics
    # ------------------------------------------

    path(
        "player-statistics/",
        PlayerStatisticsListAPIView.as_view(),
        name="player-statistics-list"
    ),

    path(
        "player-statistics/<int:pk>/",
        PlayerStatisticsDetailAPIView.as_view(),
        name="player-statistics-detail"
    ),
]