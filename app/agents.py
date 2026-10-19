"""The private agents and the neutral mediator — the heart of 51/51.

Each partner's agent is the AI given ONLY that partner's private answers.
It writes a private note about how heavy the week was *for its person*.
The mediator reads both notes plus the shared logs and writes what the couple
sees: words (never numbers) and one kind message per partner.
Private answers and private notes never leave the server.
"""
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor

from . import ai

AREAS = ("kids", "home", "money")


# ---------- context ----------
def private_context(p) -> str:
    material = json.loads(p["material"] or "{}")
    immaterial = json.loads(p["immaterial"] or "{}")
    lines = [f"Name: {p['name']}",
             f"Children: {p['kids_count'] if p['kids_count'] is not None else 'not said'} ({p['kids_ages'] or 'ages not said'})"]
    labels = {"people_at_home": "People at home", "married_for": "Married for", "job": "Job",
              "working_hours": "Working hours", "who_earns_more": "Who earns more (me/partner/same)",
              "sacrifices": "What they gave up", "feelings": "How they feel about sharing",
              "how_partner_sees_it": "How they think their partner sees it", "wishes": "What they wish would change"}
    for k, label in labels.items():
        v = material.get(k) or immaterial.get(k)
        if v:
            lines.append(f"{label}: {v}")
    if p["extra_note"]:
        lines.append(f"Also: {p['extra_note']}")
    return "\n".join(lines)


def private_phrases(p) -> list[str]:
    """Free-text private answers, used to check nothing private leaks."""
    material = json.loads(p["material"] or "{}")
    immaterial = json.loads(p["immaterial"] or "{}")
    texts = [str(v) for v in list(material.values()) + list(immaterial.values()) if v] + [p["extra_note"] or ""]
    return [t.strip().lower() for t in texts if len(t.strip()) >= 12]


def leaks(text: str, partners) -> bool:
    """True if a run of 5+ words from any private answer appears in the text."""
    t = " ".join(re.findall(r"[\w']+", text.lower()))
    for p in partners:
        for phrase in private_phrases(p):
            words = re.findall(r"[\w']+", phrase)
            for i in range(len(words) - 4):
                if " ".join(words[i:i + 5]) in t:
                    return True
    return False


BRAND = "51/51"  # the app's name is the one number allowed on screen


def has_numbers(text: str) -> bool:
    return bool(re.search(r"\d|%|percent", text.replace(BRAND, ""), re.I))


def strip_numbers(text: str) -> str:
    parts = text.split(BRAND)
    parts = [re.sub(r"\b[\w-]*\d[\w-]*%?\b|%|percent", "", p, flags=re.I) for p in parts]
    text = BRAND.join(parts)
    return re.sub(r"\s{2,}", " ", text).replace(" ,", ",").replace(" .", ".").strip()


def log_lines(entries, names: dict) -> str:
    if not entries:
        return "(nothing logged)"
    return "\n".join(f"- {e['created_at'][:10]} · {names.get(e['partner_id'], '?')} · {e['area']} · {e['summary']}"
                     for e in sorted(entries, key=lambda e: e["created_at"]))


# ---------- vocabulary (used by the practice AI, and as style hints for Gemini) ----------
LEAD = ["carried most of", "held up most of", "took the lead on", "did the heavy lifting on", "was the rock for"]
HELP = ["chipped in on", "gave a hand with", "helped a little with", "showed up for", "added a bit to"]
EVEN = ["shared {area} side by side", "split {area} like a real team", "carried {area} together, nicely balanced",
        "were perfectly in step on {area}"]
QUIET = ["all quiet on {area} this week", "nothing logged for {area} yet", "{area} had a calm week"]
AREA_WORDS = {"kids": "the kids", "home": "the home", "money": "the money"}

