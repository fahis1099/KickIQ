/* =========================================================
   PLAYER AGE
   Calculate age from the date of birth in the rendered template.
========================================================= */

function calculatePlayerAge() {

    const dobElement =
        document.querySelector(".dob-value");

    const ageElement =
        document.getElementById("player-age");

    if (!dobElement || !ageElement) {
        return;
    }

    const dobValue =
        dobElement.dataset.dob;

    if (
        !dobValue ||
        dobValue === "None" ||
        dobValue === "null"
    ) {

        ageElement.textContent =
            "Age unavailable";

        return;
    }

    const dob =
        new Date(`${dobValue}T00:00:00`);

    if (Number.isNaN(dob.getTime())) {

        ageElement.textContent =
            "Age unavailable";

        return;
    }

    const today =
        new Date();

    let age =
        today.getFullYear() -
        dob.getFullYear();

    const beforeBirthday =
        today.getMonth() < dob.getMonth() ||
        (
            today.getMonth() === dob.getMonth() &&
            today.getDate() < dob.getDate()
        );

    if (beforeBirthday) {
        age -= 1;
    }

    ageElement.textContent =
        age >= 0
            ? `${age} years old`
            : "Age unavailable";
}


/* =========================================================
   GLOBAL VARIABLES
========================================================= */

let allPlayerStatistics = [];

let ratingChart = null;

let minutesChart = null;


/* =========================================================
   PAGE LOAD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        calculatePlayerAge();

        setupLogout();

        loadPlayerPerformance();

    }
);


/* =========================================================
   LOAD PLAYER PERFORMANCE
========================================================= */

async function loadPlayerPerformance() {

    try {

        const playerId =
            getPlayerIdFromURL();

        const response =
            await fetch(
                `/api/players/${playerId}/statistics/`
            );

        if (!response.ok) {

            throw new Error(
                "Failed to load player statistics"
            );

        }

        const data =
            await response.json();


        /*
            Handle both API response formats:

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

        allPlayerStatistics =
            Array.isArray(data)
                ? data
                : (data.results || []);


        console.log(
            "Player statistics:",
            allPlayerStatistics
        );


        setupSeasonFilter();


        updatePerformanceDisplay(
            allPlayerStatistics
        );


        /*
            Load FFI for all seasons initially.
        */

        loadFFI();


    } catch (error) {

        console.error(
            "Player performance loading error:",
            error
        );


        const tableBody =
            document.getElementById(
                "performance-table-body"
            );


        if (tableBody) {

            tableBody.innerHTML = `

                <tr>

                    <td
                        colspan="10"
                        class="no-data-row"
                    >

                        Unable to load performance data.

                    </td>

                </tr>

            `;

        }

    }

}


/* =========================================================
   GET PLAYER ID
========================================================= */

function getPlayerIdFromURL() {

    const pathParts =
        window.location.pathname
            .split("/")
            .filter(Boolean);

    return pathParts[
        pathParts.length - 1
    ];

}


/* =========================================================
   SEASON FILTER
========================================================= */

function setupSeasonFilter() {

    const seasonFilter =
        document.getElementById(
            "season-filter"
        );


    if (!seasonFilter) {

        return;

    }


    const seasons = [

        ...new Set(

            allPlayerStatistics

                .map(
                    stat => stat.season
                )

                .filter(Boolean)

        )

    ];


    seasons.sort(
        function (a, b) {

            return b.localeCompare(a);

        }
    );


    seasons.forEach(
        function (season) {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                season;

            option.textContent =
                season;


            seasonFilter.appendChild(
                option
            );

        }
    );


    seasonFilter.addEventListener(
        "change",
        applySeasonFilter
    );

}


/* =========================================================
   APPLY SEASON FILTER
========================================================= */

function applySeasonFilter() {

    const seasonFilter =
        document.getElementById(
            "season-filter"
        );


    if (!seasonFilter) {

        return;

    }


    const selectedSeason =
        seasonFilter.value;


    const filteredStatistics =
        selectedSeason

            ? allPlayerStatistics.filter(
                function (stat) {

                    return (
                        stat.season ===
                        selectedSeason
                    );

                }
            )

            : allPlayerStatistics;


    /*
        Update normal performance analytics.
    */

    updatePerformanceDisplay(
        filteredStatistics
    );


    /*
        FFI is calculated by the backend.

        When a season is selected,
        send that season to the FFI API.
    */

    loadFFI(
        selectedSeason
    );

}


