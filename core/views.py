from django.contrib.auth.decorators import login_required
from rest_framework import generics
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect

from .models import Club, Player, Match, PlayerStatistics
from .serializers import (
    ClubSerializer,
    PlayerSerializer,
    MatchSerializer,
    PlayerStatisticsSerializer,
)


# --------------------------------------------------
# Club APIs
# --------------------------------------------------

class ClubListAPIView(generics.ListAPIView):
    queryset = Club.objects.all().order_by("name")
    serializer_class = ClubSerializer


# --------------------------------------------------
# Player APIs
# --------------------------------------------------

class PlayerListAPIView(generics.ListAPIView):
    queryset = Player.objects.select_related(
        "current_club"
    ).all().order_by("name")

    serializer_class = PlayerSerializer


class PlayerDetailAPIView(generics.RetrieveAPIView):
    queryset = Player.objects.select_related(
        "current_club"
    ).all()

    serializer_class = PlayerSerializer


# --------------------------------------------------
# Match APIs
# --------------------------------------------------

class MatchListAPIView(generics.ListAPIView):
    serializer_class = MatchSerializer

    def get_queryset(self):
        queryset = Match.objects.select_related(
            "home_club",
            "away_club"
        ).all().order_by("-match_date")

        # Filter by season
        season = self.request.query_params.get("season")

        if season:
            queryset = queryset.filter(
                season=season
            )

        # Filter by club
        club = self.request.query_params.get("club")

        if club:
            queryset = queryset.filter(
                home_club__name__iexact=club
            ) | queryset.filter(
                away_club__name__iexact=club
            )

        return queryset


class MatchDetailAPIView(generics.RetrieveAPIView):
    queryset = Match.objects.select_related(
        "home_club",
        "away_club"
    ).all()

    serializer_class = MatchSerializer


class UpcomingMatchListAPIView(generics.ListAPIView):
    serializer_class = MatchSerializer

    def get_queryset(self):
        return Match.objects.select_related(
            "home_club",
            "away_club"
        ).filter(
            status="UPCOMING"
        ).order_by("match_date")


class CompletedMatchListAPIView(generics.ListAPIView):
    serializer_class = MatchSerializer

    def get_queryset(self):
        return Match.objects.select_related(
            "home_club",
            "away_club"
        ).filter(
            status="COMPLETED"
        ).order_by("-match_date")
        
# --------------------------------------------------
# Player Statistics APIs
# --------------------------------------------------

class PlayerStatisticsListAPIView(generics.ListAPIView):
    serializer_class = PlayerStatisticsSerializer

    def get_queryset(self):
        queryset = PlayerStatistics.objects.select_related(
            "player",
            "club",
            "match",
            "match__home_club",
            "match__away_club",
        ).all().order_by(
            "-match__match_date"
        )

        # Filter by player ID
        player_id = self.request.query_params.get("player")

        if player_id:
            queryset = queryset.filter(
                player_id=player_id
            )

        # Filter by club name
        club = self.request.query_params.get("club")

        if club:
            queryset = queryset.filter(
                club__name__iexact=club
            )

        # Filter by season
        season = self.request.query_params.get("season")

        if season:
            queryset = queryset.filter(
                match__season=season
            )

        return queryset


class PlayerStatisticsDetailAPIView(generics.RetrieveAPIView):
    queryset = PlayerStatistics.objects.select_related(
        "player",
        "club",
        "match",
        "match__home_club",
        "match__away_club",
    ).all()

    serializer_class = PlayerStatisticsSerializer


class PlayerStatisticsByPlayerAPIView(generics.ListAPIView):
    serializer_class = PlayerStatisticsSerializer

    def get_queryset(self):
        player_id = self.kwargs["player_id"]

        queryset = PlayerStatistics.objects.select_related(
            "player",
            "club",
            "match",
            "match__home_club",
            "match__away_club",
        ).filter(
            player_id=player_id
        ).order_by(
            "-match__match_date"
        )

        # Filter by season
        season = self.request.query_params.get("season")

        if season:
            queryset = queryset.filter(
                match__season=season
            )

        # Filter by club
        club = self.request.query_params.get("club")

        if club:
            queryset = queryset.filter(
                club__name__iexact=club
            )

        return queryset
    
@login_required(login_url="/login/")
@never_cache
def player_dashboard(request):
    return render(
        request,
        "core/player_dashboard.html"
    )
    
def login_page(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("/admin/")

        return redirect("/dashboard/")

    return render(
        request,
        "core/login.html"
    )
    
def register_page(request):
    return render(
        request,
        "core/register.html"
    )
    
def home(request):
    if not request.user.is_authenticated:
        return redirect("/login/")

    if request.user.is_staff:
        return redirect("/admin/")

    return redirect("/dashboard/")