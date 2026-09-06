"""
Ensures a statement is safe to execute: one SELECT of the four named columns from
the one table, and nothing else.

A shape allowlist first, then a denylist. The statement has to be a SELECT of the
known columns FROM contracts, with at most simple predicates on those columns, an
ORDER BY and a LIMIT. No UNION, no subquery, no function call, no second table, no
terminator. On top of that, no mutating keyword anywhere, matched on whole words.

The first version of this file knew keywords and not tables, and an adversarial
review showed it passing a UNION against sqlite_master and a load_extension call.
The shape is the fix, and both are pinned as refused in the tests.
"""

import re

COLUMNS = ("customer_id", "module", "expiry_date", "price")
DENIED = ["DROP", "DELETE", "ALTER", "UPDATE", "INSERT", "REPLACE", "CREATE", "ATTACH", "DETACH", "PRAGMA", "VACUUM"]

_COL = r"(?:customer_id|module|expiry_date|price)"
_LIT = r"(?:'[^';()]*'|-?\d+(?:\.\d+)?|\?)"
_PRED = rf"{_COL}\s*(?:=|!=|<>|<=|>=|<|>|LIKE)\s*{_LIT}"
_WHERE = rf"(?:\s+WHERE\s+{_PRED}(?:\s+(?:AND|OR)\s+{_PRED})*)?"
_ORDER = rf"(?:\s+ORDER\s+BY\s+{_COL}(?:\s+(?:ASC|DESC))?)?"
_LIMIT = r"(?:\s+LIMIT\s+\d+)?"
SHAPE = re.compile(rf"^SELECT\s+(?:\*|{_COL}(?:\s*,\s*{_COL})*)\s+FROM\s+contracts{_WHERE}{_ORDER}{_LIMIT}$", re.IGNORECASE)


def validate_sql(query: str) -> bool:
    text = query.strip()
    if not re.match(r"SELECT\b", text, re.IGNORECASE):
        raise ValueError("Unsafe SQL detected: only a SELECT may run.")
    if ";" in text:
        raise ValueError("Unsafe SQL detected: statement terminator found.")
    words = set(re.findall(r"[A-Za-z_]+", text.upper()))
    hit = [w for w in DENIED if w in words]
    if hit:
        raise ValueError(f"Unsafe SQL detected: {', '.join(hit)}.")
    if not SHAPE.match(text):
        raise ValueError("Unsafe SQL detected: only SELECT of the known columns FROM contracts, with simple predicates, may run.")
    return True
