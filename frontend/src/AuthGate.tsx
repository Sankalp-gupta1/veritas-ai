import { useEffect, useRef, useState } from "react";
import { ArrowRight, Check, Eye, EyeOff, Fingerprint, LoaderCircle, LockKeyhole, ShieldCheck } from "lucide-react";
import { api } from "./api";
import App from "./App";
import { RecoveryCard } from "./RecoveryCard";
import type { Account } from "./types";


export default function AuthGate() {
  const [account, setAccount] = useState<Account | null>(null);
  const [checking, setChecking] = useState(true);
  const [legacy, setLegacy] = useState(false);
  const [mode, setMode] = useState<"register" | "login" | "recover">("register");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [recovery, setRecovery] = useState("");
  const [show, setShow] = useState(false);
  const [importOld, setImportOld] = useState(true);
  const activity = useRef(Date.now());
  const heartbeat = useRef(Date.now());
  const channel = useRef<BroadcastChannel | null>(null);

  async function checkSession() {
    const result = await api<{ account: Account | null; legacy_available: boolean }>("/auth/session");
    setAccount(result.account);
    setLegacy(result.legacy_available);
    activity.current = Date.now();
  }
  useEffect(() => {
    void checkSession().catch(() => setError("We could not connect. Refresh to try again.")).finally(() => setChecking(false));
    const expire = () => { setAccount(null); setRecovery(""); setMode("login"); setError("Your session ended. Sign in to continue."); };
    window.addEventListener("veritas-session-ended", expire);
    if (typeof BroadcastChannel !== "undefined") {
      channel.current = new BroadcastChannel("veritas-account");
      channel.current.onmessage = () => { setAccount(null); setRecovery(""); setMode("login"); };
    }
    return () => { window.removeEventListener("veritas-session-ended", expire); channel.current?.close(); };
  }, []);

  useEffect(() => {
    if (!account) return;
    const touch = () => { activity.current = Date.now(); };
    const events = ["pointerdown", "keydown", "scroll"];
    events.forEach(event => window.addEventListener(event, touch, { passive: true }));
    const timer = window.setInterval(() => {
      if (Date.now() - activity.current >= 30 * 60_000) {
        setAccount(null); setRecovery(""); setMode("login"); setError("Workspace locked after 30 minutes without activity.");
        void api("/auth/logout", { method: "POST" }).catch(() => undefined);
        channel.current?.postMessage("locked");
      } else if (document.visibilityState === "visible" && Date.now() - heartbeat.current > 5 * 60_000 && activity.current > heartbeat.current) {
        heartbeat.current = Date.now();
        void api<{ account: Account | null }>("/auth/session").then(r => {
          if (!r.account) { setAccount(null); setMode("login"); }
        }).catch(() => undefined);
      }
    }, 15_000);
    return () => { clearInterval(timer); events.forEach(event => window.removeEventListener(event, touch)); };
  }, [account?.id]);

  function signedOut() {
    setAccount(null); setRecovery(""); setMode("login"); setError("");
    channel.current?.postMessage("signed-out");
  }
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password") || "");
    const confirmation = String(data.get("confirm_password") || "");
    if (mode !== "login" && password !== confirmation) { setError("The passwords do not match."); return; }
    setBusy(true); setError("");
    try {
      const result = await api<{ account?: Account; recovery_code?: string }>(`/auth/${mode}`, {
        method: "POST", body: JSON.stringify({ email: data.get("email"), password,
          ...(mode !== "login" ? { confirm_password: confirmation, import_workspace: legacy && importOld } : {}),
          ...(mode === "recover" ? { recovery_code: data.get("recovery_code") } : {}),
        }),
      });
      event.currentTarget?.reset();
      if (result.account) setAccount(result.account); else await checkSession();
      if (result.recovery_code) setRecovery(result.recovery_code);
      activity.current = Date.now();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  if (checking) return <div className="auth-loading"><ShieldCheck size={30} /><p>Opening your private workspace…</p><LoaderCircle className="spin" size={20} /></div>;
  if (account && !recovery) return <App key={account.id} account={account} onAccount={setAccount} onSignedOut={signedOut} />;
  return <main className="auth-shell">
    <section className="auth-story">
      <a href="/" className="auth-brand"><span className="brand-mark"><Check size={24} /></span> veritas<span>ai</span></a>
      <div className="auth-story-content">
        <span className="eyebrow"><span className="live-dot" /> EVIDENCE FIRST. PRIVACY BY DEFAULT.</span>
        <h1>Your ideas deserve<br />a <em>private space.</em></h1>
        <p>Read deeply. Ask freely. Check every claim.<br />You decide what leaves your research workspace.</p>
        <div className="vault-visual" aria-hidden="true"><div className="vault-orbit orbit-outer" /><div className="vault-orbit orbit-inner" /><div className="vault-core"><Fingerprint size={64} strokeWidth={1.15} /></div><span className="vault-tag"><LockKeyhole size={13} /> Protected by your account</span></div>
        <div className="auth-promises">
          <div><ShieldCheck size={20} /><span><strong>External AI starts off</strong><small>No document text goes to Gemini unless you review and approve it.</small></span></div>
          <div><LockKeyhole size={20} /><span><strong>Encrypted content storage</strong><small>Your PDFs, extracted text and saved answers are encrypted on the server.</small></span></div>
          <div><Eye size={20} /><span><strong>Clear controls, honest limits</strong><small>See your data flow. Export your work. Delete what you no longer need.</small></span></div>
        </div>
      </div>
      <p className="auth-boundary">The server processes your documents. This is not end-to-end encryption or a zero-risk guarantee.</p>
    </section>
    <section className="auth-form-side">
      {recovery ? <RecoveryCard code={recovery} onDone={() => setRecovery("")} /> : <div className="auth-card">
        <div className="auth-icon"><LockKeyhole size={24} /></div>
        <p className="eyebrow">YOUR RESEARCH. YOUR CONTROL.</p>
        <h2>{mode === "register" ? "Make room for good questions." : mode === "recover" ? "Get back to your research." : "Welcome back."}</h2>
        <p className="muted">{mode === "register" ? "Create your own workspace in a moment." : mode === "recover" ? "Use the private recovery code you saved when you created your account." : "Sign in to your private document workspace."}</p>
        {mode !== "recover" && <div className="auth-tabs" role="group" aria-label="Account action"><button aria-pressed={mode === "register"} onClick={() => { setMode("register"); setError(""); }}>Create account</button><button aria-pressed={mode === "login"} onClick={() => { setMode("login"); setError(""); }}>Sign in</button></div>}
        <form onSubmit={e => void submit(e)} key={mode}>
          <label>Email address<input type="email" name="email" autoComplete="email" placeholder="you@example.com" required maxLength={254} disabled={busy} /></label>
          {mode === "recover" && <label>Recovery code<input type="password" name="recovery_code" autoComplete="off" required maxLength={100} disabled={busy} /></label>}
          <label>{mode === "recover" ? "New password" : "Password"}<span className="password-field"><input type={show ? "text" : "password"} name="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "login" ? 1 : 15} maxLength={128} disabled={busy} /><button type="button" aria-label={show ? "Hide password" : "Show password"} onClick={() => setShow(!show)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button></span></label>
          {mode !== "login" && <><small className="field-hint">At least 15 characters. Try a memorable, unique passphrase.</small><label>Confirm password<input type={show ? "text" : "password"} name="confirm_password" autoComplete="new-password" required minLength={15} maxLength={128} disabled={busy} /></label></>}
          {mode === "register" && legacy && <label className="check-label"><input type="checkbox" checked={importOld} onChange={e => setImportOld(e.target.checked)} /> Move this browser's existing research into my new account.</label>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button type="submit" className="primary-button auth-submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={18} /> : <>{mode === "register" ? "Create my private workspace" : mode === "recover" ? "Reset password" : "Sign in"}<ArrowRight size={17} /></>}</button>
        </form>
        {mode === "login" && <button className="text-link auth-recover" onClick={() => { setMode("recover"); setError(""); }}>Forgot your password? Use your recovery code.</button>}
        {mode === "recover" && <button className="text-link auth-recover" onClick={() => { setMode("login"); setError(""); }}>Back to sign in</button>}
        <div className="auth-fine-print"><ShieldCheck size={15} /><span>No advertising trackers. No API key needed to check document evidence. Your email is a sign-in identifier; email ownership is not verified.</span></div>
        <a className="text-link privacy-policy-link" href="https://github.com/Sankalp-gupta1/veritas-ai/blob/main/docs/PRIVACY.md" target="_blank" rel="noreferrer">Read the privacy guide ↗</a>
      </div>}
    </section>
  </main>;
}
