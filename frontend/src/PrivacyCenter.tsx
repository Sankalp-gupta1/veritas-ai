import { useEffect, useRef, useState } from "react";
import { ArrowRight, CloudOff, Download, FileLock2, Globe, KeyRound, LoaderCircle, LockKeyhole, LogOut, ShieldCheck, Trash2, X } from "lucide-react";
import { api, exportJson } from "./api";
import { RecoveryCard } from "./RecoveryCard";
import type { Account } from "./types";

type PrivacyState = {
  account: Account; active_sessions: number; vault_configured: boolean; encrypted_content: boolean;
  storage: { documents: number; bytes: number; answers: number; legacy_documents: number; legacy_answers: number };
  events: { id: string; event: string; created_at: string }[]; limits: string[];
};
const eventLabels: Record<string, string> = {
  account_created: "Account created", signed_in: "Signed in", signed_out: "Signed out",
  all_sessions_revoked: "All devices signed out", external_ai_enabled: "External AI enabled for reviewed requests",
  external_ai_blocked: "External AI blocked", answer_history_enabled: "Answer history turned on",
  answer_history_disabled: "Answer history turned off", answer_history_deleted: "Answer history deleted",
  data_exported: "Private data export downloaded", external_ai_disclosure_approved: "A Gemini disclosure was approved",
  document_encrypted_and_saved: "A document was encrypted and saved", document_and_saved_answers_deleted: "A document and saved answers were deleted",
  workspace_data_deleted: "All workspace documents and answers were deleted",
  password_changed_sessions_revoked: "Password changed; other sessions revoked", account_recovered_sessions_revoked: "Account recovered; other sessions revoked",
};

