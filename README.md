<p align="center">
  <img src="assets/hero.svg" alt="Docs, or the database? Three locks on one question, each with its own source of truth. Route asks which agent answers, or whether to ask the user, and its truth is the column map. Constrain asks what SQL may run against the table, and its truth is a four-column map that Phase 2 swaps for a model. Redact asks what may leave in the answer, and its truth is four regex patterns read on the way out." width="100%">
</p>

<div align="center">

<b><font size="6">Questions to SQL, Intent Router</font></b>

<br/>

<a href="https://github.com/jameswniu/questions-to-sql-intent-router/actions/workflows/checks.yml"><img alt="checks" src="https://github.com/jameswniu/questions-to-sql-intent-router/actions/workflows/checks.yml/badge.svg?branch=master"></a>
<img alt="routes 42 of 54 labelled questions to the agent a person would pick" src="https://img.shields.io/badge/routes-42_of_54_labelled_questions-4a7fb5?style=flat-square&labelColor=15181d">
<img alt="SQL validated, 26 of 26 generated statements" src="https://img.shields.io/badge/SQL_validated-26_of_26-6b7280?style=flat-square&labelColor=15181d">
<img alt="literal injection probes refused, 7 of 7" src="https://img.shields.io/badge/literal_probes_refused-7_of_7-6b7280?style=flat-square&labelColor=15181d">
<img alt="PII redacted, 5 of 5 strings in the formats it names" src="https://img.shields.io/badge/PII-5_of_5_named_formats-6b7280?style=flat-square&labelColor=15181d">
<img alt="every number on this page is recounted in CI on every push" src="https://img.shields.io/badge/numbers-recounted_in_CI_on_every_push-4a7fb5?style=flat-square&labelColor=15181d">
<img alt="license Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-6b7280?style=flat-square&labelColor=15181d">

<br/><br/>

<strong>A support question goes to the documentation or to the database. This router decides which, and nothing the user typed ever reaches the SQL.</strong><br/>
A deterministic pilot that runs offline, measured on 54 labelled questions, 12 injection probes and 9 seeded strings.<br/>
Phases 2 and 3 are the designed path to a model behind the same three locks, and are labelled as designs.

<br/>

<code>guard -> classify -> route -> select -> validate -> redact</code>

</div>

---

**Docs, or the database? Three locks on one question, each with its own source of truth.**

| | The question it answers | Where its truth comes from | When it changes |
|:---|:---|:---|:---|
| **Route** | Which agent answers, or should the user be asked again? | The column map's own words, plus billing | When the schema changes |
| **Constrain** | What SQL may run against the table? | A four-column map, then a validator that allows one SELECT | When Phase 2 puts a model behind it |
| **Redact** | What may leave in the answer? | Four regex patterns, read on the way out | When a format shows up the patterns do not name |

Letting a chatbot answer was the easy half. Letting it near a database with nobody watching the SQL is the hard half, and the three locks split that into pieces small enough to test.

- The counts below come from running the pilot as committed, with no keys and one model download, and CI reruns them on every push.
- Phase 1 misses its own target. The plan asked for 80 percent routing accuracy and the labelled set measures 78, with every miss listed.

---

## 1. Route

Which agent answers. The source of truth is the column map's own vocabulary.

| Labelled as | Routed right | What the misses were |
|:---|:---|:---|
| contract | 25 of 26 | "What are we charging for Reporting?" carries no word the map knows |
| knowledge | 12 of 23 | six how-to questions that name a contract thing lose to the column vocabulary, five carry no keyword and are handed back |
| off topic | 5 of 5 | every one handed back with a question |

- Two word lists and no model. The contract list is the column map's keys plus billing, so a word that selects a column always routes to the agent that owns it.
- Whole words with one trailing s folded, a strict winner routes, and a tie or no hit goes back to the user as a question.
- Retrieval is the strong half. On all 23 knowledge questions FAISS returns the labelled guide section first, including the eleven the router never sent there.

Three defects sat in the pilot as first committed, each enough on its own to stop every answer, and each is now a regression test in [`tests/test_phase1.py`](tests/test_phase1.py).

- Confidence was hits divided by the size of both vocabularies, so every question fell under the 0.4 fallback. The threshold is gone and a tie is the only fallback.
- The SQL generator ended every statement with a terminator its own validator refused. It no longer emits one.
- No database file existed and nothing built one. The agent now builds it from the seed on first run.

