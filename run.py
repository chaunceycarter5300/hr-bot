import os
import requests
import pytz
import random
import statsapi

from datetime import datetime

# ==============================
# ENV
# ==============================

webhook = os.getenv("DISCORD_WEBHOOK")

# ==============================
# DISCORD
# ==============================

def send_to_discord(message):

    if not webhook:
        print("❌ NO WEBHOOK")
        return

    try:

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

        era = float(
            s.get('era', 4.00)
        )

        whip = float(
            s.get('whip', 1.30)
        )

        k9 = float(
            s.get(
                'strikeoutsPer9Inn',
                8.0
            )
        )

        hr9 = float(
            s.get(
                'homeRunsPer9',
                1.1
            )
        )

        return {
            "era": era,
            "whip": whip,
            "k9": k9,
            "hr9": hr9
        }

    except:

        return {
            "era": 4.00,
            "whip": 1.30,
            "k9": 8.0,
            "hr9": 1.1
        }

# ==============================
# DYNAMIC LINEUPS
# ==============================

team_hitters = {

    "Arizona Diamondbacks":
    ["Ketel Marte", "Christian Walker"],

    "Atlanta Braves":
    ["Matt Olson", "Austin Riley"],

    "Baltimore Orioles":
    ["Gunnar Henderson", "Adley Rutschman"],

    "Boston Red Sox":
    ["Rafael Devers", "Triston Casas"],

    "Chicago Cubs":
    ["Seiya Suzuki", "Ian Happ"],

    "Chicago White Sox":
    ["Luis Robert Jr", "Andrew Vaughn"],

    "Cincinnati Reds":
    ["Elly De La Cruz", "Spencer Steer"],

    "Cleveland Guardians":
    ["Jose Ramirez", "Josh Naylor"],

    "Colorado Rockies":
    ["Ryan McMahon", "Ezequiel Tovar"],

    "Detroit Tigers":
    ["Riley Greene", "Spencer Torkelson"],

    "Houston Astros":
    ["Yordan Alvarez", "Jose Altuve"],

    "Kansas City Royals":
    ["Bobby Witt Jr", "Salvador Perez"],

    "Los Angeles Angels":
    ["Mike Trout", "Taylor Ward"],

    "Los Angeles Dodgers":
    ["Shohei Ohtani", "Mookie Betts"],

    "Miami Marlins":
    ["Jake Burger", "Josh Bell"],

    "Milwaukee Brewers":
    ["Christian Yelich", "Rhys Hoskins"],

    "Minnesota Twins":
    ["Byron Buxton", "Carlos Correa"],

    "New York Mets":
    ["Pete Alonso", "Juan Soto"],

    "New York Yankees":
    ["Aaron Judge", "Giancarlo Stanton"],

    "Oakland Athletics":
    ["Brent Rooker", "Shea Langeliers"],

    "Philadelphia Phillies":
    ["Kyle Schwarber", "Bryce Harper"],

    "Pittsburgh Pirates":
    ["Oneil Cruz", "Bryan Reynolds"],

    "San Diego Padres":
    ["Fernando Tatis Jr", "Manny Machado"],

    "San Francisco Giants":
    ["Matt Chapman", "Jung Hoo Lee"],

    "Seattle Mariners":
    ["Julio Rodriguez", "Cal Raleigh"],

    "St. Louis Cardinals":
    ["Nolan Arenado", "Paul Goldschmidt"],

    "Tampa Bay Rays":
    ["Yandy Diaz", "Isaac Paredes"],

    "Texas Rangers":
    ["Corey Seager", "Adolis Garcia"],

    "Toronto Blue Jays":
    ["Vladimir Guerrero Jr", "Bo Bichette"],

    "Washington Nationals":
    ["James Wood", "CJ Abrams"]

}

# ==============================
# HR CONFIDENCE
# ==============================

def calculate_hr_probability(
    pitcher,
    team_strength
):

    score = 16

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

    return max(
        12,
        min(
            40,
            score
        )
    )

# ==============================
# BUILD BOARD
# ==============================

def get_board():

    today = datetime.now(
        pytz.timezone("US/Eastern")
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

            # ======================
            # TEAM STRENGTH
            # ======================

            home_strength = get_team_strength(
                home
            )

            away_strength = get_team_strength(
                away
            )

            # ======================
            # PITCHERS
            # ======================

            home_pitch = get_pitcher_stats(
                home_id
            )

            away_pitch = get_pitcher_stats(
                away_id
            )

            # ======================
            # HOME HR PLAYER
            # ======================

            if home in team_hitters:

                home_hr = random.choice(
                    team_hitters[home]
                )

                home_hr_conf = (
                    calculate_hr_probability(
                        away_pitch,
                        home_strength
                    )
                )

                board.append({

                    "player":
                    home_hr,

                    "team":
                    home,

                    "matchup":
                    f"{away} vs {home}",

                    "prob":
                    home_hr_conf

                })

            # ======================
            # AWAY HR PLAYER
            # ======================

            if away in team_hitters:

                away_hr = random.choice(
                    team_hitters[away]
                )

                away_hr_conf = (
                    calculate_hr_probability(
                        home_pitch,
                        away_strength
                    )
                )

                board.append({

                    "player":
                    away_hr,

                    "team":
                    away,

                    "matchup":
                    f"{away} vs {home}",

                    "prob":
                    away_hr_conf

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
            f"{g['player']} HR\n\n"
        )

        msg += (
            f"⚾ Team: "
            f"{g['team']}\n"
        )

        msg += (
            f"⚾ Matchup: "
            f"{g['matchup']}\n"
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
            "🔥 STARTING DYNAMIC HR MODEL"
        )

        msg = build_message()

        print(msg)

        send_to_discord(msg)

        print(
            "✅ SENT TO DISCORD"
        )

    except Exception as e:

        print(
            f"❌ BOT ERROR: {e}"
        )
