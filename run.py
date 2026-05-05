import pandas as pd
import statsapi
import random
import requests
from datetime import datetime

print("HR BOT (FAST BALANCED VERSION) RUNNING...\n")

# ------------------------
# 👉 PASTE YOUR DISCORD WEBHOOK HERE
# ------------------------
WEBHOOK_URL = "https://discord.com/api/webhooks/1501102710064418878/vuFOAAOIDwAytxdNEW5mVSBcGSbwIt0HfCDJJ6Pu7n7wF4SzjvrbZ2PQDm0oCCtMuOmW"


# ------------------------
# PARK BOOST
# ------------------------
def park_boost(venue):
    hitter_parks = ["Yankee Stadium", "Coors Field", "Great American Ball Park"]
    if any(p in venue for p in hitter_parks):
        return 1.15
    return 1.0


# ------------------------
# GET TODAY'S GAMES
# ------------------------
today_date = datetime.today().strftime('%Y-%m-%d')
games = statsapi.schedule(date=today_date)

print(f"Games found: {len(games)}\n")

players_data = []

for game in games:
    matchup = f"{game['away_name']} vs {game['home_name']}"
    venue = game.get('venue_name', "")

    roster = []

    # ------------------------
    # TRY LINEUPS FIRST
    # ------------------------
    try:
        box = statsapi.get('game_boxscore', {'gamePk': game['game_id']})

        home_players = box['teams']['home']['players']
        away_players = box['teams']['away']['players']

        for p in home_players.values():
            if 'battingOrder' in p:
                roster.append(p)

        for p in away_players.values():
            if 'battingOrder' in p:
                roster.append(p)

    except:
        pass

    # ------------------------
    # FALLBACK (NO LINEUPS)
    # ------------------------
    if len(roster) == 0:
        home = statsapi.get('team_roster', {'teamId': game['home_id']})['roster']
        away = statsapi.get('team_roster', {'teamId': game['away_id']})['roster']

        for p in home + away:
            pos = p.get('position', {}).get('abbreviation', '')
            if pos != 'P':  # remove pitchers
                roster.append(p)

    # ------------------------
    # FAST BALANCED MODEL
    # ------------------------
    for p in roster:
        try:
            name = p['person']['fullName']

            elite = ["Judge","Ohtani","Alvarez","Olson","Stanton","Schwarber","Soto"]
            strong = ["Devers","Harper","Betts","Seager","Tatis","Freeman"]
            mid = ["Lindor","Riley","Machado","Guerrero","Acuna","Robert"]

            if any(x in name for x in elite):
                base = random.uniform(0.18, 0.26)
            elif any(x in name for x in strong):
                base = random.uniform(0.14, 0.20)
            elif any(x in name for x in mid):
                base = random.uniform(0.10, 0.16)
            else:
                base = random.uniform(0.06, 0.12)

            prob = base * random.uniform(0.9, 1.1)
            prob = min(prob * park_boost(venue), 0.30)

            players_data.append({
                'player': name,
                'game_id': matchup,
                'hr_prob': prob
            })

        except:
            continue


print(f"Players collected: {len(players_data)}\n")

# ------------------------
# OUTPUT
# ------------------------
if len(players_data) == 0:
    message = "No player data available."
    print(message)

else:
    df = pd.DataFrame(players_data)

    top = (df.sort_values(['game_id','hr_prob'], ascending=[True, False])
             .groupby('game_id')
             .head(3))

    output = ["TOP 3 HR PICKS PER GAME:\n"]

    for game, group in top.groupby('game_id'):
        output.append(game)
        for _, row in group.iterrows():
            output.append(f"  {row['player']} - {round(row['hr_prob']*100,1)}%")
        output.append("")

    message = "\n".join(output)

    # safe print (no crash)
    print(message.encode('ascii', 'ignore').decode())

    # SEND TO DISCORD
    if WEBHOOK_URL.startswith("https://"):
        try:
            requests.post(WEBHOOK_URL, json={"content": message})
            print("Sent to Discord")
        except Exception as e:
            print("Discord error:", e)
    else:
        print("No webhook set (skipped Discord)")

input("\nPress Enter to exit...")