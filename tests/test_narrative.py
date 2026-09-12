from undercurrents.orchestrator import narrative
from undercurrents.orchestrator.intent import Intent
from undercurrents.orchestrator.retrieval import RetrievedFacts


class FakeOllamaClient:
    def __init__(self, response="a canned answer"):
        self.response = response
        self.received_messages = None

    def chat(self, messages):
        self.received_messages = messages
        return self.response


def test_generate_response_returns_client_output():
    client = FakeOllamaClient(response="Elephant was last played recently.")
    retrieved = RetrievedFacts(Intent.FACT, {"mentioned_song": "Elephant"})

    answer = narrative.generate_response(client, "When was Elephant last played?", retrieved, [])

    assert answer == "Elephant was last played recently."


def test_generate_response_includes_question_and_facts_in_prompt():
    client = FakeOllamaClient()
    retrieved = RetrievedFacts(Intent.FACT, {"mentioned_song": "Elephant", "total_shows": 767})

    narrative.generate_response(client, "When was Elephant last played?", retrieved, [])

    last_message = client.received_messages[-1]
    assert "When was Elephant last played?" in last_message["content"]
    assert "Elephant" in last_message["content"]
    assert "767" in last_message["content"]


def test_generate_response_includes_prior_history_before_the_new_message():
    client = FakeOllamaClient()
    retrieved = RetrievedFacts(Intent.CHAT, {})
    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]

    narrative.generate_response(client, "How are you?", retrieved, history)

    assert client.received_messages[0] == {"role": "user", "content": "Hi"}
    assert client.received_messages[1] == {"role": "assistant", "content": "Hello!"}
    assert len(client.received_messages) == 3
