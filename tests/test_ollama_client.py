import httpx
import respx

from undercurrents.orchestrator.ollama_client import OllamaClient, OllamaError


def make_client(max_retries=3, sleeps=None):
    return OllamaClient(
        max_retries=max_retries,
        sleep_fn=(sleeps.append if sleeps is not None else (lambda s: None)),
    )


@respx.mock
def test_chat_returns_message_content_on_success():
    respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(
            200, json={"message": {"role": "assistant", "content": "Hello!"}}
        )
    )
    client = make_client()
    result = client.chat([{"role": "user", "content": "Hi"}])
    assert result == "Hello!"


@respx.mock
def test_chat_sends_model_and_messages():
    route = respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": "ok"}})
    )
    client = make_client()
    client.chat([{"role": "user", "content": "Hi"}])

    sent_body = route.calls.last.request.content
    assert b"llama3.1:8b" in sent_body
    assert b"Hi" in sent_body


@respx.mock
def test_chat_retries_on_server_error_then_succeeds():
    respx.post("http://localhost:11434/api/chat").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"message": {"content": "ok"}})]
    )
    sleeps = []
    client = make_client(sleeps=sleeps)
    result = client.chat([{"role": "user", "content": "Hi"}])
    assert result == "ok"
    assert sleeps == [1]


@respx.mock
def test_chat_raises_after_exhausting_retries():
    respx.post("http://localhost:11434/api/chat").mock(return_value=httpx.Response(500))
    client = make_client(max_retries=2)
    try:
        client.chat([{"role": "user", "content": "Hi"}])
        assert False, "expected OllamaError"
    except OllamaError:
        pass


@respx.mock
def test_chat_raises_helpful_error_on_connection_failure():
    respx.post("http://localhost:11434/api/chat").mock(side_effect=httpx.ConnectError("boom"))
    client = make_client()
    try:
        client.chat([{"role": "user", "content": "Hi"}])
        assert False, "expected OllamaError"
    except OllamaError as exc:
        assert "ollama serve" in str(exc)
