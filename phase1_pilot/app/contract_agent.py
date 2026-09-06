"""
ContractAgent answers a contract question with SQL that is selected, not written.

No model. The question's words are looked up in COLUMN_MAP and the matching
columns are read from one table. Nothing in the question can reach the SQL
text, so the validator underneath is a second lock on a door that is already
shut. It stays because Phase 2 swaps this map for a language model, and then
the validator is the only lock.
"""

import os
import re
import sqlite3

from phase1_pilot.guardrails.sql_validator import validate_sql

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

COLUMN_MAP = {
    "price": "price",
    "cost": "price",
    "expiry": "expiry_date",
    "renewal": "expiry_date",
    "module": "module",
    "customer": "customer_id",
    "contract": "customer_id",
}
DEFAULT_COLUMNS = ["customer_id", "module", "expiry_date", "price"]


class ContractAgent:
    def __init__(self, db_path=os.path.join(DATA, "mock_contracts.db"), seed_path=os.path.join(DATA, "mock_contracts.sql")):
        self.db_path = db_path
        if not os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            try:
                with open(seed_path, encoding="utf-8") as f:
                    conn.executescript(f.read())
            finally:
                conn.close()

    def _construct_sql(self, query: str) -> str:
        words = [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z]+", query.lower())]
        selected = list(dict.fromkeys(COLUMN_MAP[w] for w in words if w in COLUMN_MAP)) or list(DEFAULT_COLUMNS)
        sql = f"SELECT {', '.join(selected)} FROM contracts LIMIT 10"
        validate_sql(sql)
        return sql

    def answer(self, query: str) -> str:
        sql = self._construct_sql(query)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            header = [d[0] for d in cur.description]
        finally:
            conn.close()
        if not rows:
            return "No matching records found."
        result_text = [dict(zip(header, row)) for row in rows]
        return f"Query: {sql}\n\nResults:\n{result_text}"