---

## 2. Constrain

What SQL may run. The source of truth is a four-column map, then a validator that allows one SELECT.

| Probe | Result |
|:---|:---|
| 26 contract questions, the statements the map produced | 26 of 26 pass the validator, and every one ran |
| 25 contract questions the router sent to the map | 12 of 25 carry every column the person needs |
| 7 literal injection phrasings | 7 of 7 refused on the way in |
| 5 paraphrased injections the guard does not know | 5 of 5 reached the generator, 0 changed the SQL |
| Column order across three hash seeds | identical |

- The SQL is selected, not written, from a map of seven words to four columns. Nothing typed by the user reaches the SQL text, and nothing filters rows either. "Expiry for DataHub" comes back as the expiry column for all four rows, and a predicate is the lock Phase 2 has to build.
- The validator is a shape allowlist, then a denylist. One SELECT of the four known columns from the one table, simple predicates, ORDER BY, LIMIT, and nothing else. The adversarial review before this commit caught the keyword-only version passing a UNION against sqlite_master, which is why the shape exists.
- The injection guard is seven phrases, and a paraphrase walks past it into a generator that cannot be steered. Once a model writes the SQL, seven phrases is not enough.

---

## 3. Redact

What may leave. The source of truth is four patterns, read on the way out.

| Seeded string | Format | Result |
|:---|:---|:---|
| Call me at 5551234567 | ten-digit phone | redacted |
| My SSN is 123-45-6789 | social security number | redacted |
| Email me at jane.doe@example.com | email | redacted |
| Card 4111 1111 1111 1111 | card in four groups | redacted |
| jane+contracts@sub.example.co.uk | email with a plus and a subdomain | redacted |
| reach me on 555-123-4567 | dashed phone | passes through |
| (555) 123-4567 | bracketed phone | passes through |
| 4111-1111-1111-1111 | dashed card | passes through |
| +1 415 555 0142 | international phone | passes through |

- Four regular expressions run on every answer after the agent has produced it. They name a social security number, an email, a ten-digit phone and a card in four groups.
- In Phase 1 nothing upstream contains personal data, so the filter is measured on seeded strings. It is here because a Phase 2 model may echo whatever it was given.
- A dashed or bracketed phone, a dashed card and an international number all walk through. Those are the next four patterns.

---

## The staged path

Phase 1 runs and is measured here. Phases 2 and 3 are the designed path to a model behind the same three locks.

| Phase | What it is | What it needs to run | Status |
|:---|:---|:---|:---|
| 1. Pilot | Keyword routing, FAISS over the guide, SQL selected from a map, three guardrails | python3 and one model download | runs in CI, measured above |
| 2. Production | The same three seats with a model in each, plus a feedback log, behind the same validator | An API key and a document store | written, not run |
| 3. Scaling | A Helm chart, autoscaling from 2 to 10 replicas, Prometheus alerts, Argo CD sync | A cluster | manifests only |

- The lock that changes between phases is the second one. In Phase 1 the generator cannot be steered, so the validator is redundant, and in Phase 2 it is the whole defence.
- The Phase 2 code keeps its original design as written, one model at every seat and BLEU and ROUGE-L as its metrics. None of it has been measured.

## The loop, as a map

<p align="center">
  <img src="assets/system-map.svg" alt="System map of one question through six steps, guard, classify, route, retrieve, select, validate, then the three locks that own them, then the staged path with the pilot highlighted as the phase that runs." width="100%">
</p>

Both figures are generated by the scripts in [`tools/`](tools/) from declared lists, with a fit guard on every line of text. CI fails if a committed figure drifts from its generator.

The same loop as a flowchart. Brick marks the two locks that can refuse a question.

