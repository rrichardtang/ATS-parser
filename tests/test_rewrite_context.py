"""What the rewrite writer and its ranking judge are handed, with no provider and no network."""
from types import SimpleNamespace

from ats import budget, config, llm, passes, pipeline, prompts, rewrite_eval
from ats.extract import extract
from ats.llm import Provider
from ats.models import Category, Finding, Gate, Severity
from ats.sections import Resume, Role, parse

DIGEST = {"document_count": 2, "required": [{"term": "skill/pytorch", "doc_frequency": 2}]}
LOC = "exp[0].bullet[1]"
CRITERION = "production-ownership/C1"
ROLE = Role(heading="Acme", title="ML Engineer", company="Acme Corp",
            bullets=["Built the ranker", "Owned GLIDE-ME end to end", "Ran the on-call rota"])


def _finding(rule_id, locator=LOC, why="No destination named", fix="Say where it shipped."):
    return Finding(rule_id=rule_id, category=Category.RESUME_CRAFT, gate=Gate.MANAGER,
                   severity=Severity.MAJOR, message=why, fix=fix, evidence="GLIDE-ME",
                   locator=locator, source="llm:x")


def _payload(*findings):
    return passes.target_payload(Resume(roles=[ROLE]), LOC, list(findings))


def test_a_placed_finding_carries_its_criterion_quote_and_the_role():
    payload = _payload(_finding(CRITERION))

    assert payload["defects"] == [{"criterion": CRITERION, "evidence": "GLIDE-ME",
                                   "why": "No destination named", "fix": "Say where it shipped."}]
    assert payload["role"] == "ML Engineer, Acme Corp"
    assert payload["other_bullets_in_role_context_only"] == ["Built the ranker", "Ran the on-call rota"]
    criterion = passes.referenced_criteria([payload])[CRITERION]
    assert set(criterion) == set(passes.CRITERION_FIELDS) and criterion["question"]


def test_a_deterministic_finding_keeps_its_message_and_fix_line():
    assert _payload(_finding("slop/hollow", why="m", fix="f"))["defects"] == ["m -> f"]


def test_each_criterion_is_listed_once_however_many_bullets_cite_it():
    resume = Resume(roles=[ROLE])
    targets = [passes.target_payload(resume, f"exp[0].bullet[{i}]", [_finding(CRITERION)])
               for i in range(3)]
    user = prompts.rewrite_user(targets, passes.referenced_criteria(targets), None)

    assert list(passes.referenced_criteria(targets)) == [CRITERION]
    assert user.count(passes.criteria_by_rule_id()[CRITERION]["yes_requires"]) == 1


def test_the_writer_prompt_carries_the_digest_when_given_and_not_otherwise():
    targets = [_payload()]
    assert "pytorch" in prompts.rewrite_user(targets, {}, DIGEST)
    assert "Postings" not in prompts.rewrite_user(targets, {}, None)


def test_the_judge_is_told_each_bullets_defects():
    user = prompts.judge_user([{"locator": LOC, "original": "o", "defects": ["Named system: Is it named?"],
                                "candidates": []}])
    assert "Named system: Is it named?" in user
    assert "defects" in prompts.JUDGE_SYSTEM


def test_the_rewrite_pass_gives_the_judge_the_criterion_name_and_question(monkeypatch):
    seen = []
    monkeypatch.setattr(llm, "_dispatch", lambda p, system, user, t: seen.append((system, user)) or
                        '{"rewrites": [{"locator": "%s", "rewritten": "Owned GLIDE-ME, end to end, for the team", '
                        '"what_changed": "x"}]}' % LOC)
    passes.rewrite_pass([Provider("openai", "k", "m")], Resume(roles=[ROLE]), [_finding(CRITERION)],
                        1, 1, True, 1.0, 0.0, DIGEST)

    criterion = passes.criteria_by_rule_id()[CRITERION]
    judge_user = next(user for system, user in seen if system == prompts.JUDGE_SYSTEM)
    assert f"{criterion['name']}: {criterion['question']}" in judge_user
    assert "pytorch" in next(user for system, user in seen if "rewrite weak" in system)


def test_generate_rewrites_passes_the_digest_to_the_pass(monkeypatch):
    seen = []
    monkeypatch.setattr(pipeline, "app_providers", lambda *a: [object()])
    monkeypatch.setattr(pipeline, "non_content_providers", lambda providers, settings: providers)
    monkeypatch.setattr(config, "jd_digest", lambda: DIGEST)
    monkeypatch.setattr(passes, "rewrite_pass",
                        lambda *a: seen.append(a[-1]) or passes.ensemble.PassResult())
    report = SimpleNamespace(findings=[], notes=[], run_meta={}, rewrites=[])
    pipeline.generate_rewrites(report, Resume(), {"openai": "k"}, {})

    assert seen == [DIGEST]


def test_the_dry_run_estimate_is_at_least_the_largest_real_writer_prompt(fixtures, monkeypatch):
    resume = parse(extract(str(fixtures["strong"])).text)
    findings = [_finding(rid, loc) for loc, _ in resume.bullets
                for rid in list(passes.criteria_by_rule_id())[:5]]
    seen = []
    monkeypatch.setattr(llm, "_dispatch", lambda p, system, user, t: seen.append(system + user) or "{}")
    passes.rewrite_pass([Provider("openai", "k", "m")], resume, findings, 1, 1, False, 1.0, 0.0,
                        config.jd_digest())

    assert budget.input_tokens(*rewrite_eval.writer_prompt(resume, config.jd_digest())) >= \
        budget.input_tokens(seen[0], "")
