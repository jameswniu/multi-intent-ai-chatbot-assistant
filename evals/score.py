#!/usr/bin/env python3
"""Run the Phase 1 pilot against the labelled cases and print every number the page carries.

The README claims a routing count, a SQL validation count, an injection count and a
redaction count. This file is those claims, executable. It loads the same router the
API serves, runs every case in evals/cases.jsonl through it, and counts.

    python3 evals/score.py            run, print the report, write evals/report.json
    python3 evals/score.py --check    run, then fail if evals/report.json or the README
                                      badges disagree with what was just measured

Nothing here is tuned to the classifier. The labels say what a person asking the
question wanted, and a miss is printed next to the hits. Latency is printed but never
compared, because a machine-timing number differs on every runner.

Exit 0 on a clean run or a clean check, 1 on a disagreement, 2 if the cases cannot be read.
"""
import json
import os
import re
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from phase1_pilot.app.router import QueryRouter  # noqa: E402
from phase1_pilot.guardrails.pii_filter import remove_pii  # noqa: E402
from phase1_pilot.guardrails.sql_validator import validate_sql  # noqa: E402

CASES = os.path.join(ROOT, "evals", "cases.jsonl")
REPORT = os.path.join(ROOT, "evals", "report.json")
README = os.path.join(ROOT, "README.md")

# What the README's badges claim, as (regex over the README, report keys they must equal).
BADGE_CLAIMS = [
    (r"routes-(\d+)_of_(\d+)_labelled_questions", ("routed_correctly", "route_cases")),
    (r"SQL_validated-(\d+)_of_(\d+)", ("sql_validated", "sql_generated")),
    (r"literal_probes_refused-(\d+)_of_(\d+)", ("literal_refused", "literal_probes")),
    (r"PII-(\d+)_of_(\d+)_named_formats", ("pii_named_redacted", "pii_named")),
]


