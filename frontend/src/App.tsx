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
  LoaderCircle,
  MessageSquare,
  Plus,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
  AlertCircle,
  PanelLeftClose,
  PanelLeftOpen,
  SquarePen,
  LockKeyhole,
  LogOut,
  CloudOff,
  Eye,
} from "lucide-react";
import { api, exportJson } from "./api";
import { ClaimCard } from "./ClaimCard";
import { EvidencePanel } from "./EvidencePanel";
import { SettingsDialog } from "./SettingsDialog";
import { PrivacyCenter } from "./PrivacyCenter";
import { DisclosureDialog } from "./DisclosureDialog";
const Research = lazy(() =>
  import("./Research").then((module) => ({ default: module.Research })),
);
import type { Account, Answer, Citation, Disclosure, DocumentRecord, Run, Settings } from "./types";

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

type Query = { question: string; document_ids: string[]; variant: string; provider: Settings["provider"]; model: string; temporary: boolean };
export default function App({ account, onAccount, onSignedOut }: { account: Account; onAccount: (a: Account) => void; onSignedOut: () => void }) {
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
  const [showPrivacy, setShowPrivacy] = useState(false);
  const [temporary, setTemporary] = useState(false);
  const [pending, setPending] = useState<{ disclosure: Disclosure; query: Query; compare: boolean } | null>(null);
  const [activeDoc, setActiveDoc] = useState<string | null>(null);
  const [citation, setCitation] = useState<Citation | null>(null);
  const [sidebar, setSidebar] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobile, setMobile] = useState(
    () => window.matchMedia("(max-width: 700px)").matches,
  );
  const navigationVisible = mobile ? sidebar : !sidebarCollapsed;
  const navigation = useRef<HTMLElement>(null);
  const navigationToggle = useRef<HTMLButtonElement>(null);
  const navigationClose = useRef<HTMLButtonElement>(null);
  const [drag, setDrag] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const textInput = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!account.cloud_enabled) {
      setSettings(s => ({ ...s, provider: "extractive", key: "" }));
      setPending(null);
    }
  }, [account.cloud_enabled]);

  useEffect(() => {
    const screen = window.matchMedia("(max-width: 700px)");
    const update = () => {
      setMobile(screen.matches);
      setSidebar(false);
    };
    screen.addEventListener("change", update);
    return () => screen.removeEventListener("change", update);
  }, []);

  function closeNavigation() {
    setSidebar(false);
    setSidebarCollapsed(true);
    requestAnimationFrame(() => navigationToggle.current?.focus());
  }
  function openNavigation() {
    setSidebarCollapsed(false);
    setSidebar(true);
  }

  useEffect(() => {
    if (!mobile || !sidebar) return;
    navigationClose.current?.focus();
    // Keep keyboard navigation inside the mobile drawer while the page is inert.
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") closeNavigation();
      if (event.key !== "Tab") return;
      const controls = navigation.current?.querySelectorAll<HTMLElement>(
        "button:not(:disabled), a[href], input:not(:disabled):not([hidden])",
      );
      if (!controls?.length) return;
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [mobile, sidebar]);

  useEffect(() => {
    const input = textInput.current;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
  }, [question, view]);

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
  async function ask(compare = false, approved?: { query: Query; token: string }) {
    const submittedQuestion =
      approved?.query.question || question.trim() || (compare ? answer?.question : "");
    if (!submittedQuestion || !selected.length || busy || !ready) return;
    if (compare && settings.provider === "extractive") {
      setShowSettings(true);
      return;
    }
    if (settings.provider === "gemini" && (compare || queryMode === "ask") && !account.cloud_enabled) {
      setShowPrivacy(true);
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
      const query: Query = approved?.query || {
        question: submittedQuestion,
        document_ids: selected,
        variant: "verified",
        provider: settings.provider,
        model: settings.model,
        temporary,
      };
      if (query.provider === "gemini" && (compare || queryMode === "ask") && !approved) {
        setBusy("Preparing your private disclosure preview…");
        const disclosure = await api<Disclosure>(`/privacy/preview?operation=${compare ? "compare" : "ask"}`, { method: "POST", body: JSON.stringify(query) });
        setPending({ disclosure, query, compare });
        return;
      }
      const body = JSON.stringify({ ...query, ...(approved ? { consent_token: approved.token } : {}) });
      const headers: Record<string, string> = {};
      if (
        settings.provider === "gemini" &&
        (compare || queryMode === "ask") &&
        settings.key
      ) {
        headers["X-Gemini-Key"] = settings.key;
      }
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
      setQuestion("");
      await loadData();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
      requestAnimationFrame(() => textInput.current?.focus());
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
      setQuestion("");
      setQueryMode(r.answer_kind === "claim_check" ? "verify" : "ask");
      setComparison([]);
      setActiveDoc(null);
      setSidebar(false);
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
    setActiveDoc(null);
    setCitation(null);
    setSidebar(false);
    setError("");
    setNotice("");
    setView("workspace");
    setTimeout(() => textInput.current?.focus(), 50);
  }
  const currentDoc = documents.find((d) => d.id === activeDoc);
  const checked =
    answer?.claims.filter((c) => c.verdict !== "not_checked").length || 0;

  async function dataChanged() {
    setAnswer(null); setComparison([]); setActiveDoc(null); setCitation(null); setPending(null);
    const remaining = await loadData();
    setSelected(s => s.filter(id => remaining.some(d => d.id === id)));
  }

  async function signOut() {
    try { await api("/auth/logout", { method: "POST" }); onSignedOut(); }
    catch (e) { setError((e as Error).message); }
  }

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <aside
        id="workspace-navigation"
        ref={navigation}
        className={`navigation ${sidebar ? "mobile-open" : ""}`}
        aria-label="Workspace navigation"
        inert={!navigationVisible}
      >
        <div className="navigation-header">
          <a
            href="#"
            className="brand"
            onClick={(e) => {
              e.preventDefault();
              setView("workspace");
              setSidebar(false);
            }}
            aria-label="VeritasAI home"
          >
            <span className="brand-mark">
              <Check size={23} strokeWidth={2.8} />
            </span>
            <span>
              veritas<span className="brand-ai">ai</span>
            </span>
          </a>
          <button
            ref={navigationClose}
            className="icon-button"
            aria-label="Close sidebar"
            title="Close sidebar"
            onClick={closeNavigation}
          >
            <PanelLeftClose size={20} />
          </button>
        </div>
        <button className="new-button" onClick={newQuestion} disabled={!!busy}>
          <SquarePen size={18} /> New question
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
          <button onClick={() => { setSidebar(false); setShowPrivacy(true); }}><ShieldCheck size={18} /> Privacy center <span className="nav-pill">CONTROL</span></button>
        </nav>
        <div className="sidebar-scroll">
          {runs.length > 0 && (
            <section className="recent-questions" aria-label="Recent questions">
              <h2>Recent questions</h2>
              {runs.slice(0, 5).map((run) => (
                <button
                  key={run.id}
                  className={answer?.id === run.id ? "current-question" : ""}
                  aria-current={answer?.id === run.id ? "page" : undefined}
                  title={run.question}
                  disabled={!!busy}
                  onClick={() => void openRun(run.id)}
                >
                  {run.question}
                </button>
              ))}
            </section>
          )}
          <div className="sidebar-section-heading">
            <span>Your documents</span>
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
        </div>
        <div className="sidebar-footer">
          <div className="private-workspace">
            <LockKeyhole size={15} />
            <span>
              Account protected
              <small>Encrypted content on the server.</small>
            </span>
          </div>
          <button
            className="settings-button"
            onClick={() => {
              setSidebar(false);
              setShowSettings(true);
            }}
          >
            <span className="avatar">V</span>
            <span>
              AI settings
              <small>
                {settings.provider === "gemini"
                  ? "Gemini selected for this session"
                  : settings.provider === "ollama"
                    ? "Local Ollama"
                    : "Local evidence tools"}
              </small>
            </span>
            <Settings2 size={17} />
          </button>
          <div className="account-footer"><span title={account.email}>{account.email}</span><button className="icon-button" aria-label="Sign out and lock workspace" title="Sign out and lock workspace" onClick={() => void signOut()}><LogOut size={17} /></button></div>
        </div>
      </aside>
      <input
        type="file"
        ref={fileInput}
        accept="application/pdf,.pdf"
        multiple
        hidden
        onChange={(e) => void uploadFiles(Array.from(e.target.files || []))}
      />
      {mobile && sidebar && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={closeNavigation}
          tabIndex={-1}
        />
      )}
      <div className="main-shell" inert={mobile && sidebar}>
        <header className="topbar">
          <div>
            <button
              ref={navigationToggle}
              className="navigation-toggle icon-button"
              aria-label="Open sidebar"
              aria-controls="workspace-navigation"
              aria-expanded={navigationVisible}
              hidden={navigationVisible}
              title="Open sidebar"
              onClick={openNavigation}
            >
              <PanelLeftOpen size={20} />
            </button>
            <strong>
              {view === "workspace"
                ? "VeritasAI"
                : view === "research"
                  ? "Evidence lab"
                  : "Answer history"}
            </strong>
          </div>
          <div className="topbar-right">
            <button className={`privacy-status-pill ${account.cloud_enabled ? "external-available" : ""}`} onClick={() => setShowPrivacy(true)}>{account.cloud_enabled ? <Eye size={14} /> : <CloudOff size={14} />}<span>{account.cloud_enabled ? "Review before sharing" : "External AI blocked"}</span></button>
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
            <h1>Your past questions.</h1>
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
                        {run.variant === "claim_check"
                          ? "Claim check"
                          : run.variant === "rag"
                            ? "Standard RAG"
                            : run.variant === "rerank"
                              ? "Reranked answer"
                              : "Verified answer"}{" "}
                        · {(run.latency_ms / 1000).toFixed(1)}s
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
            <main
              className={`conversation ${!answer ? "empty-conversation" : ""}`}
            >
              <div className="conversation-scroll">
                {!answer ? (
                  <div className="welcome">
                    <h1>
                      {documents.length
                        ? "What would you like to research?"
                        : "Start with a document."}
                    </h1>
                    <p>
                      {documents.length
                        ? "Ask your documents. Follow every claim to its source."
                        : "Upload a PDF to ask questions and check the evidence."}
                    </p>
                    <div className="welcome-privacy"><ShieldCheck size={15} /><span>Your PDFs are encrypted on the server. {account.save_history ? "Answer history is enabled." : "Answer history starts off."} <button onClick={() => setShowPrivacy(true)}>Your privacy controls</button></span></div>
                    {documents.length === 0 && (
                      <div className="welcome-actions">
                        <button
                          className="primary-button"
                          disabled={!ready || !!busy}
                          onClick={() => fileInput.current?.click()}
                        >
                          <Plus size={17} /> Upload PDFs
                        </button>
                        <button
                          className="sample-button"
                          disabled={!ready || !!busy}
                          onClick={() => void loadSamples()}
                        >
                          Try our authored sample documents{" "}
                          <ArrowUpRight size={15} />
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="answer-view">
                    <div className="question-heading">
                      <span className="sr-only">Your question</span>
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
                    {answer.privacy && <div className="answer-privacy-receipt"><ShieldCheck size={15} /><span>{answer.privacy.external_ai ? "Reviewed text sent to Gemini" : "No external AI used"} · {answer.privacy.history_saved ? "Saved with encryption" : "Not saved to history"}</span><button onClick={() => setShowPrivacy(true)}>Details</button></div>}
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
                    {answer.answer_kind === "generated" && !answer.abstained && (
                      <section className="guided-answer" aria-label="Structured research explanation">
                        <div className="guided-eyebrow">EVIDENCE-GROUNDED EXPLANATION</div>
                        <h2>Answer in simple steps</h2>
                        <p className="guided-intro">
                          Here is what your uploaded documents actually support. Each point links to its
                          evidence below. Claims marked as uncertain or contradicted are not presented
                          as established facts.
                        </p>
                        {answer.claims.filter((c) => c.verdict === "supported" || c.verdict === "conflict").length > 0 ? (
                          <ol className="guided-steps">
                            {answer.claims.filter((c) => c.verdict === "supported" || c.verdict === "conflict").map((claim, i) => (
                              <li key={claim.id}>
                                <strong>Step {i + 1} — {claim.verdict === "conflict" ? "Finding to review" : "What the document says"}</strong>
                                <p>{claim.text}</p>
                                <div className="guided-cites">
                                  {claim.citations.filter(c => c.document_id).map((c, j) => (
                                    <button key={j} onClick={() => showEvidence(c)}>
                                      {c.document_name || "Source"}{c.page_number ? ` · page ${c.page_number}` : ""}
                                      <ArrowUpRight size={13} />
                                    </button>
                                  ))}
                                </div>
                                {claim.verdict === "conflict" && <small>Potential disagreement: review both sources before relying on this point.</small>}
                              </li>
                            ))}
                          </ol>
                        ) : (
                          <p>The documents do not provide enough verified material for an explanation.</p>
                        )}
                        <div className="guided-tip">
                          <strong>Want a deeper explanation?</strong>
                          <span>Ask a follow-up such as “Explain step by step in Hinglish with examples” or “Explain the technical workflow in detail.” The next answer will be checked against your selected PDFs again.</span>
                        </div>
                        <h3>Claim-by-claim verification</h3>
                        <p className="guided-intro">Open any source below to inspect the page and exact passage.</p>
                      </section>
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
                    aria-pressed={queryMode === "ask"}
                    disabled={!!busy}
                    onClick={() => setQueryMode("ask")}
                  >
                    Ask your documents
                  </button>
                  <button
                    className={queryMode === "verify" ? "active" : ""}
                    aria-pressed={queryMode === "verify"}
                    disabled={!!busy}
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
                    rows={1}
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
                      <button
                        type="button"
                        className="icon-button attach-button"
                        aria-label="Attach PDFs"
                        title="Attach PDFs"
                        disabled={!ready || !!busy}
                        onClick={() => fileInput.current?.click()}
                      >
                        <Plus size={21} />
                      </button>
                      <button
                        type="button"
                        className="source-count"
                        title="Choose documents to search"
                        aria-label={`Choose sources (${selected.length} selected)`}
                        onClick={openNavigation}
                      >
                        <FileText size={14} />
                        {selected.length} source
                        {selected.length === 1 ? "" : "s"}
                      </button>
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
                      {busy ? (
                        <LoaderCircle size={20} className="spin" />
                      ) : (
                        <ArrowUp size={20} />
                      )}
                    </button>
                  </div>
                </form>
                <div className="composer-footnote">
                  <button className="history-mode-button" disabled={!!busy} onClick={() => account.save_history ? setTemporary(!temporary) : setShowPrivacy(true)} title={account.save_history ? "Toggle temporary answer mode" : "Answer history is off in Privacy center"}><LockKeyhole size={12} />{!account.save_history || temporary ? "This answer won't be saved" : "Save this answer to history"}</button>
                  <button
                    disabled={
                      !ready ||
                      !!busy ||
                      !(question.trim() || answer?.question) ||
                      !selected.length ||
                      queryMode === "verify"
                    }
                    onClick={() => void ask(true)}
                  >
                    <FlaskConical size={12} /> Compare methods
                  </button>
                </div>
                {!answer && documents.length > 0 && (
                  <div
                    className="starter-prompts"
                    aria-label="Suggested questions"
                  >
                    {questions.map((q) => (
                      <button
                        key={q}
                        disabled={!!busy}
                        onClick={() => {
                          setQueryMode("ask");
                          setQuestion(q);
                          textInput.current?.focus();
                        }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
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
          cloudEnabled={account.cloud_enabled}
          onPrivacy={() => { setShowSettings(false); setShowPrivacy(true); }}
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
      {showPrivacy && <PrivacyCenter account={account} onClose={() => setShowPrivacy(false)} onAccount={onAccount} onSignedOut={onSignedOut} onDataChanged={dataChanged} />}
      {pending && <DisclosureDialog value={pending.disclosure} onCancel={() => { setPending(null); setNotice("Cancelled. Nothing from this request was sent to Gemini."); }} onApprove={() => { const p = pending; setPending(null); void ask(p.compare, { query: p.query, token: p.disclosure.consent_token }); }} />}
    </div>
  );
}
