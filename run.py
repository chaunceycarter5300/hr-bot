import os
import requests
import pytz
import statsapi

from datetime import datetime
from nba_api.stats.endpoints import leaguestandings
from nba_api.stats.static import teams
from nhlpy import NHLClient

# ==============================
# ENV
# ==============================

webhook = os.getenv("DISCORD_WEBHOOK")

# ==============================
# NHL CLIENT
# ==============================

nhl_client = NHLClient()

# ==============================
# DISCORD
# ==============================

def send_to_discord(message):

    if not webhook:
        print("❌ NO WEBHOOK")
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
# MLB
# ==============================

def get_mlb_picks():

    today = datetime.now(
        pytz.timezone("US/Eastern")
    ).strftime('%Y-%m-%d')

    games = statsapi.schedule(
        date=today
    )

    picks = []

    for game in games:

        try:

            away = game['away_name']
            home = game['home_name']

            home_score = 50

            # HOME FIELD

            home_score += 5

            # RECORDS

            home_wins = int(
                game.get(
                    'home_win_pct',
                    '.500'
                ).replace('.','')
            )

            away_wins = int(
                game.get(
                    'away_win_pct',
                    '.500'
                ).replace('.','')
            )

            if home_wins > away_wins:
                home_score += 8

            else:
                home_score -= 5

            # LAST 10

            if "W" in game.get(
                'home_streak',
                ''
            ):

                home_score += 5

            # WIN %

            win_prob = min(
                85,
                max(
                    50,
                    home_score
                )
            )

            reason = []

            if home_score >= 60:
                reason.append(
                    "✅ Better Team Form"
                )

            if "W" in game.get(
                'home_streak',
                ''
            ):

                reason.append(
                    "✅ Hot Streak"
                )

            reason.append(
                "✅ Home Field"
            )

            picks.append({
                "league": "MLB",
                "team": home,
                "prob": win_prob,
                "reasons": reason
            })

        except Exception as e:

            print(f"MLB Error: {e}")

    return sorted(
        picks,
        key=lambda x: x['prob'],
        reverse=True
    )[:5]

# ==============================
# NBA
# ==============================

def get_nba_picks():

    picks = []

    try:

        standings = (
            leaguestandings.LeagueStandings()
            .get_data_frames()[0]
        )

        standings = standings.sort_values(
            by="WinPCT",
            ascending=False
        )

        top = standings.head(5)

        for _, row in top.iterrows():

            team = row['TeamName']

            pct = float(
                row['WinPCT']
            )

            prob = int(
                50 + (pct * 35)
            )

            reasons = [
                "✅ Better Record",
                "✅ Strong Team Form"
            ]

            if pct >= 0.700:
                reasons.append(
                    "✅ Elite Team"
                )

            picks.append({
                "league": "NBA",
                "team": team,
                "prob": prob,
                "reasons": reasons
            })

    except Exception as e:

        print(f"NBA Error: {e}")

    return picks[:5]

# ==============================
# NHL
# ==============================

def get_nhl_picks():

    picks = []

    try:

        standings = (
            nhl_client.standings.get_standings()
        )

        teams = standings[
            'standings'
        ]

        for t in teams[:5]:

            team = t['teamName']['default']

            points_pct = float(
                t.get(
                    'pointPctg',
                    0.500
                )
            )

            prob = int(
                50 + (points_pct * 35)
            )

            reasons = [
                "✅ Better Team Form",
                "✅ Better Record"
            ]

            if points_pct >= 0.650:
                reasons.append(
                    "✅ Elite Team"
                )

            picks.append({
                "league": "NHL",
                "team": team,
                "prob": prob,
                "reasons": reasons
            })

    except Exception as e:

        print(f"NHL Error: {e}")

    return picks[:5]

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    msg = "🔥 DAILY MONEYLINE BOARD 🔥\n\n"

    # MLB

    mlb = get_mlb_picks()

    msg += "⚾ MLB PICKS\n\n"

    for i, p in enumerate(mlb):

        medal = "🥇"

        if i == 1:
            medal = "🥈"

        elif i == 2:
            medal = "🥉"

        msg += (
            f"{medal} {p['team']} ML\n"
        )

        msg += (
            f"📊 Win Probability: "
            f"{p['prob']}%\n"
        )

        for r in p['reasons']:
            msg += f"{r}\n"

        msg += "\n---------------------\n\n"

    # NBA

    nba = get_nba_picks()

    msg += "🏀 NBA PICKS\n\n"

    for i, p in enumerate(nba):

        medal = "🥇"

        if i == 1:
            medal = "🥈"

        elif i == 2:
            medal = "🥉"

        msg += (
            f"{medal} {p['team']} ML\n"
        )

        msg += (
            f"📊 Win Probability: "
            f"{p['prob']}%\n"
        )

        for r in p['reasons']:
            msg += f"{r}\n"

        msg += "\n---------------------\n\n"

    # NHL

    nhl = get_nhl_picks()

    msg += "🏒 NHL PICKS\n\n"

    for i, p in enumerate(nhl):

        medal = "🥇"

        if i == 1:
            medal = "🥈"

        elif i == 2:
            medal = "🥉"

        msg += (
            f"{medal} {p['team']} ML\n"
        )

        msg += (
            f"📊 Win Probability: "
            f"{p['prob']}%\n"
        )

        for r in p['reasons']:
            msg += f"{r}\n"

        msg += "\n---------------------\n\n"

    return msg

# ==============================
# START BOT
# ==============================

if __name__ == "__main__":

    try:

        print("🔥 STARTING MONEYLINE BOT")

        message = build_message()

        print(message)

        send_to_discord(message)

        print("✅ SENT TO DISCORD")

    except Exception as e:

        print(
            f"❌ BOT ERROR: {e}"
        )
