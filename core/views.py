import re
from django.contrib.auth.decorators import login_required
from rest_framework import generics
from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect
from django.http import HttpResponse
from django.utils.html import escape
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg, Sum, Count, Q
from django.utils.timezone import localdate
from core.services.ffi import calculate_ffi
from core.services.rating_prediction import predict_next_match_rating
from .models import Club, Player, Match, PlayerStatistics
from .serializers import (
    ClubSerializer,
    PlayerSerializer,
    MatchSerializer,
    PlayerStatisticsSerializer,
)


# ==================================================
# Club APIs
# ==================================================

class ClubListAPIView(generics.ListAPIView):
    queryset = Club.objects.all().order_by("name")
    serializer_class = ClubSerializer


# ==================================================
# Player APIs
# ==================================================

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


# ==================================================
# Match APIs
# ==================================================

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
            queryset = (
                queryset.filter(home_club__name__iexact=club)
                |
                queryset.filter(away_club__name__iexact=club)
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


# ==================================================
# Player Statistics APIs
# ==================================================

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

# ==================================================
# Player FFI API
# ==================================================

class PlayerFFIAPIView(APIView):

    def get(self, request, player_id):

        # Make sure the player exists
        player = get_object_or_404(
            Player.objects.select_related("current_club"),
            id=player_id
        )

        # Optional season filter
        season = request.query_params.get("season")

        if season:
            season = season.strip()

        try:

            result = calculate_ffi(
                player_id=player.id,
                season=season if season else None,
            )

            return Response({
                "success": True,
                "player_id": player.id,
                "player_name": player.name,
                "season": season if season else None,
                **result,
            })

        except ValueError as error:

            return Response(
                {
                    "success": False,
                    "player_id": player.id,
                    "player_name": player.name,
                    "season": season if season else None,
                    "ffi": None,
                    "message": str(error),
                },
                status=400,
            )

        except Exception as error:

            return Response(
                {
                    "success": False,
                    "player_id": player.id,
                    "player_name": player.name,
                    "season": season if season else None,
                    "ffi": None,
                    "message": (
                        "Unable to calculate Football Form Index."
                    ),
                },
                status=500,
            )


# ==================================================
# Player Rating Prediction API
# ==================================================

class PlayerRatingPredictionAPIView(APIView):

    def get(self, request, player_id):
        player = get_object_or_404(Player, pk=player_id)

        try:
            result = predict_next_match_rating(player.id)
            return Response({
                "success": True,
                **result,
            })

        except ValueError as error:
            return Response({
                "success": False,
                "player_id": player.id,
                "player_name": player.name,
                "message": str(error),
            }, status=400)

        except FileNotFoundError:
            return Response({
                "success": False,
                "message": (
                    "The trained rating model was not found. "
                    "Check the model file location."
                ),
            }, status=503)

        except Exception:
            # Keep internal errors out of the public API response.
            return Response({
                "success": False,
                "message": "Unable to generate the player rating prediction.",
            }, status=500)


# ==================================================
# Player Attribute Radar API
# ==================================================

class PlayerRadarAPIView(APIView):
    """Return position-relative radar scores for a season or all seasons."""

    MIN_MINUTES = 450
    MIN_COHORT_SIZE = 10

    @staticmethod
    def _safe_divide(numerator, denominator):
        if not denominator:
            return None
        return (float(numerator) / float(denominator)) * 100.0

    @staticmethod
    def _percentile(value, peer_values, higher_is_better=True):
        """Midrank percentile; identical values (including all-zero groups) tie."""
        if value is None:
            return None
        usable = [float(item) for item in peer_values if item is not None]
        if not usable:
            return None
        current = float(value)
        below = sum(item < current for item in usable)
        equal = sum(item == current for item in usable)
        percentile = ((below + 0.5 * equal) / len(usable)) * 100.0
        if not higher_is_better:
            percentile = 100.0 - percentile
        return round(max(0.0, min(100.0, percentile)), 2)

    @staticmethod
    def _aggregate_player(player, rows):
        totals = {
            "minutes": 0, "goals": 0, "assists": 0, "shots": 0,
            "shots_on_target": 0, "tackles_won": 0, "interceptions": 0,
            "fouls_committed": 0, "yellow_cards": 0, "red_cards": 0,
            "penalty_conceded": 0, "own_goals": 0, "passes_completed": 0,
            "passes_attempted": 0, "key_passes": 0, "crosses": 0,
            "dribbles_completed": 0, "dribbles_attempted": 0,
            "saves": 0, "shots_faced": 0, "penalty_saved": 0,
            "penalty_faced": 0, "goals_conceded": 0,
        }
        totals["position"] = player.position
        totals["player_id"] = player.id
        totals["player_name"] = player.name
        for stat in rows:
            for field in totals:
                if field in ("position", "player_id", "player_name", "goals_conceded"):
                    continue
                model_field = "minutes_played" if field == "minutes" else field
                totals[field] += int(getattr(stat, model_field, 0) or 0)
            # Team goals conceded can only be derived for a goalkeeper who actually played.
            if player.position == "GK" and int(stat.minutes_played or 0) > 0:
                match = stat.match
                if match.home_goals is not None and match.away_goals is not None:
                    if stat.club_id == match.home_club_id:
                        totals["goals_conceded"] += int(match.away_goals)
                    elif stat.club_id == match.away_club_id:
                        totals["goals_conceded"] += int(match.home_goals)
        minutes = totals["minutes"]
        per90 = lambda value: (float(value) * 90.0 / minutes) if minutes > 0 else None
        totals["goals_per90"] = per90(totals["goals"])
        totals["assists_per90"] = per90(totals["assists"])
        totals["shots_per90"] = per90(totals["shots"])
        totals["shots_on_target_per90"] = per90(totals["shots_on_target"])
        totals["tackles_won_per90"] = per90(totals["tackles_won"])
        totals["interceptions_per90"] = per90(totals["interceptions"])
        totals["fouls_committed_per90"] = per90(totals["fouls_committed"])
        totals["yellow_cards_per90"] = per90(totals["yellow_cards"])
        totals["red_cards_per90"] = per90(totals["red_cards"])
        totals["penalty_conceded_per90"] = per90(totals["penalty_conceded"])
        totals["own_goals_per90"] = per90(totals["own_goals"])
        totals["key_passes_per90"] = per90(totals["key_passes"])
        totals["passes_attempted_per90"] = per90(totals["passes_attempted"])
        totals["crosses_per90"] = per90(totals["crosses"])
        totals["saves_per90"] = per90(totals["saves"])
        totals["pass_ratio"] = PlayerRadarAPIView._safe_divide(totals["passes_completed"], totals["passes_attempted"])
        totals["dribble_ratio"] = PlayerRadarAPIView._safe_divide(totals["dribbles_completed"], totals["dribbles_attempted"])
        totals["shot_ratio"] = PlayerRadarAPIView._safe_divide(totals["shots_on_target"], totals["shots"])
        totals["save_ratio"] = PlayerRadarAPIView._safe_divide(totals["saves"], totals["shots_faced"])
        totals["penalty_save_ratio"] = PlayerRadarAPIView._safe_divide(totals["penalty_saved"], totals["penalty_faced"])
        totals["goals_conceded_per90"] = per90(totals["goals_conceded"])
        return totals

    def get(self, request, player_id):
        player = get_object_or_404(Player, pk=player_id)
        season = (request.query_params.get("season") or "").strip()
        completed = Match.objects.filter(status="COMPLETED")
        # An empty season means "All Seasons": aggregate every completed
        # match across the player's full available history. Only apply a
        # season filter when the user explicitly selects one.
        if season:
            completed = completed.filter(season=season)

        rows = list(PlayerStatistics.objects.filter(
            player=player, match__in=completed
        ).select_related("match", "club").order_by("match__match_date"))
        current = self._aggregate_player(player, rows)
        if not rows:
            return Response({"status": "no_statistics", "player_id": player.id,
                             "player_name": player.name, "position": player.position,
                             "season": season, "minutes": 0, "cohort_size": 0,
                             "scores": {"attacking": None, "defending": None,
                                        "goalkeeping": None, "passing": None, "technique": None}})

        if current["minutes"] < self.MIN_MINUTES:
            return Response({"status": "insufficient_minutes", "player_id": player.id,
                             "player_name": player.name, "position": player.position,
                             "position_label": player.get_position_display(), "season": season,
                             "minutes": current["minutes"], "cohort_size": 0,
                             "scores": {"attacking": None, "defending": None,
                                        "goalkeeping": None, "passing": None, "technique": None}})

        cohort_players = Player.objects.filter(position=player.position)
        cohort_rows = PlayerStatistics.objects.filter(
            player__in=cohort_players, match__in=completed
        ).select_related("player", "match", "club", "match__home_club", "match__away_club").order_by("match__match_date")
        grouped = {}
        for stat in cohort_rows:
            grouped.setdefault(stat.player_id, []).append(stat)
        aggregates = []
        for peer in cohort_players:
            peer_rows = grouped.get(peer.id, [])
            if not peer_rows:
                continue
            aggregate = self._aggregate_player(peer, peer_rows)
            if aggregate["minutes"] >= self.MIN_MINUTES:
                aggregates.append(aggregate)

        cohort_size = len(aggregates)
        base_response = {
            "player_id": player.id, "player_name": player.name,
            "position": player.position, "position_label": player.get_position_display(),
            "season": season, "minutes": current["minutes"], "cohort_size": cohort_size,
            "minimum_minutes": self.MIN_MINUTES,
            "minimum_cohort_size": self.MIN_COHORT_SIZE,
        }
        empty_scores = {"attacking": None, "defending": None, "goalkeeping": None,
                        "passing": None, "technique": None}
        if cohort_size < self.MIN_COHORT_SIZE:
            return Response({**base_response, "status": "small_cohort", "scores": empty_scores})

        # Each component tuple: metric key, weight, higher-is-better.
        definitions = {
            "attacking": [("goals_per90", 40, True), ("assists_per90", 25, True),
                          ("shots_on_target_per90", 20, True), ("shots_per90", 15, True)],
            "defending": [("tackles_won_per90", 30, True), ("interceptions_per90", 30, True),
                          ("fouls_committed_per90", 10, False), ("yellow_cards_per90", 10, False),
                          ("red_cards_per90", 10, False), ("penalty_conceded_per90", 5, False),
                          ("own_goals_per90", 5, False)],
            "passing": [("pass_ratio", 35, True), ("key_passes_per90", 30, True),
                        ("passes_attempted_per90", 20, True), ("crosses_per90", 15, True)],
            "technique": [("pass_ratio", 35, True), ("dribble_ratio", 35, True),
                          ("shot_ratio", 30, True)],
            "goalkeeping": [("save_ratio", 40, True), ("penalty_save_ratio", 20, True),
                            ("saves_per90", 15, True), ("goals_conceded_per90", 25, False)],
        }
        scores = {}
        component_details = {}
        for attribute, components in definitions.items():
            if attribute == "goalkeeping" and player.position != "GK":
                scores[attribute] = None
                component_details[attribute] = []
                continue
            weighted_total = 0.0
            available_weight = 0.0
            details = []
            for key, weight, higher_is_better in components:
                value = current.get(key)
                peer_values = [peer.get(key) for peer in aggregates]
                percentile = self._percentile(value, peer_values, higher_is_better)
                if percentile is None:
                    details.append({"metric": key, "weight": weight, "score": None, "available": False})
                    continue
                weighted_total += percentile * weight
                available_weight += weight
                details.append({"metric": key, "weight": weight, "score": percentile, "available": True})
            scores[attribute] = round(weighted_total / available_weight, 2) if available_weight else None
            component_details[attribute] = details

        return Response({**base_response, "status": "ok", "scores": scores,
                         "components": component_details,
                         "method": "position-season midrank percentiles; per-90 count metrics; weighted component average"})

# ==================================================
# Dashboard API
# ==================================================

class DashboardAPIView(APIView):

    def get(self, request):

        # ==================================================
        # Overall Summary
        # ==================================================

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

        total_available_stats = PlayerStatistics.objects.count()

        # ==================================================
        # Top Performing Players
        # ==================================================

        top_players = list(
            PlayerStatistics.objects
            .filter(
                rating__isnull=False,
                player__is_active=True
            )
            .values(
                "player_id",
                "player__name",
                "player__position",
                "player__preferred_foot",
                "player__photo_path"
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

        # ==================================================
        # Statistical Leaders
        # ==================================================

        leader_specs = [
            ("goals", "Goals"),
            ("assists", "Assists"),
            ("red_cards", "Red Cards"),
            ("yellow_cards", "Yellow Cards"),
            ("saves", "Saves"),
        ]

        statistical_leaders = {}

        for stat_field, _label in leader_specs:
            leader = (
                PlayerStatistics.objects
                .filter(player__is_active=True)
                .values("player_id", "player__name", "player__photo_path")
                .annotate(total=Sum(stat_field))
                .filter(total__gt=0)
                .order_by("-total", "player__name")
                .first()
            )

            if leader:
                statistical_leaders[stat_field] = {
                    "player_id": leader["player_id"],
                    "player_name": leader["player__name"],
                    "photo_path": leader["player__photo_path"],
                    "total": leader["total"] or 0,
                }
            else:
                statistical_leaders[stat_field] = None

        # ==================================================
        # Position Summary
        # ==================================================

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

        # ==================================================
        # Next / Upcoming Matches
        # ==================================================

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

                # Club logos
                "home_logo": match.home_club.logo_path,

                "away_logo": match.away_club.logo_path,
            })

        # ==================================================
        # Recent Completed Matches
        # ==================================================

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

                # Club logos
                "home_logo": match.home_club.logo_path,

                "away_logo": match.away_club.logo_path,
            })

        # ==================================================
        # League Points Table
        # ==================================================

        # Dropdown options come from completed matches with a recorded score.
        scored_completed_matches = Match.objects.filter(
            status="COMPLETED",
            home_goals__isnull=False,
            away_goals__isnull=False,
        ).select_related("home_club", "away_club")

        standings_seasons = list(
            scored_completed_matches.exclude(season__isnull=True)
            .exclude(season="")
            .values_list("season", flat=True)
            .distinct()
            .order_by("-season")
        )

        standings_competitions = list(
            scored_completed_matches.exclude(competition__isnull=True)
            .exclude(competition="")
            .values_list("competition", flat=True)
            .distinct()
            .order_by("competition")
        )

        selected_standings_season = (request.query_params.get("season") or "").strip()
        selected_standings_competition = (request.query_params.get("competition") or "").strip()

        standings_matches = scored_completed_matches
        if selected_standings_season:
            standings_matches = standings_matches.filter(season=selected_standings_season)
        if selected_standings_competition:
            standings_matches = standings_matches.filter(competition=selected_standings_competition)

        standings_by_club = {}

        def get_standing(club):
            if club.id not in standings_by_club:
                standings_by_club[club.id] = {
                    "club_id": club.id,
                    "club_name": club.name,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_difference": 0,
                    "points": 0,
                }
            return standings_by_club[club.id]

        for match in standings_matches.order_by("match_date", "id"):
            home = get_standing(match.home_club)
            away = get_standing(match.away_club)
            home_goals = int(match.home_goals)
            away_goals = int(match.away_goals)

            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += home_goals
            home["goals_against"] += away_goals
            away["goals_for"] += away_goals
            away["goals_against"] += home_goals

            if home_goals > away_goals:
                home["won"] += 1
                away["lost"] += 1
                home["points"] += 3
            elif home_goals < away_goals:
                away["won"] += 1
                home["lost"] += 1
                away["points"] += 3
            else:
                home["drawn"] += 1
                away["drawn"] += 1
                home["points"] += 1
                away["points"] += 1

        standings = list(standings_by_club.values())
        for standing in standings:
            standing["goal_difference"] = standing["goals_for"] - standing["goals_against"]

        standings.sort(key=lambda row: (
            -row["points"],
            -row["goal_difference"],
            -row["goals_for"],
            row["club_name"].casefold(),
        ))

        # ==================================================
        # Final Dashboard Response
        # ==================================================

        return Response({

            # ------------------------------------------
            # Summary
            # ------------------------------------------

            "summary": {

                "total_players": total_players,

                "active_players": active_players,

                "total_clubs": total_clubs,

                "total_matches": total_matches,

                "completed_matches": completed_matches_count,

                "upcoming_matches": upcoming_matches_count,

                "total_available_stats": total_available_stats,
            },

            # ------------------------------------------
            # Top Players
            # ------------------------------------------

            "top_players": top_players,

            # ------------------------------------------
            # Statistical Leaders
            # ------------------------------------------

            "statistical_leaders": statistical_leaders,

            # ------------------------------------------
            # Position Summary
            # ------------------------------------------

            "position_summary": position_summary,

            # ------------------------------------------
            # Upcoming Matches
            # ------------------------------------------

            "upcoming_matches": upcoming_matches,

            # ------------------------------------------
            # Recent Results
            # ------------------------------------------

            "recent_matches": recent_matches,

            # ------------------------------------------
            # League Points Table
            # ------------------------------------------

            "standings": standings,
            "standings_seasons": standings_seasons,
            "standings_competitions": standings_competitions,
            "selected_standings_season": selected_standings_season,
            "selected_standings_competition": selected_standings_competition,
        })

