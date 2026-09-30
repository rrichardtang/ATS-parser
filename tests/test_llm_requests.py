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
OPENAI = Provider("openai", "k", "gpt-6-luna")


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeAnthropic:
    """Mimics anthropic 1.x streaming: Messages.stream() has no `temperature` parameter
    and yields a context manager that iterates events and whose get_final_message()
    is the whole reply."""

    def __init__(self, sent, stop_reason="end_turn", reply='{"ok": true}'):
        self.sent, self.stop_reason, self.reply = sent, stop_reason, reply
        self.messages = self
        self.closed = False

    def stream(self, **params):
        self.sent.append(params)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True
        return False

    def __iter__(self):
        return iter(["ping", "content_block_delta"])

    def get_final_message(self):
        return type("Message", (), {
            "content": [_Block(self.reply)], "stop_reason": self.stop_reason,
            "usage": type("Usage", (), {"input_tokens": 7, "output_tokens": 42,
                                         "cache_read_input_tokens": None})(),
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
                f"Error code: 400 - Unsupported parameter: '{self.reject}' is not "
                "supported with this model."
            )
        message = type("Message", (), {"content": self.reply})()
        choice = type("Choice", (), {
            "message": message, "finish_reason": self.finish_reason,
        })()
        usage = type("Usage", (), {
            "prompt_tokens": 7, "completion_tokens": 42,
            "prompt_tokens_details": type("Details", (), {"cached_tokens": 3})(),
            "completion_tokens_details": type("Details", (), {"reasoning_tokens": 30})(),
        })()
        return type("Response", (), {"choices": [choice], "usage": usage})()


def _patch(monkeypatch, provider_module, factory):
    pytest.importorskip(provider_module)
    monkeypatch.setattr(llm, f"_{provider_module}_client", lambda api_key, *_: factory)


@pytest.mark.parametrize("provider_module", ["anthropic", "openai"])
def test_real_clients_are_built_with_a_short_connect_and_the_call_timeout(provider_module):
    """Every client is bounded to gather's timeout, or a call gather gave up on holds
    the process open for the SDK's default ten minutes. The connect leg stays short
    so a dead endpoint fails fast. Builds the real SDK client: a fake here hid that
    the SDKs reject a plain `httpx.Timeout`."""
    pytest.importorskip(provider_module)
    timeout = getattr(llm, f"_{provider_module}_client")("sk-test").timeout
    assert timeout.read == llm.CALL_TIMEOUT
    assert timeout.connect == 5.0


def test_openai_retries_are_the_sdk_default_unless_the_provider_sets_them():
    """The app keeps the SDK's resend; the harness turns it off (`openai_max_retries=0`)."""
    openai = pytest.importorskip("openai")
    assert llm._openai_client("sk-test").max_retries == openai.DEFAULT_MAX_RETRIES
    assert llm._openai_client("sk-test", 0).max_retries == 0


def test_real_anthropic_client_has_the_streaming_helper():
    """A fake stands in for `messages.stream` everywhere else; this fails on a wrong
    method name before a live run does."""
    pytest.importorskip("anthropic")
    assert callable(llm._anthropic_client("sk-test").messages.stream)


def test_anthropic_omits_temperature_the_sdk_no_longer_accepts(monkeypatch):
    sent = []
    _patch(monkeypatch, "anthropic", _FakeAnthropic(sent))

    assert llm.call(ANTHROPIC, "sys", "user", 0.7) == {"ok": True}
    assert "temperature" not in sent[0]


def test_anthropic_sends_medium_effort_a_cached_system_and_no_thinking(monkeypatch):
    """Sonnet 5 rejects `budget_tokens`; effort goes inside `output_config`."""
    sent = []
    _patch(monkeypatch, "anthropic", _FakeAnthropic(sent))

    llm.call(ANTHROPIC, "sys", "user")
    assert sent[0]["max_tokens"] == llm.ANTHROPIC_MAX_TOKENS
    assert sent[0]["output_config"] == {"effort": "medium"}
    assert sent[0]["system"] == [
        {"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}
    ]
    assert "thinking" not in sent[0]


def test_a_lowered_cap_is_sent_and_named_when_hit(monkeypatch):
    sent = []
    _patch(monkeypatch, "anthropic", _FakeAnthropic(sent, stop_reason="max_tokens"))

    with pytest.raises(LLMError, match="1234-token cap"):
        llm.call(Provider("anthropic", "k", "claude-sonnet-5", 1234), "sys", "user")
    assert sent[0]["max_tokens"] == 1234


def test_openai_sends_max_completion_tokens_and_no_temperature(monkeypatch):
    sent = []
    _patch(monkeypatch, "openai", _FakeOpenAI(sent))

    llm.call(OPENAI, "sys", "user", 0.7)
    assert sent[0]["max_completion_tokens"] == llm.MAX_TOKENS
    assert "max_tokens" not in sent[0]
    assert "temperature" not in sent[0]
    assert sent[0]["reasoning_effort"] == "medium"


def test_openai_sends_the_providers_effort_and_cap(monkeypatch):
    sent = []
    _patch(monkeypatch, "openai", _FakeOpenAI(sent))

    llm.call(Provider("openai", "k", "gpt-6-luna", openai_max_tokens=24000,
                      openai_effort="high"), "sys", "user")
    assert sent[0]["max_completion_tokens"] == 24000
    assert sent[0]["reasoning_effort"] == "high"


def test_openai_usage_is_logged(monkeypatch, caplog):
    _patch(monkeypatch, "openai", _FakeOpenAI([]))

    with caplog.at_level("INFO", logger="ats.llm"):
        llm.call(OPENAI, "sys", "user")
    assert ("openai:gpt-6-luna used 7 input (3 cached) and 42 output tokens "
            "(30 reasoning) (finish_reason=stop)") in caplog.text


def test_a_truncated_openai_reply_fails_at_the_cap_it_was_sent(monkeypatch):
    sent = []
    _patch(monkeypatch, "openai", _FakeOpenAI(sent, finish_reason="length"))

    with pytest.raises(LLMError, match="24000-token cap .* cut off"):
        llm.call(Provider("openai", "k", "gpt-6-luna", openai_max_tokens=24000),
                 "sys", "user")
    assert len(sent) == 1


def test_openai_legacy_model_keeps_the_old_spelling(monkeypatch):
    sent = []
    _patch(monkeypatch, "openai", _FakeOpenAI(sent))

    llm.call(Provider("openai", "k", "gpt-4o"), "sys", "user", 0.7)
    assert sent[0]["max_tokens"] == llm.MAX_TOKENS
    assert sent[0]["temperature"] == 0.7
    assert "reasoning_effort" not in sent[0]


def test_a_rejected_parameter_surfaces_instead_of_being_papered_over(monkeypatch):
    """A 400 must reach the ensemble log naming the parameter, not be retried away.

    Silently re-spelling the request is what hid the real bug last time: the pass
    degraded to one provider and the only trace was a warning nobody read.
    """
    sent = []
    _patch(monkeypatch, "openai", _FakeOpenAI(sent, reject="max_completion_tokens"))

    with pytest.raises(LLMError, match="max_completion_tokens"):
        llm.call(OPENAI, "sys", "user")
    assert len(sent) == 1


def test_truncated_reply_fails_as_truncation_not_as_bad_json(monkeypatch):
    sent = []
    _patch(monkeypatch, "anthropic", _FakeAnthropic(
        sent, stop_reason="max_tokens", reply='{"findings": [{"message": "cut off',
    ))

    with pytest.raises(LLMError, match=f"{llm.ANTHROPIC_MAX_TOKENS}-token cap .* cut off"):
        llm.call(ANTHROPIC, "sys", "user")
    assert len(sent) == 1, "a truncated reply must not be retried as a parse repair"


def test_unparseable_reply_after_repair_names_the_provider(monkeypatch):
    sent = []
    _patch(monkeypatch, "anthropic", _FakeAnthropic(sent, reply="not json at all"))

    with pytest.raises(LLMError, match="anthropic:claude-sonnet-5"):
        llm.call(ANTHROPIC, "sys", "user")
    assert len(sent) == 2


def test_a_stream_past_its_deadline_is_abandoned_and_closed(monkeypatch):
    """Pings reset the read timeout, so only a wall clock stops a runaway reply from
    billing on after gather has dropped it; leaving the `with` closes the stream."""
    fake = _FakeAnthropic([])
    _patch(monkeypatch, "anthropic", fake)
    monkeypatch.setattr(llm, "STREAM_DEADLINE", -1.0)

    with pytest.raises(LLMError, match="still streaming"):
        llm.call(ANTHROPIC, "sys", "user")
    assert fake.closed


def test_the_stream_deadline_fits_inside_the_content_pass_budget():
    from ats import passes

    assert llm.STREAM_DEADLINE < passes.CONTENT_TIMEOUT


def test_both_providers_are_told_to_read_context_and_answer_every_place(monkeypatch):
    """Ticket 15, 29 September: Luna judged resume 21's rework bullet without the bullet
    before it, and skipped resume 09's one project bullet in every try."""
    from ats import prompts, sections
    from ats.answer_key import KEY

    text = (KEY.parent / "synthetic" / "09-llm-platform-career-change.txt").read_text()
    resume = sections.parse(text)
    system, user = prompts.content_system(), prompts.content_user(resume, text, "", [])
    sent_claude, sent_openai = [], []
    _patch(monkeypatch, "anthropic", _FakeAnthropic(sent_claude))
    llm.call(ANTHROPIC, system, user)
    _patch(monkeypatch, "openai", _FakeOpenAI(sent_openai))
    llm.call(OPENAI, system, user)

    claude_system = sent_claude[0]["system"][0]["text"]
    claude_user = sent_claude[0]["messages"][0]["content"]
    openai_system, openai_user = (m["content"] for m in sent_openai[0]["messages"])
    for sent_system, sent_user in ((claude_system, claude_user), (openai_system, openai_user)):
        assert "in the context of the other bullets in the same role or project" in sent_system
        assert "bullets under a Projects heading" in sent_system
        assert "PLACES (14; the only locators you may use):" in sent_user
        assert "exp[3].bullet[0]: A small serving benchmark I run each release" in sent_user
