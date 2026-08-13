from django.shortcuts import render

from rest_framework import generics

from .models import Club, Player, Match
from .serializers import (
    ClubSerializer, 
    PlayerSerializer,
    MatchSerializer
)

class ClubListAPIView(generics.ListAPIView):
    queryset = Club.objects.all().order_by("name")
    serializer_class = ClubSerializer

class PlayerListAPIView(generics.ListAPIView):
    queryset = Player.objects.select_related(
        "current_club"
    ).all().order_by("name")
    
    serializer_class = PlayerSerializer
    
class MatchListAPIView(generics.ListAPIView):
    serializer_class = MatchSerializer
    
    def get_queryset(self):
        queryset = Match.objects.select_related(
            "home_club",
            "away_club"
        ).all().order_by("-match_date")
        
        #filter by season
        season = self.request.query_params.get("season")
        
        if season:
            queryset = queryset.filter(
                season=season
            )
            
        #filter by club
        club = self.request.query_params.get("club")
        
        if club:
            queryset = queryset.filter(
                home_club__name__iexact=club
            ) | queryset.filter(
                away_club__name__iexact=club
            )
        
        return queryset
    
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