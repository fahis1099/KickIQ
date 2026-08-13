from django.urls import path

from .views import (
    ClubListAPIView, 
    PlayerListAPIView,
    MatchListAPIView,
    UpcomingMatchListAPIView,
    CompletedMatchListAPIView,
)

from .admin_views import match_result_update

urlpatterns = [
    path(
        "clubs/",
        ClubListAPIView.as_view(),
        name="club-list"
    ),
    
    path(
        "players/",
        PlayerListAPIView.as_view(),
        name="player_list"
    ),
    
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
]