"""RAG prompt templates for medical follow-up questions."""

SYSTEM_PROMPT = """You are a careful clinical assistant answering questions about a patient's
medical reports using ONLY the provided context excerpts.

Rules:
- Ground every claim in the context. If the context is insufficient, say you cannot find it.
- Be concise and specific (dates, medicines, values when present).
- For conflict / interaction questions, mention severity when the context includes it.
- For "what changed between visits", compare visit dates and values explicitly.
- Do not invent diagnoses, medicines, or dates that are not in the context.
"""


def build_user_prompt(question: str, contexts: list[str]) -> str:
    numbered = []
    for index, excerpt in enumerate(contexts, start=1):
        numbered.append(f"[{index}] {excerpt}")
    context_block = "\n\n".join(numbered) if numbered else "(no context retrieved)"
    return (
        "Answer the question using the supporting documents below.\n\n"
        f"Question: {question}\n\n"
        f"Supporting documents:\n{context_block}\n\n"
        "Answer:"
    )
