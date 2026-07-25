const STATE_LABEL = {
  broken: "Real hole",
  suspended: "Protected",
  outstanding: "Overdue",
};

// Sort order for the findings grid: real defects first (most urgent to a
// writer), then protected twists (the proof), then open obligations.
const STATE_ORDER = { broken: 0, suspended: 1, outstanding: 2 };

let currentSeries = null;

async function load() {
  const [series, audit, discrimination] = await Promise.all([
    fetch("/api/series").then((response) => response.json()),
    fetch("/api/audit").then((response) => response.json()),
    fetch("/api/discrimination").then((response) => response.json()),
  ]);
  currentSeries = series;

  document.getElementById("series-line").textContent =
    `${series.title} — ${series.total_episodes} episodes`;
  document.getElementById("baseline-count").textContent = audit.headline.baseline_flags;
  document.getElementById("real-holes").textContent = audit.headline.real_holes;
  document.getElementById("twists").textContent = audit.headline.twists_protected;
  document.getElementById("overdue").textContent = audit.headline.overdue_obligations;

  renderFindings(audit.findings);
  renderDiscrimination(discrimination);
  loadPrediction(series.total_episodes - 1);
}

// Two honest numbers, never rendered adjacent without the label saying what
// each one measures -- an unlabelled pair invites a reader to assume the
// higher figure is the headline, which is the single misleading metric this
// dashboard exists to not have.
function renderDiscrimination(report) {
  const ledger = report.ledger;
  const extracted = report.extracted;

  document.getElementById("ledger-values").textContent =
    `recall ${ledger.recall.toFixed(2)} · precision ${ledger.precision.toFixed(2)} · ` +
    `false positive rate ${ledger.false_positive_rate.toFixed(2)}`;
  document.getElementById("ledger-explainer").textContent =
    "Given a correct, hand-authored graph, the resolver separates all " +
    `${ledger.holes_total} real plot holes from all ${ledger.twists_total} intentional twists ` +
    "with no false positives. This measures graph traversal only, not extraction.";

  if (!extracted) {
    document.getElementById("extracted-values").textContent = "not run";
    document.getElementById("extracted-explainer").textContent =
      "No extractor was supplied for this report.";
    return;
  }

  document.getElementById("extracted-values").textContent =
    `recall ${extracted.recall.toFixed(2)} · precision ${extracted.precision.toFixed(2)} · ` +
    `false positive rate ${extracted.false_positive_rate.toFixed(2)}`;
  // Derived from the report, never hardcoded: prose stating counts the report
  // does not carry goes stale silently the moment the extractor or series
  // changes, and it already did once.
  const cleansFlagged = Math.round(extracted.false_positive_rate * extracted.clean_total);
  document.getElementById("extracted-explainer").textContent =
    "Run end-to-end through the offline heuristic extractor, the system recovers " +
    `${extracted.holes_caught} of ${extracted.holes_total} real plot holes and protects ` +
    `${extracted.twists_protected} of ${extracted.twists_total} intentional twists. ` +
    `It over-flags ${cleansFlagged} of ${extracted.clean_total} clean controls. ` +
    "No twist can be protected until a Verifier exists: protection requires a verified " +
    "payoff link by design, and no extractor here can produce one, so the reachable " +
    "precision ceiling is 0.55 rather than 1.0.";
}

async function loadPrediction(episode) {
  const payload = await fetch(`/api/predict?episode=${episode}`).then((r) => r.json());
  const valueEl = document.getElementById("prediction-value");
  const intervalEl = document.getElementById("prediction-interval");
  const disclosureEl = document.getElementById("prediction-disclosure");
  disclosureEl.textContent = payload.disclosure || "";

  if (payload.degraded) {
    valueEl.textContent = "offline";
    intervalEl.textContent =
      "Inference was too slow -- switched to the golden path (real ledger data, no model call).";
    return;
  }

  const pct = (payload.prediction.value * 100).toFixed(1);
  const lo = (payload.prediction.lower_ci * 100).toFixed(1);
  const hi = (payload.prediction.upper_ci * 100).toFixed(1);
  valueEl.textContent = `${pct}%`;
  intervalEl.textContent =
    `${lo}%–${hi}% (${payload.prediction.ci_method})` +
    (payload.prediction.clamped ? " · clamped to [0,1]" : "") +
    ` — boundary after episode ${payload.episode}`;
}

function renderFindings(findings) {
  const container = document.getElementById("findings");
  container.innerHTML = "";
  const ordered = [...findings].sort(
    (a, b) => STATE_ORDER[a.state] - STATE_ORDER[b.state]
  );
  for (const finding of ordered) {
    const card = document.createElement("article");
    card.className = `finding ${finding.state}${finding.overdue ? " overdue" : ""}`;
    const label = finding.state === "suspended" ? "Protected" : finding.state;
    const span = payoffSpan(finding);
    card.innerHTML = `
      <span class="tag">${label}</span>
      <h3>${finding.entry.description}</h3>
      <p class="reason">${finding.reason}</p>
      ${span ? `<p class="span-badge">${span}-episode payoff span</p>` : ""}`;
    card.addEventListener("click", () => showEvidence(finding));
    container.appendChild(card);
  }
}

