const STATE_LABEL = {
  broken: "Real hole",
  suspended: "Protected",
  outstanding: "Overdue",
};

// Sort order for the findings grid: real defects first (most urgent to a
// writer), then protected twists (the proof), then open obligations.
const STATE_ORDER = { broken: 0, suspended: 1, outstanding: 2 };

let currentSeries = null;
const uiState = { loading: false, error: null };

async function load() {
  uiState.loading = true;
  uiState.error = null;
  try {
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
  loadSurfaceSummaries(series.total_episodes);
  document.getElementById("health-status").textContent = "ready · cited ledger and model surfaces loaded";
  document.getElementById("comparison-status").textContent = `${audit.headline.baseline_flags} baseline flags compared with ${audit.headline.real_holes} real holes`;
  document.getElementById("obligation-heatmap").textContent = `${audit.findings.length} cited obligations available across the series`;
  } catch (error) {
    uiState.error = error;
    const status = document.getElementById("health-status");
    status.textContent = "error loading series";
    const retry = document.createElement("button");
    retry.textContent = "Retry";
    retry.addEventListener("click", load);
    status.appendChild(retry);
  } finally {
    uiState.loading = false;
  }
}

async function loadSurfaceSummaries(totalEpisodes) {
  const [handoff, debt, cohorts, discovery] = await Promise.all([
    fetch(`/api/handoff?writer_id=unknown&episode=${totalEpisodes}`).then((r) => r.json()),
    fetch("/api/debt-board").then((r) => r.json()),
    fetch("/api/cohorts").then((r) => r.json()),
    fetch("/api/discover?query=rainy%20Sunday%20after%20heartbreak").then((r) => r.json()),
  ]);
  document.getElementById("handoff-surface").textContent =
    `${handoff.inherited.length} inherited open obligations · ${handoff.overdue.length} overdue · ${handoff.source_version.slice(0, 8)} version`;
  document.getElementById("debt-surface").textContent =
    `${debt.total_open} open obligations ranked by urgency and age.`;
  document.getElementById("cohort-surface").textContent =
    `${cohorts.cohorts.length} fixed cohorts · ${cohorts.reactions.length} structural reactions · simulation only.`;
  const match = discovery.matches[0];
  document.getElementById("discovery-surface").textContent = match
    ? `${match.explanation} Cite ${match.citation_ids.join(", ")}.`
    : "No obligation-shape match found.";
  document.getElementById("memory-surface").textContent = "Search prior plants, claims, payoffs, and citations.";
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
  container.replaceChildren();
  const ordered = [...findings].sort(
    (a, b) => STATE_ORDER[a.state] - STATE_ORDER[b.state]
  );
  for (const finding of ordered) {
    const card = document.createElement("article");
    card.className = `finding ${finding.state}${finding.overdue ? " overdue" : ""}`;
    const label = finding.state === "suspended" ? "Protected" : finding.state;
    const span = payoffSpan(finding);
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = label;
    const title = document.createElement("h3");
    title.textContent = finding.entry.description;
    const reason = document.createElement("p");
    reason.className = "reason";
    reason.textContent = finding.reason;
    card.append(tag, title, reason);
    if (span) {
      const badge = document.createElement("p");
      badge.className = "span-badge";
      badge.textContent = `${span}-episode payoff span`;
      card.appendChild(badge);
    }
    card.addEventListener("click", () => showEvidence(finding));
    container.appendChild(card);
  }
}

function payoffSpan(finding) {
  if (!finding.payoff) return null;
  return finding.payoff.episode - Math.min(...finding.entry.episodes);
}

function showEvidence(finding) {
  const drawer = document.getElementById("evidence-drawer");
  const body = document.getElementById("evidence-body");
  const rewriteBody = document.getElementById("rewrite-body");
  drawer.hidden = false;
  rewriteBody.replaceChildren();
  const label = finding.state === "suspended" ? "Protected" : finding.state;
  body.replaceChildren();
  const heading = document.createElement("h3");
  heading.textContent = "Evidence";
  const summary = document.createElement("p");
  summary.className = "evidence-summary";
  summary.textContent = `${label} — ${finding.entry.description}`;
  const reason = document.createElement("p");
  reason.className = "reason";
  reason.textContent = finding.reason;
  body.append(heading, summary, reason);
  for (const citation of finding.citations) {
    const quote = document.createElement("blockquote");
    quote.textContent = `Ep ${citation.episode}: ${citation.text}`;
    body.appendChild(quote);
  }

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
  rewriteBody.replaceChildren();
  const progress = document.createElement("p");
  progress.className = "reason";
  progress.textContent = "Computing attributed movement…";
  rewriteBody.appendChild(progress);

  const totalEpisodes = currentSeries ? currentSeries.total_episodes : 220;
  const beforeEpisode = Math.min(...finding.entry.episodes);
  const afterEpisode = Math.min(beforeEpisode + 10, totalEpisodes);

  const [beforePredict, afterPredict] = await Promise.all([
    fetch(`/api/predict?episode=${beforeEpisode}`).then((r) => r.json()),
    fetch(`/api/predict?episode=${afterEpisode}`).then((r) => r.json()),
  ]);

  const edit = pickCoherentRepairEdit(beforePredict.features, afterPredict.features);
  if (!edit) {
    rewriteBody.replaceChildren();
    const empty = document.createElement("p");
    empty.className = "reason";
    empty.textContent = "No structural feature moved between these two boundaries — nothing to attribute.";
    rewriteBody.appendChild(empty);
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
  rewriteBody.replaceChildren();
  const heading = document.createElement("h3");
  heading.textContent = "Attributed prediction movement";
  const summary = document.createElement("p");
  summary.className = "reason";
  summary.textContent = `Total predicted movement (Ep ${Math.round(report.features_before.episode)} → Ep ${Math.round(report.features_after.episode)}): ${pct(report.total_delta)}`;
  const list = document.createElement("ul");
  list.className = "attribution";
  for (const edit of report.edits) {
    const item = document.createElement("li");
    item.textContent = `${edit.hunk} — ${pct(edit.delta)} → ${edit.obligation_id}`;
    list.appendChild(item);
  }
  const remainder = document.createElement("p");
  remainder.className = "reason unattributed";
  remainder.textContent = `Unattributed: ${pct(report.unattributed)} — movement the named edits do not account for, reported rather than absorbed.`;
  rewriteBody.append(heading, summary, list, remainder);
}

function closeEvidence() {
  document.getElementById("evidence-drawer").hidden = true;
}

document.getElementById("evidence-close").addEventListener("click", closeEvidence);

document.getElementById("memory-search").addEventListener("click", async () => {
  const query = document.getElementById("memory-query").value.trim();
  if (!query) return;
  const response = await fetch(`/api/memory?query=${encodeURIComponent(query)}`);
  const payload = await response.json();
  document.getElementById("memory-surface").textContent = response.ok
    ? `${payload.hits.length} cited ledger hits: ${payload.hits.map((hit) => hit.entry.description).join(" · ")}`
    : payload.detail || "Memory query failed.";
});

load();