# ==================================================
# Dashboard Page
# ==================================================

@login_required(login_url="/login/")
@never_cache
def player_dashboard(request):
    return render(
        request,
        "core/player_dashboard.html"
    )


# ==================================================
# Players Page
# ==================================================

@login_required(login_url="/login/")
@never_cache
def players_page(request):
    return render(
        request,
        "core/players.html"
    )


# ==================================================
# Player Performance Page
# ==================================================

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

    return render(
        request,
        "core/player_performance.html",
        {
            "player": player,
            "summary": summary,
        }
    )




# ==================================================
# Player Comparison
# ==================================================

@login_required(login_url="/login/")
@never_cache
def player_comparison_page(request):
    """
    Compare two players using all available completed-match statistics.
    An optional season query parameter restricts the comparison to one season.
    """
    players = Player.objects.select_related("current_club").filter(
        is_active=True
    ).order_by("name")

    # Use case-insensitive status matching so imported status capitalization
    # does not silently exclude valid completed matches.
    completed_matches = Match.objects.filter(status__iexact="COMPLETED")

    seasons = list(
        completed_matches.exclude(season="")
        .values_list("season", flat=True)
        .distinct()
        .order_by("-season")
    )

    player_a = None
    player_b = None
    comparison = None
    error_message = None
    season = request.GET.get("season", "").strip()
    id_a = request.GET.get("player_a", "").strip()
    id_b = request.GET.get("player_b", "").strip()

    # Resolve each player independently so Player A can be preselected from
    # the player performance page even before Player B is selected.
    if id_a:
        player_a = get_object_or_404(players, id=id_a)
    if id_b:
        player_b = get_object_or_404(players, id=id_b)

    if player_a and player_b:
        if player_a.id == player_b.id:
            error_message = "Please select two different players."
        else:
            def player_metrics(player):
                qs = PlayerStatistics.objects.filter(
                    player_id=player.id,
                    match__status__iexact="COMPLETED",
                ).select_related("match", "club")

                if season:
                    qs = qs.filter(match__season=season)

                # Count all recorded completed-match appearances. Do not filter
                # by rating: that incorrectly discards valid match statistics
                # whenever the rating is blank.
                aggregate_fields = (
                    "minutes_played",
                    "goals",
                    "assists",
                    "penalty_goals",
                    "penalty_attempts",
                    "shots",
                    "shots_on_target",
                    "passes_completed",
                    "passes_attempted",
                    "key_passes",
                    "crosses",
                    "dribbles_completed",
                    "dribbles_attempted",
                    "tackles_won",
                    "interceptions",
                    "yellow_cards",
                    "red_cards",
                    "fouls_committed",
                    "fouls_drawn",
                    "offsides",
                    "own_goals",
                    "penalty_won",
                    "penalty_conceded",
                    "shots_faced",
                    "saves",
                    "penalty_faced",
                    "penalty_saved",
                )

                aggregation = {
                    "appearances": Count("id"),
                    "starts": Count("id", filter=Q(started=True)),
                    "minutes": Sum("minutes_played"),
                    "average_rating": Avg("rating"),
                }
                for field in aggregate_fields:
                    aggregation[field] = Sum(field)

                values = qs.aggregate(**aggregation)

                for key, value in list(values.items()):
                    if key != "average_rating" and value is None:
                        values[key] = 0

                appearances = values.get("appearances") or 0
                minutes = values.get("minutes") or 0

                values["minutes_per_appearance"] = (
                    round(minutes / appearances, 1) if appearances else 0
                )
                values["goals_per_game"] = (
                    round((values.get("goals") or 0) / appearances, 2)
                    if appearances else 0
                )
                values["assists_per_game"] = (
                    round((values.get("assists") or 0) / appearances, 2)
                    if appearances else 0
                )
                values["shots_per_game"] = (
                    round((values.get("shots") or 0) / appearances, 2)
                    if appearances else 0
                )
                values["key_passes_per_game"] = (
                    round((values.get("key_passes") or 0) / appearances, 2)
                    if appearances else 0
                )

                attempted_passes = values.get("passes_attempted") or 0
                values["pass_accuracy"] = (
                    round((values.get("passes_completed") or 0) / attempted_passes * 100, 1)
                    if attempted_passes else None
                )

                attempted_dribbles = values.get("dribbles_attempted") or 0
                values["dribble_success"] = (
                    round((values.get("dribbles_completed") or 0) / attempted_dribbles * 100, 1)
                    if attempted_dribbles else None
                )

                total_shots = values.get("shots") or 0
                values["shot_accuracy"] = (
                    round((values.get("shots_on_target") or 0) / total_shots * 100, 1)
                    if total_shots else None
                )

                if values.get("average_rating") is not None:
                    values["average_rating"] = round(float(values["average_rating"]), 2)

                try:
                    ffi_result = calculate_ffi(
                        player_id=player.id,
                        season=season or None,
                    )
                    ffi_value = (
                        ffi_result.get("ffi", ffi_result.get("ffi_score"))
                        if isinstance(ffi_result, dict) else None
                    )
                    values["ffi"] = (
                        round(float(ffi_value), 2)
                        if ffi_value is not None else None
                    )
                except Exception:
                    values["ffi"] = None

                return values

            comparison = {
                "a": player_metrics(player_a),
                "b": player_metrics(player_b),
            }

    return render(
        request,
        "core/player_comparison.html",
        {
            "players": players,
            "seasons": seasons,
            "selected_season": season,
            "player_a": player_a,
            "player_b": player_b,
            "comparison": comparison,
            "error_message": error_message,
        },
    )

