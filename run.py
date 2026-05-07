# ==============================
# ADD THIS UNDER SETTINGS
# ==============================

TOP_PLAYS_TO_SHOW = 5


# ==============================
# REPLACE build_message()
# ==============================

def build_message():

    games = get_games_today()

    msg = "🔥 FINAL HR PICKS 🔥\n\n"

    all_best_plays = []

    for game in games:

        home = game['home_name']
        away = game['away_name']

        venue = game.get(
            'venue_name',
            ''
        )

        away_top, away_all = get_team_picks(
            game['away_id'],
            game['home_id'],
            venue
        )

        home_top, home_all = get_team_picks(
            game['home_id'],
            game['away_id'],
            venue
        )

        if away_top:
            all_best_plays.extend(away_top)

        if home_top:
            all_best_plays.extend(home_top)

        if not away_top and not home_top:
            continue

        msg += f"🏟️ {away} vs {home}\n\n"

        for side in [away_top, home_top]:

            for (
                name,
                percent,
                emoji,
                tags,
                hr_prob
            ) in side:

                msg += (
                    f"{emoji} {name} "
                    f"({percent}%)\n"
                )

                for t in tags:
                    msg += f"{t}\n"

                # ======================
                # BEST PLAY TAG
                # ======================

                msg += "🎯 BEST PLAY\n"

                if hr_prob >= 38:
                    msg += "💣 NUKE PLAY\n"

                msg += "\n"

        msg += (
            "----------------------\n\n"
        )

    # ==============================
    # OVERALL BEST PLAYS
    # ==============================

    msg += "🔥 TOP BEST PLAYS 🔥\n\n"

    all_best_plays = sorted(
        all_best_plays,
        key=lambda x: x[1],
        reverse=True
    )

    for i, (
        name,
        percent,
        emoji,
        tags,
        hr_prob
    ) in enumerate(
        all_best_plays[:TOP_PLAYS_TO_SHOW]
    ):

        msg += (
            f"{i+1}. "
            f"{emoji} {name} "
            f"({percent}%)\n"
        )

        msg += (
            f"🚀 HR Probability: "
            f"{hr_prob}%\n"
        )

        if hr_prob >= 38:
            msg += "💣 NUKE PLAY\n"

        msg += "\n"

    return msg
