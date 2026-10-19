---
doc: prd
status: approved
---

# 51/51 — Product Requirements

*Not 50/50 — both partners give a little more than half.*
An app for married couples (with or without kids): each partner has a private AI agent that knows their real situation; together they show who carried what — kids, home, money — in words, never numbers, and help the couple settle conflicts without fighting each other.
Source: `scope.md > The Unique Kernel`, `scope.md > Who It's For`.

## The Core Journey
1. **Partner 1 opens 51/51 for the first time** and answers their private questions (see *Private Onboarding*).
2. Partner 1 gets a short **partner code** and gives it to Partner 2 (wife or husband — either can start).
3. **Partner 2 opens 51/51**, chooses "I have my partner's code", enters it — becoming Partner 1's partner — and answers their own private questions.
4. From each person's answers, the app builds **that person's private agent**: it knows their life, sets boundaries for them, defends them respectfully, and avoids arguments.
5. If an obvious shared fact doesn't match (she says 5 kids, he says 3), a question appears on the **shared board** for the couple to settle.
6. **Every day**, each partner opens the app and sees today's activity for both of them, and can add something new (text or photo).
7. The **weekly board** describes, in words, how much each partner carried in kids, home and money this week, plus a **reality-check message**.
8. **When one of them is upset**, they press the **conflict button** and talk it out in a **private chat** with the neutral mediator. If something should change, the other partner receives a **kind suggestion** in their notifications — never the complaint itself.

Source: `scope.md > The Core Loop`.

## Screens and Layout
- **Welcome**: first question — "Are you the first of you two here, or do you have your partner's code?"
- **Onboarding** (once per partner): private questions, then the partner code to share (Partner 1) or the joined confirmation (Partner 2).
- **Home (Today)** — the screen seen every day:
  - Top: the **conflict button**, always visible.
  - Today: what *she* did and what *he* did, each in their own colour.
  - An **Add** area: write a text entry or upload a photo (receipt, bank payment).
  - **This week** board: the balance per area (kids / home / money) in words.
  - A **reality-check message**.
- **Conflict ("Talk it out")**: a private chat between one partner and the mediator, oldest message first, with the message box at the bottom.
- **Notifications (bell)**: the personal weekly message and kind suggestions from 51/51.
- **Shared-fact check**: shown on the board only when the partners' obvious facts disagree.

## Look and Feel
- Warm, playful, friendly — made for ordinary spouses and parents, not engineers. Never technical.
- Each partner has their own distinct, cheerful colour (learner mentioned pink, blue, orange, green as the kind of contrasting colours she likes).
- The balance is **described in words**, never as numbers or percentages — playful, varied vocabulary.
- Easy on the eye; the learner delegated visual polish (spacing, shapes, typography) to the build, within this direction.

Source: `scope.md > Inspiration & Identity`.

## Features and Behavior

### Private Onboarding
Each partner, alone, answers two kinds of questions:
- **Material** (facts you can see and touch): how many people live in the home, how long they've been married, their job and working hours, who earns more, the kids and their ages.
- **Immaterial**: sacrifices made, how they feel, how they see the situation, what they want.
- A free box to **add anything else** so the agent understands them better.

- As a spouse, I want to tell my agent my real situation privately so it can defend me fairly without exposing me.
  - [ ] Onboarding shows both material and immaterial questions plus a free "anything else" box.
  - [ ] On first open, the app asks whether you're the first partner or have a partner's code.
  - [ ] After Partner 1 finishes, a partner code is shown; entering it links Partner 2 to Partner 1 and starts Partner 2's own onboarding.
  - [ ] A wrong code shows a friendly message and lets the person try again.
  - [ ] Partner 2 never sees Partner 1's answers, and vice versa.

### Private Agents
- Each partner's agent knows only its own person's answers and that person's logs-in-context.
- It **considers** what is a lot and what is not a lot for its person (e.g. "works until 8, so pickups are impossible"; "went part-time for the kids"; pregnancy). No fixed formula.
- Agents defend their person respectfully and never reveal private details (salary, feelings, sacrifices) to the other partner.
- Agents judge from logged facts and each person's context — **never from gender**.
  - [ ] Nothing shown on the shared board or in conflict replies quotes or reveals a partner's private answers.

### Shared-Fact Check
- Obvious material facts that both partners answer (number of kids, their ages) must match.
- If they differ, a question appears on the shared board (e.g. "One of you said 5 kids and the other 3 — which is right?").
  - [ ] Giving different numbers of kids during onboarding makes this question appear on the board.
  - [ ] Private facts (salary, who earns more) are never compared on the board.