# ==================================================
# Player PDF Report
# ==================================================

@login_required(login_url="/login/")
@never_cache
def player_performance_report_pdf(request, player_id):
    """
    Download a player performance report as a PDF.
    Optional season filter: ?season=2025/26
    Requires ReportLab: pip install reportlab
    """
    player = get_object_or_404(
        Player.objects.select_related("current_club"),
        id=player_id,
    )
    season = request.GET.get("season", "").strip()

    statistics = PlayerStatistics.objects.filter(
        player=player,
        match__status="COMPLETED",
    ).select_related(
        "match", "club", "match__home_club", "match__away_club"
    ).order_by("match__match_date")

    if season:
        statistics = statistics.filter(match__season=season)

    summary = statistics.aggregate(
        appearances=Count("id"),
        minutes=Sum("minutes_played"),
        goals=Sum("goals"),
        assists=Sum("assists"),
        shots=Sum("shots"),
        key_passes=Sum("key_passes"),
        shots_on_target=Sum("shots_on_target"),
        passes_completed=Sum("passes_completed"),
        passes_attempted=Sum("passes_attempted"),
        average_rating=Avg("rating"),
    )

    # Import only when the PDF endpoint is requested.
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            KeepTogether,
        )
    except ImportError:
        return HttpResponse(
            "PDF generation requires ReportLab. Install it with: pip install reportlab",
            status=500,
            content_type="text/plain",
        )

    response = HttpResponse(content_type="application/pdf")
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", player.name).strip("_") or "player"
    response["Content-Disposition"] = (
        f'attachment; filename="{safe_name}_KickIQ_Report.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"KickIQ Player Report - {player.name}",
        author="KickIQ",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="KickIQTitle", parent=styles["Title"], alignment=TA_CENTER,
        textColor=colors.HexColor("#13834a"), spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="SmallCell", parent=styles["BodyText"], fontSize=7,
        leading=9,
    ))

    story = [
        Paragraph("KickIQ", styles["KickIQTitle"]),
        Paragraph("Player Performance Report", styles["Heading2"]),
        Spacer(1, 5),
        Paragraph(f"<b>Player:</b> {escape(player.name)}", styles["BodyText"]),
        Paragraph(
            f"<b>Club:</b> {escape(player.current_club.name if player.current_club else 'Not assigned')}",
            styles["BodyText"],
        ),
        Paragraph(
            f"<b>Position:</b> {escape(player.get_position_display())}",
            styles["BodyText"],
        ),
        Paragraph(
            f"<b>Season:</b> {escape(season or 'All seasons')}",
            styles["BodyText"],
        ),
        Paragraph(
            f"<b>Generated:</b> {localdate().strftime('%d %B %Y')}",
            styles["BodyText"],
        ),
        Spacer(1, 12),
    ]

    average_rating = summary["average_rating"]
    summary_rows = [
        ["Metric", "Value", "Metric", "Value"],
        ["Appearances", str(summary["appearances"] or 0),
         "Minutes played", str(summary["minutes"] or 0)],
        ["Goals", str(summary["goals"] or 0),
         "Assists", str(summary["assists"] or 0)],
        ["Average rating", f"{float(average_rating):.2f}" if average_rating is not None else "N/A",
         "Shots", str(summary["shots"] or 0)],
        ["Key passes", str(summary["key_passes"] or 0),
         "Matches in report", str(statistics.count())],
    ]
    summary_table = Table(summary_rows, colWidths=[38*mm, 30*mm, 38*mm, 30*mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14352a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f3f8f5")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d6e4db")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [Paragraph("Performance Summary", styles["Heading2"]), summary_table, Spacer(1, 8)]

    # Efficiency ratios are computed from the same filtered completed-match records.
    shots_total = summary.get("shots") or 0
    passes_attempted = summary.get("passes_attempted") or 0
    ratio_rows = [
        ["Efficiency metric", "Value"],
        ["Shot accuracy", f"{(summary.get('shots_on_target') or 0) / shots_total * 100:.1f}%" if shots_total else "N/A"],
        ["Pass completion", f"{(summary.get('passes_completed') or 0) / passes_attempted * 100:.1f}%" if passes_attempted else "N/A"],
    ]
    ratio_table = Table(ratio_rows, colWidths=[70*mm, 55*mm])
    ratio_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14352a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f3f8f5")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d6e4db")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [Paragraph("Efficiency Analysis", styles["Heading2"]), ratio_table, Spacer(1, 12)]

    # Embed a compact rating trend chart in the PDF rather than relying on browser-only charts.
    try:
        from reportlab.graphics.shapes import Drawing, String
        from reportlab.graphics.charts.linecharts import HorizontalLineChart
        rated_stats = [(st.match.match_date, float(st.rating)) for st in statistics if st.rating is not None]
        if rated_stats:
            drawing = Drawing(480, 175)
            chart = HorizontalLineChart()
            chart.x = 42
            chart.y = 28
            chart.width = 420
            chart.height = 112
            chart.data = [[value for _, value in rated_stats]]
            chart.categoryAxis.categoryNames = [date.strftime("%d-%b") for date, _ in rated_stats]
            chart.categoryAxis.labels.angle = 35
            chart.categoryAxis.labels.fontSize = 6
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = max(10, max(value for _, value in rated_stats))
            chart.valueAxis.valueStep = 2
            chart.lines[0].strokeColor = colors.HexColor("#13834a")
            chart.lines[0].strokeWidth = 2
            drawing.add(chart)
            drawing.add(String(42, 155, "Match rating trend", fontName="Helvetica-Bold", fontSize=10))
            story += [Paragraph("Rating Trend", styles["Heading2"]), drawing, Spacer(1, 8)]
    except Exception:
        # Charts are supplementary; the tabular report remains available if chart rendering fails.
        pass

    try:
        ffi_result = calculate_ffi(player_id=player.id, season=season or None)
        if isinstance(ffi_result, dict):
            ffi_value = ffi_result.get("ffi", ffi_result.get("ffi_score"))
            if ffi_value is not None:
                story += [
                    Paragraph("Football Form Index (FFI)", styles["Heading2"]),
                    Paragraph(f"<b>FFI score:</b> {escape(str(ffi_value))}", styles["BodyText"]),
                    Spacer(1, 10),
                ]
    except Exception:
        # A report can still be generated if FFI cannot be calculated.
        pass

    # Prediction is optional: report its output and explanation only when the existing
    # prediction service provides them. Do not make PDF generation depend on ML availability.
    try:
        prediction_result = predict_next_match_rating(player.id)
        if isinstance(prediction_result, dict):
            story.append(Paragraph("Next-Match Rating Prediction", styles["Heading2"]))
            predicted_value = next(
                (prediction_result.get(key) for key in
                 ("predicted_rating", "prediction", "predicted_rating_next_match", "predicted_value")
                 if prediction_result.get(key) is not None),
                None,
            )
            if predicted_value is not None:
                story.append(Paragraph(
                    f"<b>Predicted rating:</b> {escape(str(round(float(predicted_value), 2)))}",
                    styles["BodyText"],
                ))
            else:
                story.append(Paragraph(
                    "Prediction details were returned, but no recognised predicted-rating field was available.",
                    styles["BodyText"],
                ))

            # Common service response shapes are supported without assuming a single schema.
            explanation = None
            for key in ("shap_explanation", "shap_values", "feature_contributions", "explanation", "top_features"):
                if prediction_result.get(key) is not None:
                    explanation = prediction_result[key]
                    break
            if isinstance(explanation, dict):
                shap_rows = [["Feature", "Contribution / explanation"]]
                for feature, contribution in list(explanation.items())[:12]:
                    shap_rows.append([Paragraph(escape(str(feature)), styles["SmallCell"]),
                                      Paragraph(escape(str(contribution)), styles["SmallCell"])])
                shap_table = Table(shap_rows, colWidths=[65*mm, 105*mm], repeatRows=1)
                shap_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14352a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d6e4db")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f8f5")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]))
                story += [Paragraph("SHAP / Prediction Explanation", styles["Heading3"]), shap_table, Spacer(1, 8)]
            elif isinstance(explanation, (list, tuple)) and explanation:
                expl_rows = [["Prediction explanation"]]
                for item in explanation[:12]:
                    expl_rows.append([Paragraph(escape(str(item)), styles["SmallCell"])])
                expl_table = Table(expl_rows, colWidths=[170*mm], repeatRows=1)
                expl_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14352a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d6e4db")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]))
                story += [Paragraph("SHAP / Prediction Explanation", styles["Heading3"]), expl_table, Spacer(1, 8)]
            else:
                story.append(Paragraph(
                    "A structured SHAP explanation was not available from the prediction service for this report.",
                    styles["SmallCell"],
                ))
            story.append(Spacer(1, 8))
    except Exception:
        story += [
            Paragraph("Next-Match Rating Prediction", styles["Heading2"]),
            Paragraph("Prediction was unavailable when this report was generated; historical analysis is included below.", styles["BodyText"]),
            Spacer(1, 8),
        ]

    story.append(Paragraph("Match-by-Match Statistics", styles["Heading2"]))
    match_rows = [[
        "Date", "Season", "Opponent", "H/A", "Min", "G", "A", "Rating"
    ]]
    for stat in statistics:
        match = stat.match
        is_home = stat.club_id == match.home_club_id
        opponent = match.away_club.name if is_home else match.home_club.name
        match_rows.append([
            stat.match.match_date.strftime("%d-%m-%Y"),
            str(match.season),
            Paragraph(escape(opponent), styles["SmallCell"]),
            "H" if is_home else "A",
            str(stat.minutes_played),
            str(stat.goals),
            str(stat.assists),
            f"{float(stat.rating):.2f}" if stat.rating is not None else "N/A",
        ])

    match_table = Table(
        match_rows,
        repeatRows=1,
        colWidths=[22*mm, 20*mm, 47*mm, 12*mm, 15*mm, 10*mm, 10*mm, 19*mm],
    )
    match_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14352a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d6e4db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white, colors.HexColor("#f3f8f5")
        ]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(match_table)
    doc.build(story)
    return response



