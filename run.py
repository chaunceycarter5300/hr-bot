import os
import requests
import pytz
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
# TEAM FORM
# ==============================

def get_team_form(team_name):

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
                            team.get(
                                'w',
                                0
                            )
                        )

                        losses = int(
                            team.get(
                                'l',
                                0
                            )
                        )

                        pct = (
                            wins / (wins + losses)
                            if wins + losses > 0
                            else 0.5
                        )

                        return pct

    except:

        pass

    return 0.5

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

        return {
            "era": era,
            "whip": whip,
            "k9": k9
        }

    except:

        return {
            "era": 4.00,
            "whip": 1.30,
            "k9": 8.0
        }

# ==============================
# PROJECT RUNS
# ==============================

def project_team_runs(
    offense_form,
    opposing_pitcher
):

    runs = 4.2

    # BAD PITCHER

    if opposing_pitcher['era'] >= 5:

        runs += 1.4

    elif opposing_pitcher['era'] >= 4:

        runs += 0.7

    # GOOD PITCHER

    elif opposing_pitcher['era'] <= 3:

        runs -= 1.0

    # WHIP

    if opposing_pitcher['whip'] >= 1.40:

        runs += 0.8

    elif opposing_pitcher['whip'] <= 1.10:

        runs -= 0.5

    # K9

    if opposing_pitcher['k9'] >= 10:

        runs -= 0.5

    elif opposing_pitcher['k9'] <= 7:

        runs += 0.4

    # TEAM FORM

    if offense_form >= 0.600:

        runs += 0.6

    elif offense_form <= 0.450:

        runs -= 0.5

    return round(runs, 1)

# ==============================
# MLB PICKS
# ==============================

def get_mlb_board():

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
            # TEAM FORM
            # ======================

            home_form = get_team_form(
                home
            )

            away_form = get_team_form(
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

            home_runs = project_team_runs(
                home_form,
                away_pitch
            )

            away_runs = project_team_runs(
                away_form,
                home_pitch
            )

            total_runs = round(
                home_runs + away_runs,
                1
            )

            # ======================
            # MONEYLINE EDGE
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

            confidence = int(
                58 + (edge * 6)
            )

            confidence = max(
                58,
                min(
                    80,
                    confidence
                )
            )

            # ======================
            # TOTAL BET
            # ======================

            if total_runs >= 9.5:

                total_bet = (
                    f"OVER {total_runs}"
                )

            elif total_runs <= 7.5:

                total_bet = (
                    f"UNDER {total_runs}"
                )

            else:

                total_bet = (
                    f"LEAN OVER {total_runs}"
                )

            board.append({

                "matchup":
                f"{away} vs {home}",

                "ml_team":
                ml_team,

                "confidence":
                confidence,

                "home_runs":
                home_runs,

                "away_runs":
                away_runs,

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
        key=lambda x: x['confidence'],
        reverse=True
    )[:7]

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    board = get_mlb_board()

    msg = (
        "🔥 GOD TIER MLB BOARD 🔥\n\n"
    )

    for i, g in enumerate(board):

        medal = "🥇"

        if i == 1:
            medal = "🥈"

        elif i == 2:
            medal = "🥉"

        else:
            medal = "⭐"

        msg += (
            f"{medal} "
            f"{g['matchup']}\n\n"
        )

        # ======================
        # MONEYLINE
        # ======================

        msg += (
            f"⚾ ML: "
            f"{g['ml_team']}\n"
        )

        msg += (
            f"📊 Confidence: "
            f"{g['confidence']}%\n\n"
        )

        # ======================
        # PROJECTED RUNS
        # ======================

        msg += (
            f"🏟️ Projected Score:\n"
        )

        msg += (
            f"Home: {g['home_runs']}\n"
        )

        msg += (
            f"Away: {g['away_runs']}\n"
        )

        msg += (
            f"🔥 Total Runs: "
            f"{g['total_runs']}\n\n"
        )

        # ======================
        # TOTAL BET
        # ======================

        msg += (
            f"🔥 Recommended Total:\n"
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
            "🔥 STARTING MLB BOT"
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
