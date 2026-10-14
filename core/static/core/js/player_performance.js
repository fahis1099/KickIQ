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

        window.__kickIQPlayerStatistics = allPlayerStatistics;


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
   SELF-CONTAINED CANVAS CHARTS
   No Chart.js/CDN dependency required.
========================================================= */

function drawPerformanceCanvas(canvas, values, labels, options = {}) {
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = Math.max(320, canvas.clientWidth || canvas.parentElement?.clientWidth || 600);
    const height = Math.max(240, canvas.clientHeight || canvas.parentElement?.clientHeight || 320);
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    const isBar = options.type === "bar";
    const color = "#16a34a";
    const plot = { left: 48, right: width - 18, top: 18, bottom: height - 48 };
    const plotWidth = plot.right - plot.left;
    const plotHeight = plot.bottom - plot.top;
    if (plotWidth <= 0 || plotHeight <= 0 || !values.length) return;

    const maxValue = options.maxValue || Math.max(1, Math.ceil(Math.max(...values) / 10) * 10);
    const minValue = options.minValue ?? 0;
    const range = Math.max(1, maxValue - minValue);
    const y = value => plot.bottom - ((value - minValue) / range) * plotHeight;
    const x = index => values.length === 1
        ? plot.left + plotWidth / 2
        : plot.left + (index / (values.length - 1)) * plotWidth;

    ctx.font = "12px Arial, sans-serif";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#e5e7eb";
    ctx.fillStyle = "#64748b";

    const ticks = 5;
    for (let i = 0; i <= ticks; i++) {
        const value = minValue + (range / ticks) * i;
        const yy = y(value);
        ctx.beginPath();
        ctx.moveTo(plot.left, yy);
        ctx.lineTo(plot.right, yy);
        ctx.stroke();
        ctx.textAlign = "right";
        ctx.fillText(Number.isInteger(value) ? String(value) : value.toFixed(1), plot.left - 9, yy);
    }

    if (isBar) {
        const slot = plotWidth / values.length;
        const barWidth = Math.max(1, Math.min(24, slot * 0.68));
        values.forEach((value, i) => {
            const barX = x(i) - barWidth / 2;
            const barY = y(value);
            ctx.fillStyle = color;
            const barH = Math.max(0, plot.bottom - barY);
            ctx.beginPath();
            const radius = Math.min(5, barWidth / 2, barH / 2);
            ctx.roundRect(barX, barY, barWidth, barH, radius);
            ctx.fill();
        });
    } else {
        // Light fill under the rating trend.
        ctx.beginPath();
        values.forEach((value, i) => {
            const px = x(i), py = y(value);
            if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        });
        ctx.lineTo(x(values.length - 1), plot.bottom);
        ctx.lineTo(x(0), plot.bottom);
        ctx.closePath();
        ctx.fillStyle = "rgba(22, 163, 74, 0.10)";
        ctx.fill();

        ctx.beginPath();
        values.forEach((value, i) => {
            const px = x(i), py = y(value);
            if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        });
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.lineJoin = "round";
        ctx.stroke();

        // Draw a visible point for EVERY match so each rating can be hovered.
        values.forEach((value, i) => {
            ctx.beginPath();
            ctx.arc(x(i), y(value), values.length > 80 ? 2.6 : 3.5, 0, Math.PI * 2);
            ctx.fillStyle = "#ffffff";
            ctx.fill();
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.8;
            ctx.stroke();
        });
    }

    // Show a readable subset of match labels when there are many records.
    const labelStep = Math.max(1, Math.ceil(labels.length / 8));
    ctx.fillStyle = "#64748b";
    ctx.font = "11px Arial, sans-serif";
    ctx.textAlign = "center";
    labels.forEach((label, i) => {
        if (i % labelStep !== 0 && i !== labels.length - 1) return;
        const px = isBar
            ? (values.length === 1 ? plot.left + plotWidth / 2 : plot.left + (i / values.length) * plotWidth + plotWidth / values.length / 2)
            : x(i);
        ctx.fillText(label, px, plot.bottom + 20);
    });

    ctx.fillStyle = "#334155";
    ctx.font = "12px Arial, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(options.xTitle || "Matches", plot.left + plotWidth / 2, height - 10);
    ctx.save();
    ctx.translate(13, plot.top + plotHeight / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(options.yTitle || "Value", 0, 0);
    ctx.restore();

    // Store chart geometry and metadata for interactive point tooltips.
    canvas.__kickIQChart = {
        values: values.slice(),
        labels: labels.slice(),
        x,
        y,
        plot,
        dpr,
        metadata: Array.isArray(options.pointMetadata) ? options.pointMetadata : [],
        valueLabel: options.valueLabel || (isBar ? "Value" : "Rating"),
        isBar
    };

    if (!canvas.__kickIQHoverBound) {
        canvas.__kickIQHoverBound = true;
        canvas.style.cursor = "crosshair";
        canvas.addEventListener("mousemove", event => {
            const chart = canvas.__kickIQChart;
            if (!chart || !chart.values.length) return;
            const rect = canvas.getBoundingClientRect();
            const px = event.clientX - rect.left;
            const py = event.clientY - rect.top;
            let nearest = -1;
            let nearestDistance = Infinity;
            chart.values.forEach((value, index) => {
                const pointX = chart.x(index);
                const pointY = chart.y(value);
                const distance = Math.hypot(px - pointX, py - pointY);
                if (distance < nearestDistance) {
                    nearestDistance = distance;
                    nearest = index;
                }
            });
            const hitRadius = chart.isBar ? 18 : 12;
            if (nearest < 0 || nearestDistance > hitRadius) {
                hideKickIQChartTooltip(canvas);
                return;
            }
            const meta = chart.metadata[nearest] || {};
            const tooltip = getKickIQChartTooltip(canvas);
            tooltip.replaceChildren();
            const rows = [
                [chart.valueLabel || "Rating", meta.value ?? meta.rating ?? chart.values[nearest]],
                ["Match week", meta.week ?? "Unavailable"],
                ["Season", meta.season ?? "Unavailable"]
            ];
            rows.forEach(([label, value]) => {
                const row = document.createElement("div");
                row.style.cssText = "display:flex;gap:10px;justify-content:space-between;white-space:nowrap;";
                const key = document.createElement("span");
                key.textContent = label;
                key.style.color = "#cbd5e1";
                const val = document.createElement("strong");
                val.textContent = String(value);
                val.style.color = "#ffffff";
                row.append(key, val);
                tooltip.appendChild(row);
            });
            tooltip.style.display = "block";
            const hostRect = (canvas.parentElement || canvas).getBoundingClientRect();
            let left = event.clientX - hostRect.left + 12;
            let top = event.clientY - hostRect.top + 12;
            left = Math.max(4, Math.min(left, hostRect.width - tooltip.offsetWidth - 4));
            top = Math.max(4, Math.min(top, hostRect.height - tooltip.offsetHeight - 4));
            tooltip.style.left = `${left}px`;
            tooltip.style.top = `${top}px`;
        });
        canvas.addEventListener("mouseleave", () => hideKickIQChartTooltip(canvas));
    }
}

function getKickIQChartTooltip(canvas) {
    const host = canvas.parentElement || canvas;
    if (getComputedStyle(host).position === "static") host.style.position = "relative";
    let tooltip = host.querySelector(":scope > .kickiq-chart-tooltip");
    if (!tooltip) {
        tooltip = document.createElement("div");
        tooltip.className = "kickiq-chart-tooltip";
        tooltip.style.cssText = "position:absolute;z-index:20;display:none;pointer-events:none;padding:9px 11px;border-radius:8px;background:#0f172a;color:#fff;font:12px/1.6 Arial,sans-serif;box-shadow:0 8px 24px rgba(15,23,42,.22);";
        host.appendChild(tooltip);
    }
    return tooltip;
}

function hideKickIQChartTooltip(canvas) {
    const host = canvas.parentElement || canvas;
    const tooltip = host.querySelector(":scope > .kickiq-chart-tooltip");
    if (tooltip) tooltip.style.display = "none";
}

function getMatchWeek(stat, index) {
    const match = stat.match && typeof stat.match === "object" ? stat.match : {};
    const value = stat.match_week ?? stat.matchweek ?? stat.match_week_number ??
        stat.matchweek_number ?? stat.gameweek ?? stat.game_week ?? stat.week ??
        stat.round ?? match.match_week ?? match.matchweek ?? match.gameweek ?? match.week ?? match.round;
    if (value !== null && value !== undefined && String(value).trim() !== "") return value;
    return `Match ${index + 1}`;
}

function createRatingChart(statistics) {
    const canvas = document.getElementById("rating-chart");
    if (!canvas) return;

    const ratedMatches = (Array.isArray(statistics) ? statistics : [])
        .filter(stat => stat.rating !== null && stat.rating !== undefined && stat.rating !== "" && Number.isFinite(Number(stat.rating)))
        .slice().reverse();

    if (!ratedMatches.length) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
            canvas.width = Math.max(320, canvas.clientWidth || 600);
            canvas.height = Math.max(240, canvas.clientHeight || 320);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = "#64748b";
            ctx.font = "14px Arial, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("No rating data available", canvas.width / 2, canvas.height / 2);
        }
        return;
    }

    drawPerformanceCanvas(
        canvas,
        ratedMatches.map(stat => Number(stat.rating)),
        ratedMatches.map((_, index) => `Match ${index + 1}`),
        {
            type: "line",
            minValue: 0,
            maxValue: 10,
            yTitle: "Rating",
            xTitle: "Matches",
            pointMetadata: ratedMatches.map((stat, index) => ({
                rating: Number(stat.rating).toFixed(2),
                week: getMatchWeek(stat, index),
                season: stat.season ?? stat.season_name ?? (stat.match && stat.match.season) ?? "Unavailable"
            }))
        }
    );
}

