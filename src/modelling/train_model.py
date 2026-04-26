# src/models/train.py
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import mlflow
import mlflow.sklearn
from src.utils.logger import get_logger
from sklearn.model_selection import GridSearchCV
import joblib

logger = get_logger(__name__)

FEATURES = [
    'home_rolling_points',
    'away_rolling_points',
    'home_rolling_goals',
    'away_rolling_goals',
    'home_rolling_sot',
    'away_rolling_sot',
    'home_rest_days',
    'away_rest_days',
    'h2h_home_win_rate',
    'temp_max',
    'precipitation_mm',
    'windspeed_kmh',
]

TARGET = 'ft_result'

# train on historical seasons, test on most recent season
TRAIN_SEASONS = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324']
TEST_SEASON = '2425'

def load_gold(seasons):
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent

    dfs = []
    for season in seasons:
        path = root_dir / "data" / "gold" / "match_features" / f"season_{season}.csv"
        df = pd.read_csv(path)
        df['season'] = season
        dfs.append(df)

    combined = pd.concat(dfs).reset_index(drop=True)
    logger.info(f"loaded {len(combined)} rows from {len(seasons)} seasons")
    return combined

def prepare_data(df):
    X = df[FEATURES]
    y = df[TARGET]
    return X, y

def evaluate(model, X_test, y_test, model_name):
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred)

    logger.info(f"{model_name} accuracy: {accuracy:.4f}")
    print(f"\n=== {model_name} ===")
    print(f"accuracy: {accuracy:.4f}")
    print(report)

    return accuracy, y_pred

def tune_hyperparameters(X_train, y_train):
    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [3, 5, 8, None],
        'min_samples_leaf': [1, 5, 10],
        'class_weight': ['balanced']
    }

    rf = RandomForestClassifier(random_state=42)

    grid_search = GridSearchCV(
        rf,
        param_grid,
        cv=5,   
        scoring='f1_macro', 
        verbose=1
    )

    grid_search.fit(X_train, y_train)

    logger.info(f"best params: {grid_search.best_params_}")
    logger.info(f"best cv score: {grid_search.best_score_:.4f}")

    return grid_search.best_estimator_, grid_search.best_params_

def save_model(model):
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    model_path = root_dir / "models" / "random_forest.pkl"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    logger.info(f"model saved to {model_path}")

def train():
    train_df = load_gold(TRAIN_SEASONS)
    test_df = load_gold([TEST_SEASON])

    X_train, y_train = prepare_data(train_df)
    X_test, y_test = prepare_data(test_df)

    mlflow.set_experiment("epl_match_prediction")

    with mlflow.start_run(run_name="random_forest_tuned"):
        # tune first
        model, best_params = tune_hyperparameters(X_train, y_train)

        # evaluate on test set
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, zero_division=0)

        print(f"Best params: {best_params}")
        print(f"Accuracy: {accuracy:.4f}")
        print(report)

        # log best params to mlflow
        for param, value in best_params.items():
            mlflow.log_param(param, value)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.sklearn.log_model(model, "random_forest_tuned")

        logger.info(f"best params: {best_params}")
        logger.info(f"accuracy: {accuracy:.4f}")

        # feature importance
        importance = pd.Series(
            model.feature_importances_,
            index=FEATURES
        ).sort_values(ascending=False)
        print("\n=== Feature Importance ===")
        print(importance)

    save_model(model)
    return model

if __name__ == '__main__':
    train()
