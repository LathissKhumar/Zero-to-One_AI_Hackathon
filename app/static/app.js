const STATE_LABEL = {
  broken: "Real hole",
  suspended: "Protected",
  outstanding: "Overdue",
};

// Sort order for the findings grid: real defects first (most urgent to a
// writer), then protected twists (the proof), then open obligations.
const STATE_ORDER = { broken: 0, suspended: 1, outstanding: 2 };

async function load() {
  const [series, audit] = await Promise.all([
    fetch("/api/series").then((response) => response.json()),
    fetch("/api/audit").then((response) => response.json()),
  ]);

  document.getElementById("series-line").textContent =
    `${series.title} — ${series.total_episodes} episodes`;
  document.getElementById("baseline-count").textContent = audit.headline.baseline_flags;
  document.getElementById("real-holes").textContent = audit.headline.real_holes;
  document.getElementById("twists").textContent = audit.headline.twists_protected;
  document.getElementById("overdue").textContent = audit.headline.overdue_obligations;

  renderFindings(audit.findings);
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
  drawer.hidden = false;
  const label = finding.state === "suspended" ? "Protected" : finding.state;
  body.innerHTML =
    `<h3>Evidence</h3>
     <p class="evidence-summary"><span class="tag">${label}</span> ${finding.entry.description}</p>
     <p class="reason">${finding.reason}</p>` +
    finding.citations
      .map((citation) => `<blockquote>Ep ${citation.episode}: ${citation.text}</blockquote>`)
      .join("");
  drawer.scrollIntoView({ behavior: "smooth", block: "start" });
}

function closeEvidence() {
  document.getElementById("evidence").hidden = true;
}

document.getElementById("evidence-close").addEventListener("click", closeEvidence);

load();
