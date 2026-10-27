# Why the project is built this way

## Separate quote checking from semantic checking

A quote can be real but irrelevant. A claim can be plausible but unsupported. We therefore show deterministic quote integrity separately from a model's support decision. The original PDF is always available for review.

## Use a different model for verification

Gemini or Ollama writes the draft. A small local NLI model checks it. This avoids simply asking the same generator whether it agrees with itself. It does not make the verifier independent of all training biases, and it does not make its labels human ground truth.

## Keep rejected claims visible

Unsupported claims are excluded from the accepted `answer` text but remain in the audit record and UI as clearly marked withheld claims. A researcher can inspect what the system removed instead of trusting a hidden filter.

## Reuse the reranked draft in comparisons

Generating a fresh draft for the verified variant would mix two causes: a different random answer and verification. The comparison endpoint therefore reuses the exact reranked draft. The verified card's latency is incremental to cached drafting; it is not an independent full-pipeline benchmark. Standalone `/api/ask` timing measures the full pipeline.

## Choose small CPU models

POTION static embeddings, TinyBERT reranking and a quantized DeBERTa verifier avoid a GPU requirement. This makes local setup and small hosted deployments practical. The trade-off is limited semantic capacity, visible in the false-insufficient fixture results. Static embeddings do not model word order as well as a contextual transformer.

## Store small PDFs in PostgreSQL for version one

The project limits PDFs to 4 MB. Keeping bytes, pages and chunks in one transaction makes indexing and deletion simple, durable and reviewable. It avoids pretending serverless local storage is persistent. This increases database size and bandwidth; private object storage should replace `bytea` when limits grow. This is a deliberate bounded-prototype choice, not a recommendation for a large document platform.

## Require an account before opening private documents

Email, password and password confirmation create an account with one workspace. Argon2id protects the password; a random session token stays in an HttpOnly cookie and only its hash is stored. Server-side sessions can expire or be revoked. This supports signing in on another device without exposing document access tokens to JavaScript.

Email is an identifier, not proof of identity. No email delivery service is configured, so recovery uses a private random code shown once. Losing both the password and code means losing access. Email verification, passkeys and MFA remain future work. Existing anonymous workspaces can be imported only by the browser holding their old cookie; importing assigns ownership, encrypts old content and invalidates that capability in one transaction.

## Encrypt stored content without claiming end-to-end encryption

The server needs readable passages for search and verification. AES-256-GCM encrypts PDFs, extracted text, filenames, email and saved answers before database writes. Each record is bound to its workspace, row and field. Losing or replacing the vault key makes these records unreadable; setup must keep a private backup.

The runtime can decrypt content. Vectors, hashes, sizes and timestamps remain queryable. This protects against a database-only disclosure but does not protect against a compromised application server. True end-to-end encryption would require a different processing architecture.

## Make external disclosure an explicit action

Gemini starts blocked, including direct API requests. Enabling it does not approve every future question: the user reviews the actual outgoing question and passages before each request. Common identifiers are masked and filenames become source labels. A short-lived, single-use approval binds the exact payload, model, question, sources and privacy-settings version. Editing any of them requires a fresh review.

Masking is a precaution, not reliable anonymization. Names and sensitive details can remain. The preview lets the user inspect those limits; local source excerpts and claim checking remain available without Gemini. History also starts off, while uploaded PDFs remain until explicitly deleted.

## Offer useful keyless tools without mislabelling them

Source excerpts and statement checking work locally. Generated explanations need an actual generative model. The app labels the difference and refuses to present excerpt mode as a normal RAG baseline. This keeps the interface usable while avoiding fake model execution.

## Prefer uncertainty over confident unsupported output

The conservative threshold can reject a correct claim. That cost must be measured with answer coverage and false abstentions. Lower unsupported-claim rates are not sufficient on their own: a system that says nothing would otherwise appear perfect.

## Keep research claims modest

Atomic facts, citation evaluation and post-generation checking already appear in FActScore, ALCE and RARR. The implemented pipeline is an engineering contribution and a platform for experiments. Any publishable novelty must come from a clearly tested policy or method and comparisons against prior work.
