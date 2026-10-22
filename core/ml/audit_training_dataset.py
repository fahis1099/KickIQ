
from pathlib import Path
import json

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BASE_DIR / "datasets" / "kickiq_training_dataset.csv"
OUTPUT_DIR = BASE_DIR / "datasets"
REPORT_PATH = OUTPUT_DIR / "feature_timing_target_quality_audit.txt"
JSON_PATH = OUTPUT_DIR / "feature_timing_target_quality_audit.json"

TARGET = "target_rating"

IDENTIFIER_COLUMNS = [
    "player_id",
    "match_id",
    "match_date",
    "season",
    "competition",
    "club",
    "opponent",
]

# These are contextual values that should be known before a match.
EXPECTED_CONTEXT_COLUMNS = [
    "is_home",
    "position",
    "preferred_foot",
]


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def section(title):
    return f"\n{'=' * 72}\n{title}\n{'=' * 72}\n"


def safe_float(value):
    if pd.isna(value):
        return None
    return float(value)


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}\n"
            "Run: python manage.py build_training_dataset"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATASET_PATH)
    report = []
    results = {}

    # -----------------------------------------------------
    # 1. BASIC DATASET VALIDATION
    # -----------------------------------------------------

    report.append(section("1. DATASET OVERVIEW"))

    results["dataset"] = {
        "file": str(DATASET_PATH),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_player_match_pairs": (
            int(df.duplicated(["player_id", "match_id"]).sum())
            if {"player_id", "match_id"}.issubset(df.columns)
            else None
        ),
    }

    report.append(f"File: {DATASET_PATH}")
    report.append(f"Rows: {len(df):,}")
    report.append(f"Columns: {len(df.columns):,}")
    report.append(f"Duplicate complete rows: {df.duplicated().sum():,}")

    if {"player_id", "match_id"}.issubset(df.columns):
        duplicates = df.duplicated(["player_id", "match_id"]).sum()
        report.append(f"Duplicate player-match pairs: {duplicates:,}")

    required_columns = [
        TARGET,
        "player_id",
        "match_id",
        "match_date",
        "position",
    ]

    missing_required = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_required:
        raise ValueError(
            f"Missing required columns: {missing_required}"
        )

    # Parse dates for chronology checks.
    df["match_date"] = pd.to_datetime(
        df["match_date"], errors="coerce"
    )

    invalid_dates = int(df["match_date"].isna().sum())
    report.append(f"Invalid/missing match dates: {invalid_dates:,}")

    results["dataset"]["invalid_match_dates"] = invalid_dates

    # -----------------------------------------------------
    # 2. TARGET RATING QUALITY
    # -----------------------------------------------------

    report.append(section("2. TARGET RATING QUALITY"))

    target = pd.to_numeric(df[TARGET], errors="coerce")
    valid_target = target.dropna()

    target_summary = {
        "missing": int(target.isna().sum()),
        "minimum": safe_float(valid_target.min()),
        "maximum": safe_float(valid_target.max()),
        "mean": safe_float(valid_target.mean()),
        "median": safe_float(valid_target.median()),
        "standard_deviation": safe_float(valid_target.std()),
        "unique_values": int(valid_target.nunique()),
        "quantiles": {
            str(q): safe_float(valid_target.quantile(q))
            for q in [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
        },
        "outside_0_to_10": int(
            ((target < 0) | (target > 10)).sum()
        ),
        "integer_valued_targets": int(
            np.isclose(
                valid_target.to_numpy(),
                np.round(valid_target.to_numpy()),
                atol=1e-8,
            ).sum()
        ),
    }

    results["target_quality"] = target_summary

    for key, value in target_summary.items():
        if key != "quantiles":
            report.append(f"{key}: {value}")

    report.append("\nTarget quantiles:")
    for q, value in target_summary["quantiles"].items():
        report.append(f"  {q}: {value}")

    # Target distribution by position.
    report.append("\nTarget distribution by position:")
    position_summary = (
        df.assign(_target=target)
        .groupby("position", dropna=False)["_target"]
        .agg(["count", "mean", "std", "min", "median", "max"])
        .round(4)
    )

    report.append(position_summary.to_string())

    results["target_by_position"] = (
        position_summary.reset_index().to_dict(orient="records")
    )

    # Target distribution by season.
    if "season" in df.columns:
        report.append("\nTarget distribution by season:")
        season_summary = (
            df.assign(_target=target)
            .groupby("season", dropna=False)["_target"]
            .agg(["count", "mean", "std", "min", "max"])
            .round(4)
        )
        report.append(season_summary.to_string())
        results["target_by_season"] = (
            season_summary.reset_index().to_dict(orient="records")
        )

    # Target distribution by time period.
    dated = df.dropna(subset=["match_date"]).copy()
    dated["_target"] = pd.to_numeric(
        dated[TARGET], errors="coerce"
    )
    dated["_year_month"] = dated["match_date"].dt.to_period("M").astype(str)

    monthly = (
        dated.groupby("_year_month")["_target"]
        .agg(["count", "mean", "std"])
        .round(4)
    )

    report.append("\nMonthly target distribution (first 12 and last 12 months):")
    report.append(monthly.head(12).to_string())
    if len(monthly) > 12:
        report.append("\n...")
        report.append(monthly.tail(12).to_string())

    results["monthly_target_rows"] = int(len(monthly))

    # -----------------------------------------------------
    # 3. FEATURE TIMING AND TARGET LEAKAGE CHECKS
    # -----------------------------------------------------

    report.append(section("3. FEATURE TIMING AND LEAKAGE REVIEW"))

    excluded = [
        col for col in IDENTIFIER_COLUMNS + [TARGET]
        if col in df.columns
    ]

    # Mirror the exclusions used by the existing training script.
    model_features = [
        col for col in df.columns
        if col not in excluded
    ]

    results["feature_review"] = {
        "excluded_from_model": excluded,
        "model_feature_count": len(model_features),
        "model_features": model_features,
    }

    report.append("Columns excluded by the current training policy:")
    report.append(", ".join(excluded))

    report.append(f"\nRemaining candidate model features: {len(model_features)}")

    report.append("\nCandidate feature groups:")
    groups = {
        "Historical features": [
            c for c in model_features if c.startswith("history_")
        ],
        "FFI features": [
            c for c in model_features
            if c == "ffi" or c.startswith("ffi_")
        ],
        "Context features": [
            c for c in EXPECTED_CONTEXT_COLUMNS if c in model_features
        ],
        "Other candidate features": [
            c for c in model_features
            if not c.startswith("history_")
            and not (c == "ffi" or c.startswith("ffi_"))
            and c not in EXPECTED_CONTEXT_COLUMNS
        ],
    }

    for group, columns in groups.items():
        report.append(f"\n{group} ({len(columns)}):")
        report.append(", ".join(columns) if columns else "(none)")

    # Flag unexpected features for manual review.
    unexpected = groups["Other candidate features"]

    report.append("\nUnexpected candidate features requiring review:")
    report.append(
        ", ".join(unexpected)
        if unexpected
        else "None detected by this naming-based check."
    )

    results["feature_review"]["unexpected_candidate_features"] = unexpected

    # Check the generated dataset for columns whose names suggest
    # target/current-match information accidentally entered as features.
    suspicious_tokens = [
        "target_rating",
        "actual_rating",
        "current_match",
        "match_rating",
        "result_rating",
    ]

    suspicious_features = [
        col for col in model_features
        if any(token in col.lower() for token in suspicious_tokens)
    ]

    report.append("\nFeatures with potentially suspicious names:")
    report.append(
        ", ".join(suspicious_features)
        if suspicious_features
        else "None detected."
    )

    results["feature_review"]["suspicious_names"] = suspicious_features

    # Validate history and FFI field presence.
    history_features = [
        c for c in model_features if c.startswith("history_")
    ]
    ffi_features = [
        c for c in model_features
        if c == "ffi" or c.startswith("ffi_")
    ]

    report.append(f"\nHistorical feature count: {len(history_features)}")
    report.append(f"FFI feature count: {len(ffi_features)}")

    # Important: the CSV alone cannot prove that each feature was calculated
    # strictly before its target match. That requires reviewing the generator.
    report.append(
        "\nTIMING LOGIC TO VERIFY IN SOURCE CODE:\n"
        "- History queries must use match_date strictly earlier than the target.\n"
        "- FFI must be calculated with before_date=target.match_date.\n"
        "- The target match's statistics must not contribute to history or FFI.\n"
        "- Historical club context must be used for transferred players.\n"
        "- Position, preferred foot, and home/away status must reflect "
        "information available for the target match."
    )

    # -----------------------------------------------------
    # 4. MISSING, INFINITE, AND CONSTANT FEATURES
    # -----------------------------------------------------

    report.append(section("4. FEATURE DATA QUALITY"))

    missing_counts = df[model_features].isna().sum()
    missing_features = {
        col: int(count)
        for col, count in missing_counts.items()
        if count > 0
    }

    numeric_features = df[model_features].select_dtypes(
        include=[np.number]
    ).columns.tolist()

    infinite_features = {}
    for col in numeric_features:
        values = pd.to_numeric(df[col], errors="coerce").to_numpy()
        count = int(np.isinf(values).sum())
        if count > 0:
            infinite_features[col] = count

    constant_features = [
        col for col in model_features
        if df[col].nunique(dropna=False) <= 1
    ]

    results["feature_data_quality"] = {
        "features_with_missing_values": missing_features,
        "features_with_infinite_values": infinite_features,
        "constant_features": constant_features,
    }

    report.append(f"Features with missing values: {len(missing_features)}")
    for col, count in missing_features.items():
        report.append(f"  {col}: {count}")

    report.append(f"\nFeatures with infinite values: {len(infinite_features)}")
    for col, count in infinite_features.items():
        report.append(f"  {col}: {count}")

    report.append(f"\nConstant features: {len(constant_features)}")
    report.append(", ".join(constant_features) or "(none)")

    # -----------------------------------------------------
    # 5. CHRONOLOGICAL PARTITION AUDIT
    # -----------------------------------------------------

    report.append(section("5. CHRONOLOGICAL SPLIT AUDIT"))

    chronological = df.dropna(subset=["match_date"]).copy()
    unique_dates = np.sort(chronological["match_date"].unique())

    if len(unique_dates) < 3:
        report.append("Not enough distinct dates to construct three partitions.")
        results["chronological_split"] = {"error": "Too few distinct dates"}
    else:
        first_cut = int(len(unique_dates) * 0.60)
        second_cut = int(len(unique_dates) * 0.80)

        train_end = pd.Timestamp(unique_dates[first_cut - 1])
        validation_end = pd.Timestamp(unique_dates[second_cut - 1])

        train = chronological[
            chronological["match_date"] <= train_end
        ]
        validation = chronological[
            (chronological["match_date"] > train_end)
            & (chronological["match_date"] <= validation_end)
        ]
        test = chronological[
            chronological["match_date"] > validation_end
        ]

        def partition_summary(frame):
            values = pd.to_numeric(frame[TARGET], errors="coerce")
            return {
                "rows": int(len(frame)),
                "start_date": (
                    frame["match_date"].min().date().isoformat()
                    if len(frame) else None
                ),
                "end_date": (
                    frame["match_date"].max().date().isoformat()
                    if len(frame) else None
                ),
                "target_mean": safe_float(values.mean()),
                "target_std": safe_float(values.std()),
                "target_min": safe_float(values.min()),
                "target_max": safe_float(values.max()),
                "position_counts": {
                    str(k): int(v)
                    for k, v in frame["position"].value_counts(
                        dropna=False
                    ).items()
                },
            }

        split_results = {
            "train": partition_summary(train),
            "validation": partition_summary(validation),
            "test": partition_summary(test),
            "distinct_dates": int(len(unique_dates)),
        }

        results["chronological_split"] = split_results

        for name, details in split_results.items():
            if name == "distinct_dates":
                report.append(f"Distinct dates: {details}")
                continue
            report.append(f"\n{name.upper()}:")
            for key, value in details.items():
                report.append(f"  {key}: {value}")

        # Every target row sharing a date must stay in one partition.
        date_partition = {}
        for name, frame in [
            ("train", train),
            ("validation", validation),
            ("test", test),
        ]:
            for date in frame["match_date"].unique():
                date_partition.setdefault(str(date), set()).add(name)

        cross_partition_dates = {
            date: sorted(partitions)
            for date, partitions in date_partition.items()
            if len(partitions) > 1
        }

        results["chronological_split"]["dates_crossing_partitions"] = (
            cross_partition_dates
        )

        report.append(
            "\nDates appearing in multiple partitions: "
            f"{len(cross_partition_dates)}"
        )

    # -----------------------------------------------------
    # 6. CORRELATION DIAGNOSTIC
    # -----------------------------------------------------

    report.append(section("6. NUMERIC FEATURE CORRELATION DIAGNOSTIC"))

    numeric_df = df[model_features].select_dtypes(
        include=[np.number]
    ).copy()
    numeric_df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")

    correlations = (
        numeric_df.corr(numeric_only=True)[TARGET]
        .drop(labels=[TARGET], errors="ignore")
        .dropna()
    )

    top_correlations = correlations.reindex(
        correlations.abs().sort_values(ascending=False).index
    ).head(20)

    report.append(
        "Top 20 numeric feature correlations with target_rating "
        "(descriptive only):"
    )
    report.append(top_correlations.round(4).to_string())

    results["top_target_correlations"] = {
        str(k): safe_float(v) for k, v in top_correlations.items()
    }

    report.append(
        "\nInterpretation warning: high correlation alone does not prove "
        "leakage. Review feature-generation timing before removing features."
    )

    # -----------------------------------------------------
    # 7. SUMMARY AND OUTPUT
    # -----------------------------------------------------

    report.append(section("7. AUDIT SUMMARY"))

    issues = []

    if results["dataset"]["duplicate_player_match_pairs"] not in (0, None):
        issues.append("Duplicate player-match pairs exist.")

    if invalid_dates:
        issues.append("Some rows have invalid/missing match dates.")

    if target_summary["missing"]:
        issues.append("Target ratings are missing.")

    if target_summary["outside_0_to_10"]:
        issues.append("Some target ratings are outside the 0-10 range.")

    if missing_features:
        issues.append("Candidate features contain missing values.")

    if infinite_features:
        issues.append("Candidate features contain infinite values.")

    if constant_features:
        issues.append("Some candidate features are constant.")

    if unexpected:
        issues.append("Review unexpected candidate feature names.")

    if suspicious_features:
        issues.append("Review potentially suspicious feature names.")

    if issues:
        report.append("Items requiring attention:")
        for issue in issues:
            report.append(f"- {issue}")
    else:
        report.append(
            "No basic structural issues were detected by these checks."
        )

    report.append(
        "\nThis is a diagnostic audit, not proof that the ratings are "
        "accurate or that no leakage exists. Source-code timing checks "
        "remain essential."
    )

    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
    JSON_PATH.write_text(
        json.dumps(results, indent=2, default=str),
        encoding="utf-8",
    )

    print("\n".join(report))
    print(f"\nText report saved to: {REPORT_PATH}")
    print(f"JSON report saved to: {JSON_PATH}")


if __name__ == "__main__":
    main()
