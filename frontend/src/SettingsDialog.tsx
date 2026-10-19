import { useEffect, useRef, useState } from "react";
import { X, KeyRound, ShieldCheck, ArrowUpRight } from "lucide-react";
import type { Settings } from "./types";
export function SettingsDialog({
  value,
  onClose,
  onSave,
  serverKey,
  ollama,
  cloudEnabled,
  onPrivacy,
}: {
  value: Settings;
  onClose: () => void;
  onSave: (s: Settings) => void;
  serverKey: boolean;
  ollama: boolean;
  cloudEnabled: boolean;
  onPrivacy: () => void;
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
      aria-labelledby="settings-title"
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
        <h2 id="settings-title">Your research, your AI</h2>
        <p className="muted">
          Local search and evidence checks work without a key. Connect Gemini
          for AI-written answers and RAG comparisons.
        </p>
        <p className="privacy-note">
          <ShieldCheck size={16} />
          <span>
            Document content and saved answers are encrypted on the server.
            The server decrypts them to do research. This is not end-to-end encrypted.{" "}
            <a
              className="text-link"
              href="https://github.com/Sankalp-gupta1/veritas-ai/blob/main/docs/PRIVACY.md"
              target="_blank"
              rel="noreferrer"
            >
              Read how your data is handled
            </a>
          </span>
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
            <option value="gemini" disabled={!cloudEnabled}>Gemini · {cloudEnabled ? "reviewed AI-written answers" : "blocked in Privacy center"}</option>
            {ollama && <option value="ollama">Ollama · local model</option>}
          </select>
        </label>
        {!cloudEnabled && <p className="privacy-note"><ShieldCheck size={16} /><span>External AI is blocked. <button type="button" className="text-link" onClick={onPrivacy}>Open Privacy center</button> to allow reviewed Gemini requests.</span></p>}
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
                The app keeps the entered key in this tab's memory and does not
                save it to its database. Gemini generation sends it through our
                backend to Google over HTTPS. A preview shows your question and selected passages before you approve sending them. File names are replaced and obvious identifiers are masked. Refreshing or signing out clears the entered
                key from app state. Check Google's data-use terms before sending
                personal information.
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
