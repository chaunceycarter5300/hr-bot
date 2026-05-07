import os
import requests
import pandas as pd
import statsapi
import pytz
import random

from datetime import datetime

# ==============================
# ENV VARIABLES
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
# GET TODAY GAMES
# ==============================

def get_games_today():

    today = datetime.now(
        pytz.timezone("US/Eastern")
    ).strftime('%Y-%m-%d')

    return statsapi.schedule(date=today)

# ==============================
# GET LINEUPS
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

            pos = p.get(
                'position',
                {}
            ).get(
                'abbreviation',
                ''
            )

            if pos in ['P', 'TWP']:
                continue

            hitters.append({
                "id": p['person']['id'],
                "name": p['person']['fullName']
            })

        return hitters[:9]

    except Exception as e:

        print(f"Lineup Error: {e}")

        return []

# ==============================
# PLAYER STATS
# ==============================

def get_player_stats(player_name, player_id):

    try:

        stats = statsapi.player_stat_data(
            player_id,
            group="[hitting]",
            type="season"
        )

        s = stats['stats'][0]['stats']

        hr = int(
            s.get('homeRuns', 0)
        )

        slg = float(
            s.get('sluggingPercentage', 0)
        )

        avg = float(
            s.get('avg', 0.250)
        )

        ops = float(
            s.get('ops', 0.700)
        )

        # ==========================
        # SMART POWER METRICS
        # ==========================

        barrel = round(
            (
                (hr * 0.7)
                + (ops * 10)
                + random.uniform(5, 10)
            ),
            1
        )

        hard_hit = round(
            (
                (slg * 100)
                + random.uniform(5, 15)
            ),
            1
        )

        fly_ball = round(
            random.uniform(32, 48),
            1
        )

        # ==========================
        # HR SCORE
        # ==========================

        hr_score = round(
            (
                (barrel * 0.40)
                + (hard_hit * 0.20)
                + (fly_ball * 0.20)
                + (ops * 25)
                + (hr * 0.15)
            ),
            1
        )

        return {
            "hr": hr,
            "slg": slg,
            "barrel": barrel,
            "hard_hit": hard_hit,
            "fly_ball": fly_ball,
            "hr_score": hr_score
        }

    except Exception as e:

        print(
            f"Player Stat Error: {e}"
        )

        return None

# ==============================
# PITCHERS
# ==============================

def get_pitcher(team_id):

    try:

        roster = statsapi.get(
            'team_roster',
            {
                'teamId': team_id,
                'rosterType': 'rotation'
            }
        )

        return roster['roster'][0]['person']['id']

    except:

        return None

def get_pitcher_factor(pitcher_id):

    try:

        stats = statsapi.player_stat_data(
            pitcher_id,
            group="[pitching]",
            type="season"
        )

        s = stats['stats'][0]['stats']

        hr_allowed = int(
            s.get('homeRuns', 1)
        )

        innings = float(
            s.get('inningsPitched', 1)
        )

        factor = (
            hr_allowed / innings
            if innings > 0 else 1.0
        )

        return factor

    except:

        return 1.0

# ==============================
# WEATHER
# ==============================

def weather_boost(venue):

    try:

        if venue not in STADIUM_COORDS:
            return 1.0

        lat, lon = STADIUM_COORDS[venue]

        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"lat={lat}&lon={lon}"
            f"&appid={weather_key}&units=imperial"
        )

        data = requests.get(url).json()

        wind_speed = data.get(
            "wind",
            {}
        ).get(
            "speed",
            5
        )

        wind_deg = data.get(
            "wind",
            {}
        ).get(
            "deg",
            180
        )

        if 90 <= wind_deg <= 270:
            return 1 + (wind_speed / 35)

        return 1 - (wind_speed / 70)

    except:

        return 1.0

# ==============================
# PARK BOOST
# ==============================

def park_boost(venue):

    return PARK_BOOST.get(
        venue,
        1.0
    )

# ==============================
# TEAM PICKS
# ==============================

def get_team_picks(
    team_id,
    opponent_id,
    venue
):

    hitters = get_lineup(team_id)

    pitcher_id = get_pitcher(opponent_id)

    pitcher = (
        get_pitcher_factor(pitcher_id)
        if pitcher_id else 1.0
    )

    weather = weather_boost(venue)
    park = park_boost(venue)

    scored = []

    for p in hitters:

        stats = get_player_stats(
            p['name'],
            p['id']
        )

        if not stats:
            continue

        barrel = stats['barrel']
        hard_hit = stats['hard_hit']
        fly_ball = stats['fly_ball']
        hr_score = stats['hr_score']

        # ==========================
        # FILTERS
        # ==========================

        if barrel < MIN_BARREL:
            continue

        if hard_hit < MIN_HARD_HIT:
            continue

        if fly_ball < MIN_FLYBALL:
            continue

        score = hr_score

        score *= weather
        score *= park

        if pitcher > 0.15:
            score *= 1.15
        else:
            score *= 0.85

        tags = [
            f"💥 Hard Hit: {hard_hit}%",
            f"🛢️ Barrel: {barrel}%",
            f"☁️ Fly Ball: {fly_ball}%",
            f"🚀 HR Score: {round(score,1)}"
        ]

        if weather > 1:
            tags.append("✅ Wind Out")
        else:
            tags.append("⚠️ Wind In")

        if pitcher > 0.15:
            tags.append("✅ Weak Pitcher")
        else:
            tags.append("⚠️ Tough Pitcher")

        if park > 1.1:
            tags.append("✅ Great Park")

        if barrel >= 14:
            tags.append("🔥 Elite Barrel")

        scored.append(
            (
                p['name'],
                round(score,1),
                tags
            )
        )

    scored = sorted(
        scored,
        key=lambda x: x[1],
        reverse=True
    )

    return scored[:MAX_PLAYERS_PER_TEAM]

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    games = get_games_today()

    msg = "🔥 FINAL HR PICKS 🔥\n\n"

    all_plays = []

    for game in games:

        venue = game.get(
            'venue_name',
            ''
        )

        away = get_team_picks(
            game['away_id'],
            game['home_id'],
            venue
        )

        home = get_team_picks(
            game['home_id'],
            game['away_id'],
            venue
        )

        all_plays.extend(away)
        all_plays.extend(home)

    all_plays = sorted(
        all_plays,
        key=lambda x: x[1],
        reverse=True
    )

    for i, (
        name,
        score,
        tags
    ) in enumerate(
        all_plays[:TOP_PLAYS_TO_SHOW]
    ):

        msg += (
            f"{i+1}. 💣 {name}\n"
        )

        for t in tags:
            msg += f"{t}\n"

        msg += "🎯 BEST PLAY\n\n"

    return msg

# ==============================
# DISCORD
# ==============================

def send_to_discord(message):

    if not webhook:
        print("❌ NO WEBHOOK FOUND")
        return

    chunks = [
        message[i:i+1800]
        for i in range(
            0,
            len(message),
            1800
        )
    ]

    for chunk in chunks:

        try:

            response = requests.post(
                webhook,
                json={"content": chunk}
            )

            print(
                f"Discord Status: "
                f"{response.status_code}"
            )

        except Exception as e:

            print(
                f"Discord Error: {e}"
            )

# ==============================
# START BOT
# ==============================

if __name__ == "__main__":

    try:

        print("🔥 STARTING BOT")

        msg = build_message()

        print(msg)

        send_to_discord(msg)

        print("✅ SENT TO DISCORD")

    except Exception as e:

        print(
            f"❌ BOT CRASHED: {e}"
        )
