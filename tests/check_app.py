"""Quick end-to-end checks for 51/51. Run: python tests/check_app.py

Uses a throwaway database and the practice AI (no Gemini key needed).
"""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ.pop("GEMINI_API_KEY", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

PRIVATE_WORDS = ["went part-time", "exhausted", "secret-salary-90k", "9am to 3pm", "until 8pm"]

WIFE = {
    "name": "Leila", "colour": "pink", "kids_count": 2, "kids_ages": "4 and 7",
    "material": {"job": "nurse, part-time", "working_hours": "9am to 3pm", "who_earns_more": "partner"},
    "immaterial": {"sacrifices": "I went part-time after our second child", "feelings": "exhausted"},
    "extra_note": "",
}
HUSBAND = {
    "name": "Karim", "colour": "blue", "kids_count": 2, "kids_ages": "4 and 7",
    "material": {"job": "engineer", "working_hours": "8am until 8pm", "who_earns_more": "me"},
    "immaterial": {"sacrifices": "secret-salary-90k", "feelings": "I feel I never see the kids"},
    "extra_note": "",
}


def ok(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        sys.exit(1)


def no_private(text: str, label: str):
    leaked = [w for w in PRIVATE_WORDS if w in text]
    ok(not leaked, f"{label} (leaked: {leaked})" if leaked else label)


def onboard(c, wife=WIFE, husband=HUSBAND):
    r = c.post("/api/couples", json=wife)
    w = r.json()
    r2 = c.post("/api/join", json={**husband, "code": w["code"]})
    h = r2.json()
    return {"X-Partner-Key": w["key"]}, {"X-Partner-Key": h["key"]}, w["code"]


def slice1(c):
    for page in ["/", "/onboarding", "/home"]:
        ok(c.get(page).status_code == 200, f"page {page} loads")
    r = c.post("/api/couples", json=WIFE)
    ok(r.status_code == 200 and r.json()["code"], "first partner gets a partner code")
    wife_key, code = r.json()["key"], r.json()["code"]

    r = c.get("/api/couples/NOPE-00")
    ok(r.status_code == 404 and "couldn't find" in r.json()["detail"], "wrong code -> friendly 404")
    r = c.post("/api/join", json={**HUSBAND, "code": "NOPE-00"})
    ok(r.status_code == 404, "joining with wrong code refused")

    r = c.get("/api/home", headers={"X-Partner-Key": wife_key})
    ok(r.json()["partner"] is None, "wife sees 'waiting for partner' before he joins")

    r = c.get(f"/api/couples/{code.lower()}")
    ok(r.status_code == 200 and r.json()["taken_colours"] == ["pink"], "code works in lowercase, pink taken")
    r = c.post("/api/join", json={**HUSBAND, "colour": "pink", "code": code})
    ok(r.status_code == 422, "partner can't take the same colour")
    r = c.post("/api/join", json={**HUSBAND, "code": code})
    ok(r.status_code == 200, "second partner joins with the code")
    husband_key = r.json()["key"]
    r = c.post("/api/join", json={**HUSBAND, "colour": "green", "code": code})
    ok(r.status_code == 409, "a third person can't join")

    hw = c.get("/api/home", headers={"X-Partner-Key": wife_key}).text
    hh = c.get("/api/home", headers={"X-Partner-Key": husband_key}).text
    ok(json.loads(hw)["partner"]["name"] == "Karim", "wife now sees Karim")
    no_private(hw + hh, "home never contains private answers")
    ok(c.get("/api/home").status_code == 401, "no key -> asked to join")


def slice2(c):
    from datetime import datetime, timezone
    from app import ai, main
    wife, husband, _ = onboard(c)

    r = c.post("/api/entries", data={"text": "Picked up Sarah from school"}, headers=wife)
    ok(r.status_code == 200 and r.json()["area"] == "kids", "text entry sorted into kids")
    r = c.post("/api/entries", data={"text": "Paid the electricity bill"}, headers=husband)
    ok(r.json()["area"] == "money", "bill sorted into money")
    r = c.post("/api/entries", files={"photo": ("r.jpg", b"fakejpeg", "image/jpeg")}, headers=husband)
    ok(r.status_code == 200 and r.json()["area"] in ai.AREAS, "receipt photo becomes an entry")
    ok(c.post("/api/entries", data={"text": "  "}, headers=wife).status_code == 422, "empty entry refused")

    real_sort, real_read = ai.sort_text, ai.read_receipt
    def boom(*a, **k):
        raise ai.AIError("quota")
    ai.sort_text = boom
    r = c.post("/api/entries", data={"text": "Cooked dinner"}, headers=wife)
    ok(r.status_code == 200 and r.json()["area"] == "unsorted" and r.json()["note"] == "ai_down",
       "AI down -> entry still saved as unsorted")
    ai.sort_text = real_sort
    ai.read_receipt = lambda *a, **k: None
    r = c.post("/api/entries", files={"photo": ("r.jpg", b"blurry", "image/jpeg")}, headers=wife)
    ok(r.status_code == 422 and "describe it" in r.json()["detail"], "unreadable photo -> asks to describe it")
    ai.read_receipt = real_read

    hw = c.get("/api/home", headers=wife).json()
    hh = c.get("/api/home", headers=husband).json()
    ok(len(hw["entries"]) == 4 and len(hh["entries"]) == 4, "both partners see all four entries")
    ok(hw["ai_mode"] == "practice", "practice AI is labelled")
    ok(c.get("/api/ai-check").json()["mode"] == "practice", "ai-check reports the mode")

    # Week starts Monday 00:00 local: Wed 22 Oct 2026 10:00 UTC, Paris (-120) -> Sun 19 Oct 22:00 UTC
    ws = main.week_start_utc(-120, datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc))
    ok(ws == datetime(2026, 10, 18, 22, 0, tzinfo=timezone.utc), "week starts Monday midnight local time")


def slice3(c):
    from app import agents, ai
    import re as _re
    wife, husband, _ = onboard(c)
    h = c.get("/api/week", headers=wife).json()
    ok(h["week"] is None, "empty week -> invitation to log, no judgement")

    for t in ["Picked up the kids from school", "Did the dishes", "Cooked dinner", "Picked up Sarah",
              "Did the laundry"]:
        c.post("/api/entries", data={"text": t}, headers=wife)
    c.post("/api/entries", data={"text": "Paid the mortgage"}, headers=husband)
    hw = c.get("/api/week", headers=wife).json()
    hh = c.get("/api/week", headers=husband).json()
    board_text = json.dumps(hw["week"]) + json.dumps(hh["week"])
    ok(all(hw["week"]["areas"][a] for a in ("kids", "home", "money")), "board has words for kids, home, money")
    ok(not _re.search(r"\d|%", json.dumps(hw["week"]["areas"]) + hw["week"]["message"] + hh["week"]["message"]),
       "board and messages contain no numbers")
    ok(hw["week"]["message"] != hh["week"]["message"], "uneven week -> each partner gets a different message")
    ok(hw["week"]["message"] in [m.format(other="Karim") for m in agents.MORE_MSG],
       "the partner who did more is told they did a lot")
    ok(hh["week"]["message"] in [m.format(other="Leila") for m in agents.LESS_MSG]
       and "thank" in hh["week"]["message"].lower(), "the other is told to say thank you")
    no_private(board_text, "board never contains private answers")
    ok("message" not in json.dumps(hh["week"]).replace('"message"', ""), "each partner only receives their own message")

    # balanced week
    w2, h2, _ = onboard(c)
    for t in ["Picked up the kids", "Did the dishes", "Paid the bill"]:
        c.post("/api/entries", data={"text": t}, headers=w2)
        c.post("/api/entries", data={"text": t}, headers=h2)
    a = c.get("/api/week", headers=w2).json()["week"]["message"]
    b = c.get("/api/week", headers=h2).json()["week"]["message"]
    ok(a == b and ("balanced" in a.lower() or "team" in a.lower()), "balanced week -> both praised")

    # shared facts: 2 kids vs 3 kids
    w3, h3, _ = onboard(c, husband={**HUSBAND, "kids_count": 3})
    q = c.get("/api/home", headers=w3).json()["fact_question"]
    ok(q and "Karim" in q, "different number of kids -> question on the board")
    c.post("/api/me/kids", json={"kids_count": 2, "kids_ages": "4 and 7"}, headers=h3)
    ok(c.get("/api/home", headers=w3).json()["fact_question"] is None, "question disappears once fixed")

    # guards on what the (real) AI might write
    real = ai.ask_json
    ai_mode = ai.mode
    ai.mode = lambda: "gemini"
    calls = {"n": 0}
    def fake(prompt, image=None, mime=None):
        calls["n"] += 1
        if "PRIVATE agent" in prompt:
            return {"load": {"kids": 3, "home": 2, "money": 1}, "note": "private"}
        return {"areas": {"kids": "Leila did 80% of the 5 pickups", "home": "Shared the home nicely",
                          "money": "Karim covered the money"},
                "balance": "a_more", "headline": "Week 42!",
                "messages": {"Leila": "You did a lot, be proud.", "Karim": "Say thank you to Leila."}}
    ai.ask_json = fake
    with __import__("app.db", fromlist=["connect"]).connect() as conn:
        rows = conn.execute("SELECT * FROM partners ORDER BY id LIMIT 2").fetchall()
    board = agents.weekly_board(rows[0], rows[1], [])
    ok(not _re.search(r"\d|%", json.dumps(board["areas"]) + board["headline"]), "numbers from the AI are removed")
    def leaky(prompt, image=None, mime=None):
        if "PRIVATE agent" in prompt:
            return {"load": {"kids": 3, "home": 2, "money": 1}, "note": "x"}
        return {"areas": {"kids": "She went part-time after our second child", "home": "ok", "money": "ok"},
                "balance": "a_more", "headline": "",
                "messages": {"Leila": "hi", "Karim": "hi"}}
    ai.ask_json = leaky
    board = agents.weekly_board(rows[0], rows[1], [])
    ok("part-time" not in json.dumps(board), "a private answer written by the AI is caught and replaced")
    ai.ask_json, ai.mode = real, ai_mode


def _ryan_key(emily_key):
    from app import db as _db
    with _db.connect() as conn:
        return conn.execute("SELECT key FROM partners WHERE couple_id=(SELECT couple_id FROM partners WHERE key=?)"
                            " AND key!=?", (emily_key, emily_key)).fetchone()[0]


def slice4(c):
    import re as _re
    from app import sample
    from app import db as _db
    d = c.post("/api/demo", json={"role": "woman", "name": "Emily", "colour": "pink",
                                  "material": {"job": ""}, "immaterial": {}, "extra_note": ""}).json()
    leila = {"X-Partner-Key": d["key"]}
    h = c.get("/api/home", headers=leila).json()
    ok(h["sample"] and h["partner"]["name"] == "Ryan", "sample: you join as the wife, Ryan is already there")
    wk = c.get("/api/week", headers=leila).json()["week"]
    ok(wk and wk["areas"]["kids"], "sample couple has a full week on the board")
    ok(len(h["entries"]) > 10, "the home shows the whole week day by day, not just today")
    ok(2 <= len(wk["ideas"]) <= 3, "Emily gets two or three ideas from her private agent")
    ryan_week = c.get("/api/week", headers={"X-Partner-Key": _ryan_key(d["key"])}).json()["week"]
    ok(any("calendar" in i["detail"].lower() for i in ryan_week["ideas"]),
       "Ryan's agent suggests keeping the family calendar, since Emily handles the kids")
    ok(wk["ideas"] != ryan_week["ideas"], "each partner gets their own ideas")
    ok(len(h["story"]) >= 5 and all(not _re.search(r"\d|%", w["story"]) for w in h["story"]),
       "'Your story' tells past weeks in words, never numbers")
    ok(any(w["leader"] for w in h["story"]), "the story shows weeks where one partner carried more")
    ok(len(h["nudges"]) == 1 and "thank" in h["nudges"][0]["text"].lower(), "the wife has one kind nudge from an earlier chat, not the chat itself")
    ok(set(wk["lean"]) == {"kids", "home", "money"} and wk["lean"]["kids"]["toward"] == h["me"]["id"],
       "the kids seesaw tips toward the wife, who did the pickups")
    with _db.connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM entries e JOIN partners p ON p.id=e.partner_id WHERE p.key=?",
                         (d["key"],)).fetchone()[0]
        first = conn.execute("SELECT MIN(e.created_at) FROM entries e JOIN partners p ON p.id=e.partner_id"
                             " WHERE p.couple_id=(SELECT couple_id FROM partners WHERE key=?)", (d["key"],)).fetchone()[0]
        karim_key = conn.execute("SELECT key FROM partners WHERE name='Ryan' AND couple_id="
                                 "(SELECT couple_id FROM partners WHERE key=?)", (d["key"],)).fetchone()[0]
    from datetime import datetime as _dt, timezone as _tz
    ok(n > 40 and (_dt.now(_tz.utc) - _dt.fromisoformat(first)).days >= 50, "sample has about two months of history")
    karim = {"X-Partner-Key": karim_key}
    m = c.post("/api/demo", json={"role": "man", "name": "Sam", "colour": "pink",
                                  "material": {}, "immaterial": {}, "extra_note": ""}).json()
    hm = c.get("/api/home", headers={"X-Partner-Key": m["key"]}).json()
    ok(hm["partner"]["name"] == "Emily" and hm["partner"]["colour"] != "pink", "as the husband, Emily is your partner in another colour")
    ok(c.get("/sample").status_code == 200 and c.get("/conflict").status_code == 200, "sample and conflict pages load")

    r = c.post("/api/conflicts", json={"question": "I'm tired of always doing the dishes!"}, headers=leila)
    ok(r.status_code == 200 and "Ryan" in r.json()["reply"], "dishes complaint -> reply says Ryan will get a suggestion")
    ok("every time" in r.json()["reply"] and r.json()["nudged"], "reply points to the pattern and a nudge is sent")
    mine = c.get("/api/conflicts", headers=leila).json()["conflicts"]
    ok([m["question"] for m in mine][-1].startswith("I'm tired") and mine[0]["created_at"] < mine[-1]["created_at"],
       "Emily's chat is in order, oldest first, ending with her new message")
    his = c.get("/api/conflicts", headers=karim).json()["conflicts"]
    ok(all("tired" not in m["question"] and "dentist" not in m["question"] for m in his),
       "Ryan never sees Emily's private chat")
    hh = c.get("/api/home", headers=karim).json()
    ok(any("dishes" in n["text"] for n in hh["nudges"]) and not any("tired" in n["text"].lower() for n in hh["nudges"]),
       "Ryan gets a kind nudge about the dishes, without Emily's words")
    ok(not any("dentist" in n["text"] and "booking" not in n["text"] for n in c.get("/api/home", headers=leila).json()["nudges"]),
       "Emily doesn't receive the nudges meant for Ryan")
    reply = r.json()["reply"].lower()
    ok(not any(p in reply for p in ["part-time", "guilty", "3:30", "afford"]),
       "reply reveals no private answers")
    solo_key = c.post("/api/couples", json=WIFE).json()["key"]
    ok(c.post("/api/conflicts", json={"question": "dishes"}, headers={"X-Partner-Key": solo_key}).status_code == 409,
       "no conflict mediation before the partner joins")


if __name__ == "__main__":
    with TestClient(app) as c:
        slice1(c)
        slice2(c)
        slice3(c)
        slice4(c)
    print("All checks passed.")
