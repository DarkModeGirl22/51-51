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

# (days ago, hour, who, area, summary)
LOG = [
    # three weeks ago: the dishes still alternate
    (24, 20, "L", "home", "Did the dishes after dinner"),
    (23, 21, "K", "home", "Did the dishes after dinner"),
    (22, 20, "L", "home", "Did the dishes after dinner"),
    (21, 21, "K", "home", "Did the dishes after dinner"),
    # last two weeks: Leila every time
    (15, 20, "L", "home", "Did the dishes after dinner"),
    (13, 20, "L", "home", "Did the dishes after dinner"),
    (11, 20, "L", "home", "Did the dishes after dinner"),
    (9, 20, "L", "home", "Did the dishes after dinner"),
    (8, 21, "L", "home", "Did the dishes after dinner"),
    # this week
    (6, 16, "L", "kids", "Picked up Sarah and Adam from school"),
    (6, 18, "K", "money", "Paid this month's mortgage"),
    (5, 16, "L", "kids", "Picked up Sarah and Adam from school"),
    (5, 20, "L", "home", "Did the dishes after dinner"),
    (4, 16, "L", "kids", "Picked up the kids from school, then swimming lesson"),
    (4, 21, "K", "money", "Paid the electricity and internet bills"),
    (3, 19, "L", "home", "Cooked dinner and did the dishes"),
    (3, 20, "K", "kids", "Helped Adam with his reading homework"),
    (2, 11, "K", "money", "Receipt: weekly groceries at Carrefour, about 140 euros"),
    (2, 16, "L", "kids", "Picked up Sarah and Adam from school"),
    (1, 10, "K", "kids", "Took the kids to the park all morning"),
    (1, 20, "L", "home", "Did the dishes after dinner"),
    (0, 9, "L", "home", "Laundry: two loads washed and folded"),
]


def create_sample_couple(conn, code: str) -> dict:
    couple_id = conn.execute("INSERT INTO couples (code, is_sample) VALUES (?, 1)", (code,)).lastrowid
    ids, keys = {}, {}
    for tag, p in (("L", LEILA), ("K", KARIM)):
        key = secrets.token_urlsafe(24)
        ids[tag] = conn.execute(
            """INSERT INTO partners (couple_id, key, name, colour, kids_count, kids_ages,
                                     material, immaterial, extra_note) VALUES (?,?,?,?,?,?,?,?,?)""",
            (couple_id, key, p["name"], p["colour"], p["kids_count"], p["kids_ages"],
             json.dumps(p["material"]), json.dumps(p["immaterial"]), p["extra_note"])).lastrowid
        keys[tag] = key
    now = datetime.now(timezone.utc)
    for days, hour, who, area, summary in LOG:
        when = (now - timedelta(days=days)).replace(hour=hour, minute=secrets.randbelow(50), second=0, microsecond=0)
        if when > now:
            when = now - timedelta(minutes=5 + secrets.randbelow(60))
        kind = "photo" if summary.startswith("Receipt") else "text"
        conn.execute("INSERT INTO entries (couple_id, partner_id, created_at, kind, text, area, summary)"
                     " VALUES (?,?,?,?,?,?,?)",
                     (couple_id, ids[who], when.isoformat(), kind, summary, area, summary))
    return {"code": code,
            "partners": [{"name": "Leila", "colour": "pink", "link": f"/enter?key={keys['L']}"},
                         {"name": "Karim", "colour": "blue", "link": f"/enter?key={keys['K']}"}]}
