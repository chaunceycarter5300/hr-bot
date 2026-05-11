import os
import requests
import pytz
import statsapi
import random

from datetime import datetime

# ==============================
# ENV
# ==============================

webhook = os.getenv(
    "DISCORD_WEBHOOK"
)

# ==============================
# DISCORD
# ==============================

def send_to_discord(message):

    if not webhook:

        print("❌ NO WEBHOOK")

        return

    try:

        if len(message) > 1900:

            message = message[:1900]

        response = requests.post(

            webhook,

            json={
                "content": message
            }

        )

        if response.status_code in [200, 204]:

            print("✅ SENT TO DISCORD")

        else:

            print(
                f"❌ Discord Error: "
                f"{response.status_code}"
            )

            print(response.text)

    except Exception as e:

        print(
            f"❌ Discord Exception: {e}"
        )

# ==============================
# WEATHER
# ==============================

def get_weather_boost(city):

    api_key = os.getenv(
        "OPENWEATHER_API_KEY"
    )

    if not api_key:

        return 0

    try:

        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={api_key}&units=imperial"
        )

        r = requests.get(url).json()

        temp = r['main']['temp']

        wind = r['wind']['speed']

        boost = 0

        if temp >= 80:

            boost += 3

        if wind >= 10:

            boost += 3

        return boost

    except:

        return 0

# ==============================
# TEAM STRENGTH
# ==============================

def get_team_strength(team_name):

    try:

        standings = statsapi.standings_data()

        for league in standings.values():

            for division in league.values():

                for team in division['teams']:

                    if (
                        team['name']
                        == team_name
                    ):

                        wins = int(
                            team.get('w', 0)
                        )

                        losses = int(
                            team.get('l', 0)
                        )

                        games = wins + losses

                        if games == 0:

                            return 0.500

                        return round(
                            wins / games,
                            3
                        )

    except:

        pass

    return 0.500

# ==============================
# PITCHER STATS
# ==============================

def get_pitcher_stats(team_id):

    try:

        roster = statsapi.get(

            'team_roster',

            {

                'teamId': team_id,
                'rosterType': 'rotation'

            }

        )

        pitcher_id = (
            roster['roster'][0]
            ['person']['id']
        )

        stats = statsapi.player_stat_data(

            pitcher_id,

            group="[pitching]",
            type="season"

        )

        s = stats['stats'][0]['stats']

        return {

            "era":
            float(
                s.get('era', 4.00)
            ),

            "whip":
            float(
                s.get('whip', 1.30)
            ),

            "k9":
            float(
                s.get(
                    'strikeoutsPer9Inn',
                    8.0
                )
            ),

            "hr9":
            float(
                s.get(
                    'homeRunsPer9',
                    1.1
                )
            )

        }

    except:

        return {

            "era": 4.00,
            "whip": 1.30,
            "k9": 8.0,
            "hr9": 1.1

        }

# ==============================
# LIGHTWEIGHT POWER PROFILE
# ==============================

def get_lightweight_power_boost(

    hr,
    ops,
    slg

):

    boost = 0

    # ======================
    # BARREL STYLE BOOST
    # ======================

    if slg >= .550:

        boost += 10

    elif slg >= .500:

        boost += 6

    # ======================
    # HARD HIT STYLE BOOST
    # ======================

    if ops >= .950:

        boost += 8

    elif ops >= .850:

        boost += 4

    # ======================
    # TRUE POWER BAT
    # ======================

    if hr >= 20:

        boost += 12

    elif hr >= 15:

        boost += 8

    elif hr >= 10:

        boost += 5

    # ======================
    # FLY BALL STYLE BOOST
    # ======================

    if slg >= .500 and hr >= 10:

        boost += 5

    # ======================
    # DANGEROUS HR PROFILE
    # ======================

    if ops >= .850 and slg >= .500:

        boost += 5

    return boost

# ==============================
# LIVE TEAM HITTERS
# ==============================

def get_team_hitters(team_id):

    hitters = []

    try:

        roster = statsapi.get(

            'team_roster',

            {

                'teamId': team_id,
                'rosterType': 'active'

            }

        )

        for player in roster['roster']:

            try:

                player_name = (
                    player['person']['fullName']
                )

                player_id = (
                    player['person']['id']
                )

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
                    s.get('slg', 0.350)
                )

                ops = float(
                    s.get('ops', 0.650)
                )

                avg = float(
                    s.get('avg', 0.220)
                )

                if hr < 3:

                    continue

                score = 0

                # ======================
                # BASE POWER
                # ======================

                score += hr * 3

                score += ops * 10

                score += slg * 15

                score += avg * 5

                # ======================
                # LIGHTWEIGHT STATCAST
                # ======================

                score += get_lightweight_power_boost(

                    hr,
                    ops,
                    slg

                )

                hitters.append({

                    "name":
                    player_name,

                    "score":
                    score,

                    "hr":
                    hr,

                    "ops":
                    ops,

                    "slg":
                    slg

                })

            except:

                continue

    except:

        pass

    return hitters