function createMinutesChart(statistics) {
    const canvas = document.getElementById("minutes-chart");
    if (!canvas) return;

    const matchStatistics = (Array.isArray(statistics) ? statistics : [])
        .filter(stat => stat.minutes_played !== null && stat.minutes_played !== undefined && stat.minutes_played !== "" && Number.isFinite(Number(stat.minutes_played)))
        .slice().reverse();

    if (!matchStatistics.length) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
            canvas.width = Math.max(320, canvas.clientWidth || 600);
            canvas.height = Math.max(240, canvas.clientHeight || 320);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = "#64748b";
            ctx.font = "14px Arial, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("No minutes data available", canvas.width / 2, canvas.height / 2);
        }
        return;
    }

    const minutes = matchStatistics.map(stat => Number(stat.minutes_played));
    const maxMinutes = Math.max(90, Math.ceil(Math.max(...minutes) / 15) * 15);
    drawPerformanceCanvas(
        canvas,
        minutes,
        matchStatistics.map((_, index) => `Match ${index + 1}`),
        {
            type: "bar",
            minValue: 0,
            maxValue: maxMinutes,
            yTitle: "Minutes",
            xTitle: "Matches",
            valueLabel: "Minutes",
            pointMetadata: matchStatistics.map((stat, index) => ({
                value: Number(stat.minutes_played),
                week: getMatchWeek(stat, index),
                season: stat.season ?? stat.season_name ?? (stat.match && stat.match.season) ?? "Unavailable"
            }))
        }
    );
}

// Redraw canvas charts when the layout changes (responsive window resizing).
window.addEventListener("resize", () => {
    if (!Array.isArray(window.__kickIQPlayerStatistics)) return;
    createRatingChart(window.__kickIQPlayerStatistics);
    createMinutesChart(window.__kickIQPlayerStatistics);
});


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