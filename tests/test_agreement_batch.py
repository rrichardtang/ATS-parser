"""Claude's content calls through the Message Batches API, against a fake client.

No network. A batched judgement has to be the one a live call would have produced:
same request out, same parsing back, so a batched run measures what a live one does.
"""
import json
from types import SimpleNamespace

import pytest

from ats import agreement, agreement_batch, llm
from ats.llm import Provider
from scripts import agreement_harness as harness
from tests.test_agreement import AGREEING

CLAUDE = Provider("anthropic", "k", "claude-sonnet-5")


def _message(text, stop_reason="end_turn"):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                           stop_reason=stop_reason,
                           usage=SimpleNamespace(output_tokens=1))


def _result(custom_id, kind="succeeded", **fields):
    return SimpleNamespace(custom_id=custom_id, result=SimpleNamespace(type=kind, **fields))


class _FakeClient:
    """`messages.stream` for the live path, `messages.batches` for the batch path."""

    def __init__(self, reply=AGREEING, status="ended"):
        self.reply, self.status = reply, status
        self.streamed, self.created = [], []
        self.messages = self
        self.batches = self

    def stream(self, **params):
        self.streamed.append(params)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(())

    def get_final_message(self):
        return _message(self.reply)

    def create(self, *, requests):
        self.created = requests
        return SimpleNamespace(id="msgbatch_1")

    def retrieve(self, batch_id):
        assert batch_id == "msgbatch_1"
        counts = SimpleNamespace(processing=1, succeeded=0, errored=0)
        return SimpleNamespace(processing_status=self.status, request_counts=counts)

    def results(self, batch_id):
        # Reversed, so anything keyed by position rather than custom_id goes wrong.
        return iter([_result(r["custom_id"], message=_message(self.reply))
                     for r in reversed(self.created)])


@pytest.fixture
def client(monkeypatch, tmp_path):
    fake = _FakeClient()
    monkeypatch.setattr(llm, "_anthropic_client", lambda api_key: fake)
    monkeypatch.setattr(harness, "DEFAULT_OUT", tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    return fake


def _submit(fixtures, samples=2):
    targets = [("strong", str(fixtures["strong"])), ("scanned", str(fixtures["scanned"]))]
    return harness.submit_batch([CLAUDE], targets, samples, 0.7, [])


def test_custom_id_round_trips():
    assert agreement_batch.parse_custom_id(agreement_batch.custom_id(12, 3)) == (12, 3)


def test_a_batch_request_is_the_request_a_live_call_streams(client, fixtures):
    agreement.judge_resume([CLAUDE], "strong", str(fixtures["strong"]), 1, 0.0)
    _submit(fixtures, samples=1)

    assert [r["params"] for r in client.created] == client.streamed
    assert [r["custom_id"] for r in client.created] == ["doc0-s0"], \
        "the scanned document is skipped before any request"


def test_collect_builds_the_judgments_a_live_run_does(client, fixtures, tmp_path):
    live = agreement.judge_resume([CLAUDE], "strong", str(fixtures["strong"]), 2, 0.7)
    saved = _submit(fixtures)
    out = tmp_path / "run.json"
    harness.collect_batch(saved, out, [])

    run = agreement.HarnessRun.from_dict(json.loads(out.read_text()))
    batched = run.resumes[0]
    assert not batched.errors
    key = lambda j: j.sample  # noqa: E731
    assert sorted(batched.judgments, key=key) == sorted(live.judgments, key=key)
    assert run.resumes[1].skipped
    assert agreement_batch.NOTE in run.meta["notes"]


def test_a_batch_still_processing_exits_non_zero_without_saving(client, fixtures, tmp_path):
    saved = _submit(fixtures)
    client.status = "in_progress"
    out = tmp_path / "run.json"

    with pytest.raises(SystemExit) as stopped:
        harness.collect_batch(saved, out, [])
    assert "in_progress" in str(stopped.value.code)
    assert not out.exists()


def test_failed_truncated_and_unparseable_results_are_recorded_errors(fixtures):
    run = agreement.HarnessRun(resumes=[agreement.prepare("strong", str(fixtures["strong"]))[0]])
    results = [
        _result("doc0-s0", "errored", error={"type": "overloaded_error"}),
        _result("doc0-s1", "expired"),
        _result("doc0-s2", "canceled"),
        _result("doc0-s3", message=_message('{"categories": {', stop_reason="max_tokens")),
        _result("doc0-s4", message=_message("not json at all")),
    ]
    agreement_batch.merge(run, CLAUDE, results)

    errors = run.resumes[0].errors
    assert not run.resumes[0].judgments
    assert len(errors) == 5
    assert "errored" in errors[0] and "overloaded_error" in errors[0]
    assert "expired" in errors[1] and "canceled" in errors[2]
    assert "token cap" in errors[3]
    assert "not repaired in batch mode" in errors[4]
