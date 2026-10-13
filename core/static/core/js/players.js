/* =========================================================
   GLOBAL STATE
========================================================= */

let allPlayers = [];

/*
    Default player view.

    "active" = only active players
    "all"    = active + inactive players
*/

let currentPlayerView = "active";


/* =========================================================
   PAGE LOAD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupFilters();

        setupPlayerViewToggle();

        setupLogout();

        loadPlayers();

    }
);


/* =========================================================
   LOAD PLAYERS
========================================================= */

async function loadPlayers() {

    try {

        const response =
            await fetch(
                "/api/players/"
            );


        if (!response.ok) {

            throw new Error(
                "Failed to load players"
            );

        }


        const data =
            await response.json();


        /*
            Django REST Framework may return:

            1. Direct array

               [
                   {...},
                   {...}
               ]

            2. Paginated response

               {
                   "results": [
                       {...},
                       {...}
                   ]
               }
        */


        if (
            Array.isArray(data)
        ) {

            allPlayers =
                data;

        }

        else if (
            Array.isArray(
                data.results
            )
        ) {

            allPlayers =
                data.results;

        }

        else {

            throw new Error(
                "Invalid player data format"
            );

        }


        console.log(
            "Players:",
            allPlayers
        );


        populateClubFilter();


        /*
            Apply filters immediately.

            Because currentPlayerView defaults
            to "active", only active players
            appear when the page first loads.
        */

        applyFilters();


    }

    catch (error) {

        console.error(
            "Player loading error:",
            error
        );


        const grid =
            document.getElementById(
                "players-grid"
            );


        const count =
            document.getElementById(
                "results-count"
            );


        if (grid) {

            grid.innerHTML = `

                <div class="no-results">

                    <strong>
                        Unable to load players
                    </strong>

                    <span>
                        Player data could not be loaded.
                        Please try again.
                    </span>

                </div>

            `;

        }


        if (count) {

            count.textContent =
                "Unable to load players.";

        }

    }

}


/* =========================================================
   CLUB FILTER
========================================================= */

function populateClubFilter() {

    const clubFilter =
        document.getElementById(
            "club-filter"
        );


    if (!clubFilter) {

        return;

    }


    /*
        Remove any previously generated
        club options while keeping
        "All Teams".
    */

    while (
        clubFilter.options.length > 1
    ) {

        clubFilter.remove(1);

    }


    const clubs = [

        ...new Set(

            allPlayers

                .map(
                    player =>
                        player.club_name
                )

                .filter(Boolean)

        )

    ];


    clubs.sort(
        function (a, b) {

            return a.localeCompare(b);

        }
    );


    clubs.forEach(
        function (club) {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                club;


            option.textContent =
                club;


            clubFilter.appendChild(
                option
            );

        }
    );

}


/* =========================================================
   FILTER SETUP
========================================================= */

function setupFilters() {

    const search =
        document.getElementById(
            "player-search"
        );


    const club =
        document.getElementById(
            "club-filter"
        );


    const position =
        document.getElementById(
            "position-filter"
        );


    if (search) {

        search.addEventListener(
            "input",
            applyFilters
        );

    }


    if (club) {

        club.addEventListener(
            "change",
            applyFilters
        );

    }


    if (position) {

        position.addEventListener(
            "change",
            applyFilters
        );

    }

}


/* =========================================================
   ACTIVE / ALL PLAYERS TOGGLE
========================================================= */

function setupPlayerViewToggle() {

    const toggleButtons =
        document.querySelectorAll(
            "[data-player-view]"
        );


    toggleButtons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    const selectedView =
                        button.dataset.playerView;


                    if (
                        selectedView !== "active" &&
                        selectedView !== "all"
                    ) {

                        return;

                    }


                    currentPlayerView =
                        selectedView;


                    updateToggleState();


                    applyFilters();

                }
            );

        }
    );


    updateToggleState();

}


/* =========================================================
   UPDATE TOGGLE VISUAL STATE
========================================================= */

