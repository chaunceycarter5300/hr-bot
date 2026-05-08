import os
import requests
import statsapi
import pytz

from datetime import datetime
from pybaseball import statcast_batter_exitvelo_barrels

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

    try:

        data = statcast_batter_exitvelo_barrels(
            2025
        )

        # FIX PLAYER ID TYPES

        data['player_id'] = data[
            'player_id'
        ].astype(str)

        player = data[
            data['player_id']
            == str(player_id)
        ]

        if player.empty:

            return {
                "barrel_pct": 0,
                "hard_hit_pct": 0,
                "avg_ev": 0
            }

        row = player.iloc[0]

        barrel_pct = float(
            row.get(
                'brl_percent',
                0
            )
        )

        hard_hit_pct = float(
            row.get(
                'hard_hit_percent',
                0
            )
        )

        avg_ev = float(
            row.get(
                'avg_hit_speed',
                0
            )
        )

        return {
            "barrel_pct": barrel_pct,
            "hard_hit_pct": hard_hit_pct,
            "avg_ev": avg_ev
        }

    except Exception as e:

        print(
            f"Statcast Error: {e}"
        )

        return {
            "barrel_pct": 0,
            "hard_hit_pct": 0,
            "avg_ev": 0
        }

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
# GREEN FLAGS
# ==============================

def get_green_flags(tags):

    green_flags = 0

    for t in tags:

        if (
            "SAFE PLAY" in t
            or "Wind Out" in t
            or "Weak Pitcher" in t
            or "Great Park" in t
            or "Top Lineup Spot" in t
            or "Strong Power Split" in t
            or "Elite Barrel" in t
            or "Elite Hard Hit" in t
        ):

            green_flags += 1

    return green_flags

# ==============================
# ADVANCED HR MODEL
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

            hr = int(s.get('homeRuns', 0))
            slg = float(s.get('slg', 0.400))
            ops = float(s.get('ops', 0.700))
            avg = float(s.get('avg', 0.250))
            hits = int(s.get('hits', 0))
            games = int(s.get('gamesPlayed', 1))

            iso = slg - avg

            # REAL STATCAST

            statcast = get_statcast_data(
                p['id']
            )

            barrel_pct = statcast[
                'barrel_pct'
            ]

            hard_hit_pct = statcast[
                'hard_hit_pct'
            ]

            avg_ev = statcast[
                'avg_ev'
            ]

            # FORM

            recent_form = (
                hits / games
            ) * 10

            recent_hr_form = (
                hr / games
            ) * 20

            # SPLIT BOOST

            split_boost = 1.0

            if iso >= 0.250:
                split_boost = 1.12

            elif iso >= 0.200:
                split_boost = 1.06

            # LINEUP BOOST

            lineup_boost = 1.0

            if len(scored) < 4:
                lineup_boost = 1.10

            # ADVANCED SCORE

            score = (
                (hr * 5)
                + (slg * 160)
                + (ops * 120)
                + (iso * 200)
                + (recent_form * 2)
                + (recent_hr_form * 2)
                + (barrel_pct * 6)
                + (hard_hit_pct * 3)
                + avg_ev
            )

            # PENALTIES

            if ops < 0.720:
                score *= 0.72

            if slg < 0.430:
                score *= 0.78

            if iso < 0.170:
                score *= 0.82

            # BOOSTS

            score *= weather
            score *= park
            score *= lineup_boost
            score *= split_boost

            if pitcher_factor > 0.15:
                score *= 1.10
            else:
                score *= 0.90

            # LABEL

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

            # TAGS

            tags = [
                f"💣 HRs: {hr}",
                f"⚾ SLG: {slg}",
                f"🔥 OPS: {ops}",
                f"🎯 AVG: {avg}",
                f"💥 ISO: {round(iso,3)}",
                f"🪵 Barrel%: {round(barrel_pct,1)}%",
                f"💪 HardHit%: {round(hard_hit_pct,1)}%",
                f"🚀 ExitVelo: {round(avg_ev,1)}",
                f"📈 Form Score: {round(recent_form,1)}",
                f"🔥 HR Form: {round(recent_hr_form,1)}",
                f"🏷️ {label}"
            ]

            if barrel_pct >= 12:
                tags.append("✅ Elite Barrel")

            if hard_hit_pct >= 45:
                tags.append("✅ Elite Hard Hit")

            if split_boost > 1:
                tags.append("✅ Strong Power Split")

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

            print(f"Player Error: {e}")

            continue

    scored = sorted(
        scored,
        key=lambda x: x['score'],
        reverse=True
    )

    return scored[:3]

