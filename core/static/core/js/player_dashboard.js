document.addEventListener("DOMContentLoaded", function () {

    loadDashboard();

    setupLogout();
    setupStandingsFilters();

});


/* =====================================
   LOAD DASHBOARD
===================================== */

async function loadDashboard() {

    try {

        const response = await fetch("/api/dashboard/");

        if (!response.ok) {
            throw new Error("Failed to load dashboard data");
        }

        const data = await response.json();

        updateSummary(data.summary);

        updateTopPlayers(data.top_players);

        updateStatisticalLeaders(data.statistical_leaders);

        updatePositionChart(data.position_summary);

        updateUpcomingMatches(data.upcoming_matches);

        updateRecentMatches(data.recent_matches);
        updateStandings(data.standings, data.standings_seasons, data.standings_competitions);

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

    document.getElementById("total-available-stats").textContent =
        Number(summary.total_available_stats || 0).toLocaleString();

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
                <td colspan="8" class="loading">
                    No player data available.
                </td>
            </tr>
        `;

        return;
    }


    players.forEach(function (player, index) {

        const row = document.createElement("tr");

        row.innerHTML = `

            <td>
                ${index + 1}
            </td>

            <td class="player-name">
    <a href="/players/${player.player_id}">
        ${player.player__name}
    </a>
</td>

            <td>
                ${formatPosition(player.player__position)}
            </td>

            <td>
                ${formatPreferredFoot(player.player__preferred_foot)}
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
   STATISTICAL LEADERS
===================================== */

function updateStatisticalLeaders(leaders) {
    const container = document.getElementById("statistical-leaders");
    if (!container) return;

    const definitions = [
        { key: "goals", label: "Most Goals", icon: "⚽" },
        { key: "assists", label: "Most Assists", icon: "🎯" },
        { key: "red_cards", label: "Most Red Cards", icon: "🟥" },
        { key: "yellow_cards", label: "Most Yellow Cards", icon: "🟨" },
        { key: "saves", label: "Most Saves", icon: "🧤" }
    ];

    container.innerHTML = "";

    definitions.forEach(function (definition) {
        const leader = leaders ? leaders[definition.key] : null;
        const card = document.createElement("a");
        card.className = "leader-card";

        if (leader && leader.player_id) {
            card.href = `/players/${leader.player_id}`;
            const photoURL = getPlayerPhotoURL(leader.photo_path);
            const photo = photoURL
                ? `<img class="leader-photo" src="${photoURL}" alt="${escapeHTML(leader.player_name)}" onerror="handlePlayerPhotoError(this)">`
                : `<div class="leader-photo-fallback">${escapeHTML(getPlayerInitials(leader.player_name))}</div>`;

            card.innerHTML = `
                <div class="leader-topline">
                    <span class="leader-icon">${definition.icon}</span>
                    <span class="leader-category">${definition.label}</span>
                </div>
                <div class="leader-player">
                    ${photo}
                    <div class="leader-player-details">
                        <span class="leader-player-name">${escapeHTML(leader.player_name)}</span>
                        <strong class="leader-total">${Number(leader.total || 0).toLocaleString()}</strong>
                    </div>
                </div>
                <span class="leader-hint">View performance →</span>
            `;
        } else {
            card.classList.add("leader-card-empty");
            card.innerHTML = `
                <div class="leader-topline">
                    <span class="leader-icon">${definition.icon}</span>
                    <span class="leader-category">${definition.label}</span>
                </div>
                <p class="leader-empty-text">No data available</p>
            `;
            card.removeAttribute("href");
            card.setAttribute("aria-disabled", "true");
        }

        container.appendChild(card);
    });
}

function getPlayerPhotoURL(photoPath) {
    if (!photoPath) return null;
    if (/^https?:\/\//i.test(photoPath)) return photoPath;
    if (photoPath.startsWith("/")) return photoPath;
    return `/static/core/images/${photoPath}`;
}

function handlePlayerPhotoError(image) {
    const fallback = document.createElement("div");
    fallback.className = "leader-photo-fallback";
    fallback.textContent = getPlayerInitials(image.alt);
    image.replaceWith(fallback);
}

function getPlayerInitials(name) {
    if (!name) return "?";
    const words = name.trim().split(/\s+/);
    return (words.length === 1
        ? words[0].slice(0, 2)
        : words[0][0] + words[words.length - 1][0]).toUpperCase();
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, function (character) {
        return ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[character];
    });
}

/* =====================================
   PREFERRED FOOT FORMAT
===================================== */

function formatPreferredFoot(foot) {

    if (!foot) {
        return "-";
    }

    const feet = {
        "Right": "Right",
        "Left": "Left",
        "Both": "Both"
    };

    return feet[foot] || foot;

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


/* =====================================
   LEAGUE POINTS TABLE
   Added without changing existing dashboard functions.
===================================== */

function setupStandingsFilters() {
    const seasonSelect = document.getElementById("standings-season");
    const competitionSelect = document.getElementById("standings-competition");

    if (seasonSelect) seasonSelect.addEventListener("change", loadStandingsForFilters);
    if (competitionSelect) competitionSelect.addEventListener("change", loadStandingsForFilters);
}

async function loadStandingsForFilters() {
    const season = document.getElementById("standings-season")?.value || "";
    const competition = document.getElementById("standings-competition")?.value || "";
    const params = new URLSearchParams();

    if (season) params.set("season", season);
    if (competition) params.set("competition", competition);

    const tbody = document.getElementById("standings-table-body");
    if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="loading">Updating points table...</td></tr>';

    try {
        const query = params.toString();
        const response = await fetch("/api/dashboard/" + (query ? "?" + query : ""));
        if (!response.ok) throw new Error("Failed to load league standings");

        const data = await response.json();
        updateStandings(data.standings, data.standings_seasons, data.standings_competitions, false);
    } catch (error) {
        console.error("Standings error:", error);
        if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="loading">Unable to load points table.</td></tr>';
    }
}

function updateStandings(standings, seasons, competitions, setDefaults = true) {
    const seasonSelect = document.getElementById("standings-season");
    const competitionSelect = document.getElementById("standings-competition");
    const tbody = document.getElementById("standings-table-body");
    if (!seasonSelect || !competitionSelect || !tbody) return;

    const previousSeason = seasonSelect.value;
    const previousCompetition = competitionSelect.value;

    if (Array.isArray(seasons)) {
        seasonSelect.innerHTML = "";
        seasons.forEach(function (season) {
            const option = document.createElement("option");
            option.value = season;
            option.textContent = season;
            seasonSelect.appendChild(option);
        });
    }

    if (Array.isArray(competitions)) {
        competitionSelect.innerHTML = '<option value="">All competitions</option>';
        competitions.forEach(function (competition) {
            const option = document.createElement("option");
            option.value = competition;
            option.textContent = competition;
            competitionSelect.appendChild(option);
        });
    }

    if (setDefaults) {
        seasonSelect.value = seasons && seasons.includes(previousSeason)
            ? previousSeason
            : (seasons && seasons.length ? seasons[0] : "");
        competitionSelect.value = competitions && competitions.includes(previousCompetition)
            ? previousCompetition
            : "";
    } else {
        if (seasons && seasons.includes(previousSeason)) seasonSelect.value = previousSeason;
        if (competitions && competitions.includes(previousCompetition)) competitionSelect.value = previousCompetition;
    }

    tbody.innerHTML = "";
    if (!Array.isArray(standings) || standings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="loading">No completed match data available for this selection.</td></tr>';
        return;
    }

    standings.forEach(function (club, index) {
        const row = document.createElement("tr");
        if (index === 0) row.classList.add("standings-leader");

        row.innerHTML = `
            <td class="standings-rank">${index + 1}</td>
            <td class="standings-club">${escapeDashboardText(club.club_name)}</td>
            <td>${club.played}</td>
            <td>${club.won}</td>
            <td>${club.drawn}</td>
            <td>${club.lost}</td>
            <td>${club.goals_for}</td>
            <td>${club.goals_against}</td>
            <td class="${club.goal_difference > 0 ? "positive-gd" : club.goal_difference < 0 ? "negative-gd" : ""}">${club.goal_difference > 0 ? "+" : ""}${club.goal_difference}</td>
            <td class="standings-points">${club.points}</td>
        `;
        tbody.appendChild(row);
    });
}

function escapeDashboardText(value) {
    return String(value ?? "").replace(/[&<>"']/g, function (character) {
        return ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[character];
    });
}
