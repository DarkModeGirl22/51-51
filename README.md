# 51/51

*Not 50/50: both partners give a little more than half.*

51/51 helps married couples share kids, home and money fairly, without the fights. Each partner gets a private AI agent that knows their real situation. Together, the agents reveal effort the other partner can't see and describe the week **in words, never numbers**.

Built for Devpost's *Build With AI: Basics*. Planning documents: [`devpost/scope.md`](devpost/scope.md), [`devpost/prd.md`](devpost/prd.md), [`devpost/spec.md`](devpost/spec.md).

## Run it locally

```bash
pip install -r requirements.txt
cp .env.example .env        # add your free Gemini key from https://aistudio.google.com/apikey
uvicorn app.main:app --reload
```

Open http://localhost:8000. Use a normal window for one partner and a private window for the other.

Without a key, the app runs with a clearly labelled **practice AI** (simple rules instead of Gemini), useful for trying the screens.

## Checks

```bash
python tests/check_app.py
```
