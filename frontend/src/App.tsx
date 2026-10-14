import { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  Clock3,
  Download,
  FilePlus2,
  FileText,
  FlaskConical,
  FolderOpen,
  History,
  Layers3,
  LoaderCircle,
  Menu,
  MessageSquare,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
  AlertCircle,
  PanelLeftClose,
  LockKeyhole,
} from "lucide-react";
import { api, exportJson } from "./api";
import { ClaimCard } from "./ClaimCard";
import { EvidencePanel } from "./EvidencePanel";
import { SettingsDialog } from "./SettingsDialog";
const Research = lazy(() =>
  import("./Research").then((module) => ({ default: module.Research })),
);
import type { Answer, Citation, DocumentRecord, Run, Settings } from "./types";

const questions = [
  "What are the main findings and their limitations?",
  "Where do these documents disagree?",
  "What evidence supports the key conclusion?",
];
type Health = {
  status: string;
  gemini_configured: boolean;
  ollama_available: boolean;
};

export default function App() {
  const [view, setView] = useState<"workspace" | "research" | "history">(
    "workspace",
  );
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [queryMode, setQueryMode] = useState<"ask" | "verify">("ask");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [comparison, setComparison] = useState<Answer[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [settings, setSettings] = useState<Settings>({
    provider: "extractive",
    model: "gemini-3.5-flash-lite",
    key: "",
  });
  const [showSettings, setShowSettings] = useState(false);
  const [activeDoc, setActiveDoc] = useState<string | null>(null);
  const [citation, setCitation] = useState<Citation | null>(null);
  const [sidebar, setSidebar] = useState(false);
  const [drag, setDrag] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const textInput = useRef<HTMLTextAreaElement>(null);

  async function loadData() {
    const [d, r] = await Promise.all([
      api<{ documents: DocumentRecord[] }>("/documents"),
      api<{ runs: Run[] }>("/runs"),
    ]);
    setDocuments(d.documents);
    setRuns(r.runs);
    return d.documents;
  }
  async function initialize() {
    setError("");
    try {
      const h = await api<Health>("/health");
      setHealth(h);
      await api("/workspace", { method: "POST" });
      const d = await loadData();
      setSelected(d.map((x) => x.id));
      setReady(true);
      if (h.gemini_configured)
        setSettings((s) => ({ ...s, provider: "gemini" }));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void initialize();
  }, []);

  async function uploadFiles(files: File[]) {
    if (!ready || busy) return;
    setError("");
    setNotice("");
    let succeeded = 0;
    const ids: string[] = [];
    const failures: string[] = [];
    for (const file of files) {
      if (file.size > 4_000_000) {
        failures.push(`${file.name}: larger than 4 MB.`);
        continue;
      }
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        failures.push(`${file.name}: only PDF files are supported.`);
        continue;
      }
      setBusy(`Reading ${file.name}…`);
      try {
        const data = new FormData();
        data.append("file", file);
        const uploaded = await api<{
          id: string;
          duplicate?: boolean;
          warnings?: string[];
        }>("/documents", { method: "POST", body: data });
        ids.push(uploaded.id);
        succeeded++;
        if (uploaded.warnings?.length) failures.push(...uploaded.warnings);
      } catch (e) {
        failures.push(`${file.name}: ${(e as Error).message}`);
      }
    }
    try {
      await loadData();
      setSelected((current) => Array.from(new Set([...current, ...ids])));
    } catch (e) {
      failures.push((e as Error).message);
    }
    setBusy("");
    setError(failures.join(" "));
    if (succeeded)
      setNotice(
        `${succeeded} document${succeeded > 1 ? "s" : ""} ready to explore.`,
      );
    if (fileInput.current) fileInput.current.value = "";
  }
  async function loadSamples() {
    setError("");
    try {
      const data = await api<{ documents: { filename: string }[] }>("/samples");
      const files = await Promise.all(
        data.documents.map(async (d) => {
          const r = await fetch(`/api/samples/${d.filename}`);
          if (!r.ok) throw new Error("Could not load the sample PDFs.");
          return new File([await r.blob()], d.filename, {
            type: "application/pdf",
          });
        }),
      );
      await uploadFiles(files);
      setQuestion(
        "What did the Cedar trial find about sleep and attention, and do the reports agree?",
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function ask(compare = false) {
    if (!question.trim() || !selected.length || busy || !ready) return;
    if (compare && settings.provider === "extractive") {
      setShowSettings(true);
      return;
    }
    setBusy(
      compare
        ? "Comparing three methods on the same evidence…"
        : "Finding evidence and checking claims…",
    );
    setError("");
    setNotice("");
    setComparison([]);
    try {
      const body = JSON.stringify({
        question: question.trim(),
        document_ids: selected,
        variant: "verified",
        provider: settings.provider,
        model: settings.model,
      });
      const headers: Record<string, string> = {};
      if (settings.key) headers["X-Gemini-Key"] = settings.key;
      if (compare) {
        const r = await api<{ results: Answer[] }>("/compare", {
          method: "POST",
          body,
          headers,
        });
        setComparison(r.results);
        setAnswer(r.results[2]);
      } else
        setAnswer(
          await api<Answer>(queryMode === "verify" ? "/verify" : "/ask", {
            method: "POST",
            body,
            headers,
          }),
        );
      await loadData();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function removeDocument(doc: DocumentRecord) {
    if (
      !confirm(
        `Remove ${doc.name}? Saved answers in this workspace will also be removed because they contain document text.`,
      )
    )
      return;
    setBusy("Removing document…");
    setError("");
    try {
      await api(`/documents/${doc.id}`, { method: "DELETE" });
      setSelected((s) => s.filter((x) => x !== doc.id));
      if (activeDoc === doc.id) setActiveDoc(null);
      setAnswer(null);
      setComparison([]);
      await loadData();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function openRun(id: string) {
    setError("");
    try {
      const r = await api<Answer>(`/runs/${id}`);
      setAnswer(r);
      setQuestion(r.question);
      setComparison([]);
      setView("workspace");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function showEvidence(c: Citation) {
    if (!c.document_id) return;
    setCitation(c);
    setActiveDoc(c.document_id);
  }
  function newQuestion() {
    setAnswer(null);
    setComparison([]);
    setQuestion("");
    setView("workspace");
    setTimeout(() => textInput.current?.focus(), 50);
  }
  const currentDoc = documents.find((d) => d.id === activeDoc);
  const checked =
    answer?.claims.filter((c) => c.verdict !== "not_checked").length || 0;

  return (
    <div className="app-shell">
      <aside className={`navigation ${sidebar ? "mobile-open" : ""}`}>
        <a
          href="#"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            setView("workspace");
          }}
          aria-label="VeritasAI home"
        >
          <span className="brand-mark">
            <Check size={23} strokeWidth={2.8} />
          </span>
          <span>
            veritas<span className="brand-ai">ai</span>
            <small>FOLLOW THE EVIDENCE</small>
          </span>
        </a>
        <button className="new-button" onClick={newQuestion}>
          <Plus size={17} /> New question <span>↗</span>
        </button>
        <nav aria-label="Main navigation">
          <button
            className={view === "workspace" ? "nav-active" : ""}
            onClick={() => {
              setView("workspace");
              setSidebar(false);
            }}
          >
            <MessageSquare size={18} /> Workspace
          </button>
          <button
            className={view === "research" ? "nav-active" : ""}
            onClick={() => {
              setView("research");
              setSidebar(false);
            }}
          >
            <FlaskConical size={18} /> Evidence lab{" "}
            <span className="nav-pill">RESEARCH</span>
          </button>
          <button
            className={view === "history" ? "nav-active" : ""}
            onClick={() => {
              setView("history");
              setSidebar(false);
            }}
          >
            <History size={18} /> Answer history{" "}
            <span className="nav-count">{runs.length}</span>
          </button>
        </nav>
        <div className="sidebar-section-heading">
          <span>YOUR DOCUMENTS</span>
          <button
            className="icon-button"
            aria-label="Upload documents"
            disabled={!ready || !!busy}
            onClick={() => fileInput.current?.click()}
          >
            <Plus size={17} />
          </button>
        </div>
        <div className="document-list">
          {documents.length === 0 ? (
            <div className="no-documents">
              <FolderOpen size={30} />
              <p>A home for your sources.</p>
              <small>Your uploaded PDFs will appear here.</small>
            </div>
          ) : (
            documents.map((doc) => (
              <div
                className={`document-item ${activeDoc === doc.id ? "active-document" : ""}`}
                key={doc.id}
              >
                <input
                  aria-label={`Include ${doc.name} in search`}
                  type="checkbox"
                  checked={selected.includes(doc.id)}
                  disabled={!!busy}
                  onChange={(e) =>
                    setSelected((s) =>
                      e.target.checked
                        ? [...s, doc.id]
                        : s.filter((x) => x !== doc.id),
                    )
                  }
                />
                <button
                  className="document-open"
                  onClick={() => {
                    setActiveDoc(doc.id);
                    setCitation(null);
                    setView("workspace");
                    setSidebar(false);
                  }}
                >
                  <FileText size={19} />
                  <span>
                    <strong title={doc.name}>{doc.name}</strong>
                    <small>
                      {doc.page_count} pages ·{" "}
                      {(doc.byte_count / 1000).toFixed(0)} KB
                    </small>
                  </span>
                </button>
                <button
                  className="delete-document icon-button"
                  aria-label={`Remove ${doc.name}`}
                  disabled={!!busy}
                  onClick={() => void removeDocument(doc)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>
        <button
          className={`upload-zone ${drag ? "drag-active" : ""}`}
          disabled={!ready || !!busy}
          onClick={() => fileInput.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            void uploadFiles(Array.from(e.dataTransfer.files));
          }}
        >
          <FilePlus2 size={20} />
          <strong>Add your documents</strong>
          <span>Drop PDFs here or browse files</span>
          <small>Up to 4 MB and 80 pages per PDF</small>
        </button>
        <input
          type="file"
          ref={fileInput}
          accept="application/pdf,.pdf"
          multiple
          hidden
          onChange={(e) => void uploadFiles(Array.from(e.target.files || []))}
        />
        <div className="sidebar-footer">
          <div className="private-workspace">
            <LockKeyhole size={15} />
            <span>
              Private browser workspace
              <small>Keep this browser to keep access.</small>
            </span>
          </div>
          <button
            className="settings-button"
            onClick={() => setShowSettings(true)}
          >
            <span className="avatar">V</span>
            <span>
              AI settings
              <small>
                {settings.provider === "gemini"
                  ? "Gemini connected for this session"
                  : settings.provider === "ollama"
                    ? "Local Ollama"
                    : "Local evidence tools"}
              </small>
            </span>
            <Settings2 size={17} />
          </button>
        </div>
      </aside>
      {sidebar && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setSidebar(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <div>
            <button
              className="mobile-menu icon-button"
              aria-label="Open navigation"
              onClick={() => setSidebar(true)}
            >
              <Menu size={20} />
            </button>
            <span className="breadcrumb">Your library</span>
            <ChevronRight size={14} />
            <strong>
              {view === "workspace"
                ? "Research workspace"
                : view === "research"
                  ? "Evidence lab"
                  : "Answer history"}
            </strong>
          </div>
          <div className="topbar-right">
            <span className={`connection-status ${ready ? "online" : ""}`}>
              <i />
              {ready ? "Workspace ready" : "Connecting"}
            </span>
            <button
              className="help-button"
              onClick={() => {
                setNotice(
                  "1. Upload text-based PDFs. 2. Select your sources. 3. Ask a question. 4. Open each citation to check the exact page. AI settings enables generated answers. Source excerpts work without a key.",
                );
              }}
            >
              <BookOpen size={16} />
              <span>Quick guide</span>
            </button>
          </div>
        </header>
        {(error || notice) && (
          <div
            className={`banner ${error ? "error-banner" : "notice-banner"}`}
            role={error ? "alert" : "status"}
          >
            <AlertCircle size={17} />
            <span>{error || notice}</span>
            {!ready && <button onClick={() => void initialize()}>Retry</button>}
            <button
              aria-label="Dismiss message"
              className="icon-button"
              onClick={() => {
                setError("");
                setNotice("");
              }}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {view === "research" ? (
          <Suspense
            fallback={
              <div className="research-page">Loading evidence lab…</div>
            }
          >
            <Research runs={runs} />
          </Suspense>
        ) : view === "history" ? (
          <div className="history-page">
            <div className="section-eyebrow">
              <History size={15} /> YOUR RESEARCH TRAIL
            </div>
            <h1>Every question, kept in context.</h1>
            <p className="lead">
              Revisit the answer, its sources, and the checks behind it.
            </p>
            {runs.length === 0 ? (
              <div className="history-empty">
                <MessageSquare size={35} />
                <h2>No answers yet</h2>
                <p>Ask your first question in the workspace.</p>
                <button className="primary-button" onClick={newQuestion}>
                  Start researching <ArrowUpRight size={16} />
                </button>
              </div>
            ) : (
              <div className="history-list">
                {runs.map((run) => (
                  <button key={run.id} onClick={() => void openRun(run.id)}>
                    <span className="history-icon">
                      <MessageSquare size={20} />
                    </span>
                    <span>
                      <strong>{run.question}</strong>
                      <small>
                        {new Date(run.created_at).toLocaleDateString()} ·{" "}
                        {run.variant} · {(run.latency_ms / 1000).toFixed(1)}s
                        {run.abstained ? " · insufficient evidence" : ""}
                      </small>
                    </span>
                    <ArrowUpRight size={18} />
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div
            className={`workspace-layout ${currentDoc ? "with-evidence" : ""}`}
          >
            <main className="conversation">
              <div className="conversation-scroll">
                {!answer ? (
                  <div className="welcome">
                    <div className="welcome-label">
                      <span /> YOUR SOURCE-GROUNDED RESEARCH PARTNER
                    </div>
                    <div className="hero-symbol">
                      <Layers3 size={36} strokeWidth={1.3} />
                      <span>
                        <Check size={12} />
                      </span>
                    </div>
                    <h1>
                      Good answers.
                      <br />
                      <em>Evidence you can see.</em>
                    </h1>
                    <p>
                      Bring your papers. Ask better questions.
                      <br />
                      Follow every claim back to the source.
                    </p>
                    <div className="welcome-features">
                      <span>
                        <Search size={15} /> Find relevant evidence
                      </span>
                      <span>
                        <ShieldCheck size={15} /> Check individual claims
                      </span>
                    </div>
                    {documents.length === 0 ? (
                      <div className="get-started-card">
                        <div>
                          <span className="step-number">01</span>
                          <h3>Start with your sources</h3>
                          <p>
                            Upload research papers or reports to build your
                            private document library.
                          </p>
                        </div>
                        <button
                          className="primary-button"
                          disabled={!ready || !!busy}
                          onClick={() => fileInput.current?.click()}
                        >
                          Upload PDFs <Plus size={17} />
                        </button>
                        <div className="sample-link">
                          <span>Want to explore first?</span>
                          <button
                            disabled={!ready || !!busy}
                            onClick={() => void loadSamples()}
                          >
                            Try our authored sample documents{" "}
                            <ArrowUpRight size={13} />
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="question-suggestions">
                        <span>A FEW PLACES TO START</span>
                        {questions.map((q) => (
                          <button
                            key={q}
                            onClick={() => {
                              setQuestion(q);
                              textInput.current?.focus();
                            }}
                          >
                            {q}
                            <ArrowUpRight size={15} />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="answer-view">
                    <div className="question-heading">
                      <span className="avatar user-avatar">Y</span>
                      <h1>{answer.question}</h1>
                    </div>
                    <div className="answer-author">
                      <span className="mini-brand">
                        <Check size={15} />
                      </span>
                      <strong>VeritasAI</strong>
                      <span>
                        {answer.answer_kind === "claim_check"
                          ? "Claim check"
                          : answer.answer_kind === "source_excerpts"
                            ? "Source excerpts"
                            : "Research answer"}
                      </span>
                    </div>
                    {answer.answer_kind === "source_excerpts" && (
                      <div className="excerpt-note">
                        <BookOpen size={16} />
                        <span>
                          These are matching source excerpts, not a synthesized
                          AI answer.{" "}
                          <button onClick={() => setShowSettings(true)}>
                            Connect an AI model
                          </button>{" "}
                          for a written explanation.
                        </span>
                      </div>
                    )}
                    <div className="answer-meta">
                      <span>
                        <ShieldCheck size={14} />
                        {checked} claims checked
                      </span>
                      <span>
                        <Clock3 size={14} />
                        {(answer.latency_ms / 1000).toFixed(1)}s
                      </span>
                      <button
                        onClick={() =>
                          exportJson(
                            answer,
                            `veritas-evidence-${answer.id.slice(0, 8)}.json`,
                          )
                        }
                      >
                        <Download size={14} /> Export evidence
                      </button>
                    </div>
                    {answer.abstained && (
                      <div className="abstention">
                        <ShieldCheck size={24} />
                        <h2>The evidence is not enough.</h2>
                        <p>{answer.answer}</p>
                        <small>
                          Try a more specific question or add a relevant source.
                        </small>
                      </div>
                    )}
                    {answer.claims.map((claim, index) => (
                      <ClaimCard
                        key={claim.id}
                        claim={claim}
                        index={index}
                        onEvidence={showEvidence}
                      />
                    ))}
                    {comparison.length > 0 && (
                      <section className="comparison">
                        <h2>Same question. Three methods.</h2>
                        <p>
                          Reranked and verified answers share the same draft.
                          These numbers describe this run, not independently
                          measured answer quality.
                        </p>
                        <div>
                          {comparison.map((r) => (
                            <button
                              key={r.id}
                              onClick={() => setAnswer(r)}
                              className={
                                r.id === answer.id ? "active-comparison" : ""
                              }
                            >
                              <strong>
                                {r.variant === "rag"
                                  ? "Standard RAG"
                                  : r.variant === "rerank"
                                    ? "With reranking"
                                    : "With verification"}
                              </strong>
                              <span>
                                {r.claims.length} draft claims ·{" "}
                                {(r.latency_ms / 1000).toFixed(1)}s
                              </span>
                              <small>
                                View answer <ArrowUpRight size={12} />
                              </small>
                            </button>
                          ))}
                        </div>
                      </section>
                    )}
                    <div className="answer-caution">
                      <ShieldCheck size={15} />
                      <p>
                        Grounded in your documents. Still worth your judgment.
                        <br />
                        <span>
                          Source support does not guarantee real-world truth.
                        </span>
                      </p>
                    </div>
                  </div>
                )}
              </div>
              <div className="composer-area">
                <div
                  className="query-mode"
                  role="group"
                  aria-label="Research mode"
                >
                  <button
                    className={queryMode === "ask" ? "active" : ""}
                    onClick={() => setQueryMode("ask")}
                  >
                    Ask your documents
                  </button>
                  <button
                    className={queryMode === "verify" ? "active" : ""}
                    onClick={() => setQueryMode("verify")}
                  >
                    Check a claim <ShieldCheck size={12} />
                  </button>
                </div>
                {busy && (
                  <div className="working-status" role="status">
                    <LoaderCircle size={16} className="spin" />
                    {busy}
                  </div>
                )}
                <form
                  className="composer"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void ask();
                  }}
                >
                  <label className="sr-only" htmlFor="research-question">
                    Your research question
                  </label>
                  <textarea
                    ref={textInput}
                    id="research-question"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder={
                      queryMode === "verify"
                        ? "Enter one factual statement to check against your sources…"
                        : documents.length
                          ? "Ask a question about your selected documents…"
                          : "Upload a document, then ask anything about it…"
                    }
                    rows={2}
                    maxLength={1000}
                    disabled={!ready || !!busy}
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.shiftKey &&
                        !e.nativeEvent.isComposing
                      ) {
                        e.preventDefault();
                        void ask();
                      }
                    }}
                  />
                  <div className="composer-bottom">
                    <div>
                      <span className="source-count">
                        <FileText size={14} />
                        {selected.length} source
                        {selected.length === 1 ? "" : "s"}
                      </span>
                      <button
                        type="button"
                        className="model-button"
                        onClick={() => setShowSettings(true)}
                      >
                        <Sparkles size={13} />
                        {settings.provider === "gemini"
                          ? "Gemini"
                          : settings.provider === "ollama"
                            ? "Ollama"
                            : "Source excerpts"}
                        <ChevronRight size={12} />
                      </button>
                    </div>
                    <button
                      className="send-button"
                      aria-label="Ask question"
                      disabled={
                        !ready || !!busy || !question.trim() || !selected.length
                      }
                    >
                      <ArrowUp size={20} />
                    </button>
                  </div>
                </form>
                <div className="composer-footnote">
                  <span>
                    <LockKeyhole size={11} /> Your sources stay in this
                    workspace.
                  </span>
                  <button
                    disabled={
                      !ready ||
                      !!busy ||
                      !question.trim() ||
                      !selected.length ||
                      queryMode === "verify"
                    }
                    onClick={() => void ask(true)}
                  >
                    <FlaskConical size={12} /> Compare methods
                  </button>
                </div>
              </div>
            </main>
            {currentDoc && (
              <EvidencePanel
                citation={citation}
                document={currentDoc}
                onClose={() => setActiveDoc(null)}
              />
            )}
          </div>
        )}
      </div>
      {showSettings && (
        <SettingsDialog
          value={settings}
          serverKey={health?.gemini_configured || false}
          ollama={health?.ollama_available || false}
          onClose={() => setShowSettings(false)}
          onSave={(s) => {
            setSettings(s);
            setShowSettings(false);
            setNotice(
              s.provider === "extractive"
                ? "Local evidence tools selected."
                : "AI settings saved for this tab.",
            );
          }}
        />
      )}
    </div>
  );
}
