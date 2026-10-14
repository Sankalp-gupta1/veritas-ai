import {
  Check,
  AlertTriangle,
  CircleHelp,
  ArrowUpRight,
  Ban,
  Minus,
} from "lucide-react";
import type { Claim, Citation } from "./types";
const labels = {
  supported: "Supported by source",
  conflict: "Possible disagreement",
  contradicted: "Contradicted · withheld",
  insufficient: "Insufficient evidence · withheld",
  not_checked: "Not checked",
};
const icons = {
  supported: Check,
  conflict: AlertTriangle,
  contradicted: Ban,
  insufficient: CircleHelp,
  not_checked: Minus,
};
export function ClaimCard({
  claim,
  index,
  onEvidence,
}: {
  claim: Claim;
  index: number;
  onEvidence: (c: Citation) => void;
}) {
  const Icon = icons[claim.verdict];
  return (
    <article className={`claim-card ${claim.verdict}`}>
      <div className="claim-heading">
        <span className={`status-badge ${claim.verdict}`}>
          <Icon size={13} />
          {labels[claim.verdict]}
        </span>
        <span className="claim-number">
          CLAIM {String(index + 1).padStart(2, "0")}
        </span>
      </div>
      <p className="claim-text">{claim.text}</p>
      <div className="citation-links">
        {claim.citations.map((c, i) => (
          <button
            key={`${c.chunk_id}-${i}`}
            className="citation-link"
            disabled={!c.document_id}
            onClick={() => onEvidence(c)}
          >
            <span>{i + 1}</span>
            {c.document_name || "Invalid citation"}
            {c.page_number ? ` · p. ${c.page_number}` : ""}
            <ArrowUpRight size={13} />
          </button>
        ))}
      </div>
      <details className="check-details">
        <summary>How was this checked?</summary>
        <p>{claim.explanation}</p>
        <p>
          Exact quote check:{" "}
          {claim.citations.length && claim.citations.every((c) => c.integrity)
            ? "passed"
            : "not passed"}
          . Semantic support uses a fallible language model.
        </p>
      </details>
      {claim.counter_evidence.length > 0 && (
        <div className="counter-evidence">
          <strong>
            <AlertTriangle size={14} /> Evidence to compare
          </strong>
          {claim.counter_evidence.map((c, i) => (
            <button key={i} onClick={() => onEvidence(c)}>
              <span>
                {c.document_name} · p. {c.page_number}
              </span>
              <ArrowUpRight size={14} />
            </button>
          ))}
          <small>
            Different dates or populations can explain disagreement. Review both
            sources.
          </small>
        </div>
      )}
    </article>
  );
}
