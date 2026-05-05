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
            if pos in ['P', 'TWP']:
                continue

            hitters.append({
                "id": p['person']['id'],
                "name": p['person']['fullName']
            })

        return hitters

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

def get_pitcher_factor(team_id):
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

def score_player(player_id, pitcher_factor):
    hr, slg = get_player_stats(player_id)
    return (hr * 2) + (slg * 100) + (pitcher_factor * 50)

def get_top_3(team_id, opponent_id):
    hitters = get_hitters(team_id)
    pitcher_factor = get_pitcher_factor(opponent_id)

    scored = []
    for p in hitters:
        score = score_player(p["id"], pitcher_factor)
        scored.append((p["name"], round(score, 1)))

    scored = sorted(scored, key=lambda x: x[1], reverse=True)
    return scored[:3]

def build_message():
    games = get_games()
    msg = "🔥 **HR PICKS TODAY (3 PER TEAM)** 🔥\n\n"

    for game in games[:6]:
        home = game['home_name']
        away = game['away_name']

        msg += f"**{away} vs {home}**\n"

        away_top = get_top_3(game['away_id'], game['home_id'])
        home_top = get_top_3(game['home_id'], game['away_id'])

        msg += f"\n{away}:\n"
        for name, score in away_top:
            msg += f"- {name} ({score})\n"

        msg += f"\n{home}:\n"
        for name, score in home_top:
            msg += f"- {name} ({score})\n"

        msg += "\n---------------------\n\n"

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
