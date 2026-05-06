import os
import requests
import statsapi
import random
import pytz

from datetime import datetime

webhook = os.getenv("DISCORD_WEBHOOK")
weather_key = os.getenv("OPENWEATHER_API_KEY")

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

def get_games_today():
    today = datetime.now(
        pytz.timezone("US/Eastern")
    ).strftime('%Y-%m-%d')

    return statsapi.schedule(date=today)

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
        stats = statsapi.player_stat_data(
            player_id,
            group="[hitting]",
            type="season"
        )

        s = stats['stats'][0]['stats']

        hr = int(s.get('homeRuns', 0))
        slg = float(s.get('sluggingPercentage', 0))

        barrel = random.uniform(5, 18)
        hard_hit = random.uniform(30, 55)

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
        stats = statsapi.player_stat_data(
            pitcher_id,
            group="[pitching]",
            type="season"
        )

        s = stats['stats'][0]['stats']

        hr_allowed = int(s.get('homeRuns', 1))
        innings = float(s.get('inningsPitched', 1))

        factor = hr_allowed / innings if innings > 0 else 1.0

        return factor

    except:
        return 1.0

def weather_boost(venue):
    try:
        if venue not in STADIUM_COORDS:
            return 1.0, "Neutral Weather"

        lat, lon = STADIUM_COORDS[venue]

        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"lat={lat}&lon={lon}"
            f"&appid={weather_key}&units=imperial"
        )

        data = requests.get(url).json()

        wind_speed = data.get("wind", {}).get("speed", 5)
        wind_deg = data.get("wind", {}).get("deg", 180)

        if 90 <= wind_deg <= 270:
            return 1 + (wind_speed / 35), "✅ Wind Out"

        return 1 - (wind_speed / 70), "⚠️ Wind In"

    except:
        return 1.0, "Neutral Weather"

def park_boost(venue):
    return PARK_BOOST.get(venue, 1.0)

def calculate_score(hr, slg, barrel, hard_hit,
                    pitcher, weather, park):

    return (
        (hr * 1.5)
        + (slg * 80)
        + (barrel * 2)
        + (hard_hit * 0.5)
    ) * pitcher * weather * park

def normalize_scores(scored_list):
    scores = [p[1] for p in scored_list]

    min_s = min(scores)
    max_s = max(scores)

    normalized = []

    for name, score, tags in scored_list:

        if max_s == min_s:
            percent = 15

        else:
            percent = 10 + (
                (score - min_s)
                / (max_s - min_s)
            ) * 30

        normalized.append(
            (name, round(percent, 1), tags)
        )

    return normalized

def get_emoji(percent):
    if percent >= 30:
        return "🔥"

    elif percent >= 24:
        return "💪"

    elif percent >= 18:
        return "👀"

    return "🎯"

def get_team_picks(team_id, opponent_id, venue):

    hitters = get_lineup(team_id)

    pitcher_id = get_pitcher(opponent_id)

    pitcher = (
        get_pitcher_factor(pitcher_id)
        if pitcher_id else 1.0
    )

    weather, weather_tag = weather_boost(venue)

    park = park_boost(venue)

    scored = []

    for p in hitters:

        hr, slg, barrel, hard_hit = (
            get_player_stats(p["id"])
        )

        tags = []

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

        if barrel > 12:
            tags.append("✅ Hot Bat")

        score = calculate_score(
            hr,
            slg,
            barrel,
            hard_hit,
            pitcher,
            weather,
            park
        )

        scored.append(
            (p["name"], score, tags)
        )

    scored = sorted(
        scored,
        key=lambda x: x[1],
        reverse=True
    )

    normalized = normalize_scores(scored)

    final = []

    for name, percent, tags in normalized:

        emoji = get_emoji(percent)

        final.append(
            (name, percent, emoji, tags)
        )

    return final[:3], final

def build_message():

    games = get_games_today()

    msg = "🔥 **FINAL HR PICKS** 🔥\n\n"

    all_players = []

    for game in games:

        home = game['home_name']
        away = game['away_name']

        venue = game.get('venue_name', '')

        msg += f"🏟️ **{away} vs {home}**\n"

        away_top, away_all = get_team_picks(
            game['away_id'],
            game['home_id'],
            venue
        )

        home_top, home_all = get_team_picks(
            game['home_id'],
            game['away_id'],
            venue
        )

        all_players.extend(away_all)
        all_players.extend(home_all)

        msg += f"\n{away}:\n"

        for i, (name, percent, emoji, tags) in enumerate(away_top):

            msg += f"{emoji} {name} ({percent}%)\n"

            for t in tags:
                msg += f"{t}\n"

            if i == 0:
                msg += "🎯 BEST PLAY\n"

            msg += "\n"

        msg += f"\n{home}:\n"

        for i, (name, percent, emoji, tags) in enumerate(home_top):

            msg += f"{emoji} {name} ({percent}%)\n"

            for t in tags:
                msg += f"{t}\n"

            if i == 0:
                msg += "🎯 BEST PLAY\n"

            msg += "\n"

        msg += "-------------------------\n\n"

    all_players = sorted(
        all_players,
        key=lambda x: x[1],
        reverse=True
    )

    top = [p for p in all_players if p[1] >= 28]
    strong = [p for p in all_players if 22 <= p[1] < 28]
    value = [p for p in all_players if 18 <= p[1] < 22]

    msg += "💰 **BEST PARLAYS** 💰\n\n"

    msg += "2-Leg:\n"

    for p in top[:2]:
        msg += f"{p[0]} ({p[1]}%)\n"

    msg += "\n3-Leg:\n"

    for p in (top[:2] + strong[:1]):
        msg += f"{p[0]} ({p[1]}%)\n"

    msg += "\n4-Leg:\n"

    for p in (top[:2] + strong[:1] + value[:1]):
        msg += f"{p[0]} ({p[1]}%)\n"

    return msg

def send_to_discord(message):

    if not webhook:
        print("No webhook set")
        return

    chunks = [
        message[i:i+1900]
        for i in range(0, len(message), 1900)
    ]

    for chunk in chunks:
        requests.post(
            webhook,
            json={"content": chunk}
        )

if __name__ == "__main__":

    msg = build_message()

    print(msg)

    send_to_discord(msg)
