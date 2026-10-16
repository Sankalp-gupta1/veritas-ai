"""Provider boundary tests use controlled HTTP responses, never fake live evaluations."""

import json

import httpx
import pytest

from app import generation


def install_transport(monkeypatch, responder):
    real_client = httpx.Client
    monkeypatch.setattr(
        generation.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(responder), trust_env=False),
    )


def test_valid_json_from_provider_is_structurally_validated(monkeypatch):
    draft = {
        "claims": [
            {
                "text": "The trial enrolled 120 adults.",
                "citations": [{"chunk_id": "c1", "quote": "The trial enrolled 120 adults."}],
            }
        ]
    }

    def respond(request):
        assert request.headers["x-goog-api-key"] == "fictional-test-key"
        assert "fictional-test-key" not in str(request.url)
        body = json.loads(request.content)
        prompt = json.loads(body["contents"][0]["parts"][0]["text"])
        assert prompt == {
            "question": "How many adults?",
            "evidence": [{"chunk_id": "c1", "source": "fictional.pdf", "text": "120 adults."}],
        }
        assert "fictional-test-key" not in request.content.decode()
        assert "internal-not-for-provider" not in request.content.decode()
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": json.dumps(draft)}]}}],
                "usageMetadata": {"promptTokenCount": 12},
            },
        )

    install_transport(monkeypatch, respond)
    context = [{
        "id": "c1", "name": "fictional.pdf", "text": "120 adults.",
        "workspace_id": "internal-not-for-provider", "embedding": [0.1, 0.2],
    }]
    claims, meta = generation.generate("How many adults?", context, key="fictional-test-key")
    assert "fictional-test-key" not in json.dumps({"claims": claims, "meta": meta})
    assert claims == draft["claims"]
    assert meta["usage"]["promptTokenCount"] == 12


@pytest.mark.parametrize(
    "status,message",
    [(403, "rejected"), (404, "unavailable"), (500, "could not complete")],
)
def test_provider_errors_have_safe_human_messages(monkeypatch, status, message):
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(status, json={"private_debug": "do not expose"}),
    )
    with pytest.raises(generation.ProviderError, match=message) as error:
        generation.generate("Question about a paper", [], key="fictional-test-key")
    assert "private_debug" not in str(error.value)


def test_rate_limit_retries_once_then_reports_quota(monkeypatch):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(429)

    install_transport(monkeypatch, respond)
    monkeypatch.setattr(generation.time, "sleep", lambda _: None)
    with pytest.raises(generation.ProviderError, match="quota"):
        generation.generate("Question about a paper", [], key="fictional-test-key")
    assert len(calls) == 2


def test_malformed_model_response_is_never_treated_as_verified(monkeypatch):
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "a confident uncited answer"}]}}]},
        ),
    )
    with pytest.raises(generation.ProviderError, match="invalid answer format"):
        generation.generate("Question about a paper", [], key="fictional-test-key")
