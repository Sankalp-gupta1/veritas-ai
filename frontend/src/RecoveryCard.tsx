import { useState } from "react";
import { ArrowRight, Download, KeyRound } from "lucide-react";
import { exportJson } from "./api";

export function RecoveryCard({ code, onDone }: { code: string; onDone: () => void }) {
  const [saved, setSaved] = useState(false);
  return <section className="recovery-card" aria-labelledby="recovery-title">
    <div className="auth-icon"><KeyRound size={25} /></div>
    <h2 id="recovery-title">One last step. Keep your way back in.</h2>
    <p>This recovery code can reset your password. Save it somewhere private. We only show it now, and we do not send password-reset emails.</p>
    <code className="recovery-code">{code}</code>
    <button className="secondary-button" onClick={() => exportJson({ recovery_code: code, note: "VeritasAI account recovery. Keep private. Never share this code." }, "veritas-recovery-code.json")}><Download size={16} /> Download recovery code</button>
    <label className="check-label"><input type="checkbox" checked={saved} onChange={e => setSaved(e.target.checked)} /> I have saved my recovery code safely.</label>
    <button className="primary-button" disabled={!saved} onClick={onDone}>Open my workspace <ArrowRight size={16} /></button>
    <small>Anyone with this code and your email can reset your password. A new password creates a new code.</small>
  </section>;
}

