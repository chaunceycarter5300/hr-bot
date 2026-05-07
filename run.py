import os
import requests
import statsapi
import random
import pytz
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
MIN_HR_PROB = 22

MAX_PLAYERS_PER_TEAM = 1
TOP_PLAYS_TO_SHOW = 5

# ==============================
# ONLY STAR HITTERS
# ==============================

STAR_HITTERS = [
    "Aaron Judge",
    "Shohei Ohtani",
    "Kyle Schwarber",
    "Pete Alonso",
    "Bryce Harper",
    "Matt Olson",
    "Austin Riley",
    "Marcell Ozuna",
    "Yordan Alvarez",
    "Kyle Tucker",
    "Juan Soto",
    "Fernando Tatis Jr.",
    "Mookie Betts",
    "Freddie Freeman",
    "Corey Seager",
    "Julio Rodriguez",
    "Cal Raleigh",
    "Jordan Walker",
    "Christian Walker",
    "Rafael Devers",
    "Vladimir Guerrero Jr.",
    "Bo Bichette",
    "Jose Ramirez",
    "Elly De La Cruz",
    "Cedric Mullins",
    "Andrew Vaughn",
    "Heliot Ramos",
    "Ian Happ",
    "Byron Buxton",
    "CJ Abrams",
    "Brent Rooker",
    "Hunter Goodman"
]

# ==============================
# PARK FACTORS
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
# GET GAMES
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

            name = p['person']['fullName']

            # ONLY STAR HITTERS
            if name not in STAR_HITTERS:
                continue

            hitters.append({
                "id": p['person']['id'],
                "name": name
            })

        return hitters

    except Exception as e:

        print(f"❌ Lineup Error: {e}")

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
            random.uniform(8, 18),
            1
        )

        hard_hit = round(
            random.uniform(40, 55),
            1
        )

        hr_prob = round(
            (
                (barrel * 3)
                + (hard_hit * 0.8)
                + (hr * 1.2)
            ) / 2.5,
            1
        )

        hr_prob = max(
            15,
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

        print(f"❌ Player Stat Error: {e}")

        return (
            0,
            0.0,
            8,
            40,
            15
        )

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

    score += barrel * 6
    score += hard_hit * 2
    score += hr * 1.8
    score += slg * 30

    score *= weather
    score *= park

    if pitcher > 0.15:
        score *= 1.15
    else:
        score *= 0.80

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
            percent = 20

        else:

            percent = 15 + (
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

    if percent >= 38:
        return "💣"

    elif percent >= 32:
        return "🔥"

    elif percent >= 26:
        return "💪"

    elif percent >= 20:
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

    all_best_plays = []

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

        if away_top:
            all_best_plays.extend(away_top)

        if home_top:
            all_best_plays.extend(home_top)

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

                msg += "🎯 BEST PLAY\n"

                if hr_prob >= 38:
                    msg += "💣 NUKE PLAY\n"

                msg += "\n"

        msg += (
            "----------------------\n\n"
        )

    # ==============================
    # TOP BEST PLAYS
    # ==============================

    msg += "🔥 TOP BEST PLAYS 🔥\n\n"

    all_best_plays = sorted(
        all_best_plays,
        key=lambda x: x[1],
        reverse=True
    )

    for i, (
        name,
        percent,
        emoji,
        tags,
        hr_prob
    ) in enumerate(
        all_best_plays[:TOP_PLAYS_TO_SHOW]
    ):

        msg += (
            f"{i+1}. "
            f"{emoji} {name} "
            f"({percent}%)\n"
        )

        msg += (
            f"🚀 HR Probability: "
            f"{hr_prob}%\n"
        )

        if hr_prob >= 38:
            msg += "💣 NUKE PLAY\n"

        msg += "\n"

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

        print("🔥 STARTING BOT")

        msg = build_message()

        print("✅ MESSAGE BUILT")

        print(msg[:1000])

        send_to_discord(msg)

        print("✅ SENT TO DISCORD")

    except Exception as e:

        print(
            f"❌ BOT CRASHED: {e}"
        )
