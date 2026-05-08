# ==============================
# REAL STATCAST DATA
# REPLACE THIS ENTIRE FUNCTION
# ==============================

def get_statcast_data(player_id):

    try:

        data = statcast_batter_exitvelo_barrels(
            2025
        )

        # FIX PLAYER ID TYPES

        data['player_id'] = data[
            'player_id'
        ].astype(str)

        player = data[
            data['player_id']
            == str(player_id)
        ]

        if player.empty:

            return {
                "barrel_pct": 0,
                "hard_hit_pct": 0,
                "avg_ev": 0
            }

        row = player.iloc[0]

        # REAL BARREL %

        barrel_pct = float(
            row.get(
                'brl_percent',
                0
            )
        )

        # FIX HARD HIT %

        hard_hit_pct = float(
            row.get(
                'hard_hit_percentile',
                row.get(
                    'hard_hit_percent',
                    0
                )
            )
        )

        # EXIT VELO

        avg_ev = float(
            row.get(
                'avg_hit_speed',
                0
            )
        )

        return {
            "barrel_pct": barrel_pct,
            "hard_hit_pct": hard_hit_pct,
            "avg_ev": avg_ev
        }

    except Exception as e:

        print(
            f"Statcast Error: {e}"
        )

        return {
            "barrel_pct": 0,
            "hard_hit_pct": 0,
            "avg_ev": 0
        }
