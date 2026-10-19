"""51/51 server: saves everything, talks to the AI, and guards each partner's privacy."""
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import agents, ai, db

STATIC = Path(__file__).resolve().parent.parent / "static"
COLOURS = ["pink", "blue", "orange", "green"]
CODE_WORDS = ["MOON", "SUN", "STAR", "TEA", "HONEY", "MAPLE", "OLIVE", "PEACH", "CLOUD", "LEMON"]

app = FastAPI(title="51/51")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.on_event("startup")
def startup() -> None:
    db.init_db()


# ---------- pages ----------
for route, page in {"/": "index.html", "/onboarding": "onboarding.html",
                    "/home": "home.html", "/conflict": "conflict.html", "/enter": "enter.html", "/sample": "sample.html"}.items():
    def _page(page=page):
        return FileResponse(STATIC / page)
    app.add_api_route(route, _page, include_in_schema=False)


# ---------- helpers ----------
class Answers(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    colour: str
    material: dict = {}
    immaterial: dict = {}
    extra_note: str = Field(default="", max_length=1500)
    kids_count: int | None = Field(default=None, ge=0, le=20)
    kids_ages: str = Field(default="", max_length=80)

    @field_validator("name")
    @classmethod
    def name_is_a_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v or not re.fullmatch(r"[^\W\d_]+(?:[ '’-][^\W\d_]+)*", v):
            raise ValueError("Please use just your first name, with letters only.")
        return v

    @field_validator("material", "immaterial")
    @classmethod
    def answers_are_short_text(cls, v: dict) -> dict:
        clean = {str(k)[:40]: str(val)[:1000] for k, val in list(v.items())[:12] if val is not None}
        return clean


class JoinBody(Answers):
    code: str


def _new_code(conn) -> str:
    while True:
        code = f"{secrets.choice(CODE_WORDS)}-{secrets.randbelow(90) + 10}"
        if not conn.execute("SELECT 1 FROM couples WHERE code=?", (code,)).fetchone():
            return code


def _insert_partner(conn, couple_id: int, a: Answers) -> str:
    key = secrets.token_urlsafe(24)
    conn.execute(
        """INSERT INTO partners (couple_id, key, name, colour, kids_count, kids_ages,
                                 material, immaterial, extra_note)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (couple_id, key, a.name.strip(), a.colour, a.kids_count, a.kids_ages.strip(),
         json.dumps(a.material), json.dumps(a.immaterial), a.extra_note.strip()),
    )
    return key


def me_from_key(conn, key: str | None):
    if not key:
        raise HTTPException(401, "Please join 51/51 first.")
    row = conn.execute("SELECT * FROM partners WHERE key=?", (key,)).fetchone()
    if not row:
        raise HTTPException(401, "We don't recognise this browser. Please join again.")
    return row


def other_partner(conn, me):
    return conn.execute("SELECT * FROM partners WHERE couple_id=? AND id!=?",
                        (me["couple_id"], me["id"])).fetchone()


def public(p) -> dict | None:
    """The ONLY partner fields ever shared with the other partner."""
    if p is None:
        return None
    return {"id": p["id"], "name": p["name"], "colour": p["colour"]}


def find_couple(conn, code: str):
    return conn.execute("SELECT * FROM couples WHERE code=?",
                        (code.strip().upper(),)).fetchone()


NO_CODE = "We couldn't find that code. Check it with your partner and try again."


# ---------- API ----------
@app.post("/api/couples")
def create_couple(a: Answers):
    if a.colour not in COLOURS:
        raise HTTPException(422, "Please pick one of the colours.")
    with db.connect() as conn:
        code = _new_code(conn)
        couple_id = conn.execute("INSERT INTO couples (code) VALUES (?)", (code,)).lastrowid
        key = _insert_partner(conn, couple_id, a)
    return {"key": key, "code": code}


@app.get("/api/couples/{code}")
def check_code(code: str):
    with db.connect() as conn:
        couple = find_couple(conn, code)
        if not couple:
            raise HTTPException(404, NO_CODE)
        partners = conn.execute("SELECT name, colour FROM partners WHERE couple_id=?",
                                (couple["id"],)).fetchall()
    if len(partners) >= 2:
        raise HTTPException(409, "This couple already has two partners.")
    return {"code": couple["code"], "partner_name": partners[0]["name"],
            "taken_colours": [p["colour"] for p in partners]}


@app.post("/api/join")
def join(body: JoinBody):
    with db.connect() as conn:
        couple = find_couple(conn, body.code)
        if not couple:
            raise HTTPException(404, NO_CODE)
        partners = conn.execute("SELECT colour FROM partners WHERE couple_id=?",
                                (couple["id"],)).fetchall()
        if len(partners) >= 2:
            raise HTTPException(409, "This couple already has two partners.")
        if body.colour not in COLOURS or body.colour in [p["colour"] for p in partners]:
            raise HTTPException(422, "Please pick a colour your partner hasn't taken.")
        key = _insert_partner(conn, couple["id"], body)
    return {"key": key, "code": couple["code"]}


def week_start_utc(tz_offset_min: int, now: datetime | None = None) -> datetime:
    """Monday 00:00 in the partner's local time, expressed in UTC.
    tz_offset_min is JavaScript's getTimezoneOffset() (Paris summer = -120)."""
    now = now or datetime.now(timezone.utc)
    local = now - timedelta(minutes=tz_offset_min)
    monday = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return monday + timedelta(minutes=tz_offset_min)


def week_entries(conn, couple_id: int, start: datetime):
    rows = conn.execute(
        "SELECT * FROM entries WHERE couple_id=? AND created_at>=? ORDER BY created_at DESC",
        (couple_id, start.isoformat())).fetchall()
    return [{"id": r["id"], "partner_id": r["partner_id"], "created_at": r["created_at"],
             "kind": r["kind"], "area": r["area"], "summary": r["summary"]} for r in rows]


def shared_fact_question(me, partner) -> str | None:
    """Obvious shared facts must match (number and ages of children). Salary etc. are never compared."""
    if partner is None or me["kids_count"] is None or partner["kids_count"] is None:
        return None
    if me["kids_count"] != partner["kids_count"]:
        return (f"Quick check: you said {me['kids_count']} children, but {partner['name']} said "
                f"{partner['kids_count']}. Which is right? Fix it together below.")
    ages = lambda p: sorted(re.findall(r"\d+", p["kids_ages"] or ""))
    if ages(me) and ages(partner) and ages(me) != ages(partner):
        return (f"Quick check: you and {partner['name']} gave different ages for your children "
                f"(you: {me['kids_ages']}; {partner['name']}: {partner['kids_ages']}). Which is right?")
    return None


def get_board(conn, me, partner, cache_key: str, entries) -> dict | None:
    if partner is None or not entries:
        return None
    a, b = sorted([me, partner], key=lambda p: p["id"])
    fingerprint = f"{len(entries)}:{max(e['id'] for e in entries)}:{a['kids_count']}:{b['kids_count']}"
    row = conn.execute("SELECT * FROM board_cache WHERE couple_id=? AND week_start=?",
                       (me["couple_id"], cache_key)).fetchone()
    if row and row["fingerprint"] == fingerprint:
        board = json.loads(row["data"])
    else:
        try:
            board = agents.weekly_board(a, b, entries)
        except ai.AIError:
            if row:
                board = json.loads(row["data"])
                board["stale"] = True
                return board
            return {"error": "The AI is resting for a minute. Try again shortly."}
        board["messages"] = {str(k): v for k, v in board["messages"].items()}
        conn.execute("INSERT OR REPLACE INTO board_cache (couple_id, week_start, fingerprint, data) VALUES (?,?,?,?)",
                     (me["couple_id"], cache_key, fingerprint, json.dumps(board)))
    return board


WEEKS_AGO = ["Last week", "Two weeks ago", "Three weeks ago", "Four weeks ago", "Five weeks ago",
             "Six weeks ago", "Seven weeks ago", "Eight weeks ago"]


def week_window(couple, tz_offset: int):
    """(start, cache_key) of 'this week'. Sample couples always use the last seven days."""
    if couple["is_sample"]:
        return datetime.now(timezone.utc) - timedelta(days=7), "rolling"
    start = week_start_utc(tz_offset)
    return start, start.isoformat()


def story(conn, me, partner, start: datetime) -> list:
    """Past weeks, newest first, each told in words from the logs (no AI call)."""
    if partner is None:
        return []
    a, b = sorted([me, partner], key=lambda p: p["id"])
    out = []
    for i, label in enumerate(WEEKS_AGO):
        lo, hi = start - timedelta(days=7 * (i + 1)), start - timedelta(days=7 * i)
        rows = conn.execute("SELECT * FROM entries WHERE couple_id=? AND created_at>=? AND created_at<?",
                            (me["couple_id"], lo.isoformat(), hi.isoformat())).fetchall()
        if not rows:
            continue
        w = agents.week_story(a, b, [dict(r) for r in rows], seed=f"{me['couple_id']}-{lo.date()}")
        out.append({"label": label, **w})
    return out


@app.get("/api/home")
def home(x_partner_key: str | None = Header(default=None),
         x_tz_offset: int = Header(default=0)):
    """Everything that's instant. The AI's view of the week comes from /api/week."""
    with db.connect() as conn:
        me = me_from_key(conn, x_partner_key)
        partner = other_partner(conn, me)
        couple = conn.execute("SELECT * FROM couples WHERE id=?", (me["couple_id"],)).fetchone()
        start, _ = week_window(couple, x_tz_offset)
        entries = week_entries(conn, me["couple_id"], start)
        past = story(conn, me, partner, start)
        nudges = conn.execute(
            "SELECT nudge, created_at FROM conflicts WHERE couple_id=? AND partner_id!=? AND nudge IS NOT NULL"
            " ORDER BY created_at DESC LIMIT 3", (me["couple_id"], me["id"])).fetchall()
    return {"me": public(me), "partner": public(partner), "code": couple["code"],
            "sample": bool(couple["is_sample"]), "entries": entries, "ai_mode": ai.mode(),
            "fact_question": shared_fact_question(me, partner), "story": past,
            # suggestions that came from the OTHER partner's private chat; the complaint itself never leaves it
            "nudges": [{"text": n["nudge"], "created_at": n["created_at"]} for n in nudges],
            "my_kids": {"count": me["kids_count"], "ages": me["kids_ages"]}}


@app.get("/api/week")
def week(x_partner_key: str | None = Header(default=None),
         x_tz_offset: int = Header(default=0)):
    """The private agents + mediator's view of this week (may take a few seconds with the real AI)."""
    with db.connect() as conn:
        me = me_from_key(conn, x_partner_key)
        partner = other_partner(conn, me)
        couple = conn.execute("SELECT * FROM couples WHERE id=?", (me["couple_id"],)).fetchone()
        start, cache_key = week_window(couple, x_tz_offset)
        entries = week_entries(conn, me["couple_id"], start)
        board = get_board(conn, me, partner, cache_key, entries)
    if board is None:
        return {"week": None}
    if "error" in board:
        return {"week": {"error": board["error"]}}
    # each partner only ever receives THEIR OWN message
    return {"week": {"areas": board["areas"], "headline": board.get("headline", ""),
                     "message": board["messages"].get(str(me["id"]), ""),
                     "lean": board.get("lean", {}), "stale": board.get("stale", False),
                     # ideas from MY private agent, only for me
                     "ideas": board.get("ideas", {}).get(str(me["id"]), [])}}


class KidsFix(BaseModel):
    kids_count: int = Field(ge=0, le=20)
    kids_ages: str = ""


@app.post("/api/me/kids")
def fix_kids(body: KidsFix, x_partner_key: str | None = Header(default=None)):
    with db.connect() as conn:
        me = me_from_key(conn, x_partner_key)
        conn.execute("UPDATE partners SET kids_count=?, kids_ages=? WHERE id=?",
                     (body.kids_count, body.kids_ages.strip(), me["id"]))
    return {"ok": True}


MAX_PHOTO = 8 * 1024 * 1024


@app.post("/api/entries")
async def add_entry(text: str = Form(default=""), photo: UploadFile | None = File(default=None),
                    x_partner_key: str | None = Header(default=None)):
    text = text.strip()[:500]
    image = await photo.read() if photo is not None else b""
    if not text and not image:
        raise HTTPException(422, "Write what you did, or add a photo.")
    if len(image) > MAX_PHOTO:
        raise HTTPException(413, "That photo is too big. Try a smaller one.")
    if image and not (photo.content_type or "").startswith("image/"):
        raise HTTPException(422, "That doesn't look like a photo. Try a picture of the receipt.")
    with db.connect() as conn:
        me = me_from_key(conn, x_partner_key)

    note = None
    if image:
        try:
            result = ai.read_receipt(image, photo.content_type or "image/jpeg")
        except ai.AIError:
            result = None
            note = "ai_down"
        if result is None:
            if text:  # the partner also wrote something: sort that instead
                image = b""
            else:
                raise HTTPException(422, "I couldn't read this photo. Can you describe it in a few words?")
        elif text:
            result["summary"] = f"{text} · {result['summary']}"
    if not image:
        try:
            result = ai.sort_text(text)
        except ai.AIError:
            result = {"area": "unsorted", "summary": text}
            note = "ai_down"

    created = datetime.now(timezone.utc).isoformat()
    with db.connect() as conn:
        entry_id = conn.execute(
            "INSERT INTO entries (couple_id, partner_id, created_at, kind, text, area, summary)"
            " VALUES (?,?,?,?,?,?,?)",
            (me["couple_id"], me["id"], created, "photo" if image else "text", text,
             result["area"], result["summary"])).lastrowid
    return {"id": entry_id, "area": result["area"], "summary": result["summary"],
            "created_at": created, "note": note}


@app.get("/api/ai-check")
def ai_check():
    return ai.check()


# ---------- conflict button ----------
class ConflictBody(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


def recent_entries(conn, couple_id: int, days: int = 28):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute("SELECT * FROM entries WHERE couple_id=? AND created_at>=? ORDER BY created_at",
                        (couple_id, since)).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/conflicts")
def ask_conflict(body: ConflictBody, x_partner_key: str | None = Header(default=None)):
    with db.connect() as conn:
        me = me_from_key(conn, x_partner_key)
        partner = other_partner(conn, me)
        if partner is None:
            raise HTTPException(409, "Your partner hasn't joined yet, so there's nobody to mediate with.")
        entries = recent_entries(conn, me["couple_id"])
        history = [(r["question"], r["reply"]) for r in conn.execute(
            "SELECT question, reply FROM conflicts WHERE partner_id=? ORDER BY created_at", (me["id"],))]
    try:
        answer = agents.conflict_reply(me, partner, body.question.strip(), entries, history)
    except ai.AIError:
        raise HTTPException(503, "The AI is resting for a minute. Take a breath and try again shortly.")
    created = datetime.now(timezone.utc).isoformat()
    with db.connect() as conn:
        cid = conn.execute("INSERT INTO conflicts (couple_id, partner_id, question, reply, nudge, created_at)"
                           " VALUES (?,?,?,?,?,?)",
                           (me["couple_id"], me["id"], body.question.strip(), answer["reply"],
                            answer["nudge"], created)).lastrowid
    return {"id": cid, "reply": answer["reply"], "created_at": created, "nudged": bool(answer["nudge"])}


@app.get("/api/conflicts")
def list_conflicts(x_partner_key: str | None = Header(default=None)):
    """Only MY private chat with the mediator, oldest first."""
    with db.connect() as conn:
        me = me_from_key(conn, x_partner_key)
        partner = other_partner(conn, me)
        rows = conn.execute("SELECT * FROM conflicts WHERE partner_id=? ORDER BY created_at",
                            (me["id"],)).fetchall()
    return {"me": public(me), "partner": public(partner),
            "conflicts": [{"id": r["id"], "question": r["question"], "reply": r["reply"],
                           "nudged": bool(r["nudge"]), "created_at": r["created_at"]} for r in rows]}


# ---------- sample couple (for trying the app and the demo video) ----------
class SampleBody(Answers):
    role: str  # "woman" or "man"


@app.post("/api/demo")
def create_demo(body: SampleBody):
    from .sample import LEILA, KARIM, create_sample_couple
    if body.role not in ("woman", "man") or body.colour not in COLOURS:
        raise HTTPException(422, "Please choose woman or man, and a colour.")
    preset = LEILA if body.role == "woman" else KARIM
    me = {"name": body.name.strip(), "colour": body.colour,
          "kids_count": body.kids_count if body.kids_count is not None else preset["kids_count"],
          "kids_ages": body.kids_ages.strip() or preset["kids_ages"],
          # anything left empty falls back to the sample character's answers
          "material": {**preset["material"], **{k: v for k, v in body.material.items() if v}},
          "immaterial": {**preset["immaterial"], **{k: v for k, v in body.immaterial.items() if v}},
          "extra_note": body.extra_note.strip() or preset["extra_note"]}
    with db.connect() as conn:
        return create_sample_couple(conn, _new_code(conn), me, body.role)