/* =========================================================
   UPDATE PERFORMANCE DISPLAY
========================================================= */

function updatePerformanceDisplay(
    statistics
) {

    updateSummary(
        statistics
    );

    createRatingChart(
        statistics
    );

    createMinutesChart(
        statistics
    );

    createPositionAnalysis(
        statistics
    );

    createPerformanceTable(
        statistics
    );

}


/* =========================================================
   FOOTBALL FORM INDEX
========================================================= */

async function loadFFI(
    season = ""
) {

    const playerId =
        getPlayerIdFromURL();


    setFFIText(
        "ffi-status",
        "Loading"
    );


    setFFIText(
        "ffi-message",
        "Calculating Football Form Index..."
    );


    resetFFIDisplay();


    try {

        let url =
            `/api/players/${playerId}/ffi/`;


        /*
            Add season only when the user
            selects a specific season.

            All Seasons:
            /api/players/1/ffi/

            Selected season:
            /api/players/1/ffi/?season=2025%2F26
        */

        if (season) {

            url +=
                `?season=${encodeURIComponent(season)}`;

        }


        const response =
            await fetch(url);


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "Unable to calculate FFI."
            );

        }


        console.log(
            "FFI result:",
            data
        );


        displayFFI(
            data
        );


    } catch (error) {

        console.error(
            "FFI loading error:",
            error
        );


        showFFIUnavailable(
            error.message ||
            "Unable to calculate Football Form Index."
        );

    }

}


/* =========================================================
   DISPLAY FFI
========================================================= */

function displayFFI(data) {

    /*
        FFI = null is a valid result.

        This can happen when:
        - player has insufficient appearances
        - player has not appeared recently
        - insufficient rated matches exist

        Do not display 0 in this situation.
    */

    if (
        data.ffi === null ||
        data.ffi === undefined
    ) {

        showFFIUnavailable(
            data.message ||
            "Football Form Index is unavailable."
        );


        updateFFIBasicDetails(
            data
        );


        return;
    }


    const ffi =
        Number(data.ffi);


    /* -----------------------------
       MAIN FFI SCORE
    ----------------------------- */

    setFFIText(
        "ffi-score",
        ffi.toFixed(2)
    );


    setFFIText(
        "ffi-form-label",
        getFFIFormLabel(ffi)
    );


    setFFIText(
        "ffi-message",
        data.message ||
        "Football Form Index calculated successfully."
    );


    setFFIText(
        "ffi-status",
        "Available"
    );


    /* -----------------------------
       COMPONENT SCORES
    ----------------------------- */

    setFFIText(
        "ffi-performance",
        formatFFINumber(
            data.performance_score
        )
    );


    setFFIText(
        "ffi-trend",
        formatFFINumber(
            data.trend_score
        )
    );


    setFFIText(
        "ffi-consistency",
        formatFFINumber(
            data.consistency_score
        )
    );


    /* -----------------------------
       PROGRESS BARS
    ----------------------------- */

    setFFIProgress(
        "ffi-performance-bar",
        data.performance_score
    );


    setFFIProgress(
        "ffi-trend-bar",
        data.trend_score
    );


    setFFIProgress(
        "ffi-consistency-bar",
        data.consistency_score
    );


    /* -----------------------------
       MATCHES USED
    ----------------------------- */

    setFFIText(
        "ffi-matches-used",
        data.matches_used ??
        "—"
    );


    /* -----------------------------
       WEIGHTED RATING
    ----------------------------- */

    if (
        data.weighted_average_rating !==
            undefined &&
        data.weighted_average_rating !==
            null
    ) {

        setFFIText(
            "ffi-weighted-rating",
            Number(
                data.weighted_average_rating
            ).toFixed(2)
        );

    } else {

        setFFIText(
            "ffi-weighted-rating",
            "—"
        );

    }


    /* -----------------------------
       RATING CHANGE
    ----------------------------- */

    if (
        data.rating_change !== undefined &&
        data.rating_change !== null
    ) {

        const ratingChange =
            Number(
                data.rating_change
            );


        const formattedChange =
            ratingChange > 0

                ? `+${ratingChange.toFixed(2)}`

                : ratingChange.toFixed(2);


        setFFIText(
            "ffi-rating-change",
            formattedChange
        );

    } else {

        setFFIText(
            "ffi-rating-change",
            "—"
        );

    }


    /* -----------------------------
       CONTINUITY
    ----------------------------- */

    if (data.continuity) {

        const appearances =
            data.continuity
                .appearances_in_window;


        const fixtures =
            data.continuity
                .fixtures_analyzed;


        if (
            appearances !== undefined &&
            fixtures !== undefined
        ) {

            setFFIText(
                "ffi-appearances",
                `${appearances} / ${fixtures}`
            );

        } else {

            setFFIText(
                "ffi-appearances",
                "—"
            );

        }

    } else {

        setFFIText(
            "ffi-appearances",
            "—"
        );

    }


    /*
        Update circular score visual.
    */

    updateFFICircle(
        ffi
    );

}


