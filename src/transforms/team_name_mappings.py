# src/transforms/team_name_normaliser.py
from thefuzz import process
import pandas as pd
import logging

def map_team_names(fixtures_df, stadiums_df):

    stadium_teams = stadiums_df['Team'].tolist()
    
    def find_best_match(team_name):
        match, score = process.extractOne(team_name, stadium_teams)
        if score >= 80:  
            return match
        return None 
    
    fixtures_df['mapped_team'] = fixtures_df['HomeTeam'].apply(find_best_match)
    
    result = fixtures_df.merge(
        stadiums_df,
        left_on='mapped_team',
        right_on='Team',
        how='left'
    )
    
    return result