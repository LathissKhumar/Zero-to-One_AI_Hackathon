const $ = (selector) => document.querySelector(selector);
let story;

const formatAction = (action) => `<span class="pill ${action}">${action}</span>`;

function renderEndings() {
  const target = $("#ending-grid");
  target.innerHTML = story.endings.map((ending, index) => `
    <article class="ending-card">
      <span class="ending-tag">ENDING ${index + 1}</span>
      <h3>${ending.title}</h3><p class="hook">${ending.hook}</p><p class="ending-text">${ending.text}</p>
      <div class="debt-actions">${Object.values(ending.actions).map(formatAction).join("")}</div>
    </article>`).join("");
}

function renderBenchmark(benchmark) {
  $("#benchmark-chip").textContent = `${Math.round(benchmark.recall * 100)}% recall`;
  const metrics = [["Recall", benchmark.recall], ["Precision", benchmark.precision], ["Cited", benchmark.citation_support_rate], ["Schema valid", benchmark.structured_output_rate]];
  $("#metric-grid").innerHTML = metrics.map(([name, value]) => `<div class="metric"><strong>${Math.round(value * 100)}%</strong><span>${name}</span></div>`).join("");
}

function renderComparison(result) {
  const winner = result.options[result.winner_slug];
  $("#winner-title").textContent = winner.title;
  $("#winner-reason").textContent = result.winner_reason;
  $("#winner-score").textContent = winner.debt_health;
  $("#comparison-cards").innerHTML = Object.values(result.options).map((option) => `
    <article class="audit-card ${option.slug === result.winner_slug ? "winner" : ""}">
      <span class="label">${option.slug === result.winner_slug ? "RECOMMENDED" : "TRADE-OFF"}</span>
      <h3>${option.title}</h3>
      <div class="audit-row"><span>Debt health</span><strong>${option.debt_health}/100</strong></div>
      <div class="audit-row"><span>Paid / renewed</span><strong>${option.paid} / ${option.renewed}</strong></div>
      <div class="audit-row"><span>Deferred / defaulted</span><strong>${option.deferred} / ${option.defaulted}</strong></div>
      ${(option.risks.length ? option.risks : [{message: "No unpaid high-risk contract in this ending.", severity: "low", evidence: []}]).map(risk => `<div class="risk"><b>${risk.severity.toUpperCase()}</b> ${risk.message}<div class="citations">${risk.evidence.map(e => `Ep ${e.episode}: ${e.label}`).join(" · ")}</div></div>`).join("")}
      <div class="risk"><b>SAFE EDIT</b> ${option.safe_edits[0]}</div>
    </article>`).join("");
  $("#results").hidden = false;
}

function renderCourt(court) {
  $("#court-grid").innerHTML = court.map(juror => `
    <article class="juror" style="--accent:${juror.accent}">
      <span class="vote" style="color:${juror.accent}">${juror.vote}</span>
      <h3>${juror.cohort_name}</h3><span class="role">${juror.role}</span>
      <p>${juror.reaction}</p>
      <div class="scores"><span>Fair ${juror.fairness}</span><span>Urgency ${juror.urgency}</span></div>
      <div class="citations">Evidence: ${juror.citation_ids.join(" · ")}</div>
    </article>`).join("");
  $("#court-section").hidden = false;
}

async function runCompare() {
  const button = $("#compare-button"); button.disabled = true; button.textContent = "Court deliberating…";
  const response = await fetch("/api/compare", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({left_slug:"shock-default",right_slug:"earned-storm"})});
  const result = await response.json(); renderComparison(result); renderCourt(result.court);
  button.disabled = false; button.innerHTML = "Run Audience Court <span>→</span>";
  $("#results").scrollIntoView({behavior:"smooth", block:"start"});
}

async function runDiscovery(event) {
  event.preventDefault();
  const query = $("#mood-input").value;
  const matches = await fetch(`/api/discover?q=${encodeURIComponent(query)}`).then(response => response.json());
  $("#discovery-results").innerHTML = matches.map(match => `<div class="match"><strong>${match.title} <small>· ${match.genre}</small></strong><p>${match.why}</p><span class="tags">${match.mood_tags.join(" · ")}</span></div>`).join("");
}

async function boot() {
  story = await fetch("/api/story").then(response => response.json());
  $("#story-title").textContent = story.title; $("#story-genre").textContent = story.genre;
  $("#open-debt").textContent = `${story.debts.filter(debt => debt.status !== "paid").length} contracts`;
  renderEndings(); renderBenchmark(await fetch("/api/benchmark").then(response => response.json()));
  $("#compare-button").addEventListener("click", runCompare); $("#discovery-form").addEventListener("submit", runDiscovery); runDiscovery(new Event("submit"));
}
boot();