/* =========================================================
   UPDATE BASIC DETAILS WHEN FFI IS UNAVAILABLE
========================================================= */

function updateFFIBasicDetails(data) {

    if (!data) {

        return;

    }


    setFFIText(
        "ffi-matches-used",
        data.matches_used ??
        "—"
    );


    if (data.continuity) {

        const appearances =
            data.continuity
                .appearances_in_window;


        const fixtures =
            data.continuity
                .fixtures_analyzed;


        if (
            appearances !== undefined &&
            fixtures !== undefined
        ) {

            setFFIText(
                "ffi-appearances",
                `${appearances} / ${fixtures}`
            );

        }

    }

}


/* =========================================================
   FFI UNAVAILABLE
========================================================= */

function showFFIUnavailable(
    message
) {

    setFFIText(
        "ffi-score",
        "—"
    );


    setFFIText(
        "ffi-form-label",
        "Unavailable"
    );


    setFFIText(
        "ffi-status",
        "Unavailable"
    );


    setFFIText(
        "ffi-message",
        message
    );


    setFFIText(
        "ffi-performance",
        "—"
    );


    setFFIText(
        "ffi-trend",
        "—"
    );


    setFFIText(
        "ffi-consistency",
        "—"
    );


    setFFIText(
        "ffi-weighted-rating",
        "—"
    );


    setFFIText(
        "ffi-rating-change",
        "—"
    );


    setFFIProgress(
        "ffi-performance-bar",
        0
    );


    setFFIProgress(
        "ffi-trend-bar",
        0
    );


    setFFIProgress(
        "ffi-consistency-bar",
        0
    );


    updateFFICircle(
        0
    );

}


/* =========================================================
   RESET FFI DISPLAY
========================================================= */

function resetFFIDisplay() {

    setFFIText(
        "ffi-score",
        "—"
    );


    setFFIText(
        "ffi-form-label",
        "Calculating..."
    );


    setFFIText(
        "ffi-performance",
        "—"
    );


    setFFIText(
        "ffi-trend",
        "—"
    );


    setFFIText(
        "ffi-consistency",
        "—"
    );


    setFFIText(
        "ffi-matches-used",
        "—"
    );


    setFFIText(
        "ffi-weighted-rating",
        "—"
    );


    setFFIText(
        "ffi-rating-change",
        "—"
    );


    setFFIText(
        "ffi-appearances",
        "—"
    );


    setFFIProgress(
        "ffi-performance-bar",
        0
    );


    setFFIProgress(
        "ffi-trend-bar",
        0
    );


    setFFIProgress(
        "ffi-consistency-bar",
        0
    );


    updateFFICircle(
        0
    );

}


/* =========================================================
   FFI TEXT HELPER
========================================================= */

function setFFIText(
    elementId,
    value
) {

    const element =
        document.getElementById(
            elementId
        );


    if (element) {

        element.textContent =
            value;

    }

}


/* =========================================================
   FFI PROGRESS BAR HELPER
========================================================= */

function setFFIProgress(
    elementId,
    value
) {

    const element =
        document.getElementById(
            elementId
        );


    if (!element) {

        return;

    }


    let percentage =
        Number(value);


    if (
        !Number.isFinite(
            percentage
        )
    ) {

        percentage = 0;

    }


    percentage =
        Math.max(
            0,
            Math.min(
                100,
                percentage
            )
        );


    element.style.width =
        `${percentage}%`;

}


/* =========================================================
   FFI CIRCLE
========================================================= */

