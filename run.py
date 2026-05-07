import os

            pos = p.get(
                'position',
                {}
            ).get(
                'abbreviation', '')

            if pos in ['P', 'TWP']:
                continue

            hitters.append({
                "id": p['person']['id'],
                "name": p['person']['fullName']
            })

        return hitters[:9]

    except Exception as e:

        print(f"Lineup Error: {e}")

        return []

# ==============================
# REAL PLAYER STATS
# ==============================


def get_player_stats(player_name, player_id):

    try:

        stats = statsapi.player_stat_data(
            player_id,
            group="[hitting]",
            type="season"
        )

        s = stats['stats'][0]['stats']

        hr = int(s.get('homeRuns', 0))
        slg = float(s.get('sluggingPercentage', 0))

        row = statcast_df[
            statcast_df['Name'] == player_name
        ]

        if row.empty:
            return None

        barrel = float(row['Barrel%'].iloc[0])
        hard_hit = float(row['HardHit%'].iloc[0])
        fly_ball = float(row['FB%'].iloc[0])
        launch_angle = float(row['LA'].iloc[0])

        hr_score = round(
            (
                (barrel * 0.40)
                + (hard_hit * 0.20)
                + (fly_ball * 0.20)
                + (launch_angle * 0.10)
                + (hr * 0.10)
            ),
            1
        )

        return {
            "hr": hr,
            "slg": slg,
            "barrel": barrel,
            "hard_hit": hard_hit,
            "fly_ball": fly_ball,
            "launch_angle": launch_angle,
            "hr_score": hr_score
        }

    except Exception as e:

        print(f"Player Stat Error: {e}")

        return None

# ==============================
# PITCHERS
# ==============================


def get_pitcher(team_id):
    send_to_discord(msg)