BALANCED_MSG = [
    "This week was beautifully balanced. You both gave a little more than half, that's 51/51. Super good!",
    "You two were a real team this week. Nobody carried it alone. Be proud of each other.",
    "What a balanced week! You both showed up for kids, home and money. Keep it going.",
]
MORE_MSG = [
    "You carried a lot this week. Be proud of yourself, and let {other} take some weight off your shoulders.",
    "Wow, you did so much this week. That counts, and it's seen. Rest a little if you can.",
    "You were the engine of the house this week. Thank you, really.",
]
LESS_MSG = [
    "{other} did a lot this week. They must be tired. They deserve a big thank-you, and maybe you could carry more in the coming days.",
    "{other} carried a heavy week. A thank-you would mean a lot, and taking a few things off their plate even more.",
    "This week leaned on {other}. Say thank you, and see what you can pick up next.",
]


# ---------- private agent ----------
def agent_note(me, partner_name: str, entries, names: dict) -> dict:
    """Private, server-only. How heavy the week was FOR this person, per area (0-4)."""
    mine = [e for e in entries if e["partner_id"] == me["id"]]
    if ai.mode() == "practice":
        load = {a: min(4, sum(1 for e in mine if e["area"] == a)) for a in AREAS}
        return {"load": load, "note": f"Practice AI: counted {me['name']}'s entries."}
    prompt = f"""You are the PRIVATE agent of {me['name']}, who is married to {partner_name}.
You know your person's real situation (only you can see this):
{private_context(me)}

This week's household log for the couple:
{log_lines(entries, names)}

Consider what is a lot and what is not a lot FOR YOUR PERSON, given their situation
(working hours, part-time choices, pregnancy, sacrifices, what is impossible for them).
For example, paying most bills counts more for someone who earns less; a school run
counts for a lot when it means leaving work early. Defend your person respectfully and fairly.
Rate how much your person carried this week in each area from 0 (nothing) to 4 (carried it all),
and write a short private note explaining why (this note is never shown to anyone).
Then give your person two or three practical IDEAS for the coming days, only for them, based on the log and
their real situation. Concrete and doable, never preachy. For example, if their partner keeps handling the
kids' appointments and your person can't do pickups, suggest keeping the dates in a shared calendar;
if your person carried a lot, suggest asking for one specific thing. Each idea: a short title (max six
words) and one friendly sentence. Never mention anything private about {partner_name}.
Reply as JSON: {{"load": {{"kids": 0-4, "home": 0-4, "money": 0-4}}, "note": "...",
"ideas": [{{"title": "...", "detail": "..."}}]}}"""
    r = ai.ask_json(prompt)
    load = {a: max(0, min(4, int(r.get("load", {}).get(a, 0)))) for a in AREAS}
    ideas = []
    for i in r.get("ideas") or []:
        if isinstance(i, dict) and i.get("title") and i.get("detail"):
            ideas.append({"title": str(i["title"]).strip()[:60], "detail": str(i["detail"]).strip()[:240]})
    return {"load": load, "note": str(r.get("note", ""))[:800], "ideas": ideas[:3]}


# ---------- mediator: the weekly board ----------
def _practice_board(a, b, notes, rnd, entries=()) -> dict:
    areas = {}
    total_a = sum(notes[a["id"]]["load"].values())
    total_b = sum(notes[b["id"]]["load"].values())
    for area in AREAS:
        la, lb = notes[a["id"]]["load"][area], notes[b["id"]]["load"][area]
        if la == lb == 0:  # the agents saw nothing here; trust the logs instead
            la = min(4, sum(1 for e in entries if e["partner_id"] == a["id"] and e["area"] == area))
            lb = min(4, sum(1 for e in entries if e["partner_id"] == b["id"] and e["area"] == area))
        word = AREA_WORDS[area]
        if la == lb == 0:
            text = rnd.choice(QUIET).format(area=word).capitalize() + "."
        elif abs(la - lb) <= 1 and la and lb:
            text = f"{a['name']} and {b['name']} " + rnd.choice(EVEN).format(area=word) + "."
        else:
            lead, other = (a, b) if la > lb else (b, a)
            low = min(la, lb)
            tail = f", and {other['name']} {rnd.choice(HELP)} it" if low else ""
            text = f"{lead['name']} {rnd.choice(LEAD)} {word}{tail}."
        areas[area] = text
    if abs(total_a - total_b) <= 1:
        balance = "balanced"
    else:
        balance = "a_more" if total_a > total_b else "b_more"
    return {"areas": areas, "balance": balance, "headline": ""}


