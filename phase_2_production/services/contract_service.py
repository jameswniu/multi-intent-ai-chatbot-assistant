"""
Secure SQL microservice using LLM for natural-language to SQL translation.
"""

import os
import sqlite3
from openai import OpenAI
from phase1_pilot.guardrails.sql_validator import validate_sql

class ContractService:
    def __init__(self, db_path="phase2_production/data/contracts.db"):
        self.db_path = db_path
        self.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def handle_contract(self, query: str) -> str:
        prompt = f"Translate this question into a SQL query for the 'contracts' table:\n{query}"
        completion = self.llm.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": prompt}],
        )
        sql = completion.choices[0].message.content.strip()
        validate_sql(sql)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()

        return {"query": sql, "results": rows}
