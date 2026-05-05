import os
import requests
import statsapi
import random

webhook = os.getenv("DISCORD_WEBHOOK")

def get_games():
    return statsapi.schedule()

def get_lineup(team_id):
    try:
        roster = statsapi.roster(team_id)
        return [player['person']['fullName'] for player in roster[:9]]
    except:
        return []

def fake_hr_model(players):
    results = []
    for p in players:
        hr_chance = round(random.uniform(10, 30), 1)
        results.append((p, hr_chance))
    return sorted(results, key=lambda x: x[1], reverse=True)

def build_message():
    games = get_games()
    msg = "🔥 **HR PICKS TODAY** 🔥\n\n"

    for game in games[:5]:
        home = game['home_name']
        away = game['away_name']

        msg += f"**{away} vs {home}**\n"

        players = get_lineup(game['home_id'])
        picks = fake_hr_model(players)[:3]

        for name, prob in picks:
            msg += f"- {name} ({prob}%)\n"

        msg += "\n"

    return msg

def send_to_discord(message):
    if not webhook:
        print("⚠️ No webhook set, skipping Discord")
        return

    try:
        requests.post(webhook, json={"content": message})
        print("✅ Sent to Discord")
    except Exception as e:
        print("❌ Discord error:", e)

if __name__ == "__main__":
    message = build_message()
    print(message)
    send_to_discord(message)