def _messages(a, b, balance: str, rnd) -> dict:
    if balance == "balanced":
        msg = rnd.choice(BALANCED_MSG)
        return {a["id"]: msg, b["id"]: msg}
    more, less = (a, b) if balance == "a_more" else (b, a)
    return {more["id"]: rnd.choice(MORE_MSG).format(other=less["name"]),
            less["id"]: rnd.choice(LESS_MSG).format(other=more["name"])}


def weekly_board(a, b, entries) -> dict:
    """Returns {"areas": {area: words}, "balance", "messages": {partner_id: text}, "headline"}."""
    names = {a["id"]: a["name"], b["id"]: b["name"]}
    rnd = random.Random()
    # the two private agents think at the same time, each knowing only its own person
    with ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(agent_note, a, b["name"], entries, names)
        fb = pool.submit(agent_note, b, a["name"], entries, names)
        notes = {a["id"]: fa.result(), b["id"]: fb.result()}

    if ai.mode() == "practice":
        board = _practice_board(a, b, notes, rnd)
        board["messages"] = _messages(a, b, board["balance"], rnd)
        board = _guard(board, a, b, notes, rnd, entries)
        board["lean"] = leans(a, b, notes, entries)
        board["ideas"] = ideas_for(a, b, notes, board["lean"])
        return board

    prompt = f"""You are the neutral mediator of 51/51, an app that helps a married couple share
kids, home and money fairly. 51/51 means both give a little more than half.
Two private agents each judged how much their own person carried this week, using private
context you cannot see. Their ratings (0-4) and private notes:
- {a['name']}'s agent: {json.dumps(notes[a['id']])}
- {b['name']}'s agent: {json.dumps(notes[b['id']])}

This week's shared log:
{log_lines(entries, names)}

Write what the couple sees:
1. For each area (kids, home, money): ONE warm, playful sentence describing who carried what,
   in words only. Vary your vocabulary (e.g. "carried most of", "chipped in on", "shared side by side").
   Reveal effort the other partner may not see (e.g. one does the pickups, the other covered the bills).
2. "balance": "balanced" if overall it was roughly fair given both situations, "a_more" if {a['name']}
   carried clearly more, "b_more" if {b['name']} carried clearly more. Judge from the agents'
   considered ratings, never from gender.
3. "messages": one short message for each partner (they only see their own):
   - balanced: tell them the week was balanced, they both contributed, that's super good.
   - for whoever carried more: they did a lot, they should be proud of themselves.
   - for the other: their partner did a lot, must be tired, deserves a thank-you, and they could carry more in the coming days.
   Kind, never blaming, warm and plain-spoken, no emojis.
STRICT RULES: no numbers, digits or percentages anywhere. Never mention or hint at anything
from the private notes that the other partner shouldn't know (salary, feelings, health, sacrifices);
talk only about what was logged and fair-sounding reasons.
Reply as JSON: {{"areas": {{"kids": "...", "home": "...", "money": "..."}}, "balance": "...",
"headline": "<optional short playful title for the week>", "messages": {{"{a['name']}": "...", "{b['name']}": "..."}}}}"""
    try:
        r = ai.ask_json(prompt)
        board = {"areas": {k: str(r["areas"][k]) for k in AREAS},
                 "balance": r.get("balance") if r.get("balance") in ("balanced", "a_more", "b_more") else "balanced",
                 "headline": str(r.get("headline", ""))[:80],
                 "messages": {a["id"]: str(r["messages"][a["name"]]), b["id"]: str(r["messages"][b["name"]])}}
    except (KeyError, TypeError, ValueError):
        board = _practice_board(a, b, notes, rnd, entries)
        board["messages"] = _messages(a, b, board["balance"], rnd)
    board = _guard(board, a, b, notes, rnd, entries)
    board["lean"] = leans(a, b, notes, entries)
    board["ideas"] = ideas_for(a, b, notes, board["lean"])
    return board


