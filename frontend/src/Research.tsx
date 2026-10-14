import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  FlaskConical,
  ArrowDownToLine,
  Clock3,
  ShieldCheck,
  ChartNoAxesCombined,
} from "lucide-react";
import { api, exportJson } from "./api";
import type { Run } from "./types";
export function Research({ runs }: { runs: Run[] }) {
  const [metrics, setMetrics] = useState<any>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/research")
      .then(setMetrics)
      .catch((e) => setError(e.message));
  }, []);
  const mean = runs.length
    ? runs.reduce((a, r) => a + r.latency_ms, 0) / runs.length
    : 0;
  return (
    <div className="research-page">
      <div className="section-eyebrow">
        <FlaskConical size={15} /> THE EVIDENCE LAB
      </div>
      <h1>Measure before you believe.</h1>
      <p className="lead">
        A transparent look at what works, what fails, and what still needs
        testing.
      </p>
      <div className="metric-grid">
        <div>
          <span>
            <ChartNoAxesCombined size={16} /> Saved answers
          </span>
          <strong>{runs.length}</strong>
          <small>Most recent 100 in this workspace</small>
        </div>
        <div>
          <span>
            <Clock3 size={16} /> Mean response time
          </span>
          <strong>{runs.length ? `${(mean / 1000).toFixed(1)}s` : "—"}</strong>
          <small>Recorded pipeline time; comparisons reuse work</small>
        </div>
        <div>
          <span>
            <ShieldCheck size={16} /> Human-rated quality
          </span>
          <strong>Not evaluated</strong>
          <small>Model verdicts are not ground truth</small>
        </div>
      </div>
      <section className="research-card">
        <div className="section-heading">
          <div>
            <h2>Reproducible fixture evaluation</h2>
            <p>
              Small, authored examples that test the pipeline. These are not
              clinical findings or a research benchmark.
            </p>
          </div>
          {metrics?.status === "complete" && (
            <button
              className="secondary-button"
              onClick={() =>
                exportJson(metrics, "veritas-fixture-results.json")
              }
            >
              <ArrowDownToLine size={15} /> Download data
            </button>
          )}
        </div>
        {error ? (
          <p role="alert">{error}</p>
        ) : !metrics ? (
          <p>Loading measured results…</p>
        ) : metrics.status !== "complete" ? (
          <p className="empty-notice">
            No evaluation results yet. Run the experiment script to generate
            real measurements.
          </p>
        ) : (
          <>
            <div className="chart-caption">
              {metrics.sample_count} authored claim–evidence pairs ·{" "}
              {metrics.run_date} · CPU inference
            </div>
            <div
              className="chart"
              role="img"
              aria-label="Claim classification precision, recall and F1 by class"
            >
              <ResponsiveContainer width="100%" height={270}>
                <BarChart data={metrics.per_class}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 1]} tickLine={false} axisLine={false} />
                  <Tooltip />
                  <Legend />
                  <Bar
                    dataKey="precision"
                    fill="#a5b4fc"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar dataKey="recall" fill="#8172da" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="f1" fill="#403461" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-note">
              Macro F1: {Number(metrics.macro_f1).toFixed(3)}. This small
              fixture run cannot establish hallucination reduction on real
              research papers. Labels were authored before inference; no model
              verdict was used as its own ground truth.
            </p>
            <details>
              <summary>View exact values and failures</summary>
              <table>
                <thead>
                  <tr>
                    <th>Class</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.per_class.map((row: any) => (
                    <tr key={row.label}>
                      <td>{row.label}</td>
                      <td>{row.precision.toFixed(3)}</td>
                      <td>{row.recall.toFixed(3)}</td>
                      <td>{row.f1.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p>
                {metrics.failures?.length || 0} misclassified examples. Download
                the data to inspect every prediction.
              </p>
            </details>
          </>
        )}
      </section>
      <section className="research-card">
        <h2>The comparison that matters</h2>
        <div className="variant-grid">
          <article>
            <span>01</span>
            <h3>Standard RAG</h3>
            <p>
              Find passages with semantic search, then ask the model to write a
              cited answer.
            </p>
          </article>
          <article>
            <span>02</span>
            <h3>RAG + reranking</h3>
            <p>
              A second model reorders the same candidates before the answer is
              written.
            </p>
          </article>
          <article>
            <span>03</span>
            <h3>Claim verification</h3>
            <p>
              Reuse the exact answer from step 2. Check every quote and claim;
              withhold unsupported statements.
            </p>
          </article>
        </div>
        <div className="method-note">
          <strong>Quality comparison: not yet independently evaluated.</strong>
          <p>
            Use “Compare methods” in the workspace to collect answers.
            Independent human labels and a held-out question set are needed to
            measure unsupported-claim rate, citation support and answer
            coverage. Latency alone is not quality.
          </p>
        </div>
      </section>
    </div>
  );
}
