import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, CloudOff, Eye, ShieldCheck, X } from "lucide-react";
import type { Disclosure } from "./types";

export function DisclosureDialog({
  value,
  onCancel,
  onApprove,
}: {
  value: Disclosure;
  onCancel: () => void;
  onApprove: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [checked, setChecked] = useState(false);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const count = Object.values(value.masked).reduce((a, b) => a + b, 0);
  return (
    <dialog
      ref={dialog}
      className="modal disclosure-modal"
      aria-labelledby="disclosure-title"
      onCancel={onCancel}
    >
      <div className="modal-header">
        <div className="soft-icon">
          <Eye size={22} />
        </div>
        <button
          className="icon-button"
          aria-label="Cancel external AI request"
          onClick={onCancel}
        >
          <X size={21} />
        </button>
      </div>
      <span className="eyebrow">REVIEW BEFORE ANYTHING IS SENT</span>
      <h2 id="disclosure-title">You're in control of this handoff.</h2>
      <p>
        Recipient: <strong>{value.recipient}</strong>. Google applies its own
        data-use and retention terms. Cancel to keep this request away from the
        external AI provider.
      </p>
      <div className="disclosure-badges">
        <span>
          <ShieldCheck size={15} /> File names hidden
        </span>
        <span>
          {count} obvious identifier{count === 1 ? "" : "s"} masked
        </span>
        <span>One request · expires in 10 min</span>
      </div>
      <p className="boundary-note">{value.notice}</p>
      <div className="disclosure-content">
        {value.payloads.map((payload, i) => (
          <section key={payload.method}>
            <h3>
              {value.payloads.length > 1
                ? `Model call ${i + 1} · ${payload.method}`
                : "Text to be shared"}
            </h3>
            <h4>Your question</h4>
            <pre>{payload.question}</pre>
            <h4>Selected passages</h4>
            {payload.evidence.map((p, j) => (
              <details key={p.chunk_id} open={j === 0}>
                <summary>
                  {p.source} · passage {j + 1}
                </summary>
                <pre>{p.text}</pre>
              </details>
            ))}
          </section>
        ))}
      </div>
      <a
        className="text-link"
        href="https://ai.google.dev/gemini-api/terms"
        target="_blank"
        rel="noreferrer"
      >
        Google Gemini API terms <ArrowUpRight size={13} />
      </a>
      <label className="check-label disclosure-check">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
        />{" "}
        I reviewed this text and approve sharing it with Google for this
        request.
      </label>
      <div className="modal-actions">
        <button className="secondary-button" onClick={onCancel}>
          <CloudOff size={16} /> Cancel
        </button>
        <button
          className="primary-button"
          disabled={!checked}
          onClick={onApprove}
        >
          Approve and ask Gemini <ArrowUpRight size={15} />
        </button>
      </div>
    </dialog>
  );
}
