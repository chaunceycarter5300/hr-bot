import os
import requests
import statsapi

webhook = os.getenv("DISCORD_WEBHOOK")

def get_games():
    return statsapi.schedule()

def get_hitters(team_id):
    try:
        roster = statsapi.get('team_roster', {
            'teamId': team_id,
            'rosterType': 'active'
        })

        hitters = []
        for p in roster['roster']:
            pos = p.get('position', {}).get('abbreviation', '')
            if pos == 'P':
                continue
            hitters.append(p['person']['id'])

        return hitters[:9]

    except:
        return []

def get_player_stats(player_id):
    try:
        stats = statsapi.player_stat_data(player_id, group="[hitting]", type="season")
        s = stats['stats'][0]['stats']

        hr = int(s.get('homeRuns', 0))
        slg = float(s.get('sluggingPercentage', 0))

        return hr, slg
    except:
        return 0, 0.0

def get_pitcher_hr_rate(team_id):
    try:
        roster = statsapi.get('team_roster', {
            'teamId': team_id,
            'rosterType': 'rotation'
        })

        if not roster['roster']:
            return 1.0

        pitcher_id = roster['roster'][0]['person']['id']
        stats = statsapi.player_stat_data(pitcher_id, group="[pitching]", type="season")
        s = stats['stats'][0]['stats']

        hr_allowed = int(s.get('homeRuns', 1))
        innings = float(s.get('inningsPitched', 1))

        return hr_allowed / innings if innings > 0 else 1.0

    except:
        return 1.0

def build_message():
    games = get_games()
    msg = "🔥 **TOP HR PICKS TODAY** 🔥\n\n"

    all_picks = []

    for game in games[:6]:
        home = game['home_name']
        away = game['away_name']

        hitters = get_hitters(game['home_id'])
        pitcher_factor = get_pitcher_hr_rate(game['away_id'])

        for pid in hitters:
            hr, slg = get_player_stats(pid)

            score = (hr * 2) + (slg * 100) + (pitcher_factor * 50)

            try:
                name = statsapi.lookup_player(pid)[0]['fullName']
            except:
                continue

            all_picks.append((name, round(score, 1), home, away))

    # sort best picks
    all_picks = sorted(all_picks, key=lambda x: x[1], reverse=True)

    # 🔥 TOP 5
    msg += "🔥 **TOP PLAYS** 🔥\n"
    for p in all_picks[:5]:
        msg += f"{p[0]} ({p[1]}) - {p[3]} vs {p[2]}\n"

    msg += "\n💎 **VALUE PLAYS** 💎\n"
    for p in all_picks[5:10]:
        msg += f"{p[0]} ({p[1]})\n"

    msg += "\n🎯 **LONGSHOTS** 🎯\n"
    for p in all_picks[10:15]:
        msg += f"{p[0]} ({p[1]})\n"

    return msg

def send_to_discord(message):
    if not webhook:
        print("No webhook set")
        return

    try:
        requests.post(webhook, json={"content": message})
        print("✅ Sent to Discord")
    except Exception as e:
        print("Discord error:", e)

if __name__ == "__main__":
    msg = build_message()
    print(msg)
    send_to_discord(msg)
