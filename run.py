import os
import requests
import pandas as pd
import statsapi
import pytz

from datetime import datetime
from pybaseball import batting_stats

# ==============================
# ENV
# ==============================

webhook = os.getenv("DISCORD_WEBHOOK")
weather_key = os.getenv("OPENWEATHER_API_KEY")

# ==============================
# SETTINGS
# ==============================

MIN_BARREL = 10
MIN_HARD_HIT = 40
MIN_FLYBALL = 35

TOP_PLAYS_TO_SHOW = 5
MAX_PLAYERS_PER_TEAM = 1

# ==============================
# WEATHER / PARKS
# ==============================

PARK_BOOST = {
    "Coors Field": 1.25,
    "Yankee Stadium": 1.15,
    "Great American Ball Park": 1.12,
    "Fenway Park": 1.10
}

STADIUM_COORDS = {
    "Yankee Stadium": (40.8296, -73.9262),
    "Coors Field": (39.7559, -104.9942),
    "Fenway Park": (42.3467, -71.0972)
}

# ==============================
# LOAD REAL STATCAST DATA
# ==============================

print("Loading Statcast data...")

statcast_df = batting_stats(2025)

# ==============================
# GET TODAY GAMES
# ==============================


def get_games_today():

    today = datetime.now(
        pytz.timezone("US/Eastern")
    ).strftime('%Y-%m-%d')

    return statsapi.schedule(date=today)

# ==============================
# GET LINEUP
# ==============================


def get_lineup(team_id):

    try:

        roster = statsapi.get(
            'team_roster',
            {
                'teamId': team_id,
                'rosterType': 'active'
            }
        )

        hitters = []

        for p in roster['roster']:

    send_to_discord(msg)