IDEAS_WHEN_PARTNER_CARRIES = {
    "kids": ("Keep the family calendar",
             "{other} is handling most of the kids' logistics. You could keep the dentist, school events and "
             "activities in a shared calendar, so they aren't the only one remembering."),
    "home": ("Take the next dishes",
             "{other} has carried most of the home lately. Pick two evenings this week and take the dishes "
             "after dinner."),
    "money": ("Say thank you",
              "{other} covered a lot of the money side this week. A simple thank-you tonight goes a long way."),
}
IDEAS_WHEN_I_CARRY = ("Ask for one thing",
                      "You carried most of {area} this week. Pick one task you'd like {other} to take next week "
                      "and ask for it, or tell the mediator what's bothering you.")
IDEA_SHARED = ("Keep it going", "You and {other} are sharing {area} well. Keep logging so it stays visible.")


def ideas_for(a, b, notes, lean) -> dict:
    """Two or three ideas per partner, written by their own private agent (rules as a fallback).
    An idea is checked so it never reveals anything private about the other partner."""
    out = {}
    for me, other in ((a, b), (b, a)):
        ideas = [i for i in notes[me["id"]].get("ideas", [])
                 if not leaks(i["title"] + " " + i["detail"], [other]) and "%" not in i["detail"]]
        if len(ideas) < 2:  # the agent didn't give enough: add rule-based ideas
            for area in sorted(AREAS, key=lambda x: -lean[x]["strength"]):
                l = lean[area]
                if l["toward"] == other["id"]:
                    t, d = IDEAS_WHEN_PARTNER_CARRIES[area]
                elif l["toward"] == me["id"]:
                    t, d = IDEAS_WHEN_I_CARRY
                else:
                    t, d = IDEA_SHARED
                idea = {"title": t, "detail": d.format(other=other["name"], area=AREA_WORDS[area])}
                if idea["title"] not in [i["title"] for i in ideas]:
                    ideas.append(idea)
                if len(ideas) >= 3:
                    break
        out[str(me["id"])] = ideas[:3]
    return out


def leans(a, b, notes, entries) -> dict:
    """Which way each area's seesaw tips, and how much (0 = level, 1 = a little, 2 = a lot).
    Shown only as a tilt, never as a number."""
    out = {}
    for area in AREAS:
        la, lb = notes[a["id"]]["load"][area], notes[b["id"]]["load"][area]
        if la == lb == 0:
            la = sum(1 for e in entries if e["partner_id"] == a["id"] and e["area"] == area)
            lb = sum(1 for e in entries if e["partner_id"] == b["id"] and e["area"] == area)
        diff = la - lb
        strength = 0 if abs(diff) <= 0 else (1 if abs(diff) <= 2 else 2)
        out[area] = {"toward": (a["id"] if diff > 0 else b["id"]) if strength else None, "strength": strength}
    return out


def _guard(board: dict, a, b, notes: dict, rnd, entries=()) -> dict:
    """No numbers, no private leaks — whatever the AI wrote.
    Anything unsafe is replaced by clean wording built from the agents' ratings."""
    safe = _practice_board(a, b, notes, rnd, entries)
    texts = list(board["areas"].values()) + list(board["messages"].values()) + [board.get("headline", "")]
    if leaks(" ".join(texts), [a, b]):
        board["areas"], board["headline"] = safe["areas"], ""
        board["messages"] = _messages(a, b, board["balance"], rnd)
    for k in AREAS:
        if has_numbers(board["areas"][k]) or not board["areas"][k].strip():
            board["areas"][k] = safe["areas"][k]
    templates = _messages(a, b, board["balance"], rnd)
    for k in board["messages"]:
        if has_numbers(board["messages"][k]) or not board["messages"][k].strip():
            board["messages"][k] = templates[k]
    if has_numbers(board.get("headline", "")):
        board["headline"] = ""
    return board


