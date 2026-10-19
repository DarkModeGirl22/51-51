"""The AI behind 51/51.

With GEMINI_API_KEY set, every call goes to Google Gemini (free tier).
Without it, a clearly labelled *practice AI* answers with simple rules, so the
screens can be tried and tested without a key.
"""
import json
import os
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass

AREAS = ("kids", "home", "money")
MODELS = [m for m in [os.environ.get("GEMINI_MODEL"), "gemini-flash-latest", "gemini-2.5-flash"] if m]


class AIError(Exception):
    """The AI could not answer (no network, quota reached, bad reply...)."""


def mode() -> str:
    return "gemini" if os.environ.get("GEMINI_API_KEY") else "practice"


_client = None


def _gemini():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def ask_json(prompt: str, image: bytes | None = None, mime: str = "image/jpeg") -> dict:
    """Send a prompt (and optionally an image) to Gemini and get JSON back."""
    from google.genai import types

    contents: list = [prompt]
    if image is not None:
        contents.append(types.Part.from_bytes(data=image, mime_type=mime))
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7)
    last = None
    for model in MODELS:
        try:
            resp = _gemini().models.generate_content(model=model, contents=contents, config=config)
            return json.loads(resp.text)
        except Exception as e:  # try the next model name, then give up
            last = e
            if "not found" not in str(e).lower() and "404" not in str(e):
                break
    raise AIError(str(last)[:300])


# ---------- sorting entries ----------
SORT_RULES = """You sort one household entry for a married couple's app.
Areas:
- kids: anything for the children (school runs, homework, doctor, bath, bedtime, activities, buying things for the kids).
- home: running the house (cooking, dishes, cleaning, laundry, groceries done in person, repairs, errands).
- money: paying for things (bills, rent, school fees, insurance, a receipt or bank payment).
Reply as JSON: {"area": "kids" | "home" | "money", "summary": "<short, friendly description, max 12 words>"}"""

KIDS_WORDS = r"\b(pick(ed)?\s*up|school|kid|kids|child|children|son|daughter|homework|bath|bedtime|nursery|daycare|doctor|baby|nappy|diaper)\b"
MONEY_WORDS = r"(\bpaid\b|\bpay\b|\bbill|\brent\b|\binsurance|\bfees?\b|€|\$|£|\binvoice|\bbank\b)"


def _practice_sort(text: str) -> dict:
    t = text.lower()
    if re.search(MONEY_WORDS, t):
        area = "money"
    elif re.search(KIDS_WORDS, t):
        area = "kids"
    else:
        area = "home"
    return {"area": area, "summary": text.strip()[:120]}


def _clean(result: dict, fallback_summary: str) -> dict:
    area = str(result.get("area", "")).lower()
    if area not in AREAS:
        raise AIError("AI gave an unknown area")
    summary = str(result.get("summary") or fallback_summary).strip()[:160]
    return {"area": area, "summary": summary}


def sort_text(text: str) -> dict:
    if mode() == "practice":
        return _practice_sort(text)
    return _clean(ask_json(f"{SORT_RULES}\n\nEntry: {text}"), text)


def read_receipt(image: bytes, mime: str) -> dict | None:
    """Returns {"area", "summary"} or None if the photo can't be read."""
    if mode() == "practice":
        return {"area": "money", "summary": "Paid a receipt (practice AI can't read photos)"}
    prompt = (SORT_RULES + "\n\nThis is a photo of a receipt, bill or bank payment. "
              "Say what was bought or paid and roughly how much, in the summary. "
              'If you cannot read it, reply {"readable": false}. '
              'Otherwise add "readable": true.')
    result = ask_json(prompt, image=image, mime=mime)
    if not result.get("readable", True):
        return None
    return _clean(result, "Receipt")


def check() -> dict:
    if mode() == "practice":
        return {"mode": "practice", "ok": True,
                "detail": "No GEMINI_API_KEY set: using the practice AI (simple rules)."}
    try:
        r = ask_json('Reply with JSON {"ok": true}')
        text_ok = bool(r.get("ok"))
    except AIError as e:
        return {"mode": "gemini", "ok": False, "photos": False, "detail": f"Gemini didn't answer: {e}"}
    try:
        r = ask_json('This is a tiny solid-colour test image. Reply JSON {"seen": true, "colour": "<its colour>"}',
                     image=_TEST_PNG, mime="image/png")
        photos = bool(r.get("seen"))
    except AIError as e:
        return {"mode": "gemini", "ok": text_ok, "photos": False,
                "detail": f"Text works, but photos failed: {e}"}
    return {"mode": "gemini", "ok": text_ok, "photos": photos,
            "detail": "Gemini answered, and can read photos." if photos else "Gemini answered."}


def _tiny_png() -> bytes:
    import struct, zlib
    w = h = 16
    raw = b"".join(b"\x00" + b"\xec\x6f\x9b" * w for _ in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


_TEST_PNG = _tiny_png()
