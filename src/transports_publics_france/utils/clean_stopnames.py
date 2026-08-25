"""
Utils for cleaning stop names in French GTFS datasets
- slugify(text)
- reduce_stop_name(name)
"""

import re
import unicodedata

from transports_publics_france.config import ABBREV_MAP, STOPWORDS_FR

def slugify(text: str) -> str:
    """Transliterate, lowercase, deletes punctuation/numbers."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[\d\W_]+", " ", text)
    return text.strip()


def reduce_stop_name(name: str) -> str:
    """Reduces a stop name by removing stopwords and replacing abbreviations."""
    tokens = slugify(name).split()
    tokens = [ABBREV_MAP.get(t, t) for t in tokens if t not in STOPWORDS_FR and len(t) > 1]
    return " ".join(tokens) if tokens else name.lower()
