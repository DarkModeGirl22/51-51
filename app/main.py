"""51/51 server: saves everything, talks to the AI, and guards each partner's privacy."""
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, db

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
                    "/home": "home.html"}.items():
    def _page(page=page):
        return FileResponse(STATIC / page)
    app.add_api_route(route, _page, include_in_schema=False)


# ---------- helpers ----------
class Answers(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    colour: str
    material: dict = {}
    immaterial: dict = {}
    extra_note: str = ""
    kids_count: int | None = None
    kids_ages: str = ""


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


@app.get("/api/home")
def home(x_partner_key: str | None = Header(default=None),
         x_tz_offset: int = Header(default=0)):
    with db.connect() as conn:
        me = me_from_key(conn, x_partner_key)
        partner = other_partner(conn, me)
        code = conn.execute("SELECT code FROM couples WHERE id=?", (me["couple_id"],)).fetchone()["code"]
        entries = week_entries(conn, me["couple_id"], week_start_utc(x_tz_offset))
    return {"me": public(me), "partner": public(partner), "code": code,
            "entries": entries, "ai_mode": ai.mode()}


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
