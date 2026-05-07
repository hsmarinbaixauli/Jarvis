"""Pre-LLM goodbye phrase detection.

Detects farewell utterances before sending them to Claude, allowing
Jarvis to exit cleanly without an LLM round-trip.
"""

from __future__ import annotations

import re
import unicodedata

# Single-word phrases that trigger goodbye ONLY when the entire utterance is
# just that word (optionally + "jarvis").  This prevents "para mañana" or
# "cierra la persiana" from being misdetected.
_SINGLE_WORD: frozenset[str] = frozenset({
    "adios",
    "bye",
    "goodbye",
    "chao",
    "chau",
    "para",
    "cierra",
})

# Multi-word phrases — unambiguous enough to match anywhere in the utterance.
_MULTI_WORD: frozenset[str] = frozenset({
    "hasta luego",
    "hasta pronto",
    "hasta manana",
})


def _normalize(text: str) -> str:
    """Lowercase, strip combining accents and punctuation, collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    no_punct = re.sub(r"[^\w\s]", "", no_accents)
    return " ".join(no_punct.split())


def is_goodbye(text: str) -> bool:
    """Return True if *text* is a goodbye utterance.

    Args:
        text: Raw transcribed user speech.

    Returns:
        True when the utterance is an unambiguous farewell.
    """
    if not text or not text.strip():
        return False

    norm = _normalize(text)

    # Remove 'jarvis' tokens to get the semantic content.
    tokens = [t for t in norm.split() if t != "jarvis"]

    if len(tokens) == 1 and tokens[0] in _SINGLE_WORD:
        return True

    return any(phrase in norm for phrase in _MULTI_WORD)
