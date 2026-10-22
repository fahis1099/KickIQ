
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# --------------------------------------------------
# 1. PATHS AND CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DATASET_PATH = BASE_DIR / "datasets" / "kickiq_training_dataset.csv"
MODEL_DIR = BASE_DIR / "models"

MODEL_PATH = MODEL_DIR / "kickiq_rating_model.joblib"
METRICS_PATH = MODEL_DIR / "kickiq_model_metrics.json"
IMPORTANCE_PATH = MODEL_DIR / "kickiq_feature_importance.csv"

TARGET = "target_rating"
TEST_RATIO = 0.20
RANDOM_STATE = 42


# --------------------------------------------------
# 2. LOAD DATASET
# --------------------------------------------------

def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {DATASET_PATH}"
        )

    df = pd.read_csv(DATASET_PATH)

    if TARGET not in df.columns:
        raise ValueError(f"Target column '{TARGET}' is missing.")

    df["match_date"] = pd.to_datetime(
        df["match_date"], errors="raise"
    )

    df = df.sort_values("match_date").reset_index(drop=True)

    if df[TARGET].isna().any():
        raise ValueError("Target ratings contain missing values.")

    if not df[TARGET].between(0, 10).all():
        raise ValueError("Target ratings must be between 0 and 10.")

    print("=" * 60)
    print("KICKIQ - PLAYER RATING MODEL TRAINING")
    print("=" * 60)
    print(f"Dataset records: {len(df)}")
    print(f"Dataset columns: {len(df.columns)}")
    print(f"Date range: {df['match_date'].min().date()} to "
          f"{df['match_date'].max().date()}")


    # --------------------------------------------------
    # 3. SELECT FEATURES
    # --------------------------------------------------

    # Exclude target, direct identifiers, and date/metadata
    # from the initial baseline model.
    excluded_columns = {
        "target_rating",
        "player_id",
        "match_id",
        "match_date",
        "season",
        "competition",
        "club",
        "opponent",
    }

    feature_columns = [
        col for col in df.columns
        if col not in excluded_columns
    ]

    X = df[feature_columns].copy()
    y = df[TARGET].astype(float)

    
    categorical_features = [
        col for col in X.columns
        if (
            X[col].dtype == "object"
            or isinstance(X[col].dtype, pd.StringDtype)
            or pd.api.types.is_string_dtype(X[col])
        )
    ]

    numeric_features = [
        col for col in X.columns
        if col not in categorical_features
    ]


    print(f"Selected features: {len(feature_columns)}")
    print(f"Numeric features: {len(numeric_features)}")
    print(f"Categorical features: {len(categorical_features)}")

    if X.isna().any().any():
        raise ValueError("Input features contain missing values.")

    if categorical_features:
        for col in categorical_features:
            X[col] = X[col].astype(str)


    # --------------------------------------------------
    # 4. CHRONOLOGICAL TRAIN/TEST SPLIT
    # --------------------------------------------------

    # Split by distinct dates so records from the same date
    # are not divided between training and testing.
    unique_dates = np.sort(df["match_date"].unique())

    if len(unique_dates) < 2:
        raise ValueError(
            "At least two distinct match dates are required."
        )

    split_index = int(len(unique_dates) * (1 - TEST_RATIO))
    split_index = max(1, min(split_index, len(unique_dates) - 1))

    split_date = pd.Timestamp(unique_dates[split_index])

    train_mask = df["match_date"] < split_date
    test_mask = df["match_date"] >= split_date

    X_train = X.loc[train_mask].copy()
    X_test = X.loc[test_mask].copy()

    y_train = y.loc[train_mask].copy()
    y_test = y.loc[test_mask].copy()

    print("\nChronological split")
    print(f"Training records: {len(X_train)}")
    print(f"Testing records: {len(X_test)}")
    print(f"Last training date: "
          f"{df.loc[train_mask, 'match_date'].max().date()}")
    print(f"First testing date: "
          f"{df.loc[test_mask, 'match_date'].min().date()}")

    if len(X_train) == 0 or len(X_test) == 0:
        raise ValueError("Training or testing dataset is empty.")


    # --------------------------------------------------
    # 5. PREPROCESSING
    # --------------------------------------------------

    transformers = []

    if numeric_features:
        transformers.append(("numeric", "passthrough", numeric_features))

    if categorical_features:
        transformers.append((
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features,
        ))

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )


    # --------------------------------------------------
    # 6. RANDOM FOREST REGRESSOR
    # --------------------------------------------------

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features=1.0,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", model),
    ])


    # --------------------------------------------------
    # 7. TRAIN THE MODEL
    # --------------------------------------------------

    print("\nTraining Random Forest...")
    pipeline.fit(X_train, y_train)

    print("Training completed.")


    # --------------------------------------------------
    # 8. EVALUATE THE MODEL
    # --------------------------------------------------

    predictions = pipeline.predict(X_test)
    
    
    # Evaluate predictions separately for each position
    position_results = df.loc[test_mask, ["position"]].copy()
    position_results["actual"] = y_test.to_numpy()
    position_results["random_forest"] = predictions
    position_results["historical_mean"] = (
        df.loc[test_mask, "history_rating_mean_5"].to_numpy()
    )

    print("\nPosition-wise model evaluation")

    for position, group in position_results.groupby("position"):
        actual = group["actual"]
        rf_pred = group["random_forest"]
        history_pred = group["historical_mean"]

        print(f"\nPosition: {position} | Records: {len(group)}")
        print(
            f"Random Forest MAE: "
            f"{mean_absolute_error(actual, rf_pred):.4f}"
        )
        print(
            f"Historical Mean MAE: "
            f"{mean_absolute_error(actual, history_pred):.4f}"
        )
        print(
            f"Random Forest RMSE: "
            f"{np.sqrt(mean_squared_error(actual, rf_pred)):.4f}"
        )
        print(
            f"Random Forest R²: "
            f"{r2_score(actual, rf_pred):.4f}"
        )
    
    print("\nBaseline comparison")

    baseline_features = [
        "history_latest_rating",
        "history_rating_mean_5",
        "ffi_weighted_average_rating",
    ]

    results = []

    results.append({
        "Model": "Random Forest",
        "MAE": mean_absolute_error(y_test, predictions),
        "RMSE": np.sqrt(mean_squared_error(y_test, predictions)),
        "R2": r2_score(y_test, predictions),
    })

    for feature in baseline_features:
        if feature in df.columns:
            baseline_pred = df.loc[test_mask, feature].astype(float)

            results.append({
                "Model": feature,
                "MAE": mean_absolute_error(y_test, baseline_pred),
                "RMSE": np.sqrt(
                    mean_squared_error(y_test, baseline_pred)
                ),
                "R2": r2_score(y_test, baseline_pred),
            })

    comparison = pd.DataFrame(results)
    print(comparison.round(4).to_string(index=False))

    
    
    # Diagnostic checks
    baseline_predictions = np.full(len(y_test), y_train.mean())

    print("\nPrediction diagnostics")
    print(f"Actual rating mean: {y_test.mean():.4f}")
    print(f"Actual rating std:  {y_test.std():.4f}")
    print(f"Predicted mean:     {predictions.mean():.4f}")
    print(f"Predicted std:      {predictions.std():.4f}")
    print(
        f"Baseline MAE:       "
        f"{mean_absolute_error(y_test, baseline_predictions):.4f}"
    )
    print(
        f"Baseline RMSE:      "
        f"{np.sqrt(mean_squared_error(y_test, baseline_predictions)):.4f}"
    )

    
    print("\nRating distribution")
    print("Training target:")
    print(y_train.describe().round(3).to_string())

    print("\nTesting target:")
    print(y_test.describe().round(3).to_string())

    print("\nTesting ratings by position:")
    diagnostic_df = df.loc[test_mask, ["position", TARGET]].copy()
    print(
        diagnostic_df.groupby("position")[TARGET]
        .agg(["count", "mean", "std"])
        .round(3)
        .to_string()
    )

    if np.std(predictions) > 0 and np.std(y_test) > 0:
        correlation = np.corrcoef(y_test, predictions)[0, 1]
        print(f"\nActual-predicted correlation: {correlation:.4f}")
    else:
        print("\nActual-predicted correlation: undefined")


    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)
    acc = accuracy_score(y_test.round(), predictions.round())   

    print("\n" + "=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)
    print(f"MAE  : {mae:.4f}")
    print(f"RMSE : {rmse:.4f}")
    print(f"R²   : {r2:.4f}")
    print(f"Acc  : {acc:.4f}")

    print("\nInterpretation:")
    print(f"On average, predictions differ from actual ratings "
          f"by approximately {mae:.3f} rating points.")
    print("Lower MAE and RMSE are better.")
    print("R² measures how well the model explains rating variation; "
          "higher is generally better.")


    # --------------------------------------------------
    # 9. SAVE MODEL AND METRICS
    # --------------------------------------------------

    joblib.dump(pipeline, MODEL_PATH)

    metrics = {
        "model": "RandomForestRegressor",
        "dataset_path": str(DATASET_PATH),
        "total_records": int(len(df)),
        "training_records": int(len(X_train)),
        "testing_records": int(len(X_test)),
        "feature_count": int(len(feature_columns)),
        "features": feature_columns,
        "categorical_features": categorical_features,
        "numeric_features": numeric_features,
        "split_date": split_date.date().isoformat(),
        "training_end_date": (
            df.loc[train_mask, "match_date"].max().date().isoformat()
        ),
        "testing_start_date": (
            df.loc[test_mask, "match_date"].min().date().isoformat()
        ),
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "random_state": RANDOM_STATE,
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=4)

    # Save feature importance for later analysis.
    fitted_preprocessor = pipeline.named_steps["preprocessor"]
    fitted_model = pipeline.named_steps["regressor"]

    transformed_names = fitted_preprocessor.get_feature_names_out()

    importance_df = pd.DataFrame({
        "feature": transformed_names,
        "importance": fitted_model.feature_importances_,
    }).sort_values("importance", ascending=False)

    importance_df.to_csv(IMPORTANCE_PATH, index=False)

    print("\nSaved files:")
    print(f"Model: {MODEL_PATH}")
    print(f"Metrics: {METRICS_PATH}")
    print(f"Feature importance: {IMPORTANCE_PATH}")

    print("\nTop 15 features:")
    print(importance_df.head(15).to_string(index=False))

    print("\nTraining pipeline finished successfully.")


if __name__ == "__main__":
    main()
