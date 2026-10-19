"""SAMPLE DATA: a demo couple (Leila & Karim) with a few weeks of logs.

Used by the "Try the sample couple" button and the demo video. Everything here is
invented and the couple is flagged is_sample=1, so the app labels it clearly.
"""
import json
import secrets
from datetime import datetime, timedelta, timezone

LEILA = {
    "name": "Leila", "colour": "pink", "kids_count": 2, "kids_ages": "4 and 7",
    "material": {"people_at_home": "4", "married_for": "9 years", "job": "nurse, part-time",
                 "working_hours": "9am to 3pm, Monday to Thursday", "who_earns_more": "partner"},
    "immaterial": {"sacrifices": "I moved to part-time after our second child was born",
                   "feelings": "I feel like I do every school run and every dish, and nobody notices",
                   "how_partner_sees_it": "He probably thinks it's fair because he pays more",
                   "wishes": "I'd love him to take over the dishes and some evenings"},
    "extra_note": "",
}
KARIM = {
    "name": "Karim", "colour": "blue", "kids_count": 2, "kids_ages": "4 and 7",
    "material": {"people_at_home": "4", "married_for": "9 years", "job": "site engineer",
                 "working_hours": "7am until 8pm, often Saturdays", "who_earns_more": "me"},
    "immaterial": {"sacrifices": "I took the job with long hours so we could afford the bigger flat",
                   "feelings": "I barely see the kids on weekdays and I feel guilty about it",
                   "how_partner_sees_it": "She thinks I don't do anything at home",
                   "wishes": "I want her to see that the money side is effort too"},
    "extra_note": "School pickups at half past four are impossible with my hours.",
}

# Roles: "W" = the woman's side (Leila's story), "M" = the man's side (Karim's story).
THIS_WEEK = [
    (6, 16, "W", "kids", "Picked up Sarah and Adam from school"),
    (6, 18, "M", "money", "Paid this month's mortgage"),
    (5, 16, "W", "kids", "Picked up Sarah and Adam from school"),
    (5, 20, "W", "home", "Did the dishes after dinner"),
    (4, 16, "W", "kids", "Picked up the kids from school, then swimming lesson"),
    (4, 21, "M", "money", "Paid the electricity and internet bills"),
    (3, 19, "W", "home", "Cooked dinner and did the dishes"),
    (3, 20, "M", "kids", "Helped Adam with his reading homework"),
    (2, 11, "M", "money", "Receipt: weekly groceries at Carrefour, about 140 euros"),
    (2, 16, "W", "kids", "Picked up Sarah and Adam from school"),
    (1, 10, "M", "kids", "Took the kids to the park all morning"),
    (1, 20, "W", "home", "Did the dishes after dinner"),
    (0, 9, "W", "home", "Laundry: two loads washed and folded"),
]


def two_months_of_logs():
    """About eight weeks of invented life. Dishes alternate until two weeks ago,
    then the woman does them every time (the pattern the conflict button notices)."""
    log = []
    for days in range(58, 7, -1):
        weekday = days % 7
        if days >= 15:  # the dishes still take turns
            log.append((days, 20, "W" if days % 2 else "M", "home", "Did the dishes after dinner"))
        elif days % 2 == 0 or days in (9, 11):
            log.append((days, 20, "W", "home", "Did the dishes after dinner"))
        if weekday in (1, 2, 3, 4):
            log.append((days, 16, "W", "kids", "Picked up Sarah and Adam from school"))
        if weekday == 5:
            log.append((days, 10, "M", "money", "Receipt: weekly groceries at Carrefour"))
            log.append((days, 15, "M", "kids", "Took the kids to football practice"))
        if weekday == 6:
            log.append((days, 12, "W", "home", "Cooked Sunday lunch for the family"))
            log.append((days, 18, "M", "home", "Fixed the leaking bathroom tap" if days > 40 else "Took out the bins and cleaned the car"))
        if days in (52, 22):
            log.append((days, 19, "M", "money", "Paid this month's mortgage"))
            log.append((days, 21, "M", "money", "Paid the electricity and internet bills"))
        if days in (45, 31):
            log.append((days, 17, "W", "kids", "Took Adam to the dentist"))
            log.append((days, 9, "W", "money", "Paid the school canteen"))
    return log + THIS_WEEK


def _insert_partner(conn, couple_id, p) -> tuple[int, str]:
    key = secrets.token_urlsafe(24)
    pid = conn.execute(
        """INSERT INTO partners (couple_id, key, name, colour, kids_count, kids_ages,
                                 material, immaterial, extra_note) VALUES (?,?,?,?,?,?,?,?,?)""",
        (couple_id, key, p["name"], p["colour"], p["kids_count"], p["kids_ages"],
         json.dumps(p["material"]), json.dumps(p["immaterial"]), p["extra_note"])).lastrowid
    return pid, key


def create_sample_couple(conn, code: str, me: dict, role: str) -> dict:
    """`me` = the visitor's own quick answers; `role` = "woman" or "man".
    Their invented partner (Karim or Leila) and two months of logs are added around them."""
    couple_id = conn.execute("INSERT INTO couples (code, is_sample) VALUES (?, 1)", (code,)).lastrowid
    partner = dict(KARIM if role == "woman" else LEILA)
    if partner["colour"] == me["colour"]:
        partner["colour"] = next(c for c in ("blue", "pink", "green", "orange") if c != me["colour"])
    my_id, my_key = _insert_partner(conn, couple_id, me)
    partner_id, _ = _insert_partner(conn, couple_id, partner)
    ids = {"W": my_id, "M": partner_id} if role == "woman" else {"W": partner_id, "M": my_id}
    now = datetime.now(timezone.utc)
    for days, hour, who, area, summary in two_months_of_logs():
        when = (now - timedelta(days=days)).replace(hour=hour, minute=secrets.randbelow(50), second=0, microsecond=0)
        if when > now:
            when = now - timedelta(minutes=5 + secrets.randbelow(60))
        kind = "photo" if summary.startswith("Receipt") else "text"
        conn.execute("INSERT INTO entries (couple_id, partner_id, created_at, kind, text, area, summary)"
                     " VALUES (?,?,?,?,?,?,?)",
                     (couple_id, ids[who], when.isoformat(), kind, summary, area, summary))
    return {"key": my_key, "code": code, "partner": partner["name"]}
