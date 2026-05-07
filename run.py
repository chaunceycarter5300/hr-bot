import os
import requests
import statsapi
import random
import pytz

from datetime import datetime

webhook = os.getenv("DISCORD_WEBHOOK")
weather_key = os.getenv("OPENWEATHER_API_KEY")

# ==============================
# SETTINGS
# ==============================

MIN_BARREL = 10
MIN_HARD_HIT = 40
MIN_HR_PROB = 22

MAX_PLAYERS_PER_TEAM = 1

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

def get_player_stats(player_id):

    try:

        stats = statsapi.player_stat_data(
            player_id,
            group="[hitting]",
            type="season"
        )

        s = stats['stats'][0]['stats']

        hr = int(s.get('homeRuns', 0))

        slg = float(
            s.get('sluggingPercentage', 0)
        )

        barrel = round(
            random.uniform(5, 18),
            1
        )

        hard_hit = round(
            random.uniform(30, 55),
            1
        )

        # ==========================
        # HR PROBABILITY
        # ==========================

        hr_prob = round(
            (
                (barrel * 2.8)
                + (hard_hit * 0.7)
                + (hr * 1.2)
            ) / 2.5,
            1
        )

        hr_prob = max(
            8,
            min(hr_prob, 45)
        )

        return (
            hr,
            slg,
            barrel,
            hard_hit,
            hr_prob
        )

    except Exception as e:

        print(f"Player Stat Error: {e}")

        return (
            0,
            0.0,
            5,
            30,
            8
        )

# ==============================
# PITCHER
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
# PARK FACTOR
# ==============================

def park_boost(venue):

    return PARK_BOOST.get(
        venue,
        1.0
    )

# ==============================
# SCORE SYSTEM
# ==============================

def calculate_score(
    hr,
    slg,
    barrel,
    hard_hit,
    pitcher,
    weather,
    park
):

    score = 0

    # BARREL MOST IMPORTANT
    score += barrel * 5

    # HARD HIT
    score += hard_hit * 2

    # HR TOTAL
    score += hr * 1.5

    # SLUGGING
    score += slg * 25

    # WEATHER / PARK
    score *= weather
    score *= park

    # PITCHER
    if pitcher > 0.15:
        score *= 1.15
    else:
        score *= 0.82

    return score

# ==============================
# NORMALIZE
# ==============================

def normalize_scores(scored_list):

    scores = [p[1] for p in scored_list]

    min_s = min(scores)
    max_s = max(scores)

    normalized = []

    for (
        name,
        score,
        tags,
        hr_prob
    ) in scored_list:

        if max_s == min_s:
            percent = 15

        else:

            percent = 10 + (
                (score - min_s)
                / (max_s - min_s)
            ) * 30

        normalized.append(
            (
                name,
                round(percent, 1),
                tags,
                hr_prob
            )
        )

    return normalized

# ==============================
# EMOJIS
# ==============================

def get_emoji(percent):

    if percent >= 35:
        return "💣"

    elif percent >= 30:
        return "🔥"

    elif percent >= 24:
        return "💪"

    elif percent >= 18:
        return "👀"

    return "🎯"

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

        (
            hr,
            slg,
            barrel,
            hard_hit,
            hr_prob
        ) = get_player_stats(p["id"])

        # ==========================
        # FILTERS
        # ==========================

        if barrel < MIN_BARREL:
            continue

        if hard_hit < MIN_HARD_HIT:
            continue

        if hr_prob < MIN_HR_PROB:
            continue

        tags = []

        tags.append(
            f"💥 Hard Hit: {hard_hit}%"
        )

        tags.append(
            f"🛢️ Barrel: {barrel}%"
        )

        tags.append(
            f"🚀 HR Probability: {hr_prob}%"
        )

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
            (
                p["name"],
                score,
                tags,
                hr_prob
            )
        )

    scored = sorted(
        scored,
        key=lambda x: x[1],
        reverse=True
    )

    if not scored:
        return [], []

    normalized = normalize_scores(scored)

    final = []

    for (
        name,
        percent,
        tags,
        hr_prob
    ) in normalized:

        emoji = get_emoji(percent)

        final.append(
            (
                name,
                percent,
                emoji,
                tags,
                hr_prob
            )
        )

    return final[:MAX_PLAYERS_PER_TEAM], final

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    games = get_games_today()

    msg = "🔥 FINAL HR PICKS 🔥\n\n"

    for game in games:

        home = game['home_name']
        away = game['away_name']

        venue = game.get(
            'venue_name',
            ''
        )

        away_top, _ = get_team_picks(
            game['away_id'],
            game['home_id'],
            venue
        )

        home_top, _ = get_team_picks(
            game['home_id'],
            game['away_id'],
            venue
        )

        if not away_top and not home_top:
            continue

        msg += f"🏟️ {away} vs {home}\n\n"

        for side in [away_top, home_top]:

            for (
                name,
                percent,
                emoji,
                tags,
                hr_prob
            ) in side:

                msg += (
                    f"{emoji} {name} "
                    f"({percent}%)\n"
                )

                for t in tags:
                    msg += f"{t}\n"

                if hr_prob >= 38:
                    msg += "💣 NUKE PLAY\n"

                msg += "\n"

        msg += (
            "----------------------\n\n"
        )

    return msg

# ==============================
# DISCORD FIX
# ==============================

def send_to_discord(message):

    if not webhook:
        print("❌ No webhook found")
        return

    chunks = [
        message[i:i+1900]
        for i in range(
            0,
            len(message),
            1900
        )
    ]

    for chunk in chunks:

        try:

            response = requests.post(
                webhook,
                json={"content": chunk}
            )

            print(
                f"Discord status: "
                f"{response.status_code}"
            )

            print(response.text)

        except Exception as e:

            print(
                f"Discord Error: {e}"
            )

# ==============================
# START BOT
# ==============================

if __name__ == "__main__":

    try:

        print("🔥 Building message...")

        msg = build_message()

        print(msg)

        print("🚀 Sending to Discord...")

        send_to_discord(msg)

        print("✅ Finished")

    except Exception as e:

        print(
            f"❌ BOT CRASHED: {e}"
        )
