import { useEffect, useRef, useState } from "react";
import { X, KeyRound, ShieldCheck, ArrowUpRight } from "lucide-react";
import type { Settings } from "./types";
export function SettingsDialog({
  value,
  onClose,
  onSave,
  serverKey,
  ollama,
}: {
  value: Settings;
  onClose: () => void;
  onSave: (s: Settings) => void;
  serverKey: boolean;
  ollama: boolean;
}) {
  const [form, setForm] = useState(value);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="modal"
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === dialog.current) onClose();
      }}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSave(form);
        }}
      >
        <div className="modal-header">
          <div className="soft-icon">
            <KeyRound size={20} />
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close AI settings"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        <h2>Your research, your AI</h2>
        <p className="muted">
          Local search and evidence checks work without a key. Connect Gemini
          for AI-written answers and RAG comparisons.
        </p>
        <label>
          Answer engine
          <select
            value={form.provider}
            onChange={(e) =>
              setForm({
                ...form,
                provider: e.target.value as Settings["provider"],
              })
            }
          >
            <option value="extractive">Source excerpts · no API key</option>
            <option value="gemini">Gemini · AI-written answers</option>
            {ollama && <option value="ollama">Ollama · local model</option>}
          </select>
        </label>
        {form.provider === "gemini" && (
          <>
            <label>
              Gemini API key{" "}
              {serverKey && <small>(server key available)</small>}
              <input
                type="password"
                autoComplete="off"
                value={form.key}
                placeholder={
                  serverKey
                    ? "Leave blank to use the server key"
                    : "Paste your API key here"
                }
                onChange={(e) => setForm({ ...form, key: e.target.value })}
              />
            </label>
            <label>
              Model
              <input
                value={form.model}
                required
                onChange={(e) => setForm({ ...form, model: e.target.value })}
              />
            </label>
            <a
              className="text-link"
              href="https://aistudio.google.com/apikey"
              target="_blank"
              rel="noreferrer"
            >
              Get a key in Google AI Studio <ArrowUpRight size={14} />
            </a>
            <p className="privacy-note">
              <ShieldCheck size={16} />
              <span>
                Your key stays in this tab's memory. It is sent over HTTPS for
                your requests and is never saved to our database. Refreshing
                clears it. Relevant document excerpts go to Google when you ask
                Gemini. Provider terms and quotas apply.
              </span>
            </p>
          </>
        )}
        <div className="modal-actions">
          <button type="button" className="secondary-button" onClick={onClose}>
            Cancel
          </button>
          <button className="primary-button" type="submit">
            Save settings
          </button>
        </div>
      </form>
    </dialog>
  );
}