def load_cases():
    try:
        with open(CASES, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except (OSError, ValueError) as e:
        print(f"cannot read {CASES}: {e}")
        sys.exit(2)


def section_of(paragraph):
    return paragraph.strip().splitlines()[0].strip() if paragraph.strip() else ""


def run(cases):
    router = QueryRouter()
    r = {"route_cases": 0, "routed_correctly": 0, "asked_back_wrongly": 0, "by_intent": {},
         "retrieval_queries": 0, "retrieval_top1_hits": 0,
         "sql_generated": 0, "sql_validated": 0, "contract_routed": 0, "columns_complete": 0,
         "literal_probes": 0, "literal_refused": 0,
         "paraphrases": 0, "paraphrases_refused": 0, "paraphrases_reached_generator": 0, "paraphrases_changed_sql": 0,
         "pii_named": 0, "pii_named_redacted": 0, "pii_other": 0, "pii_other_redacted": 0,
         "misses": []}
    timings = []

    for c in cases:
        if c["kind"] == "route":
            r["route_cases"] += 1
            bucket = r["by_intent"].setdefault(c["intent"], {"n": 0, "correct": 0})
            bucket["n"] += 1
            t0 = time.perf_counter()
            got, _ = router.handle_query(c["q"])
            timings.append(time.perf_counter() - t0)
            if got == c["intent"]:
                r["routed_correctly"] += 1
                bucket["correct"] += 1
            else:
                if got == "unknown":
                    r["asked_back_wrongly"] += 1
                r["misses"].append({"q": c["q"], "wanted": c["intent"], "got": got})
            if c["intent"] == "knowledge":
                r["retrieval_queries"] += 1
                top = router.knowledge_agent._search(c["q"], top_k=1)[0]
                if section_of(top) == c["section"]:
                    r["retrieval_top1_hits"] += 1
                else:
                    r["misses"].append({"q": c["q"], "wanted_section": c["section"], "got_section": section_of(top)})
            if c["intent"] == "contract":
                r["sql_generated"] += 1
                sql = router.contract_agent._construct_sql(c["q"])
                if validate_sql(sql):
                    r["sql_validated"] += 1
                # The columns a person needs to read the answer off the table: the value asked
                # for, plus the column that identifies the row when the question names one.
                if got == "contract":
                    r["contract_routed"] += 1
                    picked = set(re.findall(r"[a-z_]+", sql.split("FROM")[0].replace("SELECT", "")))
                    if set(c["columns"]) <= picked:
                        r["columns_complete"] += 1
                    else:
                        r["misses"].append({"q": c["q"], "wanted_columns": sorted(c["columns"]), "picked": sorted(picked)})

        elif c["kind"] == "injection":
            got, _ = router.handle_query(c["q"])
            if c["form"] == "literal":
                r["literal_probes"] += 1
                if got == "unsafe":
                    r["literal_refused"] += 1
                else:
                    r["misses"].append({"q": c["q"], "wanted": "unsafe", "got": got})
            else:
                r["paraphrases"] += 1
                if got == "unsafe":
                    r["paraphrases_refused"] += 1
                elif got == "contract":
                    r["paraphrases_reached_generator"] += 1
                    sql = router.contract_agent._construct_sql(c["q"])
                    columns = set(re.findall(r"[a-z_]+", sql.split("FROM")[0].replace("SELECT", "")))
                    if not sql.startswith("SELECT ") or not columns <= {"customer_id", "module", "expiry_date", "price"}:
                        r["paraphrases_changed_sql"] += 1
                        r["misses"].append({"q": c["q"], "sql": sql})

        elif c["kind"] == "pii":
            redacted = remove_pii(c["text"]) != c["text"]
            if c["expect"] == "redacted":
                r["pii_named"] += 1
                if redacted:
                    r["pii_named_redacted"] += 1
                else:
                    r["misses"].append({"text": c["text"], "wanted": "redacted", "got": "passed"})
            else:
                r["pii_other"] += 1
                if redacted:
                    r["pii_other_redacted"] += 1

    r["_latency_median_s"] = round(statistics.median(timings), 4) if timings else None
    return r


def summary_lines(r):
    return [
        f"routes {r['routed_correctly']} of {r['route_cases']} labelled questions to the agent a person would pick",
        f"validates {r['sql_validated']} of {r['sql_generated']} generated statements before any of them runs",
        f"picks every column a person needs on {r['columns_complete']} of {r['contract_routed']} contract questions it routes",
        f"refuses {r['literal_refused']} of {r['literal_probes']} literal injection probes before any agent runs",
        f"lets {r['paraphrases_reached_generator']} of {r['paraphrases']} paraphrased probes reach the generator, and {r['paraphrases_changed_sql']} of them change the SQL",
        f"redacts {r['pii_named_redacted']} of {r['pii_named']} strings in the formats it names, and {r['pii_other_redacted']} of {r['pii_other']} in formats it does not",
    ]


def comparable(r):
    return {k: v for k, v in r.items() if not k.startswith("_")}


def main():
    cases = load_cases()
    r = run(cases)
    for line in summary_lines(r):
        print(line)
    for intent, b in sorted(r["by_intent"].items()):
        print(f"  {intent}: {b['correct']} of {b['n']}")
    print(f"  retrieval: top paragraph is the labelled section on {r['retrieval_top1_hits']} of {r['retrieval_queries']} knowledge questions")
    print(f"  asked back when a person wanted an answer: {r['asked_back_wrongly']}")
    print(f"  latency, median per question on this machine, not compared: {r['_latency_median_s']} s")
    for m in r["misses"]:
        print("  miss:", json.dumps(m))

    if "--check" not in sys.argv:
        with open(REPORT, "w", encoding="utf-8") as f:
            json.dump(comparable(r), f, indent=2)
            f.write("\n")
        print(f"wrote {os.path.relpath(REPORT, ROOT)}")
        return 0

    failures = []
    try:
        with open(REPORT, encoding="utf-8") as f:
            committed = json.load(f)
    except (OSError, ValueError) as e:
        failures.append(f"evals/report.json unreadable: {e}")
        committed = {}
    fresh = comparable(r)
    for k in sorted(set(fresh) | set(committed)):
        if k == "misses":
            continue
        if fresh.get(k) != committed.get(k):
            failures.append(f"report.json {k}: committed {committed.get(k)!r}, measured {fresh.get(k)!r}")

    readme = open(README, encoding="utf-8").read() if os.path.exists(README) else ""
    for pattern, keys in BADGE_CLAIMS:
        m = re.search(pattern, readme)
        if not m:
            failures.append(f"README carries no badge matching /{pattern}/")
            continue
        for got, key in zip(m.groups(), keys):
            if int(got) != r[key]:
                failures.append(f"README badge /{pattern}/ says {got} for {key}, measured {r[key]}")
    for line in summary_lines(r):
        if line not in readme:
            failures.append(f"README does not carry the measured line: {line}")
    # The section tables carry the same counts in prose, and a table cell rots as quietly as a badge.
    bi = r["by_intent"]
    for cell in [
        f"| contract | {bi['contract']['correct']} of {bi['contract']['n']} |",
        f"| knowledge | {bi['knowledge']['correct']} of {bi['knowledge']['n']} |",
        f"| off topic | {bi['unknown']['correct']} of {bi['unknown']['n']} |",
        f"{r['sql_validated']} of {r['sql_generated']} pass the validator",
        f"{r['columns_complete']} of {r['contract_routed']} carry every column",
        f"{r['literal_refused']} of {r['literal_probes']} refused on the way in",
        f"{r['paraphrases_reached_generator']} of {r['paraphrases']} reached the generator, {r['paraphrases_changed_sql']} changed the SQL",
        f"Retrieval at {r['retrieval_top1_hits']} of {r['retrieval_queries']}",
    ]:
        if cell not in readme:
            failures.append(f"README table does not carry the measured cell: {cell}")

    if failures:
        print("CHECK FAILED")
        for f_ in failures:
            print("  " + f_)
        return 1
    print("CHECK OK: report.json and every README badge match what was just measured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
