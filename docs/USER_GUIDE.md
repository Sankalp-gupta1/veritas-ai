# Use VeritasAI without learning the code

**[Open the live website](https://veritas-ai-v8lw.vercel.app/)**, create an account or sign in, and wait for **Workspace ready**. No installation is needed. Source excerpts and claim checks need no AI API key.

## Create your private workspace

Enter your **email**, a **password of at least 15 characters**, and **confirm password**. Use a unique passphrase. Save the recovery code shown on the next screen somewhere private; it lets you reset a forgotten password. There is no reset email and email ownership is not verified.

If the browser has research from the older version, leave **Move this browser's existing research into my new account** checked to keep it. Sign in with the same account on another device to see the same workspace.

## Before uploading

PDFs and extracted text are encrypted in the cloud database. The server decrypts them to work on your question; this is not end-to-end encryption. Start with authored samples or public documents. See [the privacy guide](PRIVACY.md) for the exact boundaries.

**External AI starts off. Answer history starts off.** The green privacy badge at the top opens **Privacy center**. You can use source excerpts and claim checks without enabling Gemini or entering a key. Uploaded PDFs stay until you delete them, even when history is off.

## The three panels

**Left: your library.** Add PDFs, choose which sources the app may use, or remove a document. A checkbox means “include this document when answering.” Clicking the file name opens it.

**Middle: your question and answer.** Start in the centered question box. Your question appears in a bubble on the right; the answer appears below it as individual claims. After an answer, the question box stays at the bottom.

**Right: the evidence.** Click a source under a claim to open this panel. “Evidence” shows extracted text with the exact quote highlighted. “PDF” opens the original page. The arrows change pages.

Use **Close sidebar** to make more space, or **Open sidebar** to bring your library back. When answer history is enabled, the most recent five saved questions appear in the sidebar. **Answer history** shows the full saved list.

The **+** button inside the question box attaches PDFs. Click the source count to choose which documents to search. **Enter** sends the question; **Shift+Enter** adds a new line. A successful send clears the box. If a request fails, your draft stays there so you can retry.

On a small screen, the sidebar opens as a drawer. Press **Escape**, click outside it, or use its close button to return. The evidence panel takes the available width; close it to return to the answer.

**Each question is independent.** The app searches the selected documents; it does not send previous answers as conversation memory. Include the subject in your next question instead of writing only “tell me more.”

## Ask a question or check a statement

**Ask your documents** finds information in the selected PDFs. Without a Gemini key, it returns matching excerpts. This is useful for finding passages but is not a synthesized explanation.

**Check a claim** checks a statement that you write. This works with local models and needs no generative API key. Keep the statement short and factual. For example: “The Cedar trial enrolled 120 adults.”

To get an AI-written explanation, first enable **Allow reviewed Gemini requests** in **Privacy center**. Open **AI settings**, choose Gemini and add your key. Ask a question, inspect the disclosure preview, then explicitly approve or cancel. No text is sent to Gemini just by opening the preview. Automatic masking can miss private information; read it before approving.

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

Connect a generative model, write one question, and click **Compare methods**. For Gemini, review both outgoing payloads and approve the request. The app runs:

1. Standard RAG: semantic retrieval and a cited draft.
2. Reranked RAG: the same candidate pool, reordered before drafting.
3. Verified RAG: the exact draft from step 2, with verification applied.

Click a method card to open its answer. A shorter answer is not automatically better. Some removed claims may have been useful and correct. Independent evaluation must measure both unsupported claims and lost answer coverage.

## Save or remove your work

**Answer history** reopens saved results. **Export evidence** downloads a JSON file with the question, claims, citations, source hashes, model information and timings. This file may contain text from your PDFs; keep it private if the documents are private.

Removing a PDF deletes its stored bytes, pages and chunks. It also deletes all saved answers in that workspace, because those answers may contain excerpts from the removed source. The app asks before doing this.

Open **Privacy center** to turn history on/off, export your text and answers, clear saved answers, delete all workspace data or delete your account. Account deletion asks for your current password and the word DELETE. Deleting active data does not instantly remove provider backups or external copies.

The small note below the question box says whether the next answer will be saved. When history is enabled, click it to make one answer temporary. Each completed answer also shows a privacy receipt: external AI used or not, and saved or not.

Use the sign-out icon next to your email on shared computers. **Sign out everywhere** revokes all sessions. A password change replaces your recovery code and signs out other sessions. The workspace locks after 30 minutes without activity. Sign in again to continue; your uploaded files remain.

## Common problems

| Message or situation | What to do |
|---|---|
| Scanned PDF has no readable text | Run OCR in a PDF tool, then upload the searchable copy. |
| File is too large | Export or split it into PDFs under 4 MB and 80 pages. |
| No answer appears | Select at least one document and write at least five characters. |
| External AI is blocked | Use source excerpts, or explicitly enable reviewed requests in Privacy center. |
| Preview expired or already used | Ask again to create a fresh preview; each approval is valid once for ten minutes. |
| Forgot password | Use your email and saved recovery code from the sign-in screen. |
| Gemini rejects the key | Check the key and model access in Google AI Studio. |
| Provider quota is exhausted | Wait, use your own permitted provider plan, or switch to local excerpts. |
| Quote is invalid | The app refuses to trust it. Retry with a narrower question. |
| A supported fact is withheld | Inspect the page. The small verifier may be wrong; record the failure for evaluation. |
| Workspace cannot connect | Check the database settings and migration; `/api/health` reports readiness. |

