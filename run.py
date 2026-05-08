import os
import requests
import pandas as pd
import statsapi
import pytz

from datetime import datetime

# ==============================
# ENV VARIABLES
# ==============================

webhook = os.getenv("DISCORD_WEBHOOK")
weather_key = os.getenv("OPENWEATHER_API_KEY")

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
# CLASSIFY PICKS
# ==============================

def classify_pick(
    slg,
    ops,
    hr,
    iso,
    recent_form,
    recent_hr_form,
    pitcher_factor,
    weather,
    park
):

    if (
        slg >= 0.550
        and ops >= 0.900
        and iso >= 0.220
        and hr >= 10
    ):

        return "🔥 SAFE PLAY"

    if (
        recent_hr_form >= 3
        or pitcher_factor > 0.15
        or weather > 1
        or park > 1.1
    ):

        return "💥 HIGH UPSIDE"

    return "⚠️ LONGSHOT"

# ==============================
# HR MODEL
# ==============================

def get_team_picks(
    team_id,
    opponent_id,
    venue
):

    hitters = get_lineup(team_id)

    pitcher_id = get_pitcher(opponent_id)

    pitcher_factor = (
        get_pitcher_factor(pitcher_id)
        if pitcher_id else 1.0
    )

    weather = weather_boost(venue)
    park = park_boost(venue)

    scored = []

    for p in hitters:

        try:

            stats = statsapi.player_stat_data(
                p['id'],
                group="[hitting]",
                type="season"
            )

            s = stats['stats'][0]['stats']

            hr = int(
                s.get('homeRuns', 0)
            )

            slg = float(
                s.get('slg', 0.400)
            )

            ops = float(
                s.get('ops', 0.700)
            )

            avg = float(
                s.get('avg', 0.250)
            )

            hits = int(
                s.get('hits', 0)
            )

            games = int(
                s.get('gamesPlayed', 1)
            )

            # ==========================
            # RECENT FORM
            # ==========================

            recent_form = (
                hits / games
            ) * 10

            # ==========================
            # RECENT HR FORM
            # ==========================

            recent_hr_form = (
                hr / games
            ) * 20

            # ==========================
            # ISO POWER
            # ==========================

            iso = slg - avg

            # ==========================
            # BATTING ORDER BOOST
            # ==========================

            lineup_boost = 1.0

            if len(scored) < 4:
                lineup_boost = 1.10

            # ==========================
            # HR SCORE
            # ==========================

            score = (
                (hr * 5)
                + (slg * 140)
                + (ops * 100)
                + (iso * 150)
                + (recent_form * 2)
                + (recent_hr_form * 2)
            )

            # ==========================
            # BOOSTS
            # ==========================

            score *= weather
            score *= park
            score *= lineup_boost

            if pitcher_factor > 0.15:
                score *= 1.10
            else:
                score *= 0.92

            # ==========================
            # LABEL
            # ==========================

            label = classify_pick(
                slg,
                ops,
                hr,
                iso,
                recent_form,
                recent_hr_form,
                pitcher_factor,
                weather,
                park
            )

            tags = [
                f"💣 HRs: {hr}",
                f"⚾ SLG: {slg}",
                f"🔥 OPS: {ops}",
                f"🎯 AVG: {avg}",
                f"💥 ISO: {round(iso,3)}",
                f"📈 Form Score: {round(recent_form,1)}",
                f"🔥 HR Form: {round(recent_hr_form,1)}",
                f"🏷️ {label}"
            ]

            if lineup_boost > 1:
                tags.append("✅ Top Lineup Spot")

            if weather > 1:
                tags.append("✅ Wind Out")

            if pitcher_factor > 0.15:
                tags.append("✅ Weak Pitcher")

            if park > 1.1:
                tags.append("✅ Great Park")

            scored.append(
                {
                    "name": p['name'],
                    "score": round(score,1),
                    "tags": tags,
                    "label": label,
                    "team_id": team_id
                }
            )

        except Exception as e:

            print(
                f"Player Error: {e}"
            )

            continue

    scored = sorted(
        scored,
        key=lambda x: x['score'],
        reverse=True
    )

    return scored[:3]

# ==============================
# BUILD PARLAYS
# ==============================

def build_parlays(all_plays):

    safe = [
        p for p in all_plays
        if "SAFE PLAY" in p['label']
    ]

    upside = [
        p for p in all_plays
        if "HIGH UPSIDE" in p['label']
    ]

    longshots = [
        p for p in all_plays
        if "LONGSHOT" in p['label']
    ]

    parlays = []

    # SAFE 2 LEG

    if len(safe) >= 2:

        parlays.append({
            "title": "🔥 SAFE 2-LEG",
            "players": safe[:2]
        })

    # UPSIDE 3 LEG

    combo = []

    combo.extend(safe[:1])
    combo.extend(upside[:2])

    if len(combo) >= 3:

        parlays.append({
            "title": "💥 UPSIDE 3-LEG",
            "players": combo[:3]
        })

    # LONGSHOT

    if len(longshots) >= 2:

        parlays.append({
            "title": "⚠️ LONGSHOT PARLAY",
            "players": longshots[:2]
        })

    return parlays

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    games = get_games_today()

    msg = "🔥 FINAL HR PICKS 🔥\n\n"

    all_plays = []

    for game in games:

        away_team = game['away_name']
        home_team = game['home_name']

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

        msg += (
            f"🏟️ {away_team} vs {home_team}\n\n"
        )

        # AWAY TEAM

        msg += f"🔥 {away_team} TOP 3\n\n"

        for i, p in enumerate(away):

            all_plays.append(p)

            msg += (
                f"{i+1}. 💣 {p['name']}\n"
            )

            for t in p['tags']:
                msg += f"{t}\n"

            msg += "\n"

        # HOME TEAM

        msg += f"🔥 {home_team} TOP 3\n\n"

        for i, p in enumerate(home):

            all_plays.append(p)

            msg += (
                f"{i+1}. 💣 {p['name']}\n"
            )

            for t in p['tags']:
                msg += f"{t}\n"

            msg += "\n"

        msg += (
            "----------------------\n\n"
        )

    # ==========================
    # PARLAYS
    # ==========================

    parlays = build_parlays(all_plays)

    msg += "🔥 BOT PARLAYS 🔥\n\n"

    for parlay in parlays:

        msg += f"{parlay['title']}\n"

        for p in parlay['players']:

            msg += (
                f"💣 {p['name']} "
                f"({p['label']})\n"
            )

        msg += "\n"

    return msg

# ==============================
# DISCORD
# ==============================

def send_to_discord(message):

    if not webhook:
        print("❌ NO WEBHOOK FOUND")
        return

    try:

        # LIMIT MESSAGE SIZE

        if len(message) > 1900:
            message = message[:1900]

        response = requests.post(
            webhook,
            json={"content": message}
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
