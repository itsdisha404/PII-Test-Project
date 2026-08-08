from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Pattern, Tuple

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider


def build_analyzer(model_name: str = "en_core_web_sm") -> AnalyzerEngine:
    """Build a Presidio AnalyzerEngine pinned to a specific spaCy model.

    Presidio defaults to en_core_web_lg, which is a large download. This
    defaults to the small model instead; pass model_name="en_core_web_lg"
    or "en_core_web_trf" for meaningfully better PERSON detection in
    production (after `python -m spacy download en_core_web_lg`).
    """
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": model_name}],
    }
    provider = NlpEngineProvider(nlp_configuration=nlp_config)
    nlp_engine = provider.create_engine()
    return AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])


@dataclass
class PIIMasker:
    """Detects PII with Presidio Analyzer and masks it with reversible
    placeholders. Keeps a local mapping so real values can be restored
    later for trusted server-side logic (never sent back to the LLM)."""

    entities: List[str] = field(default_factory=lambda: ["PERSON", "EMAIL_ADDRESS"])
    language: str = "en"
    score_threshold: float = 0.5
    spacy_model: str = "en_core_web_sm"
    # en_core_web_sm's NER is small and occasionally misfires on capitalized
    # field labels (e.g. tagging the word "Email" itself as a PERSON). This
    # denylist is a pragmatic guard for that specific failure mode -- switch
    # to a bigger spacy_model for better accuracy instead of relying on it.
    label_denylist: List[str] = field(
        default_factory=lambda: ["name", "age", "email", "user", "details"]
    )

    def __post_init__(self) -> None:
        self.analyzer = build_analyzer(self.spacy_model)
        self.mapping: Dict[str, str] = {}  # placeholder -> original value
        # (pattern, original value), in the order entities were masked. The
        # model doesn't always echo a placeholder back with the exact same
        # run-length of '*' it was given (e.g. "A***" -> "A****"), so unmask
        # matches on shape (letter + any run of '*') rather than exact text.
        self._patterns: List[Tuple[Pattern[str], str]] = []

    @staticmethod
    def _partial_mask(value: str) -> str:
        """Reveal only each word's first character, masking the rest with
        '*' (e.g. "Priya Sharma" -> "P**** S******")."""

        def mask_word(word: str) -> str:
            return word if len(word) <= 1 else word[0] + "*" * (len(word) - 1)

        return " ".join(mask_word(word) for word in value.split(" "))

    @staticmethod
    def _placeholder_pattern(placeholder: str) -> Pattern[str]:
        """Build a regex matching this placeholder even if a run of '*' in
        it comes back a different length (models sometimes rewrite these
        when restating them)."""
        parts = []
        for ch in placeholder:
            if ch == "*":
                if not parts or parts[-1] != r"\*+":
                    parts.append(r"\*+")
            else:
                parts.append(re.escape(ch))
        pattern = "".join(parts)
        if placeholder[:1].isalnum():
            pattern = r"\b" + pattern
        return re.compile(pattern)

    def mask(self, text: str) -> str:
        """Analyze `text` and replace every detected PII span with a
        partially masked placeholder, right-to-left so earlier character
        offsets stay valid."""
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities,
            language=self.language,
            score_threshold=self.score_threshold,
        )
        results = [
            r
            for r in results
            if text[r.start : r.end].strip().lower() not in self.label_denylist
        ]
        results = sorted(results, key=lambda r: r.start, reverse=True)

        masked = text
        for r in results:
            original_value = text[r.start : r.end]
            placeholder = self._partial_mask(original_value)
            self.mapping[placeholder] = original_value
            self._patterns.append((self._placeholder_pattern(placeholder), original_value))
            masked = masked[: r.start] + placeholder + masked[r.end :]
        return masked

    def unmask(self, value: str) -> str:
        """Replace any known placeholders inside `value` with their real PII.
        Used only inside trusted server-side code, never echoed to the model
        in raw form. Matches on placeholder shape, not exact text, so it
        still works if the model rewrites the number of '*' when repeating
        a placeholder back. Longer placeholders are applied first so a
        shorter one (e.g. a name) can't shadow part of a longer one (e.g.
        an email) that happens to share a leading letter."""
        for pattern, original in sorted(
            self._patterns, key=lambda p: len(p[0].pattern), reverse=True
        ):
            value = pattern.sub(original, value)
        return value