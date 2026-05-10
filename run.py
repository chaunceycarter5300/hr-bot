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
# MLB PICKS
# ==============================

def get_mlb_picks():

    today = datetime.now(
        pytz.timezone("US/Eastern")
    ).strftime('%Y-%m-%d')

    games = statsapi.schedule(
        date=today
    )

    moneylines = []
    f5_picks = []
    totals = []
    team_totals = []

    for game in games:

        try:

            away = game['away_name']
            home = game['home_name']

            home_id = game['home_id']
            away_id = game['away_id']

            # =========================
            # FORM
            # =========================

            home_form = get_team_form(
                home
            )

            away_form = get_team_form(
                away
            )

            # =========================
            # PITCHERS
            # =========================

            home_pitch = get_pitcher_stats(
                home_id
            )

            away_pitch = get_pitcher_stats(
                away_id
            )

            # =========================
            # MONEYLINE
            # =========================

            ml_score = 50
            ml_reasons = []

            ml_score += 5

            ml_reasons.append(
                "✅ Home Field"
            )

            if home_form > away_form:

                ml_score += 10

                ml_reasons.append(
                    "🔥 Better Team Form"
                )

            if (
                home_pitch['era']
                < away_pitch['era']
            ):

                ml_score += 12

                ml_reasons.append(
                    "🔥 Better Starting Pitcher"
                )

            if (
                home_pitch['whip']
                < away_pitch['whip']
            ):

                ml_score += 5

                ml_reasons.append(
                    "🔥 Better WHIP"
                )

            ml_prob = max(
                50,
                min(
                    85,
                    ml_score
                )
            )

            if ml_prob >= 60:

                moneylines.append({

                    "team": home,
                    "prob": ml_prob,
                    "reasons": ml_reasons

                })

            # =========================
            # FIRST 5
            # =========================

            f5_score = 50
            f5_reasons = []

            if (
                home_pitch['era']
                < away_pitch['era']
            ):

                f5_score += 15

                f5_reasons.append(
                    "🔥 Elite Pitching Edge"
                )

            if (
                home_pitch['whip']
                < away_pitch['whip']
            ):

                f5_score += 10

                f5_reasons.append(
                    "🔥 Better WHIP"
                )

            if (
                home_pitch['k9']
                > away_pitch['k9']
            ):

                f5_score += 8

                f5_reasons.append(
                    "🔥 Better K/9"
                )

            if f5_score >= 65:

                f5_picks.append({

                    "team": home,
                    "prob": f5_score,
                    "reasons": f5_reasons

                })

            # =========================
            # TOTALS
            # =========================

            combined_era = (
                home_pitch['era']
                +
                away_pitch['era']
            )

            combined_k9 = (
                home_pitch['k9']
                +
                away_pitch['k9']
            )

            over_score = 50
            over_reasons = []

            if combined_era >= 8:

                over_score += 15

                over_reasons.append(
                    "🔥 Weak Pitching Matchup"
                )

            if combined_k9 <= 15:

                over_score += 10

                over_reasons.append(
                    "🔥 Low Strikeout Pitchers"
                )

            if over_score >= 65:

                totals.append({

                    "matchup":
                    f"{away} vs {home}",

                    "bet":
                    "OVER 9",

                    "prob":
                    over_score,

                    "reasons":
                    over_reasons

                })

            under_score = 50
            under_reasons = []

            if combined_era <= 6:

                under_score += 15

                under_reasons.append(
                    "🔥 Elite Pitching Matchup"
                )

            if combined_k9 >= 18:

                under_score += 10

                under_reasons.append(
                    "🔥 High Strikeout Pitchers"
                )

            if under_score >= 65:

                totals.append({

                    "matchup":
                    f"{away} vs {home}",

                    "bet":
                    "UNDER 7",

                    "prob":
                    under_score,

                    "reasons":
                    under_reasons

                })

            # =========================
            # TEAM TOTALS
            # =========================

            team_total_score = 50
            team_total_reasons = []

            if (
                away_pitch['era']
                >= 4.50
            ):

                team_total_score += 15

                team_total_reasons.append(
                    "🔥 Weak Opposing Pitcher"
                )

            if (
                away_pitch['whip']
                >= 1.35
            ):

                team_total_score += 10

                team_total_reasons.append(
                    "🔥 High WHIP Matchup"
                )

            if home_form >= 0.550:

                team_total_score += 8

                team_total_reasons.append(
                    "🔥 Strong Team Form"
                )

            if team_total_score >= 65:

                team_totals.append({

                    "team":
                    home,

                    "bet":
                    "TEAM TOTAL OVER 4.5",

                    "prob":
                    team_total_score,

                    "reasons":
                    team_total_reasons

                })

        except Exception as e:

            print(
                f"Game Error: {e}"
            )

    return (
        moneylines[:5],
        f5_picks[:5],
        totals[:5],
        team_totals[:5]
    )

# ==============================
# BUILD MESSAGE
# ==============================

def build_message():

    (
        moneylines,
        f5_picks,
        totals,
        team_totals
    ) = get_mlb_picks()

    msg = (
        "🔥 GOD TIER MLB BOARD 🔥\n\n"
    )

    # ==========================
    # MONEYLINES
    # ==========================

    msg += "⚾ MONEYLINES\n\n"

    for p in moneylines:

        msg += (
            f"🔥 {p['team']} ML\n"
        )

        msg += (
            f"📊 {p['prob']}%\n"
        )

        for r in p['reasons']:

            msg += f"{r}\n"

        msg += "\n------------------\n\n"

    # ==========================
    # F5
    # ==========================

    msg += "⚾ FIRST 5 INNINGS\n\n"

    for p in f5_picks:

        msg += (
            f"🔥 {p['team']} F5 ML\n"
        )

        msg += (
            f"📊 {p['prob']}%\n"
        )

        for r in p['reasons']:

            msg += f"{r}\n"

        msg += "\n------------------\n\n"

    # ==========================
    # TOTALS
    # ==========================

    msg += "🔥 TOTAL RUNS\n\n"

    for t in totals:

        msg += (
            f"🔥 {t['matchup']} "
            f"{t['bet']}\n"
        )

        msg += (
            f"📊 {t['prob']}%\n"
        )

        for r in t['reasons']:

            msg += f"{r}\n"

        msg += "\n------------------\n\n"

    # ==========================
    # TEAM TOTALS
    # ==========================

    msg += "⚾ TEAM TOTALS\n\n"

    for t in team_totals:

        msg += (
            f"🔥 {t['team']} "
            f"{t['bet']}\n"
        )

        msg += (
            f"📊 {t['prob']}%\n"
        )

        for r in t['reasons']:

            msg += f"{r}\n"

        msg += "\n------------------\n\n"

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
