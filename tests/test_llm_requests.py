"""How a request is spelled for each provider, against fake SDK clients.

No network. Every case here is a live 400 or TypeError seen from a real run: the
newest Claude models reject `temperature`, OpenAI renamed `max_tokens`, and a reply
cut off at the token cap used to surface as an unparseable-JSON bug.
"""
import json

import pytest

from ats import llm
from ats.llm import LLMError, Provider

ANTHROPIC = Provider("anthropic", "k", "claude-sonnet-5")
OPENAI = Provider("openai", "k", "gpt-5.6-luna")


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeAnthropic:
    """Mimics anthropic 1.x: Messages.create() has no `temperature` parameter."""

    def __init__(self, sent, stop_reason="end_turn", reply='{"ok": true}'):
        self.sent, self.stop_reason, self.reply = sent, stop_reason, reply
        self.messages = self

    def create(self, *, model, max_tokens, system, messages):
        self.sent.append(dict(model=model, max_tokens=max_tokens))
        return type("Response", (), {
            "content": [_Block(self.reply)], "stop_reason": self.stop_reason,
        })()


class _FakeOpenAI:
    def __init__(self, sent, finish_reason="stop", reply='{"ok": true}', reject=None):
        self.sent, self.finish_reason, self.reply, self.reject = (
            sent, finish_reason, reply, reject,
        )
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.sent.append(kwargs)
        if self.reject and self.reject in kwargs:
            raise RuntimeError(
                f"Error code: 400 - {{'error': {{'message': \"Unsupported parameter: "
                f"'{self.reject}' is not supported with this model. Use "
                f"'max_completion_tokens' instead.\"}}}}"
            )
        message = type("Message", (), {"content": self.reply})()
        choice = type("Choice", (), {
            "message": message, "finish_reason": self.finish_reason,
        })()
        return type("Response", (), {"choices": [choice]})()


@pytest.fixture(autouse=True)
def _forget_learned_spellings():
    llm._LEARNED.clear()
    yield
    llm._LEARNED.clear()


def _patch(monkeypatch, provider_module, factory):
    module = pytest.importorskip(provider_module)
    attr = "Anthropic" if provider_module == "anthropic" else "OpenAI"
    monkeypatch.setattr(module, attr, lambda api_key: factory)


def test_anthropic_omits_temperature_the_sdk_no_longer_accepts(monkeypatch):
    sent = []
    _patch(monkeypatch, "anthropic", _FakeAnthropic(sent))

    assert llm.call(ANTHROPIC, "sys", "user", 0.7) == {"ok": True}
    assert sent == [{"model": "claude-sonnet-5", "max_tokens": llm.MAX_TOKENS}]


def test_openai_sends_max_completion_tokens_and_no_temperature(monkeypatch):
    sent = []
    _patch(monkeypatch, "openai", _FakeOpenAI(sent))

    llm.call(OPENAI, "sys", "user", 0.7)
    assert sent[0]["max_completion_tokens"] == llm.MAX_TOKENS
    assert "max_tokens" not in sent[0]
    assert "temperature" not in sent[0]


def test_openai_legacy_model_keeps_the_old_spelling(monkeypatch):
    sent = []
    _patch(monkeypatch, "openai", _FakeOpenAI(sent))

    llm.call(Provider("openai", "k", "gpt-4o"), "sys", "user", 0.7)
    assert sent[0]["max_tokens"] == llm.MAX_TOKENS
    assert sent[0]["temperature"] == 0.7


def test_rejected_parameter_is_renamed_then_remembered(monkeypatch):
    sent = []
    _patch(monkeypatch, "openai", _FakeOpenAI(sent, reject="max_tokens"))
    legacy = Provider("openai", "k", "gpt-4o")

    llm.call(legacy, "sys", "user", 0.0)
    assert "max_completion_tokens" in sent[-1]

    llm.call(legacy, "sys", "user", 0.0)
    assert len(sent) == 3, "the rename should be learned, not rediscovered per call"
    assert "max_tokens" not in sent[-1]


def test_truncated_reply_fails_as_truncation_not_as_bad_json(monkeypatch):
    sent = []
    _patch(monkeypatch, "anthropic", _FakeAnthropic(
        sent, stop_reason="max_tokens", reply='{"findings": [{"message": "cut off',
    ))

    with pytest.raises(LLMError, match="cut off"):
        llm.call(ANTHROPIC, "sys", "user")
    assert len(sent) == 1, "a truncated reply must not be retried as a parse repair"


def test_unparseable_reply_after_repair_names_the_provider(monkeypatch):
    sent = []
    _patch(monkeypatch, "anthropic", _FakeAnthropic(sent, reply="not json at all"))

    with pytest.raises(LLMError, match="anthropic:claude-sonnet-5"):
        llm.call(ANTHROPIC, "sys", "user")
    assert len(sent) == 2
