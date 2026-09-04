from django.contrib.auth.decorators import login_required
from rest_framework import generics
from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg, Sum, Count



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
    
# --------------------------------------------------
# Dashboard API
# --------------------------------------------------

class DashboardAPIView(APIView):

    def get(self, request):

        # ------------------------------------------
        # Overall Summary
        # ------------------------------------------

        total_players = Player.objects.count()

        active_players = Player.objects.filter(
            is_active=True
        ).count()

        total_clubs = Club.objects.count()

        total_matches = Match.objects.count()

        completed_matches_count = Match.objects.filter(
            status="COMPLETED"
        ).count()

        upcoming_matches_count = Match.objects.filter(
            status="UPCOMING"
        ).count()

        average_rating = PlayerStatistics.objects.filter(
            rating__isnull=False
        ).aggregate(
            avg_rating=Avg("rating")
        )["avg_rating"]

        # ------------------------------------------
        # Top Performing Players
        # ------------------------------------------

        top_players = list(
            PlayerStatistics.objects
            .filter(
                rating__isnull=False,
                player__is_active=True
            )
            .values(
                "player_id",
                "player__name",
                "player__position"
            )
            .annotate(
                average_rating=Avg("rating"),
                appearances=Count("id"),
                goals=Sum("goals"),
                assists=Sum("assists"),
                minutes=Sum("minutes_played")
            )
            .filter(
                appearances__gte=3
            )
            .order_by(
                "-average_rating"
            )[:5]
        )

        # Round player ratings
        for player in top_players:
            if player["average_rating"] is not None:
                player["average_rating"] = round(
                    float(player["average_rating"]),
                    2
                )

        # ------------------------------------------
        # Position Summary
        # ------------------------------------------

        position_summary = list(
            PlayerStatistics.objects
            .filter(
                rating__isnull=False,
                player__is_active=True
            )
            .values(
                "player__position"
            )
            .annotate(
                average_rating=Avg("rating"),
                goals=Sum("goals"),
                assists=Sum("assists"),
                minutes=Sum("minutes_played"),
                players=Count(
                    "player",
                    distinct=True
                )
            )
            .order_by(
                "player__position"
            )
        )

        # Round position ratings
        for position in position_summary:
            if position["average_rating"] is not None:
                position["average_rating"] = round(
                    float(position["average_rating"]),
                    2
                )

        # ------------------------------------------
        # Upcoming Matches
        # ------------------------------------------

        upcoming_matches_data = Match.objects.filter(
            status="UPCOMING"
        ).select_related(
            "home_club",
            "away_club"
        ).order_by(
            "match_date"
        )[:5]

        upcoming_matches = []

        for match in upcoming_matches_data:
            upcoming_matches.append({
                "id": match.id,
                "date": match.match_date,
                "competition": match.competition,
                "season": match.season,
                "home_club": match.home_club.name,
                "away_club": match.away_club.name,
            })

        # ------------------------------------------
        # Recent Completed Matches
        # ------------------------------------------

        recent_matches_data = Match.objects.filter(
            status="COMPLETED"
        ).select_related(
            "home_club",
            "away_club"
        ).order_by(
            "-match_date"
        )[:5]

        recent_matches = []

        for match in recent_matches_data:
            recent_matches.append({
                "id": match.id,
                "date": match.match_date,
                "competition": match.competition,
                "season": match.season,
                "home_club": match.home_club.name,
                "away_club": match.away_club.name,
                "home_goals": match.home_goals,
                "away_goals": match.away_goals,
            })

        # ------------------------------------------
        # Final Dashboard Response
        # ------------------------------------------

        return Response({

            "summary": {
                "total_players": total_players,
                "active_players": active_players,
                "total_clubs": total_clubs,
                "total_matches": total_matches,
                "completed_matches": completed_matches_count,
                "upcoming_matches": upcoming_matches_count,
                "average_rating": (
                    round(float(average_rating), 2)
                    if average_rating is not None
                    else None
                ),
            },

            "top_players": top_players,

            "position_summary": position_summary,

            "upcoming_matches": upcoming_matches,

            "recent_matches": recent_matches,
        }) 
@login_required(login_url="/login/")
@never_cache
def player_dashboard(request):
    return render(
        request,
        "core/player_dashboard.html"
    )
@login_required(login_url="/login/")
@never_cache
def players_page(request):
    return render(request, "core/players.html")

@login_required(login_url="/login/")
@never_cache
def players_page(request):
    return render(request, "core/players.html")


@login_required(login_url="/login/")
@never_cache
def player_performance_page(request, player_id):
    player = get_object_or_404(
        Player.objects.select_related("current_club"),
        id=player_id
    )

    statistics = PlayerStatistics.objects.filter(
        player=player,
        match__status="COMPLETED"
    )

    summary = statistics.aggregate(
        appearances=Count("id"),
        minutes=Sum("minutes_played"),
        goals=Sum("goals"),
        assists=Sum("assists"),
        shots=Sum("shots"),
        key_passes=Sum("key_passes"),
        average_rating=Avg("rating"),
    )

    if summary["average_rating"] is not None:
        summary["average_rating"] = round(
            float(summary["average_rating"]),
            2
        )

    return render(request, "core/player_performance.html", {
        "player": player,
        "summary": summary,
    })
    
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