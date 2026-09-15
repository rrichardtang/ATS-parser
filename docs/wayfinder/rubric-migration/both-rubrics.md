# Both rubrics on the same document

Ticket 07. The first time the new rubric scores a document next to the old one scoring
the same document, and what the difference is made of.

## 1. How the comparison is built

**The old column is the old code.** `03` replaced `models.Category` outright, so there
is no old path left in the package to run beside the new one, and a reconstruction here
would be a second implementation to disbelieve. `scripts/side_by_side.py` materialises
the tree from git at **`1418f0a`** — the commit that recorded
[baseline-agreement.md](../rubric-grounding/baseline-agreement.md) — and runs it in a
subprocess, because two `ats` packages cannot share an interpreter.

The pin matters more than it looks. `01` and `02` read as documentation tickets, but
`02` removed four `RULE_DIMENSION` entries, which changes what four rules cost. Pinning
one commit later would have silently moved the *before* picture.

**The judge channel.** The two rubrics ask different questions — five category scores
out of 100, against twenty-five criteria — so each side needs its own. Three modes:

| mode | old side | new side | where it applies |
|---|---|---|---|
| recorded | the 30 August baseline's two providers | the recorded `model-claude` criterion answers | the seven fixtures |
| rules-only | none | none | any document |
| live | its own content pass | its own content pass | needs credentials — **never run** |

The live path is written and unexercised: no session on this map has had provider
credentials. It is the half of 07 that cannot be finished from here.

**What is deliberately excluded on both sides:** the LLM slop pass. It is a second call
whose findings the migration changed only in where they file, and the deterministic slop
rules that carry most of that signal run on both sides already.

**What the recorded mode is not.** The old side carries two providers × two samples; the
new side carries one recorded judge. So the new column holds no inter-judge information
at all, and nothing here tests whether two judges agree under a band lookup. That is 09,
and it is the ticket's first prediction, below.

## 2. The seven fixtures, both judge channels recorded

```
document            old     new    moved   returned   n/a
buried_evidence    84.6    70.5    -14.1       20.0     0
hidden_text        40.0    40.0     +0.0       36.0     5
no_phone           91.7    76.2    -15.5       20.0     0
scanned             0.0     0.0     +0.0        0.0     5
slop               46.0    38.8     -7.2       44.0     0
strong             91.6    76.5    -15.1       20.0     0
two_column         77.0    86.6     +9.6       16.0     5
```

`returned` is what the advice-only rules used to deduct; `n/a` counts judged categories
the new rubric did not assess.

**The four that move down all move for the same reason, and it is 02's finding.**
`strong` loses 15.1: `Production ownership`, `Evaluation rigour` and `Resume craft` all
land at band A, and `Agentic systems` and `AI-assisted coding fluency` at band E on
every criterion, because the fixture was written before those categories existed. The
22.5 points 02 identified as a constant on this test set are the drop. Against that,
20 points of tool-coverage deductions come back as advice.

**`two_column` goes up 9.6, which is the one nobody predicted.** Its roles do not
survive extraction, so all five judged categories are withheld (05) and the composite
renormalises over what was checked (06). The old rubric judged it anyway — the model
read the visible text and scored five categories in the 60s and 70s — and those numbers
dragged the composite down. Withholding removes them. Two consequences worth stating
plainly:

- The new rubric scores a document *higher* for being unparseable than the old one did,
  once the parser gate's own deduction is the only charge. Whether that is right is a
  question about what `parse/multi-column` should cost, which is already on the map as
  unspecified.
- Its **human gate reads 100.0**, off `Title & seniority alignment` alone — 06's open
  item *"a subscore can renormalise down to one category"*, observed on a real document
  rather than predicted. The composite is defensible; the printed subscore is not.

`hidden_text` does not move at all: the fraud cap pins it at 40 on both sides, as 02
found under every candidate weight set.

## 3. The thirty drawn documents, deterministic layer only

08's set has no recorded judgement on either side, so this is the rule channel alone —
which is the right comparison for what `04` and `07 §1` did, and the wrong one for
anything about judges.

```
30 documents: 19 down, 11 up, 0 unchanged; mean -2.4, range -21.3 to +7.3
advice-only findings return a mean of 36.3 points per document (min 16, max 56)
```

**The deterministic layer is close to a wash, with large per-document swings.** That is
not what the ticket predicted (*"scores will move down, and unevenly"*): uneven yes,
down no — the mean move is -2.4 and a third of the documents rise. The 36 points per
document that advice-only rules stop deducting very nearly cancel the concentration
effect below.

### The finding: `Resume craft`'s rule channel is a constant

