def calculate_points(pred_home: int, pred_away: int, real_home: int, real_away: int, rules: dict) -> int:
    # sprawdzamy dokladny wynik — oba gole musza sie zgadzac
    if pred_home == real_home and pred_away == real_away:
        return rules["exact_pts"]

    # sprawdzamy roznice bramek — np. typowane 2:1 i rzeczywiste 3:2 to ta sama roznica (+1)
    if (pred_home - pred_away) == (real_home - real_away):
        return rules["diff_pts"]

    # sprawdzamy czy trafiony rezultat — wygrana gospodarz wygrana gosc lub remis
    # sign() zastepczo: porownujemy znak roznicy (moze byc -1 0 lub 1)
    pred_sign = (pred_home - pred_away > 0) - (pred_home - pred_away < 0)
    real_sign = (real_home - real_away > 0) - (real_home - real_away < 0)
    if pred_sign == real_sign:
        return rules["tendency_pts"]

    # pudlo — nic nie trafilismy
    return 0
