# Use VeritasAI without learning the code

**[Open the live website](https://veritas-ai-v8lw.vercel.app/)** and wait for **Workspace ready**. No installation is needed. Source excerpts and claim checks need no AI API key.

## The three panels

**Left: your library.** Add PDFs, choose which sources the app may use, or remove a document. A checkbox means “include this document when answering.” Clicking the file name opens it.

**Middle: your question and answer.** Start in the centered question box. Your question appears in a bubble on the right; the answer appears below it as individual claims. After an answer, the question box stays at the bottom.

**Right: the evidence.** Click a source under a claim to open this panel. “Evidence” shows extracted text with the exact quote highlighted. “PDF” opens the original page. The arrows change pages.

Use **Close sidebar** to make more space, or **Open sidebar** to bring your library back. The most recent five questions appear in the sidebar. **Answer history** shows the full saved list.

The **+** button inside the question box attaches PDFs. Click the source count to choose which documents to search. **Enter** sends the question; **Shift+Enter** adds a new line. A successful send clears the box. If a request fails, your draft stays there so you can retry.

On a small screen, the sidebar opens as a drawer. Press **Escape**, click outside it, or use its close button to return. The evidence panel takes the available width; close it to return to the answer.

**Each question is independent.** The app searches the selected documents; it does not send previous answers as conversation memory. Include the subject in your next question instead of writing only “tell me more.”

## Ask a question or check a statement

**Ask your documents** finds information in the selected PDFs. Without a Gemini key, it returns matching excerpts. This is useful for finding passages but is not a synthesized explanation.

**Check a claim** checks a statement that you write. This works with local models and needs no generative API key. Keep the statement short and factual. For example: “The Cedar trial enrolled 120 adults.”

To get an AI-written explanation, open **AI settings**, choose Gemini and add your key. Then return to **Ask your documents**.

## What the labels mean

| Label | Meaning | What you should do |
|---|---|---|
| Supported by source | The quote exists and the language model finds sufficient support. | Read the quote, especially for important decisions. |
| Possible disagreement | One passage supports the claim and another appears to contradict it. | Compare both sources and check dates, populations and methods. |
| Contradicted · withheld | Retrieved text appears to contradict the claim. | Do not treat this claim as part of the accepted answer. |
| Insufficient evidence · withheld | The quote is missing, invalid or not supportive enough. | Add a relevant document or narrow the question. |
| Not checked | You opened an unverified comparison variant. | This is a baseline answer, not a verified one. |

“Supported” does not mean that the source is scientifically correct. An inaccurate document can support an inaccurate claim. The check concerns **what your documents establish**.

## Example walkthrough

1. Click **Try our authored sample documents**. This downloads and genuinely uploads three small fictional PDFs into your workspace.
2. Select only `cedar-trial-report.pdf`.
3. Choose **Check a claim** and enter: “The Cedar trial enrolled 120 adults.”
4. Open its citation. It should point to PDF page 1.
5. Ask whether a company funded the trial. The sample does not provide that information, so the app should withhold that claim.
6. Select the Cedar reanalysis too. Check: “The Cedar sleep-extension group improved its attention score by 12 points.” Open the supporting citation and the corrected report under **Evidence to compare**.

The models can make mistakes even on these examples. That is why the actual quotes remain visible and the evaluation includes failure cases.

## Compare methods

Connect a generative model, write one question, and click **Compare methods**. The app runs:

1. Standard RAG: semantic retrieval and a cited draft.
2. Reranked RAG: the same candidate pool, reordered before drafting.
3. Verified RAG: the exact draft from step 2, with verification applied.

Click a method card to open its answer. A shorter answer is not automatically better. Some removed claims may have been useful and correct. Independent evaluation must measure both unsupported claims and lost answer coverage.

## Save or remove your work

**Answer history** reopens saved results. **Export evidence** downloads a JSON file with the question, claims, citations, source hashes, model information and timings. This file may contain text from your PDFs; keep it private if the documents are private.

Removing a PDF deletes its stored bytes, pages and chunks. It also deletes all saved answers in that workspace, because those answers may contain excerpts from the removed source. The app asks before doing this.

Your browser cookie provides workspace access. There is no email login or recovery system in this version. If you clear your cookies or switch devices, the old workspace does not automatically follow you. Download anything you need first.

## Common problems

| Message or situation | What to do |
|---|---|
| Scanned PDF has no readable text | Run OCR in a PDF tool, then upload the searchable copy. |
| File is too large | Export or split it into PDFs under 4 MB and 80 pages. |
| No answer appears | Select at least one document and write at least five characters. |
| Gemini rejects the key | Check the key and model access in Google AI Studio. |
| Provider quota is exhausted | Wait, use your own permitted provider plan, or switch to local excerpts. |
| Quote is invalid | The app refuses to trust it. Retry with a narrower question. |
| A supported fact is withheld | Inspect the page. The small verifier may be wrong; record the failure for evaluation. |
| Workspace cannot connect | Check the database settings and migration; `/api/health` reports readiness. |

