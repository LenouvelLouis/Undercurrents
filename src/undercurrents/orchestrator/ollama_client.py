import time

import httpx

BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"
RETRYABLE_STATUSES = {500, 502, 503, 504}


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(
        self,
        http_client: httpx.Client | None = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
        sleep_fn=time.sleep,
    ):
        self._client = http_client or httpx.Client(base_url=BASE_URL, timeout=60.0)
        self._model = model
        self._max_retries = max_retries
        self._sleep_fn = sleep_fn

    def chat(self, messages: list[dict]) -> str:
        attempt = 0
        while True:
            try:
                response = self._client.post(
                    "/api/chat",
                    json={"model": self._model, "messages": messages, "stream": False},
                )
            except httpx.ConnectError as exc:
                raise OllamaError(
                    "Could not connect to Ollama at http://localhost:11434 — is it running? "
                    "Start it with `ollama serve` and make sure the model is pulled "
                    f"(`ollama pull {self._model}`)."
                ) from exc

            if response.status_code == 200:
                return response.json()["message"]["content"]
            if response.status_code in RETRYABLE_STATUSES and attempt < self._max_retries:
                backoff = min(2**attempt, 30)
                self._sleep_fn(backoff)
                attempt += 1
                continue
            raise OllamaError(
                f"Ollama request failed with status {response.status_code}: {response.text}"
            )
