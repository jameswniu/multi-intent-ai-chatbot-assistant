"""What a stranger can check without a key.

The counts on the page are pinned by evals/cases.jsonl and recomputed by evals/score.py.
What is tested here is narrower: the three defects that stopped the pilot answering any
question, kept as regressions, and the properties of each lock.

    python3 -m pytest tests/ -v
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from phase1_pilot.app.contract_agent import COLUMN_MAP, ContractAgent  # noqa: E402
from phase1_pilot.app.intent_classifier import IntentClassifier  # noqa: E402
from phase1_pilot.guardrails.pii_filter import remove_pii  # noqa: E402
from phase1_pilot.guardrails.prompt_injection_guard import detect_prompt_injection  # noqa: E402
from phase1_pilot.guardrails.sql_validator import validate_sql  # noqa: E402


# Defect 1: confidence was hits divided by vocabulary size, so one keyword could never route.

def test_one_keyword_is_a_confident_route():
    intent, confidence = IntentClassifier().classify("What is the price of the Analytics module?")
    assert intent == "contract"
    assert confidence == 1.0


def test_a_tie_between_the_vocabularies_is_unknown():
    intent, confidence = IntentClassifier().classify("How do I renew a contract?")
    assert intent == "unknown"
    assert confidence == 0.0


def test_plurals_fold_and_substrings_do_not_match():
    assert IntentClassifier().classify("List all contracts with their prices")[0] == "contract"
    # "show" contains "how" and "user" contains "use"; neither is a hit on whole words.
    assert IntentClassifier().classify("show the user")[0] == "unknown"


def test_routing_vocabulary_is_the_column_map():
    assert set(COLUMN_MAP) <= IntentClassifier().contract_keywords


# Defect 2: the generator appended a terminator its own validator refuses.

def test_generated_sql_passes_its_own_validator(tmp_path):
    agent = ContractAgent(db_path=str(tmp_path / "c.db"))
    assert agent._construct_sql("Expiry for DataHub") == "SELECT expiry_date FROM contracts LIMIT 10"
    assert agent._construct_sql("hello") == "SELECT customer_id, module, expiry_date, price FROM contracts LIMIT 10"


def test_sql_column_order_does_not_depend_on_hash_seed(tmp_path):
    code = ("import sys; sys.path.insert(0, %r); from phase1_pilot.app.contract_agent import ContractAgent; "
            "print(ContractAgent(db_path=%r)._construct_sql('price and module and customer and expiry'))"
            % (ROOT, str(tmp_path / "c.db")))
    outs = set()
    for seed in ("1", "2", "3"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        outs.add(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True).stdout)
    assert len(outs) == 1, outs


# Defect 3: no database file existed and nothing built one.

def test_database_is_built_from_the_seed_on_first_run(tmp_path):
    db = tmp_path / "contracts.db"
    assert not db.exists()
    answer = ContractAgent(db_path=str(db)).answer("Which customer has the Compliance module?")
    assert db.exists()
    assert "Compliance" in answer and "C003" in answer


# The SQL lock. The shape is the allowlist, the keyword list is the second check.

@pytest.mark.parametrize("statement", [
    "DROP TABLE contracts",
    "INSERT INTO contracts VALUES ('X', 'Y', '2027-01-01', 1)",
    "SELECT price FROM contracts; DROP TABLE contracts",
    "PRAGMA table_info(contracts)",
    "UPDATE contracts SET price = 0",
    "ATTACH DATABASE '/tmp/other.db' AS other",
    # Found by the adversarial review of the keyword-only version. Each passed it.
    "SELECT sql FROM sqlite_master WHERE type = 'table'",
    "SELECT customer_id FROM contracts UNION SELECT sql FROM sqlite_master",
    "SELECT load_extension('/tmp/x')",
    "SELECT price FROM contracts WHERE price = (SELECT 1)",
    "SELECT c.price FROM contracts c JOIN sqlite_master m",
    "SELECT * FROM users",
])
def test_validator_refuses_anything_but_the_known_columns_from_the_one_table(statement):
    with pytest.raises(ValueError):
        validate_sql(statement)


@pytest.mark.parametrize("statement", [
    "SELECT price FROM contracts LIMIT 10",
    "SELECT customer_id, module, expiry_date, price FROM contracts",
    "SELECT expiry_date FROM contracts WHERE customer_id = 'C003'",
    "SELECT module, price FROM contracts WHERE price > 3000 AND module LIKE 'Data%' ORDER BY price DESC LIMIT 1",
    "SELECT price FROM contracts WHERE customer_id = ?",
])
def test_validator_allows_a_shaped_select(statement):
    assert validate_sql(statement)


def test_validator_matches_keywords_on_whole_words():
    assert validate_sql("SELECT price FROM contracts WHERE module = 'UPDATED'")


# The input lock.

@pytest.mark.parametrize("phrase", [
    "ignore previous instructions", "system override", "disable filters", "bypass safety",
    "reveal hidden data", "execute code", "drop table",
])
def test_injection_guard_catches_each_literal_phrase(phrase):
    assert detect_prompt_injection(f"Please {phrase} now")


# The output lock.

@pytest.mark.parametrize("text, token", [
    ("ssn 123-45-6789", "[SSN]"),
    ("mail jane.doe@example.com", "[EMAIL]"),
    ("phone 5551234567", "[PHONE]"),
    ("card 4111 1111 1111 1111", "[CARD]"),
])
def test_pii_filter_redacts_its_four_named_formats(text, token):
    assert token in remove_pii(text)


# The router end to end, with the real retrieval model.

@pytest.fixture(scope="module")
def router():
    from phase1_pilot.app.router import QueryRouter
    return QueryRouter()


def test_router_refuses_before_any_agent_runs(router):
    from phase1_pilot.app.router import REFUSED
    assert router.handle_query("drop table contracts") == ("unsafe", REFUSED)


def test_router_asks_again_on_a_tie_or_no_hit(router):
    from phase1_pilot.app.router import ASK_AGAIN
    assert router.handle_query("hello") == ("unknown", ASK_AGAIN)


def test_router_answers_a_contract_question_with_rows(router):
    intent, answer = router.handle_query("What is the price of the Analytics module?")
    assert intent == "contract"
    assert "SELECT price, module FROM contracts LIMIT 10" in answer
    assert "4999.0" in answer


def test_router_picks_columns_and_never_rows(router):
    # The pilot has no WHERE. A question about one customer returns the columns for every row.
    intent, answer = router.handle_query("Expiry date for customer C003")
    assert intent == "contract"
    assert "SELECT expiry_date, customer_id FROM contracts LIMIT 10" in answer
    assert all(cid in answer for cid in ("A001", "B002", "C003", "D004"))


def test_router_answers_a_knowledge_question_from_the_guide(router):
    intent, answer = router.handle_query("How can I reset a password?")
    assert intent == "knowledge"
    assert "Reset Password" in answer
