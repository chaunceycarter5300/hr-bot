import os
import requests
import pytz
import statsapi
import pandas as pd

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
# PITCHER EDGE
# ==============================

def get_pitcher_edge(team_id):

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

        score = 0

        reasons = []

        # ERA

        if era <= 3.00:

            score += 15
            reasons.append(
                f"🔥 Elite ERA ({era})"
            )

        elif era <= 4.00:

            score += 8
            reasons.append(
                f"✅ Solid ERA ({era})"
            )

        else:

            score -= 6

        # WHIP

        if whip <= 1.10:

            score += 10
            reasons.append(
                f"🔥 Elite WHIP ({whip})"
            )

        elif whip <= 1.25:

            score += 5

        else:

            score -= 5

        # K9

        if k9 >= 9:

            score += 8
            reasons.append(
                f"🔥 Strong K/9 ({k9})"
            )

        return score, reasons

    except Exception as e:

        print(f"Pitcher Error: {e}")

        return 0, []

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

                        streak = team.get(
                            'streak',
                            ''
                        )

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

                        return {
                            "pct": pct,
                            "streak": streak,
                            "wins": wins,
                            "losses": losses
                        }

    except Exception as e:

        print(f"Form Error: {e}")

    return {
        "pct": 0.5,
        "streak": "",
        "wins": 0,
        "losses": 0
    }

# ==============================
# MLB PICKS
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

            home_id = game['home_id']
            away_id = game['away_id']

            score = 50

            reasons = []

            # HOME FIELD

            score += 6

            reasons.append(
                "✅ Home Field"
            )

            # TEAM FORM

            home_form = get_team_form(home)
            away_form = get_team_form(away)

            if home_form['pct'] > away_form['pct']:

                score += 12

                reasons.append(
                    "🔥 Better Team Form"
                )

            # STREAK

            if "W" in home_form['streak']:

                score += 6

                reasons.append(
                    f"🔥 {home_form['streak']}"
                )

            # PITCHING

            home_pitch_score, pitch_reasons = (
                get_pitcher_edge(home_id)
            )

            away_pitch_score, _ = (
                get_pitcher_edge(away_id)
            )

            if home_pitch_score > away_pitch_score:

                score += 15

                reasons.append(
                    "🔥 Better Starting Pitcher"
                )

                reasons.extend(
                    pitch_reasons
                )

            # FINAL %

            prob = max(
                50,
                min(
                    85,
                    score
                )
            )

            # FILTER

            if prob >= 60:

                picks.append({
                    "team": home,
                    "prob": prob,
                    "reasons": reasons
                })

        except Exception as e:

            print(
                f"MLB Error: {e}"
            )

    return sorted(
        picks,
        key=lambda x: x['prob'],
        reverse=True
    )[:7]

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    msg = "🔥 GOD TIER MLB MONEYLINE BOARD 🔥\n\n"

    mlb = get_mlb_picks()

    if not mlb:

        msg += (
            "❌ NO STRONG MLB EDGES TODAY"
        )

        return msg

    for i, p in enumerate(mlb):

        medal = "🥇"

        if i == 1:
            medal = "🥈"

        elif i == 2:
            medal = "🥉"

        else:
            medal = "⭐"

        msg += (
            f"{medal} {p['team']} ML\n"
        )

        msg += (
            f"📊 Win Probability: "
            f"{p['prob']}%\n"
        )

        # EDGE TAG

        if p['prob'] >= 78:

            msg += "👑 GOD TIER EDGE\n"

        elif p['prob'] >= 70:

            msg += "🔥 ELITE EDGE\n"

        else:

            msg += "✅ STRONG EDGE\n"

        for r in p['reasons']:

            msg += f"{r}\n"

        msg += "\n---------------------\n\n"

    return msg

# ==============================
# START BOT
# ==============================

if __name__ == "__main__":

    try:

        print(
            "🔥 STARTING MLB MONEYLINE BOT"
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
