"""
Routes a question to the KnowledgeAgent or the ContractAgent.

The order is the design. The injection guard reads the question before anything
else does, the classifier picks a door or hands the question back, and the PII
filter reads the answer on its way out.
"""

from phase1_pilot.app.chains import KnowledgeAgent
from phase1_pilot.app.contract_agent import ContractAgent
from phase1_pilot.app.intent_classifier import IntentClassifier
from phase1_pilot.app.utils import sanitize_input
from phase1_pilot.guardrails.pii_filter import remove_pii
from phase1_pilot.guardrails.prompt_injection_guard import detect_prompt_injection

ASK_AGAIN = "I'm not confident I understand this question. Could you rephrase it or provide more context?"
REFUSED = "Your request appears unsafe or may contain restricted instructions. Please rephrase and try again."


class QueryRouter:
    def __init__(self):
        self.classifier = IntentClassifier()
        self.knowledge_agent = KnowledgeAgent()
        self.contract_agent = ContractAgent()

    def handle_query(self, query: str):
        clean = sanitize_input(query)

        # Guardrail 1: prompt injection, on the way in, before any agent runs.
        if detect_prompt_injection(clean):
            return "unsafe", REFUSED

        intent, _confidence = self.classifier.classify(clean)

        # A tie between the two vocabularies, or no hit at all, goes back to the
        # user as a question. A deterministic pilot does not guess.
        if intent == "unknown":
            response = ASK_AGAIN
        elif intent == "contract":
            response = self.contract_agent.answer(clean)
        else:
            response = self.knowledge_agent.answer(clean)

        # Guardrail 2: PII, on the way out.
        return intent, remove_pii(response)
