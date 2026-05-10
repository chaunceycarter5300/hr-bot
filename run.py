import os
import requests
import pytz
import statsapi

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

        # HOT WEATHER

        if temp >= 80:

            boost += 3

        # WIND

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

                    if team['name'] == team_name:

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

                # SKIP NON POWER

                if hr < 2:

                    continue

                # ======================
                # HR SCORE
                # ======================

                score = 0

                # POWER

                score += hr * 2.5

                # OPS

                score += ops * 12

                # SLUGGING

                score += slg * 18

                # AVG

                score += avg * 8

                # ELITE HR BOOST

                if hr >= 10:

                    score += 8

                if hr >= 20:

                    score += 12

                # ELITE OPS BOOST

                if ops >= .900:

                    score += 8

                # ELITE SLG BOOST

                if slg >= .500:

                    score += 8

                hitters.append({

                    "name":
                    player_name,

                    "score":
                    score,

                    "hr":
                    hr

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

    # BASE HITTER SCORE

    score += hitter['score'] / 10

    # ELITE HR BAT

    if hitter['hr'] >= 15:

        score += 6

    elif hitter['hr'] >= 10:

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

    # K9

    if pitcher['k9'] <= 7:

        score += 4

    elif pitcher['k9'] >= 10:

        score -= 3

    # TEAM STRENGTH

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
                45,
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
            "🔥 STARTING ADVANCED HR ENGINE"
        )

        msg = build_message()

        print(msg)

        send_to_discord(msg)

    except Exception as e:

        print(
            f"❌ BOT ERROR: {e}"
        )