| | deductions in the category | floored at 0 |
|---|---|---|
| `Resume craft` (new) | 120 to 436, median 242 | **30 of 30** |
| `Production ownership` (new) | 0 to 108, median 36 | 1 of 30 |
| `Evaluation rigour` (new) | 0 to 12, median 0 | 0 of 30 |
| `Impact & quantification` (old) | 72 to 249, median 166 | 28 of 30 |
| `Writing quality` (old) | 28 to 208, median 82 | 11 of 30 |

A category floors at 0, so a category carrying 19 deducting rules on a full-length
resume is at 0 on every document — the same value for a good resume and a bad one. Two
things follow, and the second is the serious one:

1. **The rule channel carries no information on realistic documents.** It discriminates
   on the fixtures (4–6 bullets) because they are too short to accumulate 100 points of
   cost. It is constant on documents of 12–17 bullets.
2. **`rule_share` 0.7 then caps the whole category.** `blended = rule_score × 0.7 +
   band × 0.3`, so with `rule_score` pinned at 0, `Resume craft` cannot exceed **28.5**
   whatever a judge answers — on a category weighted 25, the largest in the authored
   block. A band-A document and a band-E document land 25.5 points apart on a scale
   where the category is worth 95.

**This is inherited, not caused.** The old rubric floored `Impact & quantification` on
28 of 30 with the same 0.7 blend. What the migration changed is that the mass is now
concentrated in one category instead of spread over two, and that category is the
heaviest one. It is also the second time this map has found the rubric calibrated on
short documents: 08 found `Resume craft` C4 and C5 stop discriminating past six bullets,
by a different mechanism — predicates that get harder with length — and this is the cost
side of the same page. Both go back to the other map.

### What refiling did

Consistent across the set, and visible per document in the full output:

```
contact/no-github       Credibility & verifiability -> Structure & formatting
content/ownership       Impact & quantification     -> Production ownership
content/no-outcome      Impact & quantification     -> Resume craft
content/passive-voice   Writing quality             -> Resume craft
slop/portable           Writing quality             -> Resume craft
slop/robotic-rhythm     Writing quality             -> Resume craft
```

`content/bullet-invariants` → `content/no-outcome` is a rename, not a disappearance
(04, implementing the other map's 12), and its cost falls with it — 120 to 96 on
`19-academic-terse-mid`, where it fires ten times under the old predicate bundle and
eight under the one predicate 04 left it. `cred/no-named-models` is retired
outright (03 §4). Both are declared in the script, because a raw rule-id diff reads a
rename as a deletion and would have reported 120 points vanishing.

## 4. The two predictions

**"The old rubric's disagreement was mostly calibration, and a band lookup should delete
that offset by construction."** Not tested. The new side has one recorded judge, so
there is no second reading to disagree with it. This is 09's measurement and the
comparison built here cannot stand in for it.

**"Scores will move down, and unevenly."** Half right, and the half that fails is
informative. With the judge channel present (§2) four of seven fall by 7 to 16 points
and one rises by 10. On the deterministic layer alone (§3) the mean move is -2.4 with a
29-point range and a third of documents rising. Direction is not a property of the
migration; it is a property of whether the document has evidence in the four behaviour
categories, which is exactly what 08's set was built to vary.

## 5. What 07 does not settle

- **The live path has never run.** Both sides are wired to call their own content pass
  and neither has. Until it does, the fixtures' new column rests on one recorded judge
  and the old column on a run from 30 August.
- **The owner's resume is not in this environment.** The ticket asks for it and
  `--doc <path>` is the command; it needs the machine that holds the file.
- **`private_resume_1` cannot go through this.** The baseline holds its judged category
  scores, redacted, but not the document, and a composite needs the deterministic
  findings too.
- **Nothing here says the new rubric is better.** It says what moved and why. The old
  path is not retired by this ticket and should not be until the live run and 09 exist.

## 6. Changed

- `scripts/side_by_side.py` — new. Materialises the baseline commit, runs both rubrics
  on one document, prints composite and gates, the three categories that carried over,
  the five retired against the five that replaced them, the band and unmet criteria
  behind each judged category, withheld categories, the advice-only rules with what
  they used to cost, refiling, and renames. `--summary` for one line per document.
- `tests/test_side_by_side.py` — 7 tests: the old tree still runs from the pin, the
  recorded judgements still cover the fixtures on both sides, a withheld document is
  never given a band, the rename and the retirement are still true of both trees, and
  the rendered comparison answers each of the four things the ticket asked for.
- `docs/wayfinder/rubric-migration/both-rubrics.md` — this.
