let allPlayers = [];

document.addEventListener("DOMContentLoaded", function () {

    loadPlayers();

    setupFilters();

    setupLogout();

});


/* =====================================
   LOAD PLAYERS
===================================== */

async function loadPlayers() {

    try {

        const response = await fetch("/api/players/");

        if (!response.ok) {
            throw new Error("Failed to load players");
        }

        allPlayers = await response.json();

        populateClubFilter();

        displayPlayers(allPlayers);

    }

    catch (error) {

        console.error("Player loading error:", error);

        document.getElementById("players-grid").innerHTML = `
            <div class="no-results">
                Unable to load player data.
            </div>
        `;

    }

}


/* =====================================
   CLUB FILTER
===================================== */

function populateClubFilter() {

    const clubFilter =
        document.getElementById("club-filter");

    const clubs = [
        ...new Set(
            allPlayers
                .map(player => player.club_name)
                .filter(Boolean)
        )
    ];

    clubs.sort();

    clubs.forEach(function (club) {

        const option =
            document.createElement("option");

        option.value = club;

        option.textContent = club;

        clubFilter.appendChild(option);

    });

}


/* =====================================
   FILTER SETUP
===================================== */

function setupFilters() {

    const search =
        document.getElementById("player-search");

    const club =
        document.getElementById("club-filter");

    const position =
        document.getElementById("position-filter");


    search.addEventListener(
        "input",
        applyFilters
    );

    club.addEventListener(
        "change",
        applyFilters
    );

    position.addEventListener(
        "change",
        applyFilters
    );

}


/* =====================================
   APPLY FILTERS
===================================== */

function applyFilters() {

    const searchValue =
        document.getElementById("player-search")
            .value
            .trim()
            .toLowerCase();


    const selectedClub =
        document.getElementById("club-filter").value;


    const selectedPosition =
        document.getElementById("position-filter").value;


    const filteredPlayers =
        allPlayers.filter(function (player) {

            const playerName =
                player.name.toLowerCase();

            const matchesSearch =
                playerName.includes(searchValue);

            const matchesClub =
                !selectedClub ||
                player.club_name === selectedClub;

            const matchesPosition =
                !selectedPosition ||
                player.position === selectedPosition;


            return (
                matchesSearch &&
                matchesClub &&
                matchesPosition
            );

        });


    displayPlayers(filteredPlayers);

}


/* =====================================
   DISPLAY PLAYERS
===================================== */

function displayPlayers(players) {

    const grid =
        document.getElementById("players-grid");

    const count =
        document.getElementById("results-count");


    count.textContent =
        `${players.length} player${players.length !== 1 ? "s" : ""} found`;


    if (players.length === 0) {

        grid.innerHTML = `
            <div class="no-results">
                No players found matching your filters.
            </div>
        `;

        return;

    }


    grid.innerHTML = "";


    players.forEach(function (player) {

        const card =
            document.createElement("div");

        card.className = "player-card";


        /* -----------------------------
           Player Image
        ----------------------------- */

        let imageHTML;


        if (player.photo_path) {

            imageHTML = `
                <img
                    src="${player.photo_path}"
                    alt="${player.name}"
                >
            `;

        }

        else {

            imageHTML = `
                <span class="player-initial">
                    ${player.name.charAt(0).toUpperCase()}
                </span>
            `;

        }


        /* -----------------------------
           Player Card
        ----------------------------- */

        card.innerHTML = `

            <div class="player-image">
                ${imageHTML}
            </div>

            <div class="player-info">

                <div class="player-name">
                    ${player.name}
                </div>

                <div class="player-club">
                    ${player.club_name}
                </div>

                <span class="player-position">
                    ${formatPosition(player.position)}
                </span>

                <a
                    href="/players/${player.id}/"
                    class="view-player-btn"
                >
                    View Performance
                </a>

            </div>

        `;


        grid.appendChild(card);

    });

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
   LOGOUT
===================================== */

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

                const response =
                    await fetch(
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