function updateFFICircle(
    value
) {

    const circle =
        document.querySelector(
            ".ffi-score-circle"
        );


    if (!circle) {

        return;

    }


    let percentage =
        Number(value);


    if (
        !Number.isFinite(
            percentage
        )
    ) {

        percentage = 0;

    }


    percentage =
        Math.max(
            0,
            Math.min(
                100,
                percentage
            )
        );


    const degrees =
        (percentage / 100) * 360;


    circle.style.background = `

        conic-gradient(

            #19a974 0deg,

            #19a974 ${degrees}deg,

            #e8f0ec ${degrees}deg,

            #e8f0ec 360deg

        )

    `;

}


/* =========================================================
   FORMAT FFI NUMBER
========================================================= */

function formatFFINumber(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "—";

    }


    const number =
        Number(value);


    if (
        !Number.isFinite(number)
    ) {

        return "—";

    }


    return number.toFixed(2);

}


/* =========================================================
   FFI PRESENTATION LABEL
========================================================= */

function getFFIFormLabel(
    ffi
) {

    /*
        These labels are only for presentation.

        They DO NOT change the FFI calculation.
    */

    if (ffi >= 85) {

        return "Excellent Form";

    }


    if (ffi >= 75) {

        return "Strong Form";

    }


    if (ffi >= 65) {

        return "Good Form";

    }


    if (ffi >= 50) {

        return "Average Form";

    }


    return "Poor Form";

}


/* =========================================================
   SUMMARY
========================================================= */

function updateSummary(
    statistics
) {

    const appearances =
        statistics.length;


    const minutes =
        statistics.reduce(

            (sum, stat) =>

                sum +
                Number(
                    stat.minutes_played ||
                    0
                ),

            0

        );


    const goals =
        statistics.reduce(

            (sum, stat) =>

                sum +
                Number(
                    stat.goals ||
                    0
                ),

            0

        );


    const assists =
        statistics.reduce(

            (sum, stat) =>

                sum +
                Number(
                    stat.assists ||
                    0
                ),

            0

        );


    const shots =
        statistics.reduce(

            (sum, stat) =>

                sum +
                Number(
                    stat.shots ||
                    0
                ),

            0

        );


    const keyPasses =
        statistics.reduce(

            (sum, stat) =>

                sum +
                Number(
                    stat.key_passes ||
                    0
                ),

            0

        );


    const ratings =
        statistics

            .filter(
                stat =>
                    stat.rating !== null
            )

            .map(
                stat =>
                    Number(
                        stat.rating
                    )
            );


    const averageRating =
        ratings.length > 0

            ? ratings.reduce(

                (sum, rating) =>
                    sum + rating,

                0

            ) / ratings.length

            : null;


    setSummaryValue(
        "summary-appearances",
        appearances
    );


    setSummaryValue(
        "summary-minutes",
        minutes
    );


    setSummaryValue(
        "summary-average-rating",

        averageRating !== null

            ? averageRating.toFixed(2)

            : "—"
    );


    setSummaryValue(
        "summary-goals",
        goals
    );


    setSummaryValue(
        "summary-assists",
        assists
    );


    setSummaryValue(
        "summary-shots",
        shots
    );


    setSummaryValue(
        "summary-key-passes",
        keyPasses
    );

}


/* =========================================================
   SUMMARY VALUE HELPER
========================================================= */

function setSummaryValue(
    elementId,
    value
) {

    const element =
        document.getElementById(
            elementId
        );


    if (element) {

        element.textContent =
            value;

    }

}


/* =========================================================
   RATING CHART
========================================================= */