# ---------- mediator: the conflict button ----------
def conflict_reply(asker, other, question: str, entries, history=()) -> dict:
    """A PRIVATE chat between one partner and the mediator.
    Returns {"reply": for the asker only, "nudge": a kind suggestion for the other partner, or None}.
    The other partner never sees the complaint itself."""
    names = {asker["id"]: asker["name"], other["id"]: other["name"]}
    if ai.mode() == "practice":
        return _practice_conflict(asker, other, question, entries)
    past = "\n".join(f"{asker['name']}: {q}\nYou: {r}" for q, r in history[-6:]) or "(this is the start of the chat)"
    prompt = f"""You are the neutral mediator of 51/51 for a married couple, {asker['name']} and {other['name']}.
This is a PRIVATE chat with {asker['name']} only; {other['name']} will never see it.

Earlier in this chat:
{past}

{asker['name']} now writes:
"{question}"

Shared household log of the last few weeks (date · who · area · what):
{log_lines(entries, names)}

Private context (for YOUR understanding only, NEVER quote or reveal it):
{asker['name']}: {private_context(asker)}
{other['name']}: {private_context(other)}

1. "reply" (to {asker['name']}, calm and neutral):
- Acknowledge the feeling in a few words, then say what the log actually shows. Notice patterns by yourself
  (e.g. they used to take turns with the dishes; lately one person did it every time).
- If the log supports the complaint, say what you'll suggest to {other['name']}. If it doesn't, gently show
  the effort that may be invisible. If the log has nothing on the topic, say so and suggest logging it.
- If they quote numbers, take them seriously and check them against the log. You may mention simple
  counts from the log, never percentages, scores or "who is worse".
- Never declare anyone guilty, never judge by gender, never reveal private details of either partner.
- At most three short sentences (under seventy words). Warm, plain, no lists, no emojis.
2. "nudge" (shown to {other['name']} as a notification from 51/51), or null if nothing should change:
- One or two friendly sentences suggesting ONE concrete, practical thing {other['name']} could do
  (e.g. take the next dentist appointment from booking to finish; put school events in a shared calendar;
  take the next turns of dishes). Fair to {other['name']}'s situation.
- It must NOT reveal or quote what {asker['name']} said, and must not sound like a complaint was made.
  Write it as a helpful idea based on the week's log.
Reply as JSON: {{"reply": "...", "nudge": "..." or null}}"""
    try:
        r = ai.ask_json(prompt)
        reply = str(r["reply"]).strip()
        nudge = str(r.get("nudge") or "").strip() or None
    except (KeyError, TypeError):
        return _practice_conflict(asker, other, question, entries)
    if leaks(reply, [asker, other]) or (nudge and leaks(nudge, [asker, other])):
        return _practice_conflict(asker, other, question, entries)
    if nudge and _echoes(nudge, question):  # the nudge must never give the complaint away
        nudge = _practice_conflict(asker, other, question, entries)["nudge"]
    return {"reply": reply, "nudge": nudge}


def _echoes(text: str, source: str) -> bool:
    """True if a run of 5+ words from `source` appears in `text`."""
    t = " ".join(re.findall(r"[\w']+", text.lower()))
    words = re.findall(r"[\w']+", source.lower())
    return any(" ".join(words[i:i + 5]) in t for i in range(len(words) - 4))