```mermaid
%%{init: {'theme': 'base', 'flowchart': {'curve': 'basis'}, 'themeVariables': {'primaryColor': '#20242b', 'primaryTextColor': '#e7e5e0', 'primaryBorderColor': '#3a3f47', 'lineColor': '#7aa6d8', 'textColor': '#e7e5e0', 'edgeLabelBackground': '#20242b', 'fontSize': '16px'}}}%%
flowchart TD
    Q[A question] --> G{Guard<br/>seven phrases, on the way in}
    G -->|matched| R1[Refused]
    G -->|clean| C[Classify<br/>two vocabularies, whole words]
    C -->|contract| S[Select columns<br/>from the four-column map]
    C -->|knowledge| F[Retrieve<br/>FAISS over the guide, top two]
    C -->|tie or no hit| A[Ask the user again]
    S --> V{Validate<br/>one SELECT, one table}
    V -->|shape holds| D[(contracts)]
    V -->|anything else| R2[Refused]
    D --> P[Redact<br/>four patterns, on the way out]
    F --> P
    P --> O[Answer]
    style G fill:#20242b,stroke:#d0705a,stroke-width:2px,color:#e7e5e0
    style V fill:#20242b,stroke:#d0705a,stroke-width:2px,color:#e7e5e0
    style R1 fill:#d0705a,stroke:#d0705a,color:#14171c
    style R2 fill:#d0705a,stroke:#d0705a,color:#14171c
    style A fill:#20242b,stroke:#9a9a93,color:#9a9a93
    style O fill:#7aa6d8,stroke:#7aa6d8,color:#14171c
```

## Code map

Everything in the first block ran, in CI, on this branch.

| Where | What it is |
|:---|:---|
| [`phase1_pilot/app/router.py`](phase1_pilot/app/router.py) | The three locks in order, guard, classify and route, redact |
| [`phase1_pilot/app/intent_classifier.py`](phase1_pilot/app/intent_classifier.py) | Two vocabularies, whole words, one stemmer |
| [`phase1_pilot/app/contract_agent.py`](phase1_pilot/app/contract_agent.py) | The column map, the SQL it selects, the database built from the seed |
| [`phase1_pilot/app/chains.py`](phase1_pilot/app/chains.py) | FAISS over the guide with all-MiniLM-L6-v2, top two returned |
| [`phase1_pilot/guardrails/`](phase1_pilot/guardrails/) | The injection guard, the SQL validator, the PII filter |
| [`phase1_pilot/data/`](phase1_pilot/data/) | The guide and the seed |
| [`evals/`](evals/) | The labelled cases, the scorer, and the committed count it checks itself against |
| [`tests/test_phase1.py`](tests/test_phase1.py) | The three defects as regressions, and the properties of each lock |
| [`tools/`](tools/) | The palette and the two figure generators |
| [`.github/workflows/checks.yml`](.github/workflows/checks.yml) | Tests, then the recount, then the figure check, on every push |
| [`phase_2_production/`](phase_2_production/) | The designed production path, a model at each seat, a feedback log, Helm and Prometheus stubs |
| [`phase3_scaling/`](phase3_scaling/) | Helm chart and values, Prometheus rules, Grafana panels, the Argo CD application |

## Recounted on every push

- [`evals/score.py`](evals/score.py) runs the committed pilot against [`evals/cases.jsonl`](evals/cases.jsonl) and prints the six lines below.
- With `--check` it fails CI if [`evals/report.json`](evals/report.json), a badge, or this block disagrees with what it just measured.

```
routes 42 of 54 labelled questions to the agent a person would pick
validates 26 of 26 generated statements before any of them runs
picks every column a person needs on 12 of 25 contract questions it routes
refuses 7 of 7 literal injection probes before any agent runs
lets 5 of 5 paraphrased probes reach the generator, and 0 of them change the SQL
redacts 5 of 5 strings in the formats it names, and 0 of 4 in formats it does not
```

The labels say what a person asking the question wanted, not what the router does, and no vocabulary was changed after the first run. Check it with `python3` and one model download.

```
git clone https://github.com/jameswniu/questions-to-sql-intent-router
cd questions-to-sql-intent-router && pip install -r requirements.txt
python3 evals/score.py
```

## Where the claims stop

- A four-row table, a four-section guide, and 54 questions one person wrote in an evening. The counts are counts, never rates.
- One labeller, me. A second labeller and an agreement score are the next step.
- Routing sits under the plan's own target, 42 of 54 against 80 percent, and the shortfall is on the knowledge side.
- Retrieval at 23 of 23 says the guide is small and its sections distinct, not that the retriever is good.
- Nothing in Phase 2 or Phase 3 has run. The code needs an API key and a cluster this repository does not carry.
- Latency is printed by the scorer and never compared, because a timing number differs on every runner.
- The validator's allowlist is a regular expression, not a SQL parser, and the guard knows seven phrases. Both are named here so they are found on this page and not in a review.

This repository is the deterministic pilot as it runs, the labelled cases, and the scorer that recounts them. Apache-2.0.