function createRatingChart(
    statistics
) {

    const canvas =
        document.getElementById(
            "rating-chart"
        );


    if (!canvas) {

        return;

    }


    if (ratingChart) {

        ratingChart.destroy();

        ratingChart = null;

    }


    /*
        Only use matches where
        a rating exists.
    */

    
    const ratedMatches = statistics
    .filter(stat =>
        stat.rating !== null &&
        stat.rating !== undefined &&
        stat.rating !== "" &&
        Number.isFinite(Number(stat.rating))
    )
    .slice()
    .reverse();



    if (
        ratedMatches.length === 0
    ) {

        return;

    }


    const labels =
        ratedMatches.map(
            function (
                stat,
                index
            ) {

                return (
                    `Match ${index + 1}`
                );

            }
        );


    const ratings =
        ratedMatches.map(
            function (stat) {

                return Number(
                    stat.rating
                );

            }
        );


    ratingChart =
        new Chart(
            canvas,
            {

                type: "line",

                data: {

                    labels: labels,

                    datasets: [

                        {

                            label:
                                "Rating",

                            data:
                                ratings,

                            tension:
                                0.3,

                            borderWidth:
                                3,

                            borderColor:
                                "#16a34a",

                            backgroundColor:
                                "rgba(22, 163, 74, 0.12)",

                            pointBackgroundColor:
                                "#ffffff",

                            pointBorderColor:
                                "#16a34a",

                            pointBorderWidth:
                                2,

                            pointRadius:
                                4,

                            pointHoverRadius:
                                6,

                            fill:
                                true

                        }

                    ]

                },


                options: {

                    responsive:
                        true,

                    maintainAspectRatio:
                        false,

                    scales: {

                        y: {

                            min:
                                0,

                            max:
                                10,

                            title: {

                                display:
                                    true,

                                text:
                                    "Rating"

                            }

                        },


                        x: {

                            title: {

                                display:
                                    true,

                                text:
                                    "Matches"

                            }

                        }

                    },


                    plugins: {

                        legend: {

                            display:
                                true

                        },


                        tooltip: {

                            callbacks: {

                                label:
                                    function (
                                        context
                                    ) {

                                        return (
                                            `Rating: ${context.parsed.y}`
                                        );

                                    }

                            }

                        }

                    }

                }

            }
        );

}


/* =========================================================
   MINUTES CHART
========================================================= */

