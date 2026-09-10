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

        const data = await response.json();

        /*
         * Django REST Framework may return either:
         *
         * 1. Direct array:
         *    [ {...}, {...} ]
         *
         * 2. Paginated response:
         *    { "results": [ {...}, {...} ] }
         */

        if (Array.isArray(data)) {

            allPlayers = data;

        }

        else if (Array.isArray(data.results)) {

            allPlayers = data.results;

        }

        else {

            throw new Error("Invalid player data format");

        }


        populateClubFilter();

        displayPlayers(allPlayers);

    }

    catch (error) {

        console.error(
            "Player loading error:",
            error
        );

        document.getElementById("players-grid").innerHTML = `
            <div class="no-results">
                Unable to load player data.
            </div>
        `;

        document.getElementById("results-count").textContent =
            "Unable to load players.";

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
        document
            .getElementById("player-search")
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
                (player.name || "").toLowerCase();


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


        /* =================================
           PLAYER IMAGE
        ================================= */

        let imageHTML;


        if (player.photo_path) {

            /*
             * photo_path stored in database:
             *
             * players/aaron_ramsdale.png
             *
             * Browser URL:
             *
             * /static/core/images/players/aaron_ramsdale.png
             */

            const imageURL =
                `/static/core/images/${player.photo_path}`;


            imageHTML = `
                <img
                    src="${imageURL}"
                    alt="${player.name}"
                    class="player-photo"
                    onerror="handleImageError(this)"
                >

                <span
                    class="player-initial"
                    style="display: none;"
                >
                    ${getPlayerInitial(player.name)}
                </span>
            `;

        }

        else {

            /*
             * No photo path available
             */

            imageHTML = `
                <span class="player-initial">
                    ${getPlayerInitial(player.name)}
                </span>
            `;

        }


        /* =================================
           PLAYER CARD
        ================================= */

        card.innerHTML = `

            <div class="player-image">

                ${imageHTML}

            </div>


            <div class="player-info">

                <div class="player-name">
                    ${player.name || "Unknown Player"}
                </div>


                <div class="player-club">
                    ${player.club_name || "Unknown Club"}
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
   IMAGE ERROR HANDLER
===================================== */

function handleImageError(imageElement) {

    /*
     * If the actual image file does not exist,
     * hide the broken image and show the
     * player's initial instead.
     */

    imageElement.style.display = "none";


    const fallback =
        imageElement.nextElementSibling;


    if (fallback) {

        fallback.style.display = "flex";

    }

}


/* =====================================
   PLAYER INITIAL
===================================== */

function getPlayerInitial(name) {

    if (!name) {
        return "?";
    }


    return name
        .trim()
        .charAt(0)
        .toUpperCase();

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


    return positions[position] || position || "Unknown";

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