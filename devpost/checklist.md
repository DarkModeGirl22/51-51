---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast (learner asked to move quickly with no extra steps)

## Slices

- [x] **1. Two partners can join the same couple, privately**
  Becomes usable: Partner 1 opens the app, answers the private questions, picks a colour and gets a partner code; Partner 2 enters the code, answers their own questions and lands on the same (empty) home screen. A wrong code shows a friendly message. Neither partner can see the other's private answers.
  Why now: Everything else depends on two linked partners and on privacy being enforced by the server; bootstrapping (FastAPI, SQLite, pages, style) is included here.
  PRD ref: `prd.md > Private Onboarding`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Welcome and Onboarding Pages`, `spec.md > Server API`, `spec.md > Database`, `spec.md > Data Model`, `spec.md > Look and Feel`, `spec.md > File Structure`
  Build: Scaffold the project per the file structure; SQLite tables for couples and partners; endpoints to create a couple, join by code and read home; welcome and onboarding pages with material, immaterial and "anything else" questions plus colour pick; browser saves the partner key; empty home with "waiting for your partner" and "log your first thing" states.
  Verify (mechanical): Automated test script: create couple → code returned; join with wrong code → 404 friendly message; join with right code → linked; each partner's /api/home contains no private answers of the other; server starts and pages load with status 200.
  Learner check: In two windows, onboard as wife and husband with the code, and check the welcome and questions feel warm and simple.
  Commit: `Onboard two partners with a private profile and a partner code`

- [x] **2. Both partners log their day, and the AI sorts each entry**
  Becomes usable: Either partner adds a text entry or a receipt photo; it appears under Today in their colour, tagged kids, home or money. If the AI fails or can't read a photo, the entry is saved as unsorted or the app asks for a short description.
  Why now: Logging is the input for everything the agents do, and photo reading on Gemini's free tier is the biggest technical risk, so it comes before the kernel.
  PRD ref: `prd.md > Daily Logging`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > AI Client`, `spec.md > Server API`, `spec.md > Home Page`, `spec.md > Important Failure Modes`
  Build: Entries table; POST /api/entries for text and photo; AI client with Gemini (real key) and a clearly labelled practice-AI mode when no key is set; Today list and Add area on the home page; failure fallbacks.
  Verify (mechanical): Test script in practice-AI mode: text entry → saved with an area; photo → summary + area; simulated AI failure → saved as unsorted; both partners see both entries. `/api/ai-check` endpoint reports whether the real AI is reachable.
  Learner check: On the live Render link with your Gemini key, log "picked up Sarah from school" and upload a real receipt photo, and see both sorted correctly.
  Commit: `Log daily entries by text or photo and sort them with AI`

- [x] **3. The private agents describe the week in words (the kernel)**
  Becomes usable: The home screen shows This Week: for kids, home and money, words describing how much each partner carried, plus a different reality-check message for each partner (balanced → both praised; uneven → one praised, the other nudged to thank and carry more). No numbers anywhere. If shared facts disagree (5 kids vs 3), a question appears on the board. A sample demo couple can be loaded.
  Why now: This is 51/51's unique kernel; it needs logged entries (slice 2) and should be judged early, before the conflict button.
  PRD ref: `prd.md > Private Agents`, `prd.md > Weekly Board and Reality Check`, `prd.md > Shared-Fact Check`
  Spec ref: `spec.md > Private Agents and Mediator`, `spec.md > No-Numbers Guard`, `spec.md > Data Model`
  Build: Private agent notes built only from each partner's own answers; mediator writes per-area words and per-partner messages; board cache invalidated by new entries; no-numbers guard; shared-fact check; scripts/seed_demo.py with a labelled sample week.
  Verify (mechanical): Test script: seeded uneven week → board has no digits or "%", partners receive different messages; balanced week → both get the balanced message; mismatched kids count → question present; neither partner's response contains the other's private answers.
  Learner check: Open the demo couple on the live link and read the board and both messages — do they sound kind, fair and like 51/51?
  Commit: `Private agents describe the week in words, never numbers`

- [x] **4. The conflict button gives a neutral way to fix it**
  Becomes usable: From the top of home, a partner explains why they're upset; the AI answers neutrally from the logs and both contexts, points out patterns (e.g. she did the dishes every time lately), proposes a fix, and both partners can see the exchange.
  Why now: Builds on the agents and logs from slices 2–3; it's the second demo moment.
  PRD ref: `prd.md > Conflict Button`
  Spec ref: `spec.md > Conflict Page`, `spec.md > Private Agents and Mediator`, `spec.md > Server API`
  Build: Conflicts table; POST/GET /api/conflicts; mediator conflict prompt (neutral, no gender, no private details, propose a fix); conflict page; button on home.
  Verify (mechanical): Test script: seeded dishes pattern + complaint → reply saved and visible to both partners; reply contains no private answers of either partner.
  Learner check: Press the conflict button as the upset partner on the live link, complain about the dishes, and check the reply feels neutral and useful from both sides.
  Commit: `Add the conflict button with neutral AI replies`

## Hands-on Checkpoints

- [ ] Early usable behavior explored — moved into the final review at the learner's request ("finish it then I'll open it"); the real-Gemini and photo check now happens there
- [ ] Final kick-the-tires exploration and feedback completed

## Final Review

- [x] Trick tests added (`tests/check_tricks.py`, 36 checks) at the learner's request — fixed: "51/51" was stripped by the no-numbers guard; unsafe AI sentences now replaced with clean wording from the logs; names, sizes and photo types validated
- [x] Pitch README and MIT license added (rules require an open-source license)
- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence:
Route and stops:
Edit outcome:
Reflection:
Activity mode:

## Revisions

- Early hands-on checkpoint after slice 2 moved into the final review — the learner asked to see the finished app first; real Gemini and photo reading are checked on Render during the final review instead.
- Sample couple uses "the last seven days" instead of Monday–Sunday — on a Monday the calendar week is almost empty, so the demo wouldn't show a full board; real couples keep Monday–Sunday.
- Added a "Try the sample couple" button and `/api/demo` instead of only `scripts/seed_demo.py` — Render's free plan has no shell to run scripts, and the database resets when the service sleeps.
- Slices 3 and 4 were built in one pass (they share the mediator), committed as two commits.

- Sample couple reworked at the learner's request — the visitor chooses wife or husband, answers three quick pages of three questions (pre-filled, editable), and joins an invented partner with about two months of logs; real couples keep the two original buttons.
- Home page reworked after the learner's first look on Render ("so empty"): the page now appears instantly and the AI's view loads separately (/api/week), the two private agents run in parallel, and the sample home shows the whole week day by day, 'Your story' (past weeks in words), earlier talks with the mediator, and a seesaw per area that tips toward whoever carried more, without numbers.
- Visual redesign after the learner's review: two columns on desktop (logging and day by day on the left; this week, your story and talks on the right), the personal message moved into a notification bell, a calmer palette (fog grey, navy ink, evergreen actions; plum, harbor blue, amber and sage for partners), line icons instead of emojis, a serif voice for what the agents say, and American names for the sample couple (Emily and Ryan).