function createMinutesChart(
    statistics
) {

    const canvas =
        document.getElementById(
            "minutes-chart"
        );


    if (!canvas) {

        return;

    }


    if (minutesChart) {

        minutesChart.destroy();

        minutesChart = null;

    }


    /*
        Keep statistics that contain
        actual playing information.
    */

    
const matchStatistics = statistics
    .filter(stat =>
        stat.minutes_played !== null &&
        stat.minutes_played !== undefined &&
        stat.minutes_played !== "" &&
        Number.isFinite(Number(stat.minutes_played))
    )
    .slice()
    .reverse();



    if (
        matchStatistics.length ===
        0
    ) {

        return;

    }


    const labels =
        matchStatistics.map(
            function (
                stat,
                index
            ) {

                return (
                    `Match ${index + 1}`
                );

            }
        );


    const minutes =
        matchStatistics.map(
            function (stat) {

                return Number(
                    stat.minutes_played
                );

            }
        );


    minutesChart =
        new Chart(
            canvas,
            {

                type:
                    "bar",

                data: {

                    labels:
                        labels,

                    datasets: [

                        {

                            label:
                                "Minutes Played",

                            data:
                                minutes,

                            backgroundColor:
                                "rgba(22, 163, 74, 0.78)",

                            hoverBackgroundColor:
                                "#15803d",

                            borderColor:
                                "#15803d",

                            borderWidth:
                                1,

                            borderRadius:
                                6

                        }

                    ]

                },


                options: {

                    responsive:
                        true,

                    maintainAspectRatio:
                        false,

                    scales: {

                        y: {

                            beginAtZero:
                                true,

                            title: {

                                display:
                                    true,

                                text:
                                    "Minutes"

                            }

                        },


                        x: {

                            title: {

                                display:
                                    true,

                                text:
                                    "Matches"

                            }

                        }

                    },


                    plugins: {

                        legend: {

                            display:
                                true

                        },


                        tooltip: {

                            callbacks: {

                                label:
                                    function (
                                        context
                                    ) {

                                        const index =
                                            context.dataIndex;


                                        const stat =
                                            matchStatistics[
                                                index
                                            ];


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

            }
        );

}


/* =========================================================
   POSITION ANALYSIS
========================================================= */

function createPositionAnalysis(
    statistics
) {

    const container =
        document.getElementById(
            "position-metrics"
        );


    const description =
        document.getElementById(
            "position-description"
        );


    if (!container) {

        return;

    }


    /*
        Get player position
        from the page.
    */

    const positionElement =
        document.querySelector(
            ".position"
        );


    if (!positionElement) {

        return;

    }


    const position =
        positionElement
            .textContent
            .trim();


    /*
        Calculate totals.
    */

    const totalGoals =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.goals ||
                    0
                ),

            0

        );


    const totalAssists =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.assists ||
                    0
                ),

            0

        );


    const totalShots =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.shots ||
                    0
                ),

            0

        );


    const totalShotsOnTarget =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.shots_on_target ||
                    0
                ),

            0

        );


    const totalKeyPasses =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.key_passes ||
                    0
                ),

            0

        );


    const totalTackles =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.tackles_won ||
                    0
                ),

            0

        );


    const totalInterceptions =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.interceptions ||
                    0
                ),

            0

        );


    const totalPassesCompleted =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.passes_completed ||
                    0
                ),

            0

        );


    const totalPassesAttempted =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.passes_attempted ||
                    0
                ),

            0

        );


    const totalDribblesCompleted =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.dribbles_completed ||
                    0
                ),

            0

        );


    const totalDribblesAttempted =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.dribbles_attempted ||
                    0
                ),

            0

        );


    const totalSaves =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.saves ||
                    0
                ),

            0

        );


    const totalShotsFaced =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.shots_faced ||
                    0
                ),

            0

        );


    const totalPenaltySaved =
        statistics.reduce(

            (sum, stat) =>
                sum +
                Number(
                    stat.penalty_saved ||
                    0
                ),

            0

        );


    /*
        Calculate percentages.
    */

    const passAccuracy =
        totalPassesAttempted > 0

            ? (
                totalPassesCompleted /
                totalPassesAttempted
            ) * 100

            : 0;


    const dribbleSuccess =
        totalDribblesAttempted > 0

            ? (
                totalDribblesCompleted /
                totalDribblesAttempted
            ) * 100

            : 0;


    const shotAccuracy =
        totalShots > 0

            ? (
                totalShotsOnTarget /
                totalShots
            ) * 100

            : 0;


    const savePercentage =
        totalShotsFaced > 0

            ? (
                totalSaves /
                totalShotsFaced
            ) * 100

            : 0;


    /*
        Position-specific metrics.
    */

    let metrics = [];


    if (position === "FW") {

        if (description) {

            description.textContent =
                "Attacking indicators for forwards";

        }


        metrics = [

            {
                label:
                    "Goals",

                value:
                    totalGoals
            },

            {
                label:
                    "Assists",

                value:
                    totalAssists
            },

            {
                label:
                    "Shots",

                value:
                    totalShots
            },

            {
                label:
                    "Shot Accuracy",

                value:
                    `${shotAccuracy.toFixed(1)}%`
            },

            {
                label:
                    "Key Passes",

                value:
                    totalKeyPasses
            },

            {
                label:
                    "Dribble Success",

                value:
                    `${dribbleSuccess.toFixed(1)}%`
            }

        ];

    }


    else if (
        position === "MF"
    ) {

        if (description) {

            description.textContent =
                "Creative and ball-progression indicators for midfielders";

        }


        metrics = [

            {
                label:
                    "Assists",

                value:
                    totalAssists
            },

            {
                label:
                    "Key Passes",

                value:
                    totalKeyPasses
            },

            {
                label:
                    "Pass Accuracy",

                value:
                    `${passAccuracy.toFixed(1)}%`
            },

            {
                label:
                    "Dribble Success",

                value:
                    `${dribbleSuccess.toFixed(1)}%`
            },

            {
                label:
                    "Tackles Won",

                value:
                    totalTackles
            },

            {
                label:
                    "Interceptions",

                value:
                    totalInterceptions
            }

        ];

    }


    else if (
        position === "DF"
    ) {

        if (description) {

            description.textContent =
                "Defensive and ball-retention indicators for defenders";

        }


        metrics = [

            {
                label:
                    "Tackles Won",

                value:
                    totalTackles
            },

            {
                label:
                    "Interceptions",

                value:
                    totalInterceptions
            },

            {
                label:
                    "Pass Accuracy",

                value:
                    `${passAccuracy.toFixed(1)}%`
            },

            {
                label:
                    "Dribble Success",

                value:
                    `${dribbleSuccess.toFixed(1)}%`
            },

            {
                label:
                    "Key Passes",

                value:
                    totalKeyPasses
            },

            {
                label:
                    "Assists",

                value:
                    totalAssists
            }

        ];

    }


    else if (
        position === "GK"
    ) {

        if (description) {

            description.textContent =
                "Goalkeeping indicators based on shots faced and saves";

        }


        metrics = [

            {
                label:
                    "Saves",

                value:
                    totalSaves
            },

            {
                label:
                    "Shots Faced",

                value:
                    totalShotsFaced
            },

            {
                label:
                    "Save Percentage",

                value:
                    `${savePercentage.toFixed(1)}%`
            },

            {
                label:
                    "Penalty Saves",

                value:
                    totalPenaltySaved
            },

            {
                label:
                    "Pass Accuracy",

                value:
                    `${passAccuracy.toFixed(1)}%`
            },

            {
                label:
                    "Interceptions",

                value:
                    totalInterceptions
            }

        ];

    }


    else {

        if (description) {

            description.textContent =
                "General performance indicators";

        }


        metrics = [

            {
                label:
                    "Goals",

                value:
                    totalGoals
            },

            {
                label:
                    "Assists",

                value:
                    totalAssists
            },

            {
                label:
                    "Shots",

                value:
                    totalShots
            },

            {
                label:
                    "Key Passes",

                value:
                    totalKeyPasses
            },

            {
                label:
                    "Tackles Won",

                value:
                    totalTackles
            },

            {
                label:
                    "Interceptions",

                value:
                    totalInterceptions
            }

        ];

    }


    /*
        Display metrics.
    */

    container.innerHTML =
        "";


    metrics.forEach(
        function (metric) {

            const card =
                document.createElement(
                    "div"
                );


            card.className =
                "position-metric";


            card.innerHTML = `

                <span
                    class="position-metric-label"
                >

                    ${metric.label}

                </span>

                <strong
                    class="position-metric-value"
                >

                    ${metric.value}

                </strong>

            `;


            container.appendChild(
                card
            );

        }
    );

}