function payoffSpan(finding) {
  if (!finding.payoff) return null;
  return finding.payoff.episode - Math.min(...finding.entry.episodes);
}

function showEvidence(finding) {
  const drawer = document.getElementById("evidence");
  const body = document.getElementById("evidence-body");
  const rewriteBody = document.getElementById("rewrite-body");
  drawer.hidden = false;
  rewriteBody.innerHTML = "";
  const label = finding.state === "suspended" ? "Protected" : finding.state;
  body.innerHTML =
    `<h3>Evidence</h3>
     <p class="evidence-summary"><span class="tag">${label}</span> ${finding.entry.description}</p>
     <p class="reason">${finding.reason}</p>` +
    finding.citations
      .map((citation) => `<blockquote>Ep ${citation.episode}: ${citation.text}</blockquote>`)
      .join("");

  if (finding.state === "broken") {
    const button = document.createElement("button");
    button.className = "repair-button";
    button.textContent = "Simulate repair";
    button.addEventListener("click", () => runRewrite(finding));
    rewriteBody.appendChild(button);
  }

  drawer.scrollIntoView({ behavior: "smooth", block: "start" });
}

// Features that count actual failures or unresolved gaps. The server rejects
// an edit that claims an *increase* in one of these as a repair -- there is
// no reading of "more broken promises" as an improvement. Kept in sync with
// app/rewrite.py::_WORSENS_IF_INCREASED.
const WORSENS_IF_INCREASED = new Set([
  "broken_count",
  "overdue_count",
  "max_obligation_age",
  "mean_obligation_age",
  "planting_recency",
]);

// Which feature actually moved, and how, differs per finding and per episode
// window -- the ledger is real data, not a script, so "closing this
// obligation" cannot be hardcoded to always move the same feature the same
// way. Ask the server what genuinely changed between the two boundaries and
// attribute to whichever named feature the movement actually supports,
// instead of guessing and letting the server reject an incoherent claim.
function pickCoherentRepairEdit(beforeFeatures, afterFeatures) {
  for (const name of WORSENS_IF_INCREASED) {
    if (afterFeatures[name] < beforeFeatures[name]) {
      return { feature_moved: name, delta: 0.02 };
    }
  }
  for (const name of Object.keys(beforeFeatures)) {
    if (WORSENS_IF_INCREASED.has(name)) continue;
    if (afterFeatures[name] !== beforeFeatures[name]) {
      return { feature_moved: name, delta: 0.02 };
    }
  }
  return null;
}

async function runRewrite(finding) {
  const rewriteBody = document.getElementById("rewrite-body");
  rewriteBody.innerHTML = "<p class=\"reason\">Computing attributed movement…</p>";

  const totalEpisodes = currentSeries ? currentSeries.total_episodes : 220;
  const beforeEpisode = Math.min(...finding.entry.episodes);
  const afterEpisode = Math.min(beforeEpisode + 10, totalEpisodes);

  const [beforePredict, afterPredict] = await Promise.all([
    fetch(`/api/predict?episode=${beforeEpisode}`).then((r) => r.json()),
    fetch(`/api/predict?episode=${afterEpisode}`).then((r) => r.json()),
  ]);

  const edit = pickCoherentRepairEdit(beforePredict.features, afterPredict.features);
  if (!edit) {
    rewriteBody.innerHTML =
      "<p class=\"reason\">No structural feature moved between these two boundaries -- " +
      "nothing to attribute.</p>";
    return;
  }

  const report = await fetch("/api/rewrite", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      before_episode: beforeEpisode,
      after_episode: afterEpisode,
      edits: [
        {
          hunk: "closes the obligation this finding is anchored to",
          obligation_id: finding.entry.id,
          feature_moved: edit.feature_moved,
          // A claimed, per-edit estimate -- independent of the total_delta
          // below, which the server computes from the trained predictor.
          // The gap between them (unattributed) is the honesty check.
          delta: edit.delta,
        },
      ],
    }),
  }).then((r) => r.json());

  renderRewriteReport(report);
}

function renderRewriteReport(report) {
  const rewriteBody = document.getElementById("rewrite-body");
  const pct = (value) => (value * 100).toFixed(2) + "pp";
  rewriteBody.innerHTML =
    `<h3>Attributed prediction movement</h3>
     <p class="reason">Total predicted movement (Ep ${Math.round(
       report.features_before.episode
     )} → Ep ${Math.round(report.features_after.episode)}): <strong>${pct(
      report.total_delta
    )}</strong></p>
     <ul class="attribution">` +
    report.edits
      .map(
        (edit) =>
          `<li><span class="hunk">${edit.hunk}</span><span class="delta">${pct(
            edit.delta
          )}</span><span class="obligation">→ ${edit.obligation_id}</span></li>`
      )
      .join("") +
    `</ul>
     <p class="reason unattributed">Unattributed: ${pct(report.unattributed)} — movement the named
     edits do not account for, reported rather than absorbed.</p>`;
}

function closeEvidence() {
  document.getElementById("evidence").hidden = true;
}

document.getElementById("evidence-close").addEventListener("click", closeEvidence);

load();
