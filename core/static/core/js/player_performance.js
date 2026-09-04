document.addEventListener("DOMContentLoaded", function () {
    setupLogout();
    loadPlayerPerformance();
});


async function loadPlayerPerformance() {

    try {

        const playerId = getPlayerIdFromURL();

        const response = await fetch(
            `/api/players/${playerId}/statistics/`
        );

        if (!response.ok) {
            throw new Error("Failed to load player statistics");
        }

        const data = await response.json();

        /*
            Handle both possible API response formats:

            Format 1:
            [
                {...},
                {...}
            ]

            Format 2:
            {
                "count": 21,
                "results": [
                    {...},
                    {...}
                ]
            }
        */

        const statistics = Array.isArray(data)
            ? data
            : (data.results || []);

        console.log("Player statistics:", statistics);

        createRatingChart(statistics);
        createMinutesChart(statistics);
        createPositionAnalysis(statistics);
        createPerformanceTable(statistics);

    } catch (error) {

        console.error(
            "Player performance loading error:",
            error
        );

        const tableBody =
            document.getElementById("performance-table-body");

        if (tableBody) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="10" class="no-data-row">
                        Unable to load performance data.
                    </td>
                </tr>
            `;

        }

    }
}


function getPlayerIdFromURL() {

    const pathParts = window.location.pathname
        .split("/")
        .filter(Boolean);

    return pathParts[pathParts.length - 1];
}


function createRatingChart(statistics) {

    const canvas =
        document.getElementById("rating-chart");

    if (!canvas) {
        return;
    }


    /*
        Only use matches where a rating exists.
    */

    const ratedMatches = statistics
        .filter(stat => stat.rating !== null)
        .reverse();


    if (ratedMatches.length === 0) {

        return;

    }


    const labels = ratedMatches.map(function (stat, index) {

        return `Match ${index + 1}`;

    });


    const ratings = ratedMatches.map(function (stat) {

        return Number(stat.rating);

    });


    new Chart(canvas, {

        type: "line",

        data: {

            labels: labels,

            datasets: [
                {
                    label: "Rating",

                    data: ratings,

                    tension: 0.3,

                    borderWidth: 2,

                    pointRadius: 4,

                    pointHoverRadius: 6,

                    fill: false
                }
            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            scales: {

                y: {

                    min: 0,
                    max: 10,

                    title: {
                        display: true,
                        text: "Rating"
                    }

                },

                x: {

                    title: {
                        display: true,
                        text: "Matches"
                    }

                }

            },

            plugins: {

                legend: {
                    display: true
                },

                tooltip: {

                    callbacks: {

                        label: function (context) {

                            return `Rating: ${context.parsed.y}`;

                        }

                    }

                }

            }

        }

    });
}


function createMinutesChart(statistics) {

    const canvas =
        document.getElementById("minutes-chart");

    if (!canvas) {
        return;
    }


    /*
        Keep statistics that contain
        actual playing information.
    */

    const matchStatistics = statistics
        .filter(stat => stat.minutes_played !== null)
        .reverse();


    if (matchStatistics.length === 0) {

        return;

    }


    const labels = matchStatistics.map(function (stat, index) {

        return `Match ${index + 1}`;

    });


    const minutes = matchStatistics.map(function (stat) {

        return Number(stat.minutes_played);

    });


    new Chart(canvas, {

        type: "bar",

        data: {

            labels: labels,

            datasets: [
                {
                    label: "Minutes Played",

                    data: minutes,

                    borderWidth: 1
                }
            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            scales: {

                y: {

                    beginAtZero: true,

                    title: {
                        display: true,
                        text: "Minutes"
                    }

                },

                x: {

                    title: {
                        display: true,
                        text: "Matches"
                    }

                }

            },

            plugins: {

                legend: {
                    display: true
                },

                tooltip: {

                    callbacks: {

                        label: function (context) {

                            const index =
                                context.dataIndex;

                            const stat =
                                matchStatistics[index];

                            const started =
                                stat.started
                                    ? "Yes"
                                    : "No";

                            return [
                                `Minutes: ${stat.minutes_played}`,
                                `Started: ${started}`
                            ];

                        }

                    }

                }

            }

        }

    });
}

function createPositionAnalysis(statistics) {

    const container =
        document.getElementById("position-metrics");

    const description =
        document.getElementById("position-description");

    if (!container) {
        return;
    }


    /*
        Get player position from the page.
    */

    const positionElement =
        document.querySelector(".position");

    if (!positionElement) {
        return;
    }


    const position =
        positionElement.textContent.trim();


    /*
        Calculate totals.
    */

    const totalGoals = statistics.reduce(
        (sum, stat) => sum + Number(stat.goals || 0),
        0
    );

    const totalAssists = statistics.reduce(
        (sum, stat) => sum + Number(stat.assists || 0),
        0
    );

    const totalShots = statistics.reduce(
        (sum, stat) => sum + Number(stat.shots || 0),
        0
    );

    const totalShotsOnTarget = statistics.reduce(
        (sum, stat) => sum + Number(stat.shots_on_target || 0),
        0
    );

    const totalKeyPasses = statistics.reduce(
        (sum, stat) => sum + Number(stat.key_passes || 0),
        0
    );

    const totalTackles = statistics.reduce(
        (sum, stat) => sum + Number(stat.tackles_won || 0),
        0
    );

    const totalInterceptions = statistics.reduce(
        (sum, stat) => sum + Number(stat.interceptions || 0),
        0
    );

    const totalPassesCompleted = statistics.reduce(
        (sum, stat) => sum + Number(stat.passes_completed || 0),
        0
    );

    const totalPassesAttempted = statistics.reduce(
        (sum, stat) => sum + Number(stat.passes_attempted || 0),
        0
    );

    const totalDribblesCompleted = statistics.reduce(
        (sum, stat) => sum + Number(stat.dribbles_completed || 0),
        0
    );

    const totalDribblesAttempted = statistics.reduce(
        (sum, stat) => sum + Number(stat.dribbles_attempted || 0),
        0
    );

    const totalSaves = statistics.reduce(
        (sum, stat) => sum + Number(stat.saves || 0),
        0
    );

    const totalShotsFaced = statistics.reduce(
        (sum, stat) => sum + Number(stat.shots_faced || 0),
        0
    );

    const totalPenaltySaved = statistics.reduce(
        (sum, stat) => sum + Number(stat.penalty_saved || 0),
        0
    );


    /*
        Calculate percentages.
    */

    const passAccuracy =
        totalPassesAttempted > 0
            ? (totalPassesCompleted / totalPassesAttempted) * 100
            : 0;


    const dribbleSuccess =
        totalDribblesAttempted > 0
            ? (totalDribblesCompleted / totalDribblesAttempted) * 100
            : 0;


    const shotAccuracy =
        totalShots > 0
            ? (totalShotsOnTarget / totalShots) * 100
            : 0;


    const savePercentage =
        totalShotsFaced > 0
            ? (totalSaves / totalShotsFaced) * 100
            : 0;


    /*
        Position-specific metrics.
    */

    let metrics = [];


    if (position === "FW") {

        description.textContent =
            "Attacking indicators for forwards";

        metrics = [

            {
                label: "Goals",
                value: totalGoals
            },

            {
                label: "Assists",
                value: totalAssists
            },

            {
                label: "Shots",
                value: totalShots
            },

            {
                label: "Shot Accuracy",
                value: `${shotAccuracy.toFixed(1)}%`
            },

            {
                label: "Key Passes",
                value: totalKeyPasses
            },

            {
                label: "Dribble Success",
                value: `${dribbleSuccess.toFixed(1)}%`
            }

        ];

    }


    else if (position === "MF") {

        description.textContent =
            "Creative and ball-progression indicators for midfielders";

        metrics = [

            {
                label: "Assists",
                value: totalAssists
            },

            {
                label: "Key Passes",
                value: totalKeyPasses
            },

            {
                label: "Pass Accuracy",
                value: `${passAccuracy.toFixed(1)}%`
            },

            {
                label: "Dribble Success",
                value: `${dribbleSuccess.toFixed(1)}%`
            },

            {
                label: "Tackles Won",
                value: totalTackles
            },

            {
                label: "Interceptions",
                value: totalInterceptions
            }

        ];

    }


    else if (position === "DF") {

        description.textContent =
            "Defensive and ball-retention indicators for defenders";

        metrics = [

            {
                label: "Tackles Won",
                value: totalTackles
            },

            {
                label: "Interceptions",
                value: totalInterceptions
            },

            {
                label: "Pass Accuracy",
                value: `${passAccuracy.toFixed(1)}%`
            },

            {
                label: "Dribble Success",
                value: `${dribbleSuccess.toFixed(1)}%`
            },

            {
                label: "Key Passes",
                value: totalKeyPasses
            },

            {
                label: "Assists",
                value: totalAssists
            }

        ];

    }


    else if (position === "GK") {

        description.textContent =
            "Goalkeeping indicators based on shots faced and saves";

        metrics = [

            {
                label: "Saves",
                value: totalSaves
            },

            {
                label: "Shots Faced",
                value: totalShotsFaced
            },

            {
                label: "Save Percentage",
                value: `${savePercentage.toFixed(1)}%`
            },

            {
                label: "Penalty Saves",
                value: totalPenaltySaved
            },

            {
                label: "Pass Accuracy",
                value: `${passAccuracy.toFixed(1)}%`
            },

            {
                label: "Interceptions",
                value: totalInterceptions
            }

        ];

    }


    else {

        description.textContent =
            "General performance indicators";

        metrics = [

            {
                label: "Goals",
                value: totalGoals
            },

            {
                label: "Assists",
                value: totalAssists
            },

            {
                label: "Shots",
                value: totalShots
            },

            {
                label: "Key Passes",
                value: totalKeyPasses
            },

            {
                label: "Tackles Won",
                value: totalTackles
            },

            {
                label: "Interceptions",
                value: totalInterceptions
            }

        ];

    }


    /*
        Display metrics.
    */

    container.innerHTML = "";


    metrics.forEach(function (metric) {

        const card =
            document.createElement("div");

        card.className =
            "position-metric";


        card.innerHTML = `

            <span class="position-metric-label">
                ${metric.label}
            </span>

            <strong class="position-metric-value">
                ${metric.value}
            </strong>

        `;


        container.appendChild(card);

    });
}

function createPerformanceTable(statistics) {

    const tableBody =
        document.getElementById("performance-table-body");

    if (!tableBody) {

        console.error(
            "Performance table body not found."
        );

        return;
    }


    /*
        Only statistics with a match date
        are displayed.

        Newest match first.
    */

    const completedMatches = statistics
        .filter(stat => stat.match_date)
        .sort(function (a, b) {

            return new Date(b.match_date) -
                   new Date(a.match_date);

        });


    if (completedMatches.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="no-data-row">
                    No completed match statistics available.
                </td>
            </tr>
        `;

        return;
    }


    tableBody.innerHTML = "";


    completedMatches.forEach(function (stat) {

        const playerClub =
            stat.club_name;

        let opponent = "";
        let venue = "";


        if (stat.home_club_name === playerClub) {

            opponent = stat.away_club_name;
            venue = "Home";

        } else {

            opponent = stat.home_club_name;
            venue = "Away";

        }


        const row =
            document.createElement("tr");


        row.innerHTML = `

            <td>
                ${formatDate(stat.match_date)}
            </td>

            <td class="opponent">
                ${opponent}
            </td>

            <td>
                <span class="venue ${venue.toLowerCase()}">
                    ${venue}
                </span>
            </td>

            <td>
                ${stat.started ? "Yes" : "No"}
            </td>

            <td>
                ${stat.minutes_played ?? 0}
            </td>

            <td>
                ${stat.goals ?? 0}
            </td>

            <td>
                ${stat.assists ?? 0}
            </td>

            <td>
                ${stat.shots ?? 0}
            </td>

            <td>
                ${stat.key_passes ?? 0}
            </td>

            <td class="rating">
                ${stat.rating ?? "—"}
            </td>

        `;


        tableBody.appendChild(row);

    });
}


function formatDate(dateString) {

    if (!dateString) {
        return "—";
    }


    const date = new Date(dateString);


    return date.toLocaleDateString(
        "en-GB",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );
}


function setupLogout() {

    const button =
        document.getElementById("logout-btn");

    if (!button) {
        return;
    }


    button.addEventListener(
        "click",
        async function () {

            try {

                const response = await fetch(
                    "/api/auth/logout/",
                    {
                        method: "POST"
                    }
                );


                const data =
                    await response.json();


                if (data.success) {

                    sessionStorage.clear();

                    window.location.href =
                        "/login/";

                } else {

                    alert(
                        data.message ||
                        "Logout failed."
                    );

                }

            } catch (error) {

                console.error(
                    "Logout error:",
                    error
                );

                alert(
                    "Unable to logout. Please try again."
                );

            }

        }
    );
}