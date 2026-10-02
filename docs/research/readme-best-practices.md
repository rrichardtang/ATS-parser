# README best practices for an AI engineering portfolio project

Researched 2026-10-02 for the `README.md` of this repo. The audience is a recruiter or
hiring manager screening for an AI engineer. They skim first and read closely only if the
skim works.

**How the sources were read.** The sandbox blocked `docs.github.com`, `opensource.guide`,
`makeareadme.com`, `shields.io` and `github.blog`. Each claim below links to the public page,
but the text was checked against the page's own source repository:
[github/docs](https://github.com/github/docs) (content/ and data/reusables/),
[github/opensource.guide](https://github.com/github/opensource.guide),
[dguo/make-a-readme](https://github.com/dguo/make-a-readme) (`pages/index.tsx`) and
[badges/shields](https://github.com/badges/shields). The example READMEs were read raw from
`main`. The GitHub Blog claims could only be checked through search-result summaries, so
they are marked **[unverified excerpt]**.

Labels: **[Fact]** is what a source says. **[Example]** is what a respected repo does.
**[Opinion]** is a stated view about hiring. **[Inference]** is my own reasoning from the above.

## 1. What a README is for

- [Fact] GitHub says a README tells people "why your project is useful, what they can do with
  your project, and how they can use it". It usually covers what the project does, why it is
  useful, how to get started, where to get help, and who maintains it.
  ([GitHub Docs: About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes))
- [Fact] The Open Source Guide asks the same four questions (what, why, how to start, where to
  get help). It adds: "If your only goal is to show off your work, you may not even want
  contributions, and even say so in your README."
  ([opensource.guide: Starting a project](https://opensource.guide/starting-a-project/#writing-a-readme))
- [Fact] "A README should only contain information necessary for developers to get started
  using and contributing to your project. Longer documentation is best suited for wikis."
  ([About READMEs § Wikis](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes#wikis))
- [Opinion, GitHub Blog] Recruiters and hiring managers use repositories to see "evidence that
  you can code" and to get "insight into your problem-solving skills".
  ([Career tips for beginner developers](https://github.blog/developer-skills/career-growth/career-tips-for-beginner-developers/)) **[unverified excerpt]**
- [Opinion, GitHub Blog] For an AI developer portfolio: "clear names, detailed README files, and
  instructions for others to replicate your work".
  ([Vibe coding: your roadmap to becoming an AI developer](https://github.blog/ai-and-ml/vibe-coding-your-roadmap-to-becoming-an-ai-developer/)) **[unverified excerpt]**
- No primary-source study of how recruiters read READMEs turned up. Anything more specific
  than the two blog lines above would be folklore.

## 2. Recommended section order

**Standard Readme** ([spec](https://github.com/RichardLitt/standard-readme/blob/main/spec.md)) [Fact]:
Title, Banner, Badges, Short Description, Long Description, Table of Contents, Security,
Background, Install, Usage, Extra Sections, API, Maintainers, Thanks, Contributing, License.
The required sections are Title, Short Description, ToC, Install, Usage, Contributing and
License. Its rules:
- The short description is under 120 characters, has no heading of its own, and matches the
  GitHub description.
- A ToC is required unless the README is under 100 lines, and it must cover every `##` heading.
- License is the last section, with its SPDX id and owner.

**makeareadme.com** ([source](https://github.com/dguo/make-a-readme/blob/main/pages/index.tsx)) [Fact]:
Name, Description, Badges, Visuals, Installation, Usage, Support, Roadmap, Contributing,
Authors and acknowledgment, License, Project status. For the description: "If there are
alternatives to your project, this is a good place to list differentiating factors."

**What respected AI repos actually do** [Example]:
| Repo | Order |
|---|---|
| [anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python/blob/main/README.md) | Title, 1 badge, one-sentence description, Documentation link, Installation, Getting started, Requirements, Contributing, License (55 lines) |
| [openai-python](https://github.com/openai/openai-python/blob/main/README.md) | Title, 1 badge, 3-line description, Documentation, Installation, Usage, then a long reference (about 1,250 lines; it is an SDK) |
| [transformers](https://github.com/huggingface/transformers/blob/main/README.md) | Logo, badges, one-line tagline, hero image, Installation, Quickstart, **Why should I use**, **When shouldn't I use**, examples, Citation |
| [ragas](https://github.com/explodinggradients/ragas/blob/main/README.md) | Logo, badges, nav links (Docs / Quick start / Discord), one-line value prop, Key Features, Installation, Quickstart, Community, Cite |
| [dspy](https://github.com/stanfordnlp/dspy/blob/main/README.md) | Logo, tagline as heading, docs link, 1 badge, two-paragraph pitch, Installation, Citation; everything else is on dspy.ai |

[Inference] The order these share, adapted for a portfolio project: **name, then a one-line
value prop, then a visual, then quickstart, then why and when not to use it, then how it works
(architecture), then how it is measured (evals and cost), then development and tests, then
limitations and privacy, then credits and license.**

## 3. Above the fold

- [Fact] The one-liner: Standard Readme caps the short description at 120 characters. In the
  examples it is one sentence ("State-of-the-art pretrained models for inference and training";
  "Objective metrics, intelligent test generation, and data-driven insights for LLM apps").
- [Fact] Visuals: "it can be a good idea to include screenshots or even a video (you'll
  frequently see GIFs rather than actual videos)." ([makeareadme](https://www.makeareadme.com/#visuals))
  transformers and ragas both put an image before any prose.
- [Fact] Quickstart: "Listing specific steps helps remove ambiguity and gets people to using
  your project as quickly as possible." "Use examples liberally, and show the expected output
  if you can." ([makeareadme](https://www.makeareadme.com/#installation))
- [Fact] Image paths: GitHub resolves relative links and image paths per branch, and
  "Absolute links may not work in clones", so prefer `docs/images/demo.png` over an external
  URL. ([About READMEs § Relative links](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes#relative-links-and-image-paths-in-markdown-files))
- [Fact] Outside the README, a social preview image (at least 640x320; 1280x640 is best) and
  repository topics shape how the repo looks when linked or searched.
  ([social preview](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview),
  [topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics))

## 4. Architecture and evaluation

- [Fact] GitHub renders Mermaid in fenced ` ```mermaid ` blocks in Markdown files, so a diagram
  can live in the README as text.
  ([Creating diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams))
- [Fact] `<details><summary>` collapses material that "may not be relevant or interesting to
  every reader". Use it for long diagrams or tables.
  ([Collapsed sections](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections))
- [Example] transformers has a **"When shouldn't I use Transformers?"** section. A respected
  project states its own limits in the README.
- [Example] ragas, itself an eval tool, leads with "Objective metrics" and a runnable scoring
  example. It puts methodology in its docs site, not the README.
- [Inference] None of the sources sets out how to present LLM evaluation. For a hiring-manager
  reader, the README should say three things in a short **Evaluation** section:
  1. **What is measured, and against what.** For example: inter-judge agreement (Krippendorff's
     alpha), self-consistency on rerun, and a fixture set, each named.
  2. **The latest numbers, in a small table with date and model versions**, plus the command
     that reproduces them. A harness with no published results reads as unproven.
  3. **Cost and calls per run.** A `--dry-run` budget and $/resume are signals of engineering
     judgement that recruiters can read without ML background.
  Put full methodology, per-category tables and run logs in `docs/`, and link to them.

## 5. Badges: signal vs noise

- [Fact] makeareadme describes badges as small images "that convey metadata, such as whether or
  not all the tests are passing", made with Shields.
- [Fact] A GitHub Actions workflow status badge shows the workflow's state. Badges in private
  repos cannot be embedded externally.
  ([Add a status badge](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge))
- [Fact] Shields has static badges (`/badge/<label>-<message>-<color>`) and an endpoint badge
  that reads JSON, which could publish a live metric.
  ([static badges](https://github.com/badges/shields/blob/master/frontend/docs/static-badges.md),
  [endpoint service](https://github.com/badges/shields/blob/master/services/endpoint/endpoint.service.js))
- [Example] The Anthropic and OpenAI SDKs show **one** badge (PyPI version). dspy shows one.
  transformers and ragas show 6 or 7, mostly license, release and community.
- [Inference] Worth having for a non-packaged portfolio app: **CI tests passing** (real,
  verifiable), **license**, and **Python version**. Noise: "Made with Python", stars or
  downloads on a new repo, hit counters, and static "AI-powered" badges, since they claim
  nothing anyone can check.

## 6. Length and tone

- [Fact] "While a README can be too long and detailed, too long is better than too short. If you
  think your README is too long, consider utilizing another form of documentation rather than
  cutting out information." ([makeareadme](https://www.makeareadme.com/))
- [Fact] It is rendered in full up to 500 KiB, and GitHub builds an "Outline" ToC from headings
  automatically. Standard Readme still requires an in-file ToC past 100 lines.
  ([About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes))
- [Fact] "Consider the possibility that whoever is reading your README is a novice."
  ([makeareadme](https://www.makeareadme.com/#installation))
- [Example] The three most-copied AI SDK READMEs (Anthropic, dspy, ragas) are 55 to 200 lines.
  They pitch in one or two sentences and link out for depth.
- [Inference] Tone: plain, declarative, specific numbers, no marketing superlatives.

## 7. What to move into `docs/`

- [Fact] GitHub: longer documentation belongs in a wiki or other docs. makeareadme links to
  "more sophisticated examples if they are too long to reasonably include in the README".
- [Fact] Standard files GitHub surfaces automatically sit at the root, in `.github/` or in
  `docs/`: LICENSE, CONTRIBUTING, CODE_OF_CONDUCT and SECURITY.md.
  ([opensource.guide](https://opensource.guide/starting-a-project/#launching-your-own-open-source-project),
  [Best practices for repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories))
- [Fact] Use relative links to those files (`[methodology](docs/evaluation.md)`).
- [Inference] Move these out: detailed rubric provenance, corpus-building steps, per-pass
  algorithm detail, the full scoring ledger spec, and contributor workflow (wayfinder, harness).
  Keep in the README: pitch, demo, quickstart, a one-screen architecture, the headline eval
  numbers, limits and privacy, and license.

## Checklist for this repo

Current `README.md`: 334 lines, 14 `##` sections, no ToC, no screenshot (`docs/images/` is
empty), no LICENSE file, no `.github/workflows/`, and the agreement harness has no published
numbers.

- [ ] Write a one-line value prop under 120 characters, and use the same text as the GitHub
      repo description.
- [ ] Add a screenshot or GIF of a real report (synthetic fixture resume, not `runs/` data) at
      `docs/images/`, linked relatively, directly under the one-liner.
- [ ] Keep the 3-line quickstart above the fold, and add one line of expected output.
- [ ] Add a ToC, or cut the README below 100 lines, as Standard Readme requires.
- [ ] Add an **Evaluation** section: the agreement harness metrics, a dated results table with
      model ids, the reproduce command, and calls and cost per resume.
- [ ] Keep "What this is not". It plays the same role as transformers' "When shouldn't I use".
- [ ] Wrap the Mermaid diagram in `<details>` or shorten it to one screen.
- [ ] Move "Where the rubric comes from", "Your personal JD corpus", "Rule provenance" and the
      pass-3 detail into `docs/` and link to them.
- [ ] Add a LICENSE file and a License section as the last section, and confirm that vendored
      `no-ai-slop` MIT attribution stays.
- [ ] Add a CI workflow running `pytest`, and use its status badge plus license and Python
      badges only.
- [ ] Say whether contributions are welcome. A portfolio repo can say no
      (opensource.guide).
- [ ] Set repo topics (`llm`, `evals`, `resume`, `ats`) and a 1280x640 social preview image.