export function PrivacyCenter({ account, onClose, onAccount, onSignedOut, onDataChanged }: {
  account: Account; onClose: () => void; onAccount: (a: Account) => void;
  onSignedOut: () => void; onDataChanged: () => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [state, setState] = useState<PrivacyState | null>(null);
  const [busy, setBusy] = useState(""); const [error, setError] = useState("");
  const [notice, setNotice] = useState(""); const [recovery, setRecovery] = useState("");
  const [deleting, setDeleting] = useState(false);
  async function refresh() { const p = await api<PrivacyState>("/privacy"); setState(p); onAccount(p.account); }
  useEffect(() => { dialog.current?.showModal(); void refresh().catch(e => setError(e.message)); }, []);
  async function action(label: string, job: () => Promise<void>) {
    setBusy(label); setError(""); setNotice("");
    try { await job(); } catch (e) { setError((e as Error).message); } finally { setBusy(""); }
  }
  async function preference(key: "cloud_enabled" | "save_history", value: boolean) {
    await action("Saving privacy preference…", async () => {
      const updated = { cloud_enabled: account.cloud_enabled, save_history: account.save_history, [key]: value };
      await api("/privacy/preferences", { method: "PUT", body: JSON.stringify(updated) });
      onAccount({ ...account, ...updated }); await refresh();
    });
  }
  return <dialog ref={dialog} className="modal privacy-modal" aria-labelledby="privacy-title" onCancel={onClose} onClick={e => { if (e.target === dialog.current) onClose(); }}>
    <header className="privacy-modal-header"><div><span className="eyebrow">CONTROL, NOT JUST A PROMISE</span><h2 id="privacy-title">Your privacy center</h2><p>{account.email}</p></div><button className="icon-button" aria-label="Close privacy center" onClick={onClose}><X size={21} /></button></header>
    {error && <p role="alert" className="auth-error">{error}</p>}
    {notice && <p role="status" className="privacy-notice">{notice}</p>}
    {busy && <p role="status" className="privacy-progress"><LoaderCircle size={16} className="spin" />{busy}</p>}
    {recovery ? <RecoveryCard code={recovery} onDone={() => setRecovery("")} /> : <>
      <div className="privacy-overview">
        <div><FileLock2 size={23} /><strong>{state?.encrypted_content && state.vault_configured ? "Content encrypted" : state ? "Checking older records" : "Checking storage…"}</strong><small>AES-256-GCM at rest</small></div>
        <div>{account.cloud_enabled ? <Globe size={23} /> : <CloudOff size={23} />}<strong>{account.cloud_enabled ? "Review before sharing" : "External AI blocked"}</strong><small>Enforced by the server</small></div>
        <div><LockKeyhole size={23} /><strong>Account protected</strong><small>30-minute inactivity lock</small></div>
      </div>
      <section className="privacy-section"><h3>Decide what leaves your workspace</h3>
        <div className="privacy-toggle-row"><div><strong>Allow reviewed Gemini requests</strong><p>Off means no Gemini calls. If enabled, every question needs a preview and your approval. File names are hidden and obvious emails, phone numbers and secrets are masked.</p></div><button role="switch" aria-checked={account.cloud_enabled} aria-label="Allow reviewed Gemini requests" disabled={!!busy || !state} className="privacy-switch" onClick={() => void preference("cloud_enabled", !account.cloud_enabled)}><span /></button></div>
        <div className="privacy-toggle-row"><div><strong>Save answer history</strong><p>Off by default. When off, new questions, answers and evidence are not written to answer history. Your uploaded PDFs remain stored until you delete them. Existing answers stay until cleared.</p></div><button role="switch" aria-checked={account.save_history} aria-label="Save answer history" disabled={!!busy || !state} className="privacy-switch" onClick={() => void preference("save_history", !account.save_history)}><span /></button></div>
      </section>
      <section className="privacy-section"><h3>Where your data goes</h3><div className="data-route"><span><strong>Your browser</strong><small>Question + PDFs</small></span><ArrowRight size={18} /><span><strong>VeritasAI server</strong><small>Search + evidence checks</small></span><ArrowRight size={18} /><span><strong>Encrypted database</strong><small>Documents + optional history</small></span></div><p className="boundary-note"><Globe size={16} /> Google receives reviewed passages only when you explicitly approve a Gemini request. No external AI is needed for source excerpts or claim checks.</p></section>
      <section className="privacy-section"><div className="section-title-row"><h3>Your stored data</h3><span>{state ? `${state.storage.documents} PDFs · ${(state.storage.bytes / 1_000_000).toFixed(1)} MB · ${state.storage.answers} saved answers` : "Loading…"}</span></div>
        <div className="privacy-actions"><button className="secondary-button" disabled={!!busy} onClick={() => void action("Preparing your export…", async () => { exportJson(await api("/privacy/export"), "veritas-private-data.json"); setNotice("Export downloaded. It contains private text; keep it safe. Original PDFs can be downloaded from the document viewer."); await refresh(); })}><Download size={16} /> Export my data</button>
          <button className="secondary-button" disabled={!!busy || !state?.storage.answers} onClick={() => { if (confirm("Delete all saved questions, answers and evidence? Your uploaded PDFs will stay.")) void action("Clearing answer history…", async () => { await api("/privacy/history", { method: "DELETE" }); await onDataChanged(); await refresh(); setNotice("Saved answers were removed from the active database."); }); }}><Trash2 size={16} /> Clear history</button>
          <button className="secondary-button danger-text" disabled={!!busy || !state?.storage.documents} onClick={() => { if (confirm("Delete ALL your PDFs, extracted text, search vectors and saved answers? Your account will stay. This cannot be undone in the app.")) void action("Deleting workspace data…", async () => { await api("/workspace", { method: "DELETE" }); await onDataChanged(); await refresh(); setNotice("Workspace data was removed from the active database."); }); }}><Trash2 size={16} /> Delete workspace data</button></div>
      </section>
      <section className="privacy-section"><h3>Account security</h3><p>{state?.active_sessions ?? "…"} active session(s). Sign out of all devices if you used a shared computer.</p><button className="secondary-button" disabled={!!busy} onClick={() => void action("Signing out all devices…", async () => { await api("/auth/logout-all", { method: "POST" }); onSignedOut(); })}><LogOut size={16} /> Sign out everywhere</button>
        <details className="security-details"><summary><KeyRound size={16} /> Change password</summary><form onSubmit={e => { e.preventDefault(); const form = e.currentTarget; const f = new FormData(form); void action("Changing your password…", async () => { const result = await api<{ recovery_code: string }>("/auth/password", { method: "POST", body: JSON.stringify(Object.fromEntries(f)) }); form.reset(); setRecovery(result.recovery_code); await refresh(); }); }}><label>Current password<input name="current_password" type="password" autoComplete="current-password" required maxLength={128} /></label><label>New password<input name="password" type="password" autoComplete="new-password" required minLength={15} maxLength={128} /></label><label>Confirm new password<input name="confirm_password" type="password" autoComplete="new-password" required minLength={15} maxLength={128} /></label><small>Use 15–128 characters. Other sessions and the old recovery code will stop working.</small><button className="primary-button" disabled={!!busy}>Change password</button></form></details>
      </section>
      <section className="privacy-section"><h3>Recent privacy activity</h3><p className="muted">Only action names and times. No document text, questions, emails, API keys or IP addresses. Shown for up to 30 days.</p><ol className="privacy-events">{state?.events.map(event => <li key={event.id}><ShieldCheck size={14} /><span>{eventLabels[event.event] || "Account privacy action"}</span><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></li>)}</ol></section>
      <section className="privacy-limits"><h3>What these protections do not mean</h3><ul>{(state?.limits || ["The server can decrypt content to process your requests. This is not end-to-end encryption."]).map(limit => <li key={limit}>{limit}</li>)}</ul><p>Email ownership is not verified. Your recovery code is your password-reset method. There is no independent security certification or 100% leak-proof guarantee.</p><a className="text-link" href="https://github.com/Sankalp-gupta1/veritas-ai/blob/main/docs/PRIVACY.md" target="_blank" rel="noreferrer">Read the full privacy guide ↗</a></section>
      <section className="privacy-delete"><button className="text-link danger-text" disabled={!!busy} onClick={() => setDeleting(!deleting)}>Delete my account and all active data</button>{deleting && <form onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); if (data.get("confirmation") !== "DELETE") { setError("Type DELETE to confirm."); return; } void action("Deleting your account…", async () => { await api("/auth/account", { method: "DELETE", body: JSON.stringify({ password: data.get("password") }) }); onSignedOut(); }); }}><p>This deletes your account, sessions, PDFs, text, vectors, history and privacy activity from the active database. Provider backups follow their retention schedule.</p><label>Current password<input name="password" type="password" autoComplete="current-password" required /></label><label>Type DELETE to confirm<input name="confirmation" autoComplete="off" required pattern="DELETE" /></label><button className="primary-button delete-account-button" disabled={!!busy}>Permanently delete my account</button></form>}</section>
    </>}
  </dialog>;
}
