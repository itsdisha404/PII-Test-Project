# PII Masking Test Project

Test bed for `PIIMasker` (Presidio-based PII detection + reversible partial masking), split out from `itsdisha404/PII` for isolated testing.

## Contents

- `piiMask.py` — `PIIMasker` class: detects PERSON/EMAIL_ADDRESS entities via Presidio + spaCy, masks them with reversible partial placeholders (e.g. `Priya Sharma` -> `P**** S******`), and can unmask them back server-side.
- `requirements.txt` — dependencies.

## Setup

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Quick test

```python
from piiMask import PIIMasker

masker = PIIMasker()
masked = masker.mask("Contact Priya Sharma at priya@example.com")
print(masked)          # e.g. "Contact P**** S****** at p****@*******.***"
print(masker.unmask(masked))  # restores original values
```
