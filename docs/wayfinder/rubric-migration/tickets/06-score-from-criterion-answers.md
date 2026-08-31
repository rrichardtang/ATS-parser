type: prototype (HITL)
status: open
claimed:
blocked-by: 05

# Score from criterion answers

## Question

`score.py` reads `llm_categories[category]` as `(mean, band_low, band_high)` — a mean of
the numbers providers returned, and the spread between them. After 05 there are no
numbers to average. Replace the path.

Per category, per provider sample: criterion answers → band (the lookup from 01) →
the band's value → blended with the rule channel at that category's `rule_share` (03).

## Three things that change meaning, not just shape

1. **Ensembling.** Today two providers' numbers are averaged. Under criteria, two
   providers answer the same questions; what is combined is *answers*, and the natural
   unit is per-criterion agreement, not a mean. Whether disagreeing judges average their
   bands, take the lower, or mark the category contested is a real decision and it is
   **not** inherited from the other map — raise it there if it turns out to be a rubric
   question rather than an implementation one.
2. **The disagreement range.** `score.py:127` widens a category to a low/high range when
   providers differ by 12 or more, noted as *"providers disagreed; shown as a range"*. A
   band gap is not a point gap: on `Production ownership` the smallest possible
   disagreement — one adjacent band — is 17 to 23 points, so the existing threshold
   would fire on every single split. The mechanism and its wording both need revisiting,
   and the other map's open question about a word for this (*contested* is its
   placeholder) lands exactly here.
3. **Withheld categories.** A withheld category is not a zero and not a 100. What it
   does to the composite, and what the report says in its place, has never been
   specified because nothing could withhold before.

Done when: a category's judged value is a lookup from criterion answers rather than a
number the model chose; the blend uses the per-category `rule_share`; two providers
splitting on a criterion produces something defensible and named; and a withheld
category neither inflates nor deflates the composite.