# ==============================
# HR PROBABILITY
# ==============================

def calculate_hr_probability(

    hitter,
    pitcher,
    team_strength,
    weather_boost

):

    score = 10

    score += hitter['score'] / 10

    # TRUE ELITE POWER

    if hitter['hr'] >= 20:

        score += 8

    elif hitter['hr'] >= 15:

        score += 5

    # ELITE OPS

    if hitter['ops'] >= .950:

        score += 4

    # ELITE SLG

    if hitter['slg'] >= .550:

        score += 4

    # HR/9

    if pitcher['hr9'] >= 1.6:

        score += 10

    elif pitcher['hr9'] >= 1.3:

        score += 6

    # ERA

    if pitcher['era'] >= 5:

        score += 5

    elif pitcher['era'] >= 4:

        score += 3

    # WHIP

    if pitcher['whip'] >= 1.40:

        score += 4

    # LOW K PITCHER

    if pitcher['k9'] <= 7:

        score += 4

    elif pitcher['k9'] >= 10:

        score -= 3

    # TEAM QUALITY

    if team_strength >= 0.600:

        score += 5

    elif team_strength <= 0.450:

        score -= 3

    # WEATHER

    score += weather_boost

    return int(

        max(
            15,
            min(
                48,
                score
            )
        )

    )

# ==============================
# BEST HR HITTER
# ==============================

def get_best_hr_hitter(

    hitters,
    pitcher,
    strength,
    weather_boost

):

    if not hitters:

        return None

    best = None
    best_prob = 0

    for hitter in hitters:

        prob = calculate_hr_probability(

            hitter,
            pitcher,
            strength,
            weather_boost

        )

        if prob > best_prob:

            best_prob = prob

            best = {

                "name":
                hitter['name'],

                "prob":
                prob

            }

    return best

# ==============================
# BUILD BOARD
# ==============================

def get_board():

    today = datetime.now(

        pytz.timezone(
            "US/Eastern"
        )

    ).strftime('%Y-%m-%d')

    games = statsapi.schedule(
        date=today
    )

    board = []

    for game in games:

        try:

            away = game['away_name']
            home = game['home_name']

            away_id = game['away_id']
            home_id = game['home_id']

            home_strength = get_team_strength(
                home
            )

            away_strength = get_team_strength(
                away
            )

            weather_boost = get_weather_boost(
                home
            )

            home_pitch = get_pitcher_stats(
                home_id
            )

            away_pitch = get_pitcher_stats(
                away_id
            )

            # HOME

            home_hitters = get_team_hitters(
                home_id
            )

            best_home = get_best_hr_hitter(

                home_hitters,
                away_pitch,
                home_strength,
                weather_boost

            )

            if best_home:

                board.append({

                    "team":
                    home,

                    "player":
                    best_home['name'],

                    "prob":
                    best_home['prob']

                })

            # AWAY

            away_hitters = get_team_hitters(
                away_id
            )

            best_away = get_best_hr_hitter(

                away_hitters,
                home_pitch,
                away_strength,
                weather_boost

            )

            if best_away:

                board.append({

                    "team":
                    away,

                    "player":
                    best_away['name'],

                    "prob":
                    best_away['prob']

                })

        except Exception as e:

            print(
                f"Game Error: {e}"
            )

    return sorted(

        board,

        key=lambda x: x['prob'],
        reverse=True

    )[:10]

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    board = get_board()

    msg = (
        "🔥 MOST LIKELY HR TODAY 🔥\n\n"
    )

    for i, g in enumerate(board):

        medal = "⭐"

        if i == 0:

            medal = "🥇"

        elif i == 1:

            medal = "🥈"

        elif i == 2:

            medal = "🥉"

        msg += (
            f"{medal} "
            f"{g['team']}\n\n"
        )

        msg += (
            f"💣 "
            f"{g['player']} HR\n"
        )

        msg += (
            f"📊 HR Confidence: "
            f"{g['prob']}%\n"
        )

        msg += (
            "\n----------------------\n\n"
        )

    return msg

# ==============================
# START BOT
# ==============================

if __name__ == "__main__":

    try:

        print(
            "🔥 STARTING LIGHTWEIGHT STATCAST HR ENGINE"
        )

        msg = build_message()

        print(msg)

        send_to_discord(msg)

    except Exception as e:

        print(
            f"❌ BOT ERROR: {e}"
        )