TOPICS = {
    "dishes": ["dish", "dishes", "washing up"], "laundry": ["laundry", "washing", "clothes"],
    "cooking": ["cook", "dinner", "lunch", "meal"], "cleaning": ["clean", "vacuum", "hoover", "tidy"],
    "school runs": ["pick", "school", "drop"], "groceries": ["grocer", "shopping", "supermarket"],
    "bills": ["bill", "rent", "pay", "paid"], "homework": ["homework"], "bedtime": ["bed", "bath"],
}


def _practice_conflict(asker, other, question: str, entries) -> dict:
    q = question.lower()
    topic = next((t for t, words in TOPICS.items() if any(w in q for w in words)), None)
    if topic is None:
        return {"reply": f"I hear you, {asker['name']}. The log doesn't show enough about this yet. "
                         "If you both log it each time it's done, I can show you clearly who's been carrying it. "
                         "(Practice AI)",
                "nudge": None}
    words = TOPICS[topic]
    hits = [e for e in sorted(entries, key=lambda e: e["created_at"]) if any(w in e["summary"].lower() for w in words)]
    if not hits:
        return {"reply": f"I hear you, {asker['name']}. Nobody has logged {topic} lately, so I can't see who's been "
                         f"doing it. Could you both log {topic} from now on? (Practice AI)",
                "nudge": f"Small idea for this week: log {topic} each time it's done, so it stays visible. (Practice AI)"}
    recent = hits[-4:]
    doers = {e["partner_id"] for e in recent}
    name = {asker["id"]: asker["name"], other["id"]: other["name"]}
    if len(doers) == 1:
        doer = next(iter(doers))
        if doer == asker["id"]:
            return {"reply": f"Looking at the log, you've done {topic} every time lately. That's a lot to carry alone. "
                             f"I'll suggest to {other['name']} that the next turns of {topic} go to them. (Practice AI)",
                    "nudge": f"{asker['name']} has done {topic} every time lately. Could you take the next turns? "
                             "(Practice AI)"}
        return {"reply": f"Looking at the log, {name[doer]} has done {topic} every time lately, so it may feel "
                         f"different from where you stand. Maybe pick up the next turn of {topic} yourself. (Practice AI)",
                "nudge": None}
    return {"reply": f"The log shows you've both been doing {topic} lately, so it may feel heavier than it looks. "
                     f"Clear turns for {topic} this week could help. (Practice AI)",
            "nudge": f"Idea for this week: agree on clear turns for {topic} and log each one. (Practice AI)"}


# ---------- your story: past weeks, told in words (rules only, no AI call) ----------


def week_story(a, b, entries, seed: str) -> dict:
    """A one-line story of a past week from the logs alone (no AI, so it costs nothing)."""
    rnd = random.Random(seed)
    counts = {p["id"]: {area: min(4, sum(1 for e in entries if e["partner_id"] == p["id"] and e["area"] == area))
                        for area in AREAS} for p in (a, b)}
    notes = {p["id"]: {"load": counts[p["id"]]} for p in (a, b)}
    board = _practice_board(a, b, notes, rnd, entries)
    if board["balance"] == "balanced":
        busiest = max(AREAS, key=lambda area: counts[a["id"]][area] + counts[b["id"]][area])
    else:  # lead with the area that explains why one partner carried more
        lead, other_p = (a, b) if board["balance"] == "a_more" else (b, a)
        busiest = max(AREAS, key=lambda area: counts[lead["id"]][area] - counts[other_p["id"]][area])
    lines = [board["areas"][busiest]]
    other = [x for x in AREAS if x != busiest and "nothing logged" not in board["areas"][x].lower()
             and "quiet" not in board["areas"][x].lower() and "calm" not in board["areas"][x].lower()]
    if other:
        lines.append(board["areas"][rnd.choice(other)])
    leader = None if board["balance"] == "balanced" else (a if board["balance"] == "a_more" else b)
    return {"story": " ".join(lines), "balance": board["balance"],
            "leader": leader["id"] if leader else None,
            "lean": leans(a, b, notes, entries)}
