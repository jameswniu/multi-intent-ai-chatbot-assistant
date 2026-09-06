"""
KnowledgeAgent: FAISS over the user guide, one paragraph per entry, offline.
"""

import os

import faiss
from sentence_transformers import SentenceTransformer

from phase1_pilot.app.utils import load_docs

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


class KnowledgeAgent:
    def __init__(self, docs_path=os.path.join(DATA, "user_guide_sample.txt")):
        self.docs = load_docs(docs_path)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = self.model.encode(self.docs, convert_to_numpy=True)
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)

    def _search(self, query: str, top_k: int = 2):
        query_vec = self.model.encode([query], convert_to_numpy=True)
        _, I = self.index.search(query_vec, top_k)
        return [self.docs[i] for i in I[0]]

    def answer(self, query: str) -> str:
        top_docs = self._search(query)
        context = "\n\n".join(top_docs)
        return f"Here's what I found based on documentation:\n\n{context}"
