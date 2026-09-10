document.addEventListener("DOMContentLoaded", function () {

    loadDashboard();

    setupLogout();

});


async function loadDashboard() {

    try {

        const response = await fetch("/api/dashboard/");

        if (!response.ok) {
            throw new Error("Failed to load dashboard data");
        }

        const data = await response.json();

        updateSummary(data.summary);

        updateTopPlayers(data.top_players);

        updatePositionChart(data.position_summary);

        updateUpcomingMatches(data.upcoming_matches);

        updateRecentMatches(data.recent_matches);

    }

    catch (error) {

        console.error("Dashboard error:", error);

    }

}


/* =====================================
   SUMMARY
===================================== */

function updateSummary(summary) {

    document.getElementById("total-players").textContent =
        summary.total_players;

    document.getElementById("active-players").textContent =
        summary.active_players;

    document.getElementById("total-clubs").textContent =
        summary.total_clubs;

    document.getElementById("total-matches").textContent =
        summary.total_matches;

    document.getElementById("completed-matches").textContent =
        summary.completed_matches;

    document.getElementById("upcoming-matches").textContent =
        summary.upcoming_matches;

    document.getElementById("average-rating").textContent =
        summary.average_rating;
}


/* =====================================
   TOP PLAYERS
===================================== */

function updateTopPlayers(players) {

    const tbody =
        document.getElementById("top-players-body");

    tbody.innerHTML = "";

    if (!players || players.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="loading">
                    No player data available.
                </td>
            </tr>
        `;

        return;
    }


    players.forEach(function (player, index) {

        const row = document.createElement("tr");

        row.innerHTML = `

            <td>${index + 1}</td>

            <td class="player-name">
                ${player.player__name}
            </td>

            <td>
                ${formatPosition(player.player__position)}
            </td>

            <td class="rating">
                ${player.average_rating}
            </td>

            <td>
                ${player.appearances}
            </td>

            <td>
                ${player.goals}
            </td>

            <td>
                ${player.assists}
            </td>

        `;

        tbody.appendChild(row);

    });

}


/* =====================================
   POSITION CHART
===================================== */

function updatePositionChart(positionData) {

    const labels = positionData.map(
        item => formatPosition(item.player__position)
    );

    const ratings = positionData.map(
        item => item.average_rating
    );


    new Chart(
        document.getElementById("positionChart"),
        {
            type: "bar",

            data: {

                labels: labels,

                datasets: [
                    {
                        label: "Average Rating",

                        data: ratings,

                        borderWidth: 1
                    }
                ]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                scales: {

                    y: {
                        beginAtZero: false,

                        min: 6,

                        max: 8
                    }

                },

                plugins: {

                    legend: {
                        display: false
                    }

                }

            }

        }
    );

}


/* =====================================
   UPCOMING MATCHES
===================================== */

function updateUpcomingMatches(matches) {

    const container =
        document.getElementById(
            "upcoming-matches-container"
        );


    container.innerHTML = "";


    if (!matches || matches.length === 0) {

        container.innerHTML = `
            <div class="loading">
                No upcoming matches available.
            </div>
        `;

        return;
    }


    matches.forEach(function (match) {

        const item = document.createElement("div");

        item.className = "match-item";


        /*
         * Convert:
         *
         * logos/arsenal.png
         *
         * into:
         *
         * /static/core/images/logos/arsenal.png
         */

        const homeLogo = getLogoURL(
            match.home_logo
        );

        const awayLogo = getLogoURL(
            match.away_logo
        );


        item.innerHTML = `

            <div class="match-date">
                ${formatDate(match.date)}
            </div>


            <div class="match-teams">

                <div class="match-team">

                    ${createClubLogo(
                        homeLogo,
                        match.home_club
                    )}

                    <span>
                        ${match.home_club}
                    </span>

                </div>


                <div class="match-vs">
                    VS
                </div>


                <div class="match-team">

                    ${createClubLogo(
                        awayLogo,
                        match.away_club
                    )}

                    <span>
                        ${match.away_club}
                    </span>

                </div>

            </div>


            <div class="match-competition">
                ${match.competition}
            </div>

        `;


        container.appendChild(item);

    });

}


/* =====================================
   RECENT MATCHES
===================================== */

function updateRecentMatches(matches) {

    const container =
        document.getElementById(
            "recent-matches-container"
        );


    container.innerHTML = "";


    if (!matches || matches.length === 0) {

        container.innerHTML = `
            <div class="loading">
                No recent results available.
            </div>
        `;

        return;
    }


    matches.forEach(function (match) {

        const item = document.createElement("div");

        item.className = "match-item";


        const homeLogo = getLogoURL(
            match.home_logo
        );

        const awayLogo = getLogoURL(
            match.away_logo
        );


        item.innerHTML = `

            <div class="match-date">
                ${formatDate(match.date)}
            </div>


            <div class="match-teams">

                <div class="match-team">

                    ${createClubLogo(
                        homeLogo,
                        match.home_club
                    )}

                    <span>
                        ${match.home_club}
                    </span>

                </div>


                <div class="match-score">

                    ${match.home_goals}
                    -
                    ${match.away_goals}

                </div>


                <div class="match-team">

                    ${createClubLogo(
                        awayLogo,
                        match.away_club
                    )}

                    <span>
                        ${match.away_club}
                    </span>

                </div>

            </div>


            <div class="match-competition">
                ${match.competition}
            </div>

        `;


        container.appendChild(item);

    });

}


/* =====================================
   CLUB LOGO URL
===================================== */

function getLogoURL(logoPath) {

    if (!logoPath) {
        return null;
    }


    return `/static/core/images/${logoPath}`;

}


/* =====================================
   CREATE CLUB LOGO
===================================== */

function createClubLogo(logoURL, clubName) {

    if (!logoURL) {

        return `
            <div class="club-logo-fallback">
                ${getClubInitials(clubName)}
            </div>
        `;

    }


    return `

        <img
            src="${logoURL}"
            alt="${clubName} logo"
            class="club-logo"
            onerror="handleLogoError(this, '${getClubInitials(clubName)}')"
        >

    `;

}


/* =====================================
   LOGO ERROR HANDLING
===================================== */

function handleLogoError(image, initials) {

    image.style.display = "none";


    const fallback =
        document.createElement("div");

    fallback.className =
        "club-logo-fallback";

    fallback.textContent =
        initials;


    image.parentNode.appendChild(
        fallback
    );

}


/* =====================================
   CLUB INITIALS
===================================== */

function getClubInitials(clubName) {

    if (!clubName) {
        return "?";
    }


    const words =
        clubName.trim().split(/\s+/);


    if (words.length === 1) {

        return words[0]
            .substring(0, 2)
            .toUpperCase();

    }


    return (
        words[0].charAt(0) +
        words[words.length - 1].charAt(0)
    ).toUpperCase();

}


/* =====================================
   POSITION FORMAT
===================================== */

function formatPosition(position) {

    const positions = {

        "GK": "Goalkeeper",
        "DF": "Defender",
        "MF": "Midfielder",
        "FW": "Forward"

    };

    return positions[position] || position;

}


/* =====================================
   DATE FORMAT
===================================== */

function formatDate(dateString) {

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


/* =====================================
   LOGOUT
===================================== */

function setupLogout() {

    const logoutButton =
        document.getElementById("logout-btn");


    if (!logoutButton) {
        return;
    }


    logoutButton.addEventListener(
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

                    // Clear stored login information
                    sessionStorage.clear();


                    // Return to login page
                    window.location.href =
                        "/login/";

                }

                else {

                    alert(
                        data.message ||
                        "Logout failed."
                    );

                }

            }

            catch (error) {

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