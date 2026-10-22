
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BASE_DIR / "datasets" / "kickiq_training_dataset.csv"
OUTPUT_DIR = BASE_DIR / "models"

TARGET = "target_rating"
RANDOM_STATE = 42

# Split distinct match dates, not individual rows.
TRAIN_RATIO = 0.60
VALIDATION_RATIO = 0.20

EXCLUDED_COLUMNS = {
    "target_rating",
    "player_id",
    "match_id",
    "match_date",
    "season",
    "competition",
    "club",
    "opponent",
}


# --------------------------------------------------
# 2. HELPER FUNCTIONS
# --------------------------------------------------

def make_model(numeric_features, categorical_features):
    transformers = []

    if numeric_features:
        transformers.append(
            ("numeric", "passthrough", numeric_features)
        )

    if categorical_features:
        transformers.append(
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_features,
            )
        )

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )

    return Pipeline([
        ("preprocessor", preprocessor),
        (
            "regressor",
            RandomForestRegressor(
                n_estimators=300,
                max_depth=None,
                min_samples_split=5,
                min_samples_leaf=2,
                max_features=1.0,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        ),
    ])


def calculate_metrics(actual, predicted):
    return {
        "Records": len(actual),
        "MAE": mean_absolute_error(actual, predicted),
        "RMSE": np.sqrt(mean_squared_error(actual, predicted)),
        "R2": r2_score(actual, predicted),
    }


def prepare_features(frame, feature_columns, categorical_features):
    X = frame[feature_columns].copy()

    for col in categorical_features:
        X[col] = X[col].astype(str)

    return X


# --------------------------------------------------
# 3. LOAD AND VALIDATE DATA
# --------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    df["match_date"] = pd.to_datetime(df["match_date"], errors="raise")
    df = df.sort_values("match_date").reset_index(drop=True)

    if df[TARGET].isna().any():
        raise ValueError("Target ratings contain missing values.")

    if not df[TARGET].between(0, 10).all():
        raise ValueError("Target ratings must be between 0 and 10.")

    unique_dates = np.sort(df["match_date"].unique())

    if len(unique_dates) < 3:
        raise ValueError("At least three distinct match dates are required.")

    # Date boundaries based on distinct dates.
    train_end_index = int(len(unique_dates) * TRAIN_RATIO)
    validation_end_index = int(
        len(unique_dates) * (TRAIN_RATIO + VALIDATION_RATIO)
    )

    train_end_index = max(1, train_end_index)
    validation_end_index = max(
        train_end_index + 1,
        validation_end_index,
    )
    validation_end_index = min(
        validation_end_index,
        len(unique_dates) - 1,
    )

    train_end_date = pd.Timestamp(unique_dates[train_end_index])
    validation_end_date = pd.Timestamp(
        unique_dates[validation_end_index]
    )

    train_mask = df["match_date"] < train_end_date
    validation_mask = (
        (df["match_date"] >= train_end_date)
        & (df["match_date"] < validation_end_date)
    )
    test_mask = df["match_date"] >= validation_end_date

    train_df = df.loc[train_mask].copy()
    validation_df = df.loc[validation_mask].copy()
    test_df = df.loc[test_mask].copy()

    print("=" * 70)
    print("KICKIQ: CHRONOLOGICAL TRAIN / VALIDATION / TEST")
    print("=" * 70)

    for name, frame in [
        ("Training", train_df),
        ("Validation", validation_df),
        ("Final test", test_df),
    ]:
        if frame.empty:
            raise ValueError(f"{name} period is empty.")

        print(
            f"{name:12}: {len(frame):5} records | "
            f"{frame['match_date'].min().date()} to "
            f"{frame['match_date'].max().date()}"
        )

    feature_columns = [
        col for col in df.columns
        if col not in EXCLUDED_COLUMNS
    ]

    # Detect text columns using the complete feature schema.
    categorical_features = [
        col for col in feature_columns
        if (
            pd.api.types.is_object_dtype(df[col])
            or pd.api.types.is_string_dtype(df[col])
        )
    ]

    numeric_features = [
        col for col in feature_columns
        if col not in categorical_features
    ]

    print(f"\nFeature count: {len(feature_columns)}")
    print(f"Numeric features: {len(numeric_features)}")
    print(f"Categorical features: {len(categorical_features)}")

    # --------------------------------------------------
    # 4. TRAIN ON TRAINING PERIOD ONLY
    # --------------------------------------------------

    X_train = prepare_features(
        train_df, feature_columns, categorical_features
    )
    y_train = train_df[TARGET].astype(float)

    X_validation = prepare_features(
        validation_df, feature_columns, categorical_features
    )
    y_validation = validation_df[TARGET].astype(float)

    X_test = prepare_features(
        test_df, feature_columns, categorical_features
    )
    y_test = test_df[TARGET].astype(float)

    model = make_model(numeric_features, categorical_features)

    print("\nTraining global Random Forest on training period...")
    model.fit(X_train, y_train)

    # --------------------------------------------------
    # 5. VALIDATION COMPARISON
    # --------------------------------------------------

    validation_predictions = model.predict(X_validation)

    validation_results = []

    validation_results.append({
        "Model": "Random Forest - Global",
        **calculate_metrics(y_validation, validation_predictions),
    })

    validation_baseline = validation_df[
        "history_rating_mean_5"
    ].astype(float).to_numpy()

    validation_results.append({
        "Model": "Historical Mean",
        **calculate_metrics(y_validation, validation_baseline),
    })

    # Train position-specific models on the training period only.
    position_validation_predictions = pd.Series(
        index=validation_df.index,
        dtype=float,
    )

    for position in sorted(train_df["position"].dropna().unique()):
        pos_train = train_df[train_df["position"] == position]
        pos_validation = validation_df[
            validation_df["position"] == position
        ]

        if pos_validation.empty or len(pos_train) < 50:
            continue

        X_pos_train = prepare_features(
            pos_train, feature_columns, categorical_features
        )
        y_pos_train = pos_train[TARGET].astype(float)

        X_pos_validation = prepare_features(
            pos_validation, feature_columns, categorical_features
        )

        pos_model = make_model(
            numeric_features, categorical_features
        )
        pos_model.fit(X_pos_train, y_pos_train)

        pos_predictions = pos_model.predict(X_pos_validation)

        position_validation_predictions.loc[
            pos_validation.index
        ] = pos_predictions

    valid_position_validation = (
        position_validation_predictions.notna()
    )

    if valid_position_validation.any():
        actual = validation_df.loc[
            valid_position_validation, TARGET
        ].astype(float)

        predicted = position_validation_predictions.loc[
            valid_position_validation
        ]

        validation_results.append({
            "Model": "Random Forest - Position-Specific",
            **calculate_metrics(actual, predicted),
        })

        validation_results.append({
            "Model": "Historical Mean - Same Records",
            **calculate_metrics(
                actual,
                validation_df.loc[
                    valid_position_validation,
                    "history_rating_mean_5",
                ].astype(float),
            ),
        })

    validation_table = pd.DataFrame(validation_results)
    validation_table = validation_table.sort_values("MAE")

    print("\n" + "=" * 70)
    print("VALIDATION RESULTS — USE THESE FOR MODEL SELECTION")
    print("=" * 70)
    print(validation_table.round(4).to_string(index=False))

    validation_path = (
        OUTPUT_DIR / "kickiq_validation_comparison.csv"
    )
    validation_table.to_csv(validation_path, index=False)

    print(f"\nValidation results saved to: {validation_path}")

    # --------------------------------------------------
    # 6. FINAL TEST: NOT USED FOR MODEL SELECTION
    # --------------------------------------------------

    # This is an initial final-period evaluation of the global model.
    # Do not use these results to tune hyperparameters.
    test_predictions = model.predict(X_test)

    final_results = [
        {
            "Model": "Random Forest - Global",
            **calculate_metrics(y_test, test_predictions),
        },
        {
            "Model": "Historical Mean",
            **calculate_metrics(
                y_test,
                test_df["history_rating_mean_5"].astype(float),
            ),
        },
    ]

    final_table = pd.DataFrame(final_results)

    print("\n" + "=" * 70)
    print("FINAL TEST RESULTS — GLOBAL MODEL VS BASELINE")
    print("=" * 70)
    print(final_table.round(4).to_string(index=False))

    final_path = OUTPUT_DIR / "kickiq_final_test_results.csv"
    final_table.to_csv(final_path, index=False)

    print(f"\nFinal test results saved to: {final_path}")
    print("\nEvaluation completed.")


if __name__ == "__main__":
    main()