/* =========================================================
   PERFORMANCE TABLE
========================================================= */

function createPerformanceTable(
    statistics
) {

    const tableBody =
        document.getElementById(
            "performance-table-body"
        );


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

    const completedMatches =
        statistics

            .filter(
                stat =>
                    stat.match_date
            )

            .slice()

            .sort(
                function (a, b) {

                    return (
                        new Date(
                            b.match_date
                        ) -
                        new Date(
                            a.match_date
                        )
                    );

                }
            );


    if (
        completedMatches.length ===
        0
    ) {

        tableBody.innerHTML = `

            <tr>

                <td
                    colspan="10"
                    class="no-data-row"
                >

                    No completed match statistics available.

                </td>

            </tr>

        `;


        return;

    }


    tableBody.innerHTML =
        "";


    completedMatches.forEach(
        function (stat) {

            const playerClub =
                stat.club_name;


            let opponent =
                "";

            let venue =
                "";


            if (
                stat.home_club_name ===
                playerClub
            ) {

                opponent =
                    stat.away_club_name;

                venue =
                    "Home";

            } else {

                opponent =
                    stat.home_club_name;

                venue =
                    "Away";

            }


            const row =
                document.createElement(
                    "tr"
                );


            row.innerHTML = `

                <td>

                    ${formatDate(
                        stat.match_date
                    )}

                </td>


                <td class="opponent">

                    ${opponent}

                </td>


                <td>

                    <span
                        class="venue ${venue.toLowerCase()}"
                    >

                        ${venue}

                    </span>

                </td>


                <td>

                    ${
                        stat.started
                            ? "Yes"
                            : "No"
                    }

                </td>


                <td>

                    ${
                        stat.minutes_played ??
                        0
                    }

                </td>


                <td>

                    ${
                        stat.goals ??
                        0
                    }

                </td>


                <td>

                    ${
                        stat.assists ??
                        0
                    }

                </td>


                <td>

                    ${
                        stat.shots ??
                        0
                    }

                </td>


                <td>

                    ${
                        stat.key_passes ??
                        0
                    }

                </td>


                <td class="rating">

                    ${
                        stat.rating ??
                        "—"
                    }

                </td>

            `;


            tableBody.appendChild(
                row
            );

        }
    );

}


/* =========================================================
   FORMAT DATE
========================================================= */

function formatDate(
    dateString
) {

    if (!dateString) {

        return "—";

    }


    const date =
        new Date(
            dateString
        );


    return date.toLocaleDateString(

        "en-GB",

        {

            day:
                "2-digit",

            month:
                "short",

            year:
                "numeric"

        }

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