# ==================================================
# Player Comparison PDF Report
# ==================================================

@login_required(login_url="/login/")
@never_cache
def player_comparison_report_pdf(request):
    """Download a PDF for the two players currently selected on the comparison page."""
    player_a_id = (request.GET.get("player_a") or "").strip()
    player_b_id = (request.GET.get("player_b") or "").strip()
    season = (request.GET.get("season") or "").strip()

    if not player_a_id or not player_b_id:
        return HttpResponse("Select two players before generating the comparison report.", status=400,
                            content_type="text/plain")
    if player_a_id == player_b_id:
        return HttpResponse("Choose two different players for comparison.", status=400,
                            content_type="text/plain")

    players = Player.objects.select_related("current_club")
    player_a = get_object_or_404(players, id=player_a_id)
    player_b = get_object_or_404(players, id=player_b_id)

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    except ImportError:
        return HttpResponse(
            "PDF generation requires ReportLab. Install it with: pip install reportlab",
            status=500, content_type="text/plain"
        )

    aggregate_fields = (
        "minutes_played", "goals", "assists", "penalty_goals", "penalty_attempts",
        "shots", "shots_on_target", "passes_completed", "passes_attempted", "key_passes",
        "crosses", "dribbles_completed", "dribbles_attempted", "tackles_won",
        "interceptions", "yellow_cards", "red_cards", "fouls_committed", "fouls_drawn",
        "offsides", "own_goals", "penalty_won", "penalty_conceded", "shots_faced",
        "saves", "penalty_faced", "penalty_saved",
    )

    def player_metrics(player):
        qs = PlayerStatistics.objects.filter(
            player_id=player.id, match__status__iexact="COMPLETED"
        )
        if season:
            qs = qs.filter(match__season=season)
        aggregation = {
            "appearances": Count("id"),
            "starts": Count("id", filter=Q(started=True)),
            "minutes": Sum("minutes_played"),
            "average_rating": Avg("rating"),
        }
        for field in aggregate_fields:
            aggregation[field] = Sum(field)
        values = qs.aggregate(**aggregation)
        for key, value in list(values.items()):
            if key != "average_rating" and value is None:
                values[key] = 0
        apps = values.get("appearances") or 0
        minutes = values.get("minutes") or 0
        values["minutes_per_appearance"] = round(minutes / apps, 1) if apps else 0
        values["goals_per_game"] = round((values.get("goals") or 0) / apps, 2) if apps else 0
        values["assists_per_game"] = round((values.get("assists") or 0) / apps, 2) if apps else 0
        values["shots_per_game"] = round((values.get("shots") or 0) / apps, 2) if apps else 0
        values["key_passes_per_game"] = round((values.get("key_passes") or 0) / apps, 2) if apps else 0
        for key, numerator, denominator in (
            ("pass_accuracy", "passes_completed", "passes_attempted"),
            ("dribble_success", "dribbles_completed", "dribbles_attempted"),
            ("shot_accuracy", "shots_on_target", "shots"),
        ):
            den = values.get(denominator) or 0
            values[key] = round((values.get(numerator) or 0) / den * 100, 1) if den else None
        if values.get("average_rating") is not None:
            values["average_rating"] = round(float(values["average_rating"]), 2)
        try:
            ffi_result = calculate_ffi(player_id=player.id, season=season or None)
            ffi_value = ffi_result.get("ffi", ffi_result.get("ffi_score")) if isinstance(ffi_result, dict) else None
            values["ffi"] = round(float(ffi_value), 2) if ffi_value is not None else None
        except Exception:
            values["ffi"] = None
        return values

    a = player_metrics(player_a)
    b = player_metrics(player_b)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="KickIQ_Comparison_{player_a.id}_vs_{player_b.id}.pdf"'
    )
    doc = SimpleDocTemplate(
        response, pagesize=landscape(A4), rightMargin=14*mm, leftMargin=14*mm,
        topMargin=13*mm, bottomMargin=13*mm,
        title=f"KickIQ Player Comparison - {player_a.name} vs {player_b.name}", author="KickIQ"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ComparisonTitle", parent=styles["Title"], alignment=TA_CENTER,
                              textColor=colors.HexColor("#13834a"), spaceAfter=8))
    styles.add(ParagraphStyle(name="ComparisonCell", parent=styles["BodyText"], fontSize=8, leading=10))
    story = [
        Paragraph("KickIQ", styles["ComparisonTitle"]),
        Paragraph("Player Comparison Report", styles["Heading2"]),
        Paragraph(f"<b>Player A:</b> {escape(player_a.name)} &nbsp; | &nbsp; "
                  f"<b>Club:</b> {escape(player_a.current_club.name if player_a.current_club else 'Not assigned')} "
                  f"&nbsp; | &nbsp; <b>Position:</b> {escape(player_a.get_position_display())}", styles["BodyText"]),
        Paragraph(f"<b>Player B:</b> {escape(player_b.name)} &nbsp; | &nbsp; "
                  f"<b>Club:</b> {escape(player_b.current_club.name if player_b.current_club else 'Not assigned')} "
                  f"&nbsp; | &nbsp; <b>Position:</b> {escape(player_b.get_position_display())}", styles["BodyText"]),
        Paragraph(f"<b>Scope:</b> {escape(season or 'All completed seasons')} &nbsp; | &nbsp; "
                  f"<b>Generated:</b> {localdate().strftime('%d %B %Y')}", styles["BodyText"]),
        Spacer(1, 10),
    ]

    metric_labels = [
        ("Appearances", "appearances"), ("Starts", "starts"), ("Total minutes", "minutes"),
        ("Minutes per appearance", "minutes_per_appearance"), ("Goals", "goals"),
        ("Goals per game", "goals_per_game"), ("Assists", "assists"),
        ("Assists per game", "assists_per_game"), ("Shots", "shots"),
        ("Shots on target", "shots_on_target"), ("Shot accuracy", "shot_accuracy"),
        ("Key passes", "key_passes"), ("Key passes per game", "key_passes_per_game"),
        ("Crosses", "crosses"), ("Passes completed", "passes_completed"),
        ("Passes attempted", "passes_attempted"), ("Pass completion", "pass_accuracy"),
        ("Tackles won", "tackles_won"), ("Interceptions", "interceptions"),
        ("Dribbles completed", "dribbles_completed"), ("Dribbles attempted", "dribbles_attempted"),
        ("Dribble success", "dribble_success"), ("Saves", "saves"),
        ("Shots faced", "shots_faced"), ("Penalties saved", "penalty_saved"),
        ("Yellow cards", "yellow_cards"), ("Red cards", "red_cards"),
        ("Fouls committed", "fouls_committed"), ("Fouls drawn", "fouls_drawn"),
        ("Offsides", "offsides"), ("Average rating", "average_rating"), ("Football Form Index (FFI)", "ffi"),
    ]
    rows = [["Statistic", player_a.name, player_b.name]]
    for label, key in metric_labels:
        va, vb = a.get(key), b.get(key)
        if key in ("shot_accuracy", "pass_accuracy", "dribble_success"):
            va = f"{va:.1f}%" if va is not None else "N/A"
            vb = f"{vb:.1f}%" if vb is not None else "N/A"
        else:
            va = f"{va:.2f}" if isinstance(va, float) else (str(va) if va is not None else "N/A")
            vb = f"{vb:.2f}" if isinstance(vb, float) else (str(vb) if vb is not None else "N/A")
        rows.append([label, va, vb])
    table = Table(rows, colWidths=[82*mm, 82*mm, 82*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14352a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d6e4db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f8f5")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [Paragraph("Side-by-Side Statistics", styles["Heading2"]), table, Spacer(1, 10)]

    # PDF-native bar chart mirrors the two browser comparison charts.
    try:
        from reportlab.graphics.shapes import Drawing, String
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        drawing = Drawing(720, 230)
        chart = VerticalBarChart()
        chart.x, chart.y, chart.width, chart.height = 55, 35, 630, 160
        chart.data = [
            [float(a.get("goals") or 0), float(a.get("assists") or 0),
             float(a.get("shots") or 0), float(a.get("key_passes") or 0)],
            [float(b.get("goals") or 0), float(b.get("assists") or 0),
             float(b.get("shots") or 0), float(b.get("key_passes") or 0)],
        ]
        chart.categoryAxis.categoryNames = ["Goals", "Assists", "Shots", "Key passes"]
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = max(1, max(max(chart.data[0]), max(chart.data[1])) * 1.15)
        chart.valueAxis.valueStep = max(1, int(chart.valueAxis.valueMax / 5))
        chart.groupSpacing = 8
        chart.barWidth = 12
        chart.bars[0].fillColor = colors.HexColor("#13834a")
        chart.bars[1].fillColor = colors.HexColor("#777bff")
        drawing.add(chart)
        drawing.add(String(55, 210, "Core statistics comparison", fontName="Helvetica-Bold", fontSize=10))
        story += [Paragraph("Visual Comparison", styles["Heading2"]), drawing]
    except Exception:
        pass

    doc.build(story)
    return response


# ==================================================
# Login Page
# ==================================================

def login_page(request):

    if request.user.is_authenticated:

        if request.user.is_staff:
            return redirect("/admin/")

        return redirect("/dashboard/")

    return render(
        request,
        "core/login.html"
    )


# ==================================================
# Register Page
# ==================================================

def register_page(request):

    return render(
        request,
        "core/register.html"
    )


# ==================================================
# Home
# ==================================================

def home(request):

    if not request.user.is_authenticated:
        return redirect("/login/")

    if request.user.is_staff:
        return redirect("/admin/")

    return redirect("/dashboard/")