---
doc: spec
status: approved
---

# 51/51 — Technical Spec

## How This Works, In Plain Language
51/51 is one small **Python web app**. It has three parts:

1. **The pages** (HTML, CSS, a little JavaScript) — what the couple sees in the browser: welcome, private questions, home screen, conflict screen.
2. **The server** (Python, FastAPI) — receives what the pages send ("she logged a pickup", "here is a receipt photo"), saves it, and asks the AI for help. It is also the guard: it never sends one partner's private answers to the other.
3. **The AI** (Google Gemini, free tier) — sorts entries into kids/home/money, reads receipt photos, writes the weekly words and messages, and answers the conflict button.

Everything is saved in one small database file (**SQLite** — think of it as a spreadsheet the program reads and writes).

The **private agents** live on the server: each partner's agent is the AI given *only that partner's private answers*. Each agent writes a private note about its person's week ("she works part-time by choice, did all pickups — that's a lot for her"). A neutral **mediator** reads both notes plus the shared logs and writes what the couple sees. The private notes never leave the server.

No logins or passwords: when you join, the browser remembers who you are (a small saved key). Two partners = two browsers (or one normal + one private window when recording the demo).

Why this shape: it's the stack you already used (Python, Render), one server, one free AI, one database file — nothing extra to break.

## The Core Journey Through the System
PRD ref: `prd.md > The Core Journey`.

1. Partner 1 opens the site → **Welcome** page asks "first here, or have a partner's code?" → chooses first.
2. Answers private questions → page sends them to the server → server creates a **couple** with a short code (e.g. `MOON-42`) and a **partner** record holding the private answers → browser saves its partner key → page shows the code to share.
3. Partner 2 opens the site → enters the code → server links a second partner to that couple → Partner 2 answers their own questions.
4. Server compares obvious shared facts (number of kids, ages). If they differ → a **shared-fact question** shows on both home screens.
5. Daily: a partner types "picked up Sarah" or uploads a receipt photo → server saves it → AI sorts it into kids/home/money (and reads the photo) → it appears under **Today** in that partner's colour.
6. Home screen loads the **weekly board** → server runs both private agents + mediator on this week's entries → returns words per area and a different reality-check message for each partner (no numbers). The result is reused until a new entry is added.
7. Conflict button → partner writes why they're upset → server gives the mediator the question, this week's and recent logs, and both private agents' notes → neutral reply with a fix → saved and visible to both partners.

## Stack
- **Python 3.11+** — you know it.
- **FastAPI** — small Python web server. https://fastapi.tiangolo.com/
- **Uvicorn** — runs FastAPI. https://www.uvicorn.org/
- **SQLite** (built into Python, `sqlite3`) — the database file. https://docs.python.org/3/library/sqlite3.html
- **Plain HTML + CSS + JavaScript** — no frontend framework, no build step.
- **Google Gemini API, free tier**, via the `google-genai` Python SDK, model in the Flash family. https://ai.google.dev/gemini-api/docs
  - Free tier through Google AI Studio, no credit card (source: geotoolbox Gemini pricing, updated Oct 17 2026).
  - **To verify first in the build:** image input works on the free tier, and the current free quota shown in AI Studio.
  - In France (EEA), free-tier inputs are not used to train Google's models (same source).
- **Render free web service** for an optional live link — you've deployed there before. https://render.com/docs/free

Decision: recommended by Claude because the learner asked for zero cost and already uses Python, Claude and Render. Claude's API has no free tier, so Gemini replaces it. Learner to confirm at review.

## Where It Runs and How Someone Tries It
- Local: `pip install -r requirements.txt`, put `GEMINI_API_KEY=...` in `.env`, run `uvicorn app.main:app --reload`, open `http://localhost:8000`.
- Demo recording: one normal browser window (Partner 1) + one private window (Partner 2), side by side.
- `python scripts/seed_demo.py` fills a **sample** demo couple with a week of entries (clearly labelled sample data) so the board and conflict button have something to work with on camera.
- Optional live link on Render (free). Note: Render's free disk is temporary — the database can reset when the service sleeps or redeploys. Fine for a demo; the seed script refills it.
- Submission still needs the demo video + public GitHub repo; the live link is a bonus.

## Look and Feel
From `prd.md > Look and Feel`:
- Warm, playful, friendly; for ordinary spouses, never technical.
- Each partner picks a cheerful colour at onboarding (pink, blue, orange, green); everything they log shows in their colour.
- Rounded cards, soft shadows, generous spacing, light background; one friendly rounded font (e.g. Nunito from Google Fonts).
- The balance and messages are words only — no numbers, percentages or charts with values.
- Big, obvious conflict button at the top in a calm (not alarming) colour.
- Copy tone: kind, short, a little playful; appreciation, never blame.

## Components

### Welcome and Onboarding Pages
`static/index.html`, `static/onboarding.html`. First question (first partner vs have a code), private questions (material + immaterial + "anything else"), colour pick, then shows the partner code or the "joined" confirmation. Wrong code → friendly message, try again.
PRD ref: `prd.md > Private Onboarding`, `prd.md > States and Boundaries`.

