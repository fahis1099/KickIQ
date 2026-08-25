from django.db import models


class Club(models.Model):
    name = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=100, blank=True)
    logo_path = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    POSITION_CHOICES = [
        ("GK", "Goalkeeper"),
        ("DF", "Defender"),
        ("MF", "Midfielder"),
        ("FW", "Forward"),
    ]

    name = models.CharField(max_length=100)
    current_club = models.ForeignKey(
        Club,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_players"
    )
    position = models.CharField(
        max_length=2,
        choices=POSITION_CHOICES
    )
    nationality = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    jersey_number = models.PositiveIntegerField(null=True, blank=True)
    photo_path = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Match(models.Model):
    STATUS_CHOICES = [
        ("UPCOMING", "Upcoming"),
        ("COMPLETED", "Completed"),
        ("POSTPONED", "Postponed"),
        ("CANCELLED", "Cancelled"),
    ]

    season = models.CharField(max_length=10)
    competition = models.CharField(max_length=100)
    match_date = models.DateField()

    home_club = models.ForeignKey(
        Club,
        on_delete=models.PROTECT,
        related_name="home_matches"
    )
    away_club = models.ForeignKey(
        Club,
        on_delete=models.PROTECT,
        related_name="away_matches"
    )

    home_goals = models.PositiveIntegerField(null=True, blank=True)
    away_goals = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="UPCOMING"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "season",
                    "match_date",
                    "home_club",
                    "away_club",
                ],
                name="unique_match_per_season"
            )
        ]

    def __str__(self):
        return f"{self.home_club} vs {self.away_club} ({self.season})"


class PlayerStatistics(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="statistics"
    )

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="player_statistics"
    )

    # Club represented by the player in THIS match.
    # Important for historical transfers.
    club = models.ForeignKey(
        Club,
        on_delete=models.PROTECT,
        related_name="player_statistics"
    )

    # General
    minutes_played = models.PositiveIntegerField(default=0)

    started = models.BooleanField(default=False)

    goals = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)

    penalty_goals = models.PositiveIntegerField(default=0)
    penalty_attempts = models.PositiveIntegerField(default=0)

    shots = models.PositiveIntegerField(default=0)
    shots_on_target = models.PositiveIntegerField(default=0)

    # Passing
    passes_completed = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    passes_attempted = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    key_passes = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # Crossing / Dribbling
    crosses = models.PositiveIntegerField(default=0)

    dribbles_completed = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    dribbles_attempted = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # Defensive
    tackles_won = models.PositiveIntegerField(default=0)
    interceptions = models.PositiveIntegerField(default=0)

    yellow_cards = models.PositiveIntegerField(default=0)
    red_cards = models.PositiveIntegerField(default=0)

    fouls_committed = models.PositiveIntegerField(default=0)
    fouls_drawn = models.PositiveIntegerField(default=0)

    offsides = models.PositiveIntegerField(default=0)

    own_goals = models.PositiveIntegerField(default=0)

    penalty_won = models.PositiveIntegerField(default=0)
    penalty_conceded = models.PositiveIntegerField(default=0)

    # Goalkeeper
    shots_faced = models.PositiveIntegerField(default=0)
    saves = models.PositiveIntegerField(default=0)

    penalty_faced = models.PositiveIntegerField(default=0)
    penalty_saved = models.PositiveIntegerField(default=0)

    # Target variable
    rating = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "match"],
                name="unique_player_statistics_per_match"
            )
        ]

    def __str__(self):
        return f"{self.player} - {self.match}"


class Prediction(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("EVALUATED", "Evaluated"),
    ]

    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="predictions"
    )

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="predictions"
    )

    predicted_rating = models.DecimalField(
        max_digits=4,
        decimal_places=2
    )

    actual_rating = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    prediction_error = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    predicted_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "match"],
                name="unique_prediction_per_player_match"
            )
        ]

    def __str__(self):
        return f"{self.player} - {self.match} - {self.predicted_rating}"