# ==============================
# ULTRA SELECTIVE PARLAYS
# ==============================

def build_parlays(all_plays):

    filtered = []

    for p in all_plays:

        flags = get_green_flags(
            p['tags']
        )

        if (
            p['score'] >= 260
            and flags >= 3
            and "LONGSHOT" not in p['label']
        ):

            p['flags'] = flags
            filtered.append(p)

    filtered = sorted(
        filtered,
        key=lambda x: (
            x['flags'],
            x['score']
        ),
        reverse=True
    )

    safe = [
        p for p in filtered
        if "SAFE PLAY" in p['label']
    ]

    upside = [
        p for p in filtered
        if "HIGH UPSIDE" in p['label']
    ]

    parlays = []

    if len(safe) >= 2:

        parlays.append({
            "title": "🔥 ELITE HR 2-LEG",
            "players": [
                safe[0],
                safe[1]
            ]
        })

    combo = []

    if len(safe) >= 1:
        combo.append(safe[0])

    for p in upside:

        if all(
            p['team_id'] != x['team_id']
            for x in combo
        ):

            combo.append(p)

        if len(combo) == 3:
            break

    if len(combo) == 3:

        parlays.append({
            "title": "💥 ULTRA UPSIDE 3-LEG",
            "players": combo
        })

    return parlays

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    games = get_games_today()

    msg = "🔥 HR TARGET BOARD 🔥\n\n"

    elite_plays = []
    upside_plays = []
    risky_plays = []

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

    for p in all_plays:

        if (
            "SAFE PLAY" in p['label']
            and p['score'] >= 220
        ):

            elite_plays.append(p)

        elif (
            "HIGH UPSIDE" in p['label']
            and p['score'] >= 180
        ):

            upside_plays.append(p)

        else:

            risky_plays.append(p)

    elite_plays = sorted(
        elite_plays,
        key=lambda x: x['score'],
        reverse=True
    )

    upside_plays = sorted(
        upside_plays,
        key=lambda x: x['score'],
        reverse=True
    )

    risky_plays = sorted(
        risky_plays,
        key=lambda x: x['score'],
        reverse=True
    )

    # ELITE

    msg += "🔥 ELITE HR TARGETS 🔥\n\n"

    for p in elite_plays[:10]:

        msg += f"💣 {p['name']}\n"

        for t in p['tags']:
            msg += f"{t}\n"

        msg += "\n--------------------------------\n\n"

    # UPSIDE

    msg += "💥 UPSIDE HR TARGETS 💥\n\n"

    for p in upside_plays[:10]:

        msg += f"💣 {p['name']}\n"

        for t in p['tags']:
            msg += f"{t}\n"

        msg += "\n--------------------------------\n\n"

    # RISKY

    msg += "⚠️ RISKY HR TARGETS ⚠️\n\n"

    for p in risky_plays[:6]:

        msg += f"💣 {p['name']}\n"

        for t in p['tags']:
            msg += f"{t}\n"

        msg += "\n--------------------------------\n\n"

    # PARLAYS

    parlays = build_parlays(all_plays)

    msg += "🔥 BEST HR PARLAYS 🔥\n\n"

    for parlay in parlays:

        msg += f"{parlay['title']}\n"

        for p in parlay['players']:

            msg += (
                f"💣 {p['name']} "
                f"({p['label']})\n"
            )

        msg += "\n--------------------------------\n\n"

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
