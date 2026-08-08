# PII Test Project

Test bed for PII masking in an LLM chat flow: user messages get PII (names,
emails) detected and masked before hitting the model/tools, then unmasked
where needed for ground-truth checks.

## Contents

- `piiMask.py` — `PIIMasker`: detects PERSON/EMAIL_ADDRESS entities via
  Presidio + spaCy, masks them with reversible partial placeholders (e.g.
  `Priya Sharma` -> `P**** S******`), and can unmask them back server-side.
- `chat.py` — `EligibilityChatbot`, wraps the masking + tool-calling loop.
- `eligibility.py` — ground-truth eligibility check (age > 18 and
  `@gmail.com` email), exposed as a tool for the chatbot.
- `memory.py` — per-user conversation memory.
- `logs.py` — records masking events for inspection.
- `config.py` — app configuration.
- `server.py` — Flask app: serves `index.html` / `view.html` and exposes
  `/api/chat`, `/api/reset`, `/api/logs`.
- `index.html` / `view.html` — chat UI and masking-log viewer.

## Setup

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Run

```bash
python server.py
```

Then open `http://127.0.0.1:5000/` for the chat UI and `/view` for the
masking log.

## Quick test

```python
from piiMask import PIIMasker

masker = PIIMasker()
masked = masker.mask("Contact Priya Sharma at priya@example.com")
print(masked)                 # e.g. "Contact P**** S****** at p****@*******.***"
print(masker.unmask(masked))  # restores original values
```
