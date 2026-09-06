"""
IntentClassifier decides which agent a question belongs to.

Two vocabularies, no model. The contract vocabulary is the column map's own
keys plus "billing", so any word that can select a column also routes to the
agent that owns that column, and the two can never disagree. Matching is on
whole words with a trailing "s" folded, which is the entire stemmer.

Confidence is the margin between the two vocabularies as a share of all hits.
A tie, or no hit at all, is "unknown", and the router hands that question back
to the user rather than guessing.
"""

import re
from typing import Tuple

from phase1_pilot.app.contract_agent import COLUMN_MAP

CONTRACT_KEYWORDS = sorted(set(COLUMN_MAP) | {"billing"})
KNOWLEDGE_KEYWORDS = ["how", "guide", "use", "setup", "instructions", "help"]


def tokens(text: str):
    """Lowercase words, plurals folded by dropping one trailing s."""
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z]+", text.lower())}


class IntentClassifier:
    def __init__(self):
        self.contract_keywords = tokens(" ".join(CONTRACT_KEYWORDS))
        self.knowledge_keywords = tokens(" ".join(KNOWLEDGE_KEYWORDS))

    def classify(self, query: str) -> Tuple[str, float]:
        words = tokens(query)
        contract_score = len(words & self.contract_keywords)
        knowledge_score = len(words & self.knowledge_keywords)
        total = contract_score + knowledge_score
        if total == 0 or contract_score == knowledge_score:
            return "unknown", 0.0
        intent = "contract" if contract_score > knowledge_score else "knowledge"
        return intent, abs(contract_score - knowledge_score) / total
