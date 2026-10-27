# Research protocol

## Question

Does claim-level verification reduce unsupported statements at comparable answer coverage, and what extra latency does it require?

This is a hypothesis to test, not an established result of the current prototype.

## Controlled variants

| Variant | Candidate retrieval | Context | Draft | Verification |
|---|---|---|---|---|
| `rag` | Same dense top 20 | First 5 | Generator call A | Off |
| `rerank` | Same dense top 20 | Reranked top 5 | Generator call B | Off |
| `verified` | Same dense top 20 | Same reranked top 5 | Exact cached call B | On |

Freeze document hashes, extraction code, chunks, model revisions, prompts, context budget and generation settings. The current generator uses temperature zero, which still does not guarantee deterministic provider output. Save every raw run.

Verification currently uses the same retrieved context. If a future version retrieves extra evidence while verifying, add a matched extra-retrieval baseline so the effect of verification is not confounded with extra context.

## Two evaluation tracks

**Verifier diagnostics:** The included 24 authored pairs check support, contradiction and insufficient evidence. Their labels were fixed before inference. They are small development fixtures, not a statistically representative sample. Do not publish their score as research-paper hallucination reduction.

**Application evaluation:** Build roughly 20-30 licensed documents, 20 development questions and 100 held-out questions. Separate document families between development and held-out evaluation. Include answerable, unanswerable, numerical, multi-document and scope-matched conflict questions. Annotate required facts, source pages and evidence spans before scoring system outputs.

SciFact can provide a separate verifier benchmark with claim/abstract evidence labels. It does not supply original PDF page references, so it cannot replace page-provenance tests. Use official claim IDs and avoid leakage from flattened wrapper rows. Do not claim hidden-test performance without official labels/evaluation access.

## Collect and review real outputs

With the application running and a real Gemini key supplied in your environment:

```bash
python research/run_experiment.py --out research/private-runs/run-001
```

The command creates a disposable account, uploads authored PDFs, calls the real comparison endpoint, saves the results and deletes its account in cleanup. History stays off. For Gemini, it shows the exact outgoing masked question and passages and requires you to type `SHARE` for each question. The key is sent only on the approved generation request. A provider failure leaves partial raw outputs visible; it does not invent missing predictions.

The privacy transformation is part of the experiment configuration: common identifiers are replaced with placeholders, source filenames become labels, and returned placeholders are restored before citation checks. Apply the same policy to every variant and retain its configuration with the raw outputs. Different context selections can produce different masked fields. Masking may affect answer quality, especially identifier-dependent questions; measure this separately before attributing an improvement to verification. Do not compare an older unmasked baseline against a masked verified variant as though verification were the only change.

Review `claims_for_review.csv`. Variant names, model verdicts and scores are hidden from the review sheet. Assign:

- `gold_label`: supported, contradicted or insufficient.
- `citation_set_supports`: yes or no, based on the complete cited evidence set.
- `covered_fact_ids`: semicolon-separated IDs from the question's predefined facts.
- `reviewer`: reviewer identifier.

For serious evaluation, use two annotators, adjudicate disagreements and report agreement. A reviewer must read the actual documents; quotes alone may omit important qualifications. A second model can assist, but model judgments must not be presented as independent human evaluation.

Then run:

```bash
python research/score_experiment.py research/private-runs/run-001
```

The scorer refuses missing labels, unknown gold facts and incomplete variant sets. It creates `scored_metrics.json` and `rag_comparison.png`. No generative comparison results are included in the initial source release because no live generator key was available.

## Metrics

| Metric | Definition |
|---|---|
| Unsupported retained-claim rate | Independently judged contradicted or insufficient retained claims / all retained factual claims |
| Citation-set support rate | Retained claims whose complete cited set independently supports the claim and whose quotes pass integrity / all retained claims |
| Answer-fact coverage | Distinct required facts recovered by supported retained claims / predefined required facts |
| Correct abstention rate | Abstentions on unanswerable questions / unanswerable questions |
| False abstention rate | Abstentions on answerable questions / answerable questions |
| NLI macro-F1 | Mean of per-class F1 for support, contradiction and insufficient evidence |
| Latency | Recorded request time, with p50/p95 and explicit cold/cached conditions |

Citation-set support rate is intentionally not called ALCE citation precision. ALCE's precision metric also evaluates individual citations' necessity within a jointly supportive set. That more detailed metric remains future work.

Undefined ratios are null, not 0 or 100%. Withholding every claim must not earn a perfect factual score. Report claim count, answer coverage and abstention alongside unsupported rate.

## Uncertainty and bias

The scorer performs 2,000 paired bootstrap samples by question, with seed 42, for verified-minus-reranked unsupported rate. Some samples may have no retained claims; report the usable sample count. Small or convenience samples do not support broad population claims even when a narrow interval appears.

The app's thresholds were selected as initial conservative operational settings, not tuned to maximize the fixture score. Three supported fixture claims were withheld. Do not repeatedly tune on the held-out set to erase such failures.

The comparison endpoint caches retrieval and reuses the reranked draft for the verified stage. Its displayed per-variant times do not represent three independent end-to-end requests. Use standalone calls with controlled warm/cold conditions for a fair latency benchmark.

## Four-month research roadmap

1. Weeks 1-3: harden ingestion, collect licensed sources, formalize annotation rules.
2. Weeks 4-6: run development diagnostics, improve sentence segmentation and calibrate thresholds.
3. Weeks 7-10: freeze the test protocol and collect blind judgments on held-out questions.
4. Weeks 11-13: run controlled ablations and analyse false support, missed support, conflicts and citation errors.
5. Weeks 14-16: write the final empirical report, reproduce results, release permitted artifacts and decide whether the contribution supports a paper submission.

## Prior work

- ALCE: https://aclanthology.org/2023.emnlp-main.398/
- FActScore: https://aclanthology.org/2023.emnlp-main.741/
- RARR: https://aclanthology.org/2023.acl-long.910/
- Self-RAG: https://github.com/AkariAsai/self-rag
- SciFact: https://aclanthology.org/2020.emnlp-main.609/

These works establish that citations, atomic facts and verification are existing research ideas. VeritasAI must earn a contribution through a new, evaluated method or a well-supported empirical finding.