function updateToggleState() {

    const toggleButtons =
        document.querySelectorAll(
            "[data-player-view]"
        );


    toggleButtons.forEach(
        function (button) {

            const isSelected =
                button.dataset.playerView ===
                currentPlayerView;


            button.classList.toggle(
                "active",
                isSelected
            );


            button.setAttribute(
                "aria-pressed",
                isSelected
                    ? "true"
                    : "false"
            );

        }
    );


    const resultsStatus =
        document.getElementById(
            "results-status"
        );


    if (resultsStatus) {

        if (
            currentPlayerView ===
            "active"
        ) {

            resultsStatus.innerHTML = `

                <span
                    class="results-status-dot"
                ></span>

                Active Players

            `;

        }

        else {

            resultsStatus.innerHTML = `

                <span
                    class="results-status-dot"
                ></span>

                All Players

            `;

        }

    }

}


/* =========================================================
   APPLY FILTERS
========================================================= */

function applyFilters() {

    const searchElement =
        document.getElementById(
            "player-search"
        );


    const clubElement =
        document.getElementById(
            "club-filter"
        );


    const positionElement =
        document.getElementById(
            "position-filter"
        );


    const searchValue =
        searchElement

            ? searchElement.value
                .trim()
                .toLowerCase()

            : "";


    const selectedClub =
        clubElement
            ? clubElement.value
            : "";


    const selectedPosition =
        positionElement
            ? positionElement.value
            : "";


    const filteredPlayers =
        allPlayers.filter(
            function (player) {


                /* -----------------------------
                   SEARCH
                ----------------------------- */

                const playerName =
                    (
                        player.name ||
                        ""
                    ).toLowerCase();


                const matchesSearch =
                    playerName.includes(
                        searchValue
                    );


                /* -----------------------------
                   CLUB
                ----------------------------- */

                const matchesClub =
                    !selectedClub ||

                    player.club_name ===
                    selectedClub;


                /* -----------------------------
                   POSITION
                ----------------------------- */

                const matchesPosition =
                    !selectedPosition ||

                    player.position ===
                    selectedPosition;


                /* -----------------------------
                   ACTIVE STATUS
                ----------------------------- */

                const matchesActivity =
                    currentPlayerView ===
                    "all"

                    ||

                    player.is_active ===
                    true;


                return (

                    matchesSearch &&

                    matchesClub &&

                    matchesPosition &&

                    matchesActivity

                );

            }
        );


    displayPlayers(
        filteredPlayers
    );

}


/* =========================================================
   DISPLAY PLAYERS
========================================================= */

function displayPlayers(
    players
) {

    const grid =
        document.getElementById(
            "players-grid"
        );


    const count =
        document.getElementById(
            "results-count"
        );


    if (!grid) {

        return;

    }


    if (count) {

        const label =
            currentPlayerView === "active"
                ? "active player"
                : "player";


        count.textContent =

            `${players.length} ${label}` +

            `${players.length !== 1 ? "s" : ""} found`;

    }


    if (
        players.length === 0
    ) {

        grid.innerHTML = `

            <div class="no-results">

                <strong>
                    No players found
                </strong>

                <span>
                    Try changing the player name,
                    team, position or activity filter.
                </span>

            </div>

        `;


        return;

    }


    grid.innerHTML =
        "";


    players.forEach(
        function (player) {

            const card =
                createPlayerCard(
                    player
                );


            grid.appendChild(
                card
            );

        }
    );

}


/* =========================================================
   CREATE PLAYER CARD
========================================================= */

