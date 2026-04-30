import streamlit as st
import pandas as pd
import numpy as np
import joblib
import glob
import requests
from pathlib import Path
from datetime import date
import duckdb

# paths
ROOT = Path(__file__).resolve().parent.parent
RF_MODEL_PATH = ROOT / "models" / "random_forest.pkl"
REGRESSOR_MODEL_PATH = ROOT / "models" / "random_forest.pkl"
GOLD_PATH = ROOT / "data" / "gold" / "match_features" / "all_matches.csv"
DB_PATH = ROOT / "data" / "gold" / "matches.duckdb"

# features
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

# load data
@st.cache_resource
def load_model():
    rf_model = joblib.load(ROOT / "models" / "random_forest.pkl")
    regressor_model = joblib.load(ROOT / "models" / "goals_regressor.pkl")
    return rf_model, regressor_model

@st.cache_data
def load_gold_data():
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        df = con.execute("SELECT * FROM matches_gold ORDER BY match_date DESC").df()
        con.close()
        return df
        
    except Exception as e:
        st.error(f"Error connecting to DuckDB: {e}")
        return pd.DataFrame()

@st.cache_data
def load_stadiums():
    df = pd.read_csv(ROOT / "data" / "bronze" / "stadiums" / "stadiums.csv")
    return dict(zip(df['Team'], zip(df['Latitude'], df['Longitude'])))

# get teams and stadiums
STADIUM_COORDS = load_stadiums()
df = load_gold_data()
TEAMS = list(df['mapped_home_team'].unique())

# helpers

def get_team_stats(df, team_name):
    # find the last game team played, regardless of home or away
    latest_match = df[(df['mapped_home_team'] == team_name) | (df['mapped_away_team'] == team_name)].iloc[0]
    
    if latest_match['mapped_home_team'] == team_name:
        return {
            'points': latest_match['home_rolling_points'],
            'goals': latest_match['home_rolling_goals'],
            'sot': latest_match['home_rolling_sot'],
            'rest_days': latest_match['home_rest_days'],      
            'h2h_win_rate': latest_match['h2h_home_win_rate']
        }
    else:
        return {
            'points': latest_match['away_rolling_points'],
            'goals': latest_match['away_rolling_goals'],
            'sot': latest_match['away_rolling_sot'],
            'rest_days': latest_match['away_rest_days'],      
            'h2h_win_rate': 1 - latest_match['h2h_home_win_rate']
        }

def get_weather(lat, lon, match_date):
    # fetch weather for match date and location
    try:
        date_str = match_date.strftime("%Y-%m-%d")
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,precipitation_sum,windspeed_10m_max",
            "timezone": "Europe/London",
            "start_date": date_str,
            "end_date": date_str,
        }
        r = requests.get(url, params=params).json()
        return {
            "temp_max": r["daily"]["temperature_2m_max"][0],
            "precipitation_mm": r["daily"]["precipitation_sum"][0],
            "windspeed_kmh": r["daily"]["windspeed_10m_max"][0],
        }
    except Exception:
        return 
    
def predict_winner(model, home_row, away_row, weather):
    feature_vector = pd.DataFrame([{
        'home_rolling_points': home_row['points'],
        'away_rolling_points': away_row['points'],
        'home_rolling_goals': home_row['goals'],
        'away_rolling_goals': away_row['goals'],
        'home_rolling_sot': home_row['sot'],
        'away_rolling_sot': away_row['sot'],
        'home_rest_days': home_row['rest_days'],      
        'away_rest_days': away_row['rest_days'],
        'h2h_home_win_rate': home_row['h2h_win_rate'],
        'temp_max': weather['temp_max'],
        'precipitation_mm': weather['precipitation_mm'],
        'windspeed_kmh': weather['windspeed_kmh'],
    }])

    prediction = model.predict(feature_vector)[0]
    probabilities = model.predict_proba(feature_vector)[0]
    prob_dict = dict(zip(model.classes_, probabilities))
    return prediction, prob_dict

def predict_total_goals(model, home_row, away_row, weather):
    feature_vector = pd.DataFrame([{
        'home_rolling_points': home_row['points'],
        'away_rolling_points': away_row['points'],
        'home_rolling_goals': home_row['goals'],
        'away_rolling_goals': away_row['goals'],
        'home_rolling_sot': home_row['sot'],
        'away_rolling_sot': away_row['sot'],
        'home_rest_days': home_row['rest_days'],      
        'away_rest_days': away_row['rest_days'],
        'h2h_home_win_rate': home_row['h2h_win_rate'],
        'temp_max': weather['temp_max'],
        'precipitation_mm': weather['precipitation_mm'],
        'windspeed_kmh': weather['windspeed_kmh'],
    }])

    predicted_sum = model.predict(feature_vector)[0]
    return predicted_sum
# ── ui ─────────────────────────────────────────────────
def main():

    df = load_gold_data()

    st.set_page_config(
        page_title="EPL Match Predictor",
        page_icon="⚽",
        layout="wide"
    )

    st.title("⚽ EPL Match Predictor")
    st.caption("Predict Premier League match outcomes using historical data and weather")

    # ── inputs ──
    st.subheader("Match Details")
    col1, col2, col3 = st.columns(3)

    with col1:
        home_team = st.selectbox("Home Team", TEAMS, index=0)
    with col2:
        away_options = [t for t in TEAMS if t != home_team]
        away_team = st.selectbox("Away Team", away_options, index=1)
    with col3:
        match_date = st.date_input("Match Date", value=date.today())

    predict_btn = st.button("Predict", type="primary", use_container_width=True)

    if predict_btn:
        if home_team == away_team:
            st.error("Home and away team cannot be the same")
            return

        with st.spinner("Fetching data and making prediction..."):
            rf_model, regressor_model = load_model()

            home_features = get_team_stats(df, home_team)
            away_features = get_team_stats(df, away_team)

            # get weather
            lat, lon = STADIUM_COORDS.get(home_team)
            weather = get_weather(lat, lon, match_date)

            # make prediction
            prediction, prob_dict = predict_winner(
                rf_model, home_features, away_features, weather
            )

            total_goals_pred = predict_total_goals(
                regressor_model, home_features, away_features, weather
            )

        st.divider()
        st.subheader("Match Predicton")

        result_map = {
            'H': f"{home_team} Win",
            'D': "Draw",
            'A': f"{away_team} Win"
        }

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label=f"{home_team} Win",
                value=f"{prob_dict.get('H', 0):.0%}"
            )
        with col2:
            st.metric(
                label="Draw",
                value=f"{prob_dict.get('D', 0):.0%}"
            )
        with col3:
            st.metric(
                label=f"{away_team} Win",
                value=f"{prob_dict.get('A', 0):.0%}"
            )

        # highlight prediction
        st.success(f"**Predicted Result: {result_map[prediction]}**")

        st.markdown("---")
        st.subheader("Goals Prediction")
        
        st.metric(
            label="Predicted Total Goals", 
            value=f"{total_goals_pred:.2f}"
        )

        # ── weather ──
        st.divider()
        st.subheader(f"Match Day Weather")
        w1, w2, w3 = st.columns(3)
        with w1:
            st.metric("Temperature", f"{weather['temp_max']}°C")
        with w2:
            st.metric("Precipitation", f"{weather['precipitation_mm']}mm")
        with w3:
            st.metric("Wind Speed", f"{weather['windspeed_kmh']} km/h")

if __name__ == '__main__':
    main()