### Daily Logging
- Either partner adds an entry by **text** ("picked up Sarah from school", "paid for school") or by **photo** (receipt, bank payment screenshot).
- For photos, the AI reads what was bought/paid and roughly how much.
- The AI sorts every entry into **kids**, **home** or **money**.
- Today shows both partners' entries, each in their colour.
  - [ ] A text entry appears under Today in the author's colour, tagged with the right area.
  - [ ] A receipt photo becomes an entry describing what was bought, tagged with the right area.

### Weekly Board and Reality Check
- The board covers **the current week** (not month).
- For each area, it describes in words how much each partner carried — no numbers, varied playful vocabulary.
- **Reality-check message**:
  - Roughly balanced → both are told the week was balanced and they both contributed — "that's super good".
  - One did more → that partner is told they did a lot and should be proud; the other is told their partner did a lot, must be tired, deserves a thank-you, and could carry more in the coming days.
  - Messages vary in wording but keep the same meaning.
  - [ ] The board shows no numbers or percentages anywhere.
  - [ ] After uneven logging, each partner sees a different message matching their side.

### Conflict Button
- Always visible at the top. The upset partner explains, in their own words, why they're upset.
- The AI replies **neutrally**, based on what both partners logged and their contexts. It does not declare "this person is guilty"; it proposes **a way to correct it**.
- The AI notices patterns from the logs by itself — e.g. they usually alternate the dishes, but lately she's done them every time — nobody has to type in a rule.
- The exchange is a private chat (message, reply, message, reply), not a report. Only the person who wrote it can see it.
- If something should change, the other partner gets a kind, practical suggestion in their notifications (e.g. "take the next dentist appointment from booking to finish; a shared calendar helps"). It never quotes or reveals the complaint.
- They talk *to the AI* instead of at each other.
  - [ ] With logs showing one partner doing the dishes repeatedly, a complaint about dishes gets a reply that points to that pattern and proposes a fix (e.g. the other partner takes the next turns).
  - [ ] The reply contains no blame words about a person's gender and reveals no private answers.
  - [ ] The other partner never sees the chat, only a kind suggestion that doesn't quote it.

## States and Boundaries
- **First use** — onboarding first; the home screen isn't available until the person finishes.
- **Waiting for partner** — Partner 1 can log entries while Partner 2 hasn't joined; the board says it's waiting for the partner.
- **Empty week** — no entries yet: the board invites them to log their first thing instead of judging.
- **Wrong partner code** — a friendly message; try again.
- **Unreadable photo** — the app says it couldn't read it and lets the person describe it in text.
- **Shared facts disagree** — the board shows the question until it's settled.
- **Privacy** — private answers and conflict chats stay with each person; only logs, the board and kind suggestions are shared.

## Product Decisions
- Words, never numbers — so the couple never gets a number as an excuse to start a fight.
- Weekly board, not monthly — short enough to correct things while they're fresh.
- Conflict button kept; audio logging dropped for now — the conflict button better proves the idea.
- Conflict chats are private to each partner; the other partner only gets a kind suggestion — decided after trying the first version, where both could read everything.
- Either spouse can start and invite the other.
- Private answers are never shared; obvious shared facts must match.
- The AI decides what counts as a lot ("considers"), not a fixed formula.
- Neutral judgement from logged facts and context, never gender.
- Visual polish delegated to the build, within the Look and Feel direction.

**Assumptions (not yet confirmed by the learner):**
- The week runs Monday to Sunday.
- Conflict replies may mention plain facts from the logs (e.g. "the last three times"), but never scores or percentages.

## What We're Building
Private onboarding for both partners, linked by a partner code; private agents built from answers; shared-fact check; daily logging by text and photo with AI sorting into kids/home/money; home screen with Today, Add, weekly board in words and reality-check message; conflict button with neutral AI replies visible to both.

## Deferred From the POC
- **Audio logging** — adds recording and speech-to-text; text and photos already prove the idea.
- **Real accounts, passwords, mobile app** — the partner code is enough to show two separate partners.
- **Push notifications / reminders** — the in-app messages show the idea.
- **History beyond the current week.**

## Possible Later Enhancements
- Voice notes as entries.
- Monthly and yearly "story of your effort".
- Agents suggesting a plan for next week.

## Non-Goals
- Connecting to real bank accounts — too big and sensitive for a proof of concept.
- Any number or overall score on screen — it would start fights.
- Therapy or relationship counselling — the AI helps share the load; it is not a therapist.
- Judging by gender.

## Open Questions
- Name/style of the demo couple and kids — can be decided during the build or for the video.
