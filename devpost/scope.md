---
doc: scope
status: approved
---

# 51/51

*Not 50/50 — both partners give a little more than half.*

An app for married couples where each partner has a private AI agent that knows their real situation, so the couple can see who carries what — kids, home, money — and share the load fairly without fighting about it.

## The Unique Kernel
Each partner's AI agent knows the full picture of their person — work hours, part-time sacrifices, pregnancy, what's impossible for them — and uses that context to judge what is fair for *this* couple. It reveals effort the other partner can't see ("he can't do pickups, he works until 8 — but he covered the groceries"), instead of counting tasks with a generic 50/50 rule. There is no fixed formula: the AI *considers* what is a lot and what is not a lot for each person, given their situation. Messages are about appreciation, never blame. The balance is shown in words, never numbers ("you did a lot", "he carried a bit more", with a large, varied vocabulary) — no percentages on screen. This is one of the app's signatures — the goal is to keep the couple away from fighting, not hand them a number as an excuse to start one.

## Who It's For
A married couple, with or without kids, both busy, not technical. Example: she works part-time so she can handle more at home; he works until 8 pm, so school pickups are impossible for him, but he pays more of the bills. Each one feels they do more (Pew 2026: 63% of working mothers say they do more parenting and chores; fathers are much more likely to say it's equal). Today they keep it in their heads — and it turns into silent resentment or arguments.

## The Core Loop
Throughout the week, each partner logs what they do: "picked up the kids", "paid for school", or a photo of a grocery receipt or bank payment. The AI sorts each entry into an area (kids, home, money) and weighs it with each person's context. The home screen updates with how much each partner carried per area, described in words, not numbers. Then each partner gets a short, kind message that changes in wording but keeps the same meaning.

## Inspiration & Identity
- Inspiration: Shoulder (private agents that negotiate family fairness) — https://github.com/ahammadshawki8/Shoulder. This project must stay clearly different: Shoulder *hides* private reasons; this app *reveals invisible effort*.
- Feel: warm, cute, fun — for ordinary parents and spouses, not engineers. Balance shown in playful words instead of numbers, with a distinct colour for each partner.

## Why This Matters to the Learner
She wants to help people with something hard to talk about. The idea grew from "conversations that are not comfortable" between people who share a life.

## What "Working" Looks Like
A demo couple with two private profiles (each with their own context). Both partners log a few things during the week, including a receipt photo that the AI reads. The home screen describes, in words, how much each partner carried in kids, home and money. Then:
- If they're roughly equal: both get a message that the week was balanced and they both contributed — "that's super good".
- If one did more: that partner is told they did a lot this week and should be proud; the other is told their partner did a lot, must be tired, deserves a thank-you, and could carry more in the coming days.

## The POC Boundary
- One demo couple, two partners, each with a private context profile.
- Logging by text, and by photo of a receipt / payment (AI reads the amount and what it's for).
- AI sorts each log into kids / home / money and weighs it using each person's context.
- Home screen: how much each partner carried per area, described in varied, playful words — no numbers.
- Kind, varied messages to each partner based on the balance.

## Later
- Real-time push notifications and reminders.
- Real accounts and login, mobile app.
- Logging by voice.
- History over weeks and months.

## Explicitly Cut
- Connecting to real bank accounts — far too big for a 2–4 hour proof of concept; photos of receipts cover the idea.
- A single overall "who is worse" score — it would feel like blame.
- Percentages or numbers on screen — the balance is described in words only (the AI may calculate internally, but users never see numbers).
