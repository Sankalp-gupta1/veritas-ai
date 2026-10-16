import { useEffect, useState } from "react";
import {
  X,
  FileText,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Check,
} from "lucide-react";
import { api } from "./api";
import type { Citation, DocumentRecord } from "./types";
export function EvidencePanel({
  citation,
  document,
  onClose,
}: {
  citation: Citation | null;
  document: DocumentRecord | undefined;
  onClose: () => void;
}) {
  const [page, setPage] = useState(citation?.page_number || 1);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"text" | "pdf">("text");
  useEffect(() => {
    setPage(citation?.page_number || 1);
  }, [citation, document?.id]);
  useEffect(() => {
    let active = true;
    setText("");
    setError("");
    if (document)
      api<{ text: string }>(`/documents/${document.id}/pages/${page}`)
        .then((r) => {
          if (active) setText(r.text);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    return () => {
      active = false;
    };
  }, [document?.id, page]);
  if (!document) return null;
  const quote = citation?.page_number === page ? citation.quote : "";
  const at = quote ? text.indexOf(quote) : -1;
  return (
    <aside className="evidence-panel" aria-label="Source document">
      <div className="panel-title">
        <span>
          <FileText size={16} /> Source document
        </span>
        <button
          className="icon-button"
          aria-label="Close source document"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>
      <div className="document-detail">
        <span className="file-icon">
          <FileText size={22} />
        </span>
        <div>
          <strong title={document.name}>{document.name}</strong>
          <small>{document.page_count} pages · Original uploaded PDF</small>
        </div>
      </div>
      <div className="viewer-toolbar">
        <div className="segmented">
          <button
            className={mode === "text" ? "selected" : ""}
            aria-pressed={mode === "text"}
            onClick={() => setMode("text")}
          >
            Evidence
          </button>
          <button
            className={mode === "pdf" ? "selected" : ""}
            aria-pressed={mode === "pdf"}
            onClick={() => setMode("pdf")}
          >
            PDF
          </button>
        </div>
        <a
          className="icon-button"
          aria-label="Open original PDF"
          target="_blank"
          href={`/api/documents/${document.id}/pdf`}
          rel="noreferrer"
        >
          <ExternalLink size={16} />
        </a>
      </div>
      {quote && (
        <div className="evidence-notice">
          <Check size={15} />
          <span>
            {citation?.integrity
              ? "Exact text located in the source"
              : "Quote could not be matched"}
          </span>
        </div>
      )}
      <div className="page-view">
        {mode === "pdf" ? (
          <iframe
            title={`Original PDF: ${document.name}`}
            src={`/api/documents/${document.id}/pdf#page=${page}&toolbar=0`}
          />
        ) : (
          <article className="paper-page">
            <div className="paper-kicker">
              DOCUMENT EVIDENCE <span>{String(page).padStart(2, "0")}</span>
            </div>
            <h3>{document.name.replace(/\.pdf$/i, "")}</h3>
            {error ? (
              <p role="alert">{error}</p>
            ) : text ? (
              <p>
                {at >= 0 ? (
                  <>
                    {text.slice(0, at)}
                    <mark>{quote}</mark>
                    {text.slice(at + quote.length)}
                  </>
                ) : (
                  text
                )}
              </p>
            ) : (
              <div className="skeleton-lines" aria-label="Loading page">
                <i />
                <i />
                <i />
                <i />
              </div>
            )}
          </article>
        )}
      </div>
      <div className="page-navigation">
        <button
          className="icon-button"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft size={17} />
        </button>
        <span>
          PDF page <strong>{page}</strong> of {document.page_count}
        </span>
        <button
          className="icon-button"
          disabled={page >= document.page_count}
          onClick={() => setPage((p) => p + 1)}
          aria-label="Next page"
        >
          <ChevronRight size={17} />
        </button>
      </div>
      <p className="viewer-footnote">
        Page numbers count from the first PDF page. Evidence text is normalized
        for reliable quote matching.
      </p>
    </aside>
  );
}