function createPlayerCard(
    player
) {

    const card =
        document.createElement(
            "article"
        );


    card.className =
        "player-card";


    if (
        player.is_active === false
    ) {

        card.classList.add(
            "inactive-player"
        );

    }


    /* =====================================================
       PLAYER IMAGE
    ===================================================== */

    const playerName =
        player.name ||
        "Unknown Player";


    let imageHTML;


    if (
        player.photo_path
    ) {

        /*
            Example database path:

            players/erling_haaland.png

            Browser path:

            /static/core/images/players/erling_haaland.png
        */

        const imageURL =
            `/static/core/images/${player.photo_path}`;


        imageHTML = `

            <img
                src="${escapeHTML(imageURL)}"
                alt="${escapeHTML(playerName)}"
                class="player-photo"
                onerror="handleImageError(this)"
            >


            <span
                class="player-initial"
                style="display: none;"
            >
                ${escapeHTML(
                    getPlayerInitial(
                        playerName
                    )
                )}
            </span>

        `;

    }

    else {

        imageHTML = `

            <span class="player-initial">

                ${escapeHTML(
                    getPlayerInitial(
                        playerName
                    )
                )}

            </span>

        `;

    }


    /* =====================================================
       PLAYER STATUS
    ===================================================== */

    const isActive =
        player.is_active !== false;


    const statusText =
        isActive
            ? "Active"
            : "Inactive";


    const statusClass =
        isActive
            ? ""
            : "inactive";


    /* =====================================================
       JERSEY
    ===================================================== */

    const jerseyNumber =
        player.jersey_number !== null &&
        player.jersey_number !== undefined

            ? `#${player.jersey_number}`

            : "";


    /* =====================================================
       PLAYER INFORMATION
    ===================================================== */

    const clubName =
        player.club_name ||
        "No Current Club";


    const nationality =
        player.nationality ||
        "Not available";


    const preferredFoot =
        player.preferred_foot

            ? `${player.preferred_foot} foot`

            : "Not available";


    const positionName =
        formatPosition(
            player.position
        );


    const positionCode =
        player.position ||
        "—";


    /* =====================================================
       BUILD CARD
    ===================================================== */

    card.innerHTML = `

        <div class="player-image">


            ${imageHTML}


            <span
                class="player-status-badge ${statusClass}"
            >

                ${statusText}

            </span>


            ${
                jerseyNumber

                    ? `

                        <span
                            class="jersey-number"
                        >

                            ${escapeHTML(
                                jerseyNumber
                            )}

                        </span>

                    `

                    : ""
            }


            <span
                class="image-position-badge"
            >

                ${escapeHTML(
                    positionCode
                )}

            </span>


        </div>



        <div class="player-info">


            <div class="player-role">

                ${escapeHTML(
                    positionName
                )}

            </div>


            <div
                class="player-name"
                title="${escapeHTML(playerName)}"
            >

                ${escapeHTML(
                    playerName
                )}

            </div>


            <div
                class="player-club"
                title="${escapeHTML(clubName)}"
            >

                ${escapeHTML(
                    clubName
                )}

            </div>



            <div class="player-meta">


                <div class="player-meta-item">

                    <span
                        class="player-meta-label"
                    >
                        Nationality
                    </span>

                    <strong
                        class="player-meta-value"
                        title="${escapeHTML(nationality)}"
                    >

                        ${escapeHTML(
                            nationality
                        )}

                    </strong>

                </div>



                <div class="player-meta-item">

                    <span
                        class="player-meta-label"
                    >
                        Preferred Foot
                    </span>

                    <strong
                        class="player-meta-value"
                    >

                        ${escapeHTML(
                            preferredFoot
                        )}

                    </strong>

                </div>


            </div>



            <a
                href="/players/${encodeURIComponent(player.id)}/"
                class="view-player-btn"
            >

                <span>
                    View Performance
                </span>

                <span aria-hidden="true">
                    →
                </span>

            </a>


        </div>

    `;


    return card;

}


/* =========================================================
   IMAGE ERROR HANDLER
========================================================= */

function handleImageError(
    imageElement
) {

    /*
        Hide the broken image and
        show the fallback player initial.
    */

    imageElement.style.display =
        "none";


    const fallback =
        imageElement.nextElementSibling;


    if (fallback) {

        fallback.style.display =
            "flex";

    }

}


/* =========================================================
   PLAYER INITIAL
========================================================= */

function getPlayerInitial(
    name
) {

    if (!name) {

        return "?";

    }


    return name
        .trim()
        .charAt(0)
        .toUpperCase();

}


/* =========================================================
   POSITION FORMAT
========================================================= */

function formatPosition(
    position
) {

    const positions = {

        "GK":
            "Goalkeeper",

        "DF":
            "Defender",

        "MF":
            "Midfielder",

        "FW":
            "Forward"

    };


    return (
        positions[position] ||
        position ||
        "Unknown Position"
    );

}


/* =========================================================
   HTML ESCAPE
========================================================= */

function escapeHTML(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


/* =========================================================
   LOGOUT
========================================================= */

function setupLogout() {

    const button =
        document.getElementById(
            "logout-btn"
        );


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
                            method:
                                "POST"
                        }

                    );


                const data =
                    await response.json();


                if (
                    data.success
                ) {

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