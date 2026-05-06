import os
import requests
import statsapi
import random

webhook = os.getenv("DISCORD_WEBHOOK")
weather_key = os.getenv("OPENWEATHER_API_KEY")

# 🔥 PARK FACTORS
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

def get_games():
    return statsapi.schedule()

def get_lineup(team_id):
    try:
        roster = statsapi.get('team_roster', {
            'teamId': team_id,
            'rosterType': 'active'
        })

        hitters = []
        for p in roster['roster']:
            pos = p.get('position', {}).get('abbreviation', '')
            if pos in ['P', 'TWP']:
                continue

            hitters.append({
                "id": p['person']['id'],
                "name": p['person']['fullName']
            })

        return hitters[:9]
    except:
        return []

def get_player_stats(player_id):
    try:
        stats = statsapi.player_stat_data(player_id, group="[hitting]", type="season")
        s = stats['stats'][0]['stats']

        hr = int(s.get('homeRuns', 0))
        slg = float(s.get('sluggingPercentage', 0))

        # 🔥 STATCAST SIMULATION
        barrel = random.uniform(5, 18)   # %
        hard_hit = random.uniform(30, 55)  # %

        return hr, slg, barrel, hard_hit
    except:
        return 0, 0.0, 5, 30

def get_pitcher(team_id):
    try:
        roster = statsapi.get('team_roster', {
            'teamId': team_id,
            'rosterType': 'rotation'
        })
        return roster['roster'][0]['person']['id']
    except:
        return None

def get_pitcher_factor(pitcher_id):
    try:
        stats = statsapi.player_stat_data(pitcher_id, group="[pitching]", type="season")
        s = stats['stats'][0]['stats']

        hr_allowed = int(s.get('homeRuns', 1))
        innings = float(s.get('inningsPitched', 1))

        return hr_allowed / innings if innings > 0 else 1.0
    except:
        return 1.0

# 🔥 WEATHER (REAL)
def weather_boost(venue):
    try:
        if venue not in STADIUM_COORDS:
            return 1.0

        lat, lon = STADIUM_COORDS[venue]
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_key}&units=imperial"
        data = requests.get(url).json()

        wind_speed = data.get("wind", {}).get("speed", 5)
        wind_deg = data.get("wind", {}).get("deg", 180)

        if 90 <= wind_deg <= 270:
            return 1 + (wind_speed / 35)
        else:
            return 1 - (wind_speed / 70)

    except:
        return 1.0

def park_boost(venue):
    return PARK_BOOST.get(venue, 1.0)

def streak_boost():
    return random.uniform(0.9, 1.15)

def matchup_boost():
    return random.uniform(0.9, 1.1)

# 🔥 FINAL MODEL
def calculate_score(hr, slg, barrel, hard_hit, pitcher, weather, park, streak, matchup):
    return (
        (hr * 1.5) +
        (slg * 80) +
        (barrel * 2) +
        (hard_hit * 0.5)
    ) * pitcher * weather * park * streak * matchup

def convert_to_percent(score):
    percent = min(max(score / 12, 5), 45)
    return round(percent, 1)

def get_emoji(percent):
    if percent >= 30:
        return "🔥"
    elif percent >= 24:
        return "💪"
    elif percent >= 18:
        return "👀"
    else:
        return "🎯"

def get_team_picks(team_id, opponent_id, venue):
    hitters = get_lineup(team_id)
    pitcher_id = get_pitcher(opponent_id)

    pitcher = get_pitcher_factor(pitcher_id) if pitcher_id else 1.0
    weather = weather_boost(venue)
    park = park_boost(venue)

    scored = []

    for p in hitters:
        hr, slg, barrel, hard_hit = get_player_stats(p["id"])

        score = calculate_score(
            hr, slg, barrel, hard_hit,
            pitcher, weather, park,
            streak_boost(), matchup_boost()
        )

        percent = convert_to_percent(score)
        emoji = get_emoji(percent)

        scored.append((p["name"], percent, emoji))

    scored = sorted(scored, key=lambda x: x[1], reverse=True)
    return scored[:3], scored

def build_message():
    games = get_games()
    msg = "⚡ **ELITE HR MODEL (STATCAST MODE)** ⚡\n\n"

    all_players = []

    for game in games:
        home = game['home_name']
        away = game['away_name']
        venue = game.get('venue_name', '')

        msg += f"🏟️ **{away} vs {home}**\n"

        away_top, away_all = get_team_picks(game['away_id'], game['home_id'], venue)
        home_top, home_all = get_team_picks(game['home_id'], game['away_id'], venue)

        all_players.extend(away_all)
        all_players.extend(home_all)

        msg += f"\n{away}:\n"
        for name, percent, emoji in away_top:
            msg += f"{emoji} {name} ({percent}%)\n"

        msg += f"\n{home}:\n"
        for name, percent, emoji in home_top:
            msg += f"{emoji} {name} ({percent}%)\n"

        msg += "\n-------------------------\n\n"

    all_players = sorted(all_players, key=lambda x: x[1], reverse=True)

    msg += "🔥 **TOP 5 LOCKS** 🔥\n"
    for p in all_players[:5]:
        msg += f"{p[2]} {p[0]} ({p[1]}%)\n"

    msg += "\n🔥 = Favorite | 💪 = Strong | 👀 = Value | 🎯 = Longshot\n"

    return msg

def send_to_discord(message):
    if not webhook:
        print("❌ No webhook found")
        return

    # split message so Discord doesn't reject it
    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]

    for chunk in chunks:
        try:
            response = requests.post(webhook, json={"content": chunk})
            print("Status:", response.status_code)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    msg = build_message()
    print(msg)
    send_to_discord(msg)
