
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

TARGET = "target_rating"
TEST_RATIO = 0.20
RANDOM_STATE = 42

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
# 2. LOAD AND SORT DATA
# --------------------------------------------------

def main():
    df = pd.read_csv(DATASET_PATH)
    df["match_date"] = pd.to_datetime(df["match_date"], errors="raise")
    df = df.sort_values("match_date").reset_index(drop=True)

    unique_dates = np.sort(df["match_date"].unique())

    split_index = int(len(unique_dates) * (1 - TEST_RATIO))
    split_index = max(1, min(split_index, len(unique_dates) - 1))
    split_date = pd.Timestamp(unique_dates[split_index])

    train_mask = df["match_date"] < split_date
    test_mask = df["match_date"] >= split_date

    train_df = df.loc[train_mask].copy()
    test_df = df.loc[test_mask].copy()

    feature_columns = [
        col for col in df.columns
        if col not in EXCLUDED_COLUMNS
    ]

    X_train = train_df[feature_columns].copy()
    X_test = test_df[feature_columns].copy()

    y_train = train_df[TARGET].astype(float)
    y_test = test_df[TARGET].astype(float)

    categorical_features = [
        col for col in feature_columns
        if (
            X_train[col].dtype == "object"
            or pd.api.types.is_string_dtype(X_train[col])
        )
    ]

    numeric_features = [
        col for col in feature_columns
        if col not in categorical_features
    ]

    for col in categorical_features:
        X_train[col] = X_train[col].astype(str)
        X_test[col] = X_test[col].astype(str)

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

    print("=" * 65)
    print("KICKIQ: MODEL COMPARISON")
    print("=" * 65)
    print(f"Training records: {len(train_df)}")
    print(f"Testing records:  {len(test_df)}")
    print(f"Split date:       {split_date.date()}")
    print(f"Training ends:    {train_df['match_date'].max().date()}")
    print(f"Testing starts:   {test_df['match_date'].min().date()}")

    results = []

    # --------------------------------------------------
    # 3. EVALUATION HELPER
    # --------------------------------------------------

    def record_results(name, actual, predicted):
        results.append({
            "Model": name,
            "Records": len(actual),
            "MAE": mean_absolute_error(actual, predicted),
            "RMSE": np.sqrt(mean_squared_error(actual, predicted)),
            "R2": r2_score(actual, predicted),
        })

    # --------------------------------------------------
    # 4. HISTORICAL-MEAN BASELINE
    # --------------------------------------------------

    baseline = test_df["history_rating_mean_5"].astype(float)

    record_results(
        "Historical Mean - All Positions",
        y_test,
        baseline,
    )

    # --------------------------------------------------
    # 5. SINGLE RANDOM FOREST
    # --------------------------------------------------

    global_model = Pipeline([
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

    print("\nTraining one Random Forest for all positions...")
    global_model.fit(X_train, y_train)

    global_predictions = global_model.predict(X_test)

    record_results(
        "Random Forest - All Positions",
        y_test,
        global_predictions,
    )

    # --------------------------------------------------
    # 6. POSITION-SPECIFIC MODELS
    # --------------------------------------------------

    position_predictions = {}

    for position in sorted(train_df["position"].dropna().unique()):
        position_train_mask = train_df["position"] == position
        position_test_mask = test_df["position"] == position

        position_train = train_df.loc[position_train_mask]
        position_test = test_df.loc[position_test_mask]

        if len(position_test) == 0:
            print(f"\nSkipping {position}: no test records.")
            continue

        if len(position_train) < 50:
            print(f"\nSkipping {position}: too few training records.")
            continue

        X_pos_train = position_train[feature_columns].copy()
        X_pos_test = position_test[feature_columns].copy()

        y_pos_train = position_train[TARGET].astype(float)
        y_pos_test = position_test[TARGET].astype(float)

        for col in categorical_features:
            X_pos_train[col] = X_pos_train[col].astype(str)
            X_pos_test[col] = X_pos_test[col].astype(str)

        # Create a fresh preprocessor for each position model.
        position_preprocessor = ColumnTransformer(
            transformers=[
                ("numeric", "passthrough", numeric_features),
                *(
                    [(
                        "categorical",
                        OneHotEncoder(handle_unknown="ignore"),
                        categorical_features,
                    )]
                    if categorical_features else []
                ),
            ],
            remainder="drop",
        )

        position_model = Pipeline([
            ("preprocessor", position_preprocessor),
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

        print(
            f"\nTraining {position} model: "
            f"{len(position_train)} records"
        )

        position_model.fit(X_pos_train, y_pos_train)
        position_pred = position_model.predict(X_pos_test)

        position_predictions[position] = position_pred

        record_results(
            f"Random Forest - {position}",
            y_pos_test,
            position_pred,
        )

        # Compare this position against its own historical baseline.
        position_baseline = position_test[
            "history_rating_mean_5"
        ].astype(float)

        record_results(
            f"Historical Mean - {position}",
            y_pos_test,
            position_baseline,
        )

    # --------------------------------------------------
    # 7. COMBINED POSITION-SPECIFIC RESULT
    # --------------------------------------------------

    combined_predictions = pd.Series(
        index=test_df.index,
        dtype=float,
    )

    for position, prediction in position_predictions.items():
        mask = test_df["position"] == position
        combined_predictions.loc[test_df.index[mask]] = prediction

    valid = combined_predictions.notna()

    if valid.any():
        record_results(
            "Random Forest - Position-Specific Combined",
            y_test.loc[valid],
            combined_predictions.loc[valid],
        )

        record_results(
            "Historical Mean - Same Records",
            y_test.loc[valid],
            test_df.loc[
                valid, "history_rating_mean_5"
            ].astype(float),
        )

    # --------------------------------------------------
    # 8. DISPLAY AND SAVE RESULTS
    # --------------------------------------------------

    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        by="MAE",
        ascending=True,
    ).reset_index(drop=True)

    print("\n" + "=" * 65)
    print("COMPARISON RESULTS")
    print("=" * 65)
    print(results_df.round(4).to_string(index=False))

    output_path = BASE_DIR / "models" / "kickiq_model_comparison.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results_df.to_csv(output_path, index=False)

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
