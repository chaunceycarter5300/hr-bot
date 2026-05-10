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
# HR MODEL
# ==============================

def calculate_hr_confidence(
    pitcher,
    team_strength
):

    score = 14

    # HR/9

    if pitcher['hr9'] >= 1.5:

        score += 10

    elif pitcher['hr9'] >= 1.2:

        score += 6

    # ERA

    if pitcher['era'] >= 5:

        score += 6

    elif pitcher['era'] >= 4:

        score += 3

    # WHIP

    if pitcher['whip'] >= 1.40:

        score += 5

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
# PROJECT RUNS
# ==============================

def project_runs(
    team_strength,
    opposing_pitcher
):

    runs = 4.3

    if team_strength >= 0.600:

        runs += 1.0

    elif team_strength <= 0.450:

        runs -= 0.8

    if opposing_pitcher['era'] >= 5:

        runs += 1.4

    elif opposing_pitcher['era'] >= 4:

        runs += 0.7

    elif opposing_pitcher['era'] <= 3:

        runs -= 0.8

    return round(runs, 1)

# ==============================
# FAKE PLAYER POOL
# REPLACE WITH REAL PLAYERS LATER
# ==============================

team_hr_players = {

    "New York Yankees":
    ["Aaron Judge"],

    "Los Angeles Dodgers":
    ["Shohei Ohtani"],

    "Philadelphia Phillies":
    ["Kyle Schwarber"],

    "Atlanta Braves":
    ["Matt Olson"],

    "New York Mets":
    ["Pete Alonso"]

}

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
            # PROJECTED RUNS
            # ======================

            home_runs = project_runs(
                home_strength,
                away_pitch
            )

            away_runs = project_runs(
                away_strength,
                home_pitch
            )

            # ======================
            # WINNER
            # ======================

            if home_runs > away_runs:

                ml_team = home
                edge = (
                    home_runs - away_runs
                )

            else:

                ml_team = away
                edge = (
                    away_runs - home_runs
                )

            ml_confidence = int(
                54 + (edge * 4)
            )

            ml_confidence = max(
                54,
                min(
                    74,
                    ml_confidence
                )
            )

            # ======================
            # HR PLAYER
            # ======================

            hr_team = ml_team

            if hr_team in team_hr_players:

                hr_player = random.choice(
                    team_hr_players[hr_team]
                )

            else:

                continue

            # ======================
            # HR CONFIDENCE
            # ======================

            if hr_team == home:

                hr_confidence = (
                    calculate_hr_confidence(
                        away_pitch,
                        home_strength
                    )
                )

            else:

                hr_confidence = (
                    calculate_hr_confidence(
                        home_pitch,
                        away_strength
                    )
                )

            # ======================
            # TOTALS
            # ======================

            total_runs = round(
                home_runs + away_runs,
                1
            )

            total_runs = max(
                6.5,
                min(
                    14.5,
                    total_runs
                )
            )

            projected_total = round(
                total_runs * 2
            ) / 2

            if projected_total >= 10:

                total_bet = (
                    f"OVER {projected_total - 0.5}"
                )

            elif projected_total <= 7:

                total_bet = (
                    f"UNDER {projected_total + 0.5}"
                )

            else:

                total_bet = (
                    f"OVER {projected_total - 0.5}"
                )

            board.append({

                "matchup":
                f"{away} vs {home}",

                "ml_team":
                ml_team,

                "ml_confidence":
                ml_confidence,

                "hr_player":
                hr_player,

                "hr_confidence":
                hr_confidence,

                "total_runs":
                total_runs,

                "total_bet":
                total_bet

            })

        except Exception as e:

            print(
                f"Game Error: {e}"
            )

    return sorted(
        board,
        key=lambda x: x['hr_confidence'],
        reverse=True
    )[:5]

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    board = get_board()

    msg = (
        "🔥 ELITE HR + ML BOARD 🔥\n\n"
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
            f"{g['matchup']}\n\n"
        )

        msg += (
            f"💣 HR PROP:\n"
        )

        msg += (
            f"{g['hr_player']} HR\n"
        )

        msg += (
            f"📊 HR Confidence: "
            f"{g['hr_confidence']}%\n\n"
        )

        msg += (
            f"⚾ MONEYLINE:\n"
        )

        msg += (
            f"{g['ml_team']} ML\n"
        )

        msg += (
            f"📊 ML Confidence: "
            f"{g['ml_confidence']}%\n\n"
        )

        msg += (
            f"🔥 Total Bet:\n"
        )

        msg += (
            f"{g['total_bet']}\n"
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
            "🔥 STARTING HR + ML MODEL"
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