### Home Page
`static/home.html`. Conflict button at the top; Today (both partners' entries, coloured); Add (text box + photo upload); This Week board in words; reality-check message; shared-fact question if needed; "waiting for your partner" / "log your first thing" empty states.
PRD ref: `prd.md > Daily Logging`, `prd.md > Weekly Board and Reality Check`, `prd.md > Shared-Fact Check`.

### Conflict Page
`static/conflict.html`. Write why you're upset → see the neutral reply; list of past exchanges visible to both partners.
PRD ref: `prd.md > Conflict Button`.

### Server API
`app/main.py`. JSON endpoints:
- `POST /api/couples` — first partner's answers → creates couple + partner, returns partner key and code.
- `POST /api/join` — code + second partner's answers → links partner 2, returns partner key (404 + friendly message if the code is wrong).
- `GET /api/home` — today's entries, weekly board, my message, shared-fact question (only *my* message; never the other partner's private data).
- `POST /api/entries` — text or photo → saved + sorted by AI.
- `POST /api/conflicts`, `GET /api/conflicts` — ask / list.
Every request identifies the partner by the saved key header.
PRD ref: `prd.md > Private Agents` (privacy guard).

### Private Agents and Mediator
`app/agents.py`. Builds each partner's agent prompt from *their own* answers only. `agent_note(partner, week_entries)` → private note (server-only). `mediator_board(notes, entries)` → words per area + one message per partner. `mediator_conflict(question, entries, notes)` → neutral reply + fix. Rules in every prompt: never reveal private answers, never judge by gender, notice patterns from logs, appreciation not blame, no numbers on the board.
PRD ref: `prd.md > Private Agents`, `prd.md > Weekly Board and Reality Check`, `prd.md > Conflict Button`.

### AI Client
`app/ai.py`. Thin wrapper over Gemini: `classify_text(text)`, `read_receipt(image_bytes)` → `{summary, area}`, `generate(prompt)`. Asks for JSON output for structured results. Catches errors and quota limits.

### No-Numbers Guard
In `app/agents.py`: if board or reality-check text contains digits or "%", ask the AI to rewrite once; if still present, strip the number phrases.
PRD ref: `prd.md > Weekly Board and Reality Check` (no numbers anywhere).

### Database
`app/db.py`. Creates tables on startup, simple helper functions.

## Data Model
SQLite file `data/5151.db`:
- **couples** — id, code, created_at.
- **partners** — id, couple_id, key (secret, saved in that browser), name, colour, kids_count, kids_ages, material_answers (JSON), immaterial_answers (JSON), extra_note. *Private fields never returned to the other partner.*
- **entries** — id, couple_id, partner_id, created_at, kind (text/photo), text, area (kids/home/money/unsorted), summary.
- **board_cache** — couple_id, week_start, board JSON, my_message per partner, entry_count (recompute when entries change).
- **conflicts** — id, couple_id, partner_id, question, reply, created_at.

Week = Monday 00:00 to Sunday 23:59 (PRD assumption). Photos are not stored — only the AI's summary of them.
When a partner leaves and comes back, the browser's saved key brings them straight to Home.

## File Structure
```
build-with-ai-basics/
├── app/
│   ├── main.py        # FastAPI app: API endpoints + serves the pages
│   ├── db.py          # SQLite setup and helpers
│   ├── ai.py          # Gemini client: classify, read receipt, generate
│   └── agents.py      # private agents, mediator, no-numbers guard
├── static/
│   ├── index.html     # welcome: first partner or have a code
│   ├── onboarding.html# private questions, colour, code
│   ├── home.html      # today, add, weekly board, message, conflict button
│   ├── conflict.html  # conflict Q&A
│   ├── style.css      # warm, playful look
│   └── app.js         # shared browser logic (saved key, calls to the API)
├── scripts/
│   └── seed_demo.py   # sample demo couple + a week of entries
├── data/              # SQLite file (gitignored)
├── requirements.txt
├── .env.example       # GEMINI_API_KEY= (no secret)
├── render.yaml        # optional Render deploy
├── README.md
└── devpost/           # scope, prd, spec, checklist
```

## External Services and Dependencies
- **Google Gemini API** — key from Google AI Studio (free, no card), stored in `.env` as `GEMINI_API_KEY`, never committed. Calls via `google-genai`: `client.models.generate_content(model=..., contents=[text and/or image])`, asking for JSON responses where structured. Free quota: check in AI Studio. Docs: https://ai.google.dev/gemini-api/docs
- **Render** (optional) — free web service, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, env var `GEMINI_API_KEY`.

## Important Failure Modes
- **Gemini error or free quota hit** → the entry is still saved as "unsorted" with a gentle note; the board shows the last saved version or "try again in a minute".
- **Unreadable photo** → "I couldn't read this photo — can you describe it in a few words?" and a text box.
- **Numbers sneak into the board** → no-numbers guard rewrites or strips them.

## What Was Simplified and Why
- **Saved browser key + partner code** instead of accounts and passwords — shows two separate partners without building login. Real accounts would need passwords, sessions and recovery.
- **Board computed when the home page opens** instead of background jobs — same result, nothing running on a timer.
- **Photos summarised, not stored** — no file storage needed, and less private data kept.
- **Sample demo couple** via a seed script, labelled as sample data — the kernel (private agents, words, conflict replies) still runs live on the AI.

## Decisions and Open Issues
- **Stack (Python, FastAPI, SQLite, plain HTML, Render)** — recommended by Claude from the learner's past tools; awaiting her confirmation.
- **Gemini free tier instead of Claude** — learner wants to pay nothing; Claude's API has no free tier. Tradeoff: free-tier quota limits and a different model than she's used to.
- **Verify early in the build:** image input on Gemini's free tier; current free quota. If images aren't free, photos fall back to "describe it in text" and the rest still works.
- **Useful unknown:** none raised by the learner yet. Natural candidate during the build: how a "private agent" is really just the same AI given different private context, and how the server keeps it private.
- **Carried from PRD:** week runs Monday–Sunday (assumption); demo couple names decided during the build or for the video.
