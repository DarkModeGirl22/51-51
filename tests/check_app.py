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


if __name__ == "__main__":
    with TestClient(app) as c:
        slice1(c)
        slice2(c)
    print("All checks passed.")
