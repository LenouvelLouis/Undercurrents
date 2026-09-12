SYSTEM_PROMPT = (
    "You are a knowledgeable assistant about Tame Impala's live performance history. "
    "Answer the user's question using ONLY the structured facts provided below. "
    "If the facts don't contain enough information, say so honestly rather than guessing."
)


def build_prompt(question: str, retrieved) -> str:
    return f"{SYSTEM_PROMPT}\n\nFacts:\n{retrieved.data}\n\nQuestion: {question}\nAnswer:"


def generate_response(client, question: str, retrieved, history: list[dict]) -> str:
    prompt = build_prompt(question, retrieved)
    messages = history + [{"role": "user", "content": prompt}]
    return client.chat(messages)
