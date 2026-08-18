from rest_framework import generics

from .models import Club, Player, Match
from .serializers import (
    ClubSerializer,
    PlayerSerializer,
    MatchSerializer
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