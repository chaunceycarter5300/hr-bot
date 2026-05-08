import os
import requests
import statsapi
import pytz

from datetime import datetime
from pybaseball import statcast_batter_exitvelo_barrels

# ==============================
# CACHE
# ==============================

STATCAST_DATA = None

# ==============================
# ENV VARIABLES
# ==============================

webhook = os.getenv("DISCORD_WEBHOOK")
weather_key = os.getenv("OPENWEATHER_API_KEY")

# ==============================
# WEATHER / PARK BOOSTS
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
# REAL STATCAST DATA
# ==============================

def get_statcast_data(player_id):

    global STATCAST_DATA

    try:

        if STATCAST_DATA is None:

            print("Loading Statcast Data...")

            STATCAST_DATA = (
                statcast_batter_exitvelo_barrels(
                    2025
                )
            )

        data = STATCAST_DATA.copy()

        data['player_id'] = data[
            'player_id'
        ].astype(str)

        player = data[
            data['player_id']
            == str(player_id)
        ]

        if player.empty:

            return {
                "barrel_pct": 6.0,
                "avg_ev": 88.0
            }

        row = player.iloc[0]

        barrel_pct = float(
            row.get(
                'brl_percent',
                6
            )
        )

        avg_ev = float(
            row.get(
                'avg_hit_speed',
                88
            )
        )

        if barrel_pct == 0:
            barrel_pct = 6.0

        if avg_ev == 0:
            avg_ev = 88.0

        return {
            "barrel_pct": barrel_pct,
            "avg_ev": avg_ev
        }

    except Exception as e:

        print(
            f"Statcast Error: {e}"
        )

        return {
            "barrel_pct": 6.0,
            "avg_ev": 88.0
        }

# ==============================
# CLASSIFY PICKS
# ==============================

def classify_pick(
    slg,
    ops,
    hr,
    iso,
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
# TEAM PICKS
# ==============================

def get_team_picks(
    team_id,
    opponent_id,
    venue,
    team_name
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

            hr = int(s.get('homeRuns', 0))
            slg = float(s.get('slg', 0.400))
            ops = float(s.get('ops', 0.700))
            avg = float(s.get('avg', 0.250))

            iso = slg - avg

            statcast = get_statcast_data(
                p['id']
            )

            barrel_pct = statcast[
                'barrel_pct'
            ]

            avg_ev = statcast[
                'avg_ev'
            ]

            recent_hr_form = (
                hr / max(
                    int(s.get('gamesPlayed', 1)),
                    1
                )
            ) * 20

            score = (
                (hr * 5)
                + (slg * 160)
                + (ops * 120)
                + (iso * 200)
                + (recent_hr_form * 2)
                + (barrel_pct * 6)
                + avg_ev
            )

            score *= weather
            score *= park

            if pitcher_factor > 0.15:
                score *= 1.10

            label = classify_pick(
                slg,
                ops,
                hr,
                iso,
                recent_hr_form,
                pitcher_factor,
                weather,
                park
            )

            tags = [
                f"💣 HRs: {hr}",
                f"💥 ISO: {round(iso,3)}",
                f"⚾ SLG: {slg}",
                f"🔥 OPS: {ops}",
                f"🪵 Barrel%: {round(barrel_pct,1)}%",
                f"🚀 ExitVelo: {round(avg_ev,1)}",
                f"🏷️ {label}"
            ]

            if barrel_pct >= 12:
                tags.append("✅ Elite Barrel")

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
                    "team": team_name
                }
            )

        except Exception as e:

            print(f"Player Error: {e}")

            continue

    scored = sorted(
        scored,
        key=lambda x: x['score'],
        reverse=True
    )

    return scored[:3]

# ==============================
# SMART PARLAYS
# ==============================

def build_parlays(all_plays):

    elite = []
    upside = []

    for p in all_plays:

        barrel = 0
        ev = 0
        iso = 0
        slg = 0
        ops = 0

        for t in p['tags']:

            if "Barrel%" in t:
                barrel = float(
                    t.split(": ")[1]
                    .replace("%","")
                )

            if "ExitVelo" in t:
                ev = float(
                    t.split(": ")[1]
                )

            if "ISO" in t:
                iso = float(
                    t.split(": ")[1]
                )

            if "SLG" in t:
                slg = float(
                    t.split(": ")[1]
                )

            if "OPS" in t:
                ops = float(
                    t.split(": ")[1]
                )

        # STRICT FILTERS

        if barrel < 8:
            continue

        if iso < 0.180:
            continue

        if slg < 0.450:
            continue

        if ops < 0.760:
            continue

        if ev < 89:
            continue

        # ELITE

        if (
            barrel >= 12
            and iso >= 0.220
            and slg >= 0.550
            and ops >= 0.850
            and ev >= 91
        ):

            elite.append(p)

        else:

            upside.append(p)

    elite = sorted(
        elite,
        key=lambda x: x['score'],
        reverse=True
    )

    upside = sorted(
        upside,
        key=lambda x: x['score'],
        reverse=True
    )

    parlays = []

    # SAFEST 2 LEG

    if len(elite) >= 2:

        first = elite[0]

        second = None

        for p in elite[1:]:

            if (
                p['team']
                != first['team']
            ):

                second = p
                break

        if second:

            parlays.append({
                "title": "🔥 SAFEST HR 2-LEG",
                "players": [
                    first,
                    second
                ]
            })

    # BEST 3 LEG

    combo = []

    if len(elite) >= 1:
        combo.append(elite[0])

    for p in upside:

        same_team = False

        for c in combo:

            if (
                c['team']
                == p['team']
            ):

                same_team = True

        if not same_team:

            combo.append(p)

        if len(combo) == 3:
            break

    if len(combo) == 3:

        parlays.append({
            "title": "💥 BEST UPSIDE 3-LEG",
            "players": combo
        })

    return parlays

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    games = get_games_today()

    msg = "🔥 HR TARGET BOARD 🔥\n\n"

    all_plays = []

    for game in games:

        venue = game.get(
            'venue_name',
            ''
        )

        away_team = game.get(
            'away_name',
            'Away Team'
        )

        home_team = game.get(
            'home_name',
            'Home Team'
        )

        away = get_team_picks(
            game['away_id'],
            game['home_id'],
            venue,
            away_team
        )

        home = get_team_picks(
            game['home_id'],
            game['away_id'],
            venue,
            home_team
        )

        all_plays.extend(away)
        all_plays.extend(home)

        # AWAY TEAM

        msg += f"🔥 {away_team} 🔥\n\n"

        for i, p in enumerate(away):

            medal = "🥇"

            if i == 1:
                medal = "🥈"

            elif i == 2:
                medal = "🥉"

            msg += f"{medal} {p['name']}\n"

            for t in p['tags']:
                msg += f"{t}\n"

            msg += "\n---------------------\n\n"

        # HOME TEAM

        msg += f"🔥 {home_team} 🔥\n\n"

        for i, p in enumerate(home):

            medal = "🥇"

            if i == 1:
                medal = "🥈"

            elif i == 2:
                medal = "🥉"

            msg += f"{medal} {p['name']}\n"

            for t in p['tags']:
                msg += f"{t}\n"

            msg += "\n---------------------\n\n"

    # PARLAYS

    parlays = build_parlays(
        all_plays
    )

    msg += "🔥 BEST HR PARLAYS 🔥\n\n"

    for parlay in parlays:

        msg += f"{parlay['title']}\n\n"

        for p in parlay['players']:

            msg += f"💣 {p['name']}\n"

        msg += "\n---------------------\n\n"

    return msg

# ==============================
# DISCORD
# ==============================

def send_to_discord(message):

    if not webhook:
        print("❌ NO WEBHOOK FOUND")
        return

    try:

        chunks = []

        while len(message) > 1900:

            split_at = message.rfind(
                "\n",
                0,
                1900
            )

            if split_at == -1:
                split_at = 1900

            chunks.append(
                message[:split_at]
            )

            message = message[split_at:]

        chunks.append(message)

        for chunk in chunks:

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
