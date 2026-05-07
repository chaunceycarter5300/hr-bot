# ==============================
# ACCURACY FILTERS (ADD THIS)
# ==============================

# put this near the top under PARK_BOOST

MIN_BARREL = 10
MIN_HARD_HIT = 40
MIN_HR_PROB = 22

MAX_PLAYERS_PER_TEAM = 1


# ==============================
# REPLACE calculate_score()
# ==============================

def calculate_score(
    hr,
    slg,
    barrel,
    hard_hit,
    pitcher,
    weather,
    park
):

    score = 0

    # BARREL = MOST IMPORTANT
    score += barrel * 5

    # HARD HIT
    score += hard_hit * 2

    # HR TOTAL
    score += hr * 1.5

    # SLUGGING
    score += slg * 25

    # WEATHER / PARK
    score *= weather
    score *= park

    # PITCHER ADJUSTMENT
    if pitcher > 0.15:
        score *= 1.15
    else:
        score *= 0.82

    return score


# ==============================
# REPLACE get_team_picks()
# ==============================

def get_team_picks(
    team_id,
    opponent_id,
    venue
):

    hitters = get_lineup(team_id)

    pitcher_id = get_pitcher(opponent_id)

    pitcher = (
        get_pitcher_factor(pitcher_id)
        if pitcher_id else 1.0
    )

    weather = weather_boost(venue)

    park = park_boost(venue)

    scored = []

    for p in hitters:

        (
            hr,
            slg,
            barrel,
            hard_hit,
            hr_prob
        ) = get_player_stats(p["id"])

        # =========================
        # HARD FILTERS
        # =========================

        if barrel < MIN_BARREL:
            continue

        if hard_hit < MIN_HARD_HIT:
            continue

        if hr_prob < MIN_HR_PROB:
            continue

        # =========================
        # TAGS
        # =========================

        tags = []

        tags.append(
            f"💥 Hard Hit: {hard_hit}%"
        )

        tags.append(
            f"🛢️ Barrel: {barrel}%"
        )

        tags.append(
            f"🚀 HR Probability: {hr_prob}%"
        )

        # WEATHER
        if weather > 1:
            tags.append("✅ Wind Out")
        else:
            tags.append("⚠️ Wind In")

        # PITCHER
        if pitcher > 0.15:
            tags.append("✅ Weak Pitcher")
        else:
            tags.append("⚠️ Tough Pitcher")

        # PARK
        if park > 1.1:
            tags.append("✅ Great Park")

        # HOT BAT
        if barrel >= 14:
            tags.append("🔥 Elite Barrel")

        # =========================
        # SCORE
        # =========================

        score = calculate_score(
            hr,
            slg,
            barrel,
            hard_hit,
            pitcher,
            weather,
            park
        )

        scored.append(
            (
                p["name"],
                score,
                tags,
                hr_prob
            )
        )

    # =========================
    # SORT BEST ONLY
    # =========================

    scored = sorted(
        scored,
        key=lambda x: x[1],
        reverse=True
    )

    normalized = normalize_scores(scored)

    final = []

    for (
        name,
        percent,
        tags,
        hr_prob
    ) in normalized:

        emoji = get_emoji(percent)

        final.append(
            (
                name,
                percent,
                emoji,
                tags,
                hr_prob
            )
        )

    # ONLY RETURN TOP PLAY
    return final[:MAX_PLAYERS_PER_TEAM], final
