# src/models/train.py
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from src.utils.logger import get_logger
from sklearn.model_selection import GridSearchCV
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import duckdb

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
    'is_weekend',
    'day_of_week',
    'month'
]

WINNER_TARGET = 'result_encoded'
GOALS_TARGET = 'total_goals'

# train on historical seasons, test on most recent season
TRAIN_SEASONS = ['1516', '1617', '1718', '1819', '1920', '2021', '2122', '2223', '2324', '2425']
TEST_SEASON = '2526'

def load_gold() -> pd.DataFrame:
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "data" / "gold" / "gold_football.db"

    with duckdb.connect(str(db_path), read_only=True) as con:
        df = con.execute("""
            SELECT
                f.*,
                ht.team_name   AS home_team,
                awt.team_name  AS away_team,
                r.referee_name AS referee,
                d.is_weekend,
                d.month,
                d.day_of_week
            FROM fact_matches f
            JOIN dim_team    ht  ON f.home_team_id = ht.team_id
            JOIN dim_team    awt ON f.away_team_id = awt.team_id
            JOIN dim_referee r   ON f.referee_id   = r.referee_id
            JOIN dim_date    d   ON f.date_id      = d.date_id
            WHERE f.result_encoded IS NOT NULL
            ORDER BY d.full_date
        """).df()

    logger.info(f"Loaded {len(df)} rows from gold")
    return df

def tune_model(X_train, y_train):
    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [5, 8, None],
        'class_weight': ['balanced']
    }
    rf = RandomForestClassifier(random_state=42)
    grid = GridSearchCV(rf, param_grid, cv=5, scoring='f1_macro')
    grid.fit(X_train, y_train)
    return grid.best_estimator_, grid.best_params_

def train_goals_model(X_train, y_train):
    # Regression for total goals
    reg = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
    reg.fit(X_train, y_train)
    return reg

def save_model(model, filename):
    model_path = Path(__file__).resolve().parent.parent.parent / "models" / filename
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    logger.info(f"Model saved to {model_path}")

def train():
    df = load_gold()

    train_df = df[df['season'].isin(TRAIN_SEASONS)]
    test_df = df[df['season'] == TEST_SEASON]

    X_train, y_train_win = train_df[FEATURES], train_df[WINNER_TARGET]
    X_test, y_test_win = test_df[FEATURES], test_df[WINNER_TARGET]

    y_train_goals = train_df[GOALS_TARGET]
    y_test_goals = test_df[GOALS_TARGET]
        
    # train classifier
    logger.info("Tuning Classifier...")
    winner_model, win_params = tune_model(X_train, y_train_win)
    win_acc = accuracy_score(y_test_win, winner_model.predict(X_test))
    
    # train goals regressor
    logger.info("Training Goals Regressor...")
    goals_model = train_goals_model(X_train, y_train_goals)
    goals_mae = mean_absolute_error(y_test_goals, goals_model.predict(X_test))

    logger.info(f"Winner Accuracy: {win_acc:.4f} | Goals MAE: {goals_mae:.4f}")

    save_model(winner_model, "random_forest.pkl")
    save_model(goals_model, "goals_regressor.pkl")

if __name__ == '__main__':
    train()
