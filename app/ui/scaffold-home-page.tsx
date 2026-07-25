import { Document } from './document.tsx'

export function HomePage() {
  return () => (
    <Document
      title="CanonPulse — The Pre-Release Story Wind Tunnel"
      head={<HomeHead />}
    >
      <div className="page-shell">
        <canvas className="webgpu-backdrop" id="webgpu-backdrop" aria-hidden="true"></canvas>
        <div className="mesh mesh-one"></div>
        <div className="mesh mesh-two"></div>
        <div className="pulse-field"></div>

        <header className="site-header" aria-label="Main navigation">
          <a className="brand" href="#top" aria-label="CanonPulse home">
            <img className="brand-mark" src="/canonpulse-logo.svg" alt="" />
            <span>CanonPulse</span>
          </a>
          <nav className="nav-links" aria-label="Landing page sections">
            <a href="#ledgers">Ledgers</a>
            <a href="#court">Audience Court</a>
            <a href="#demo">Demo</a>
          </nav>
          <a className="nav-cta" href="#apply">Request demo</a>
        </header>

        <main id="top">
          <section className="hero" aria-labelledby="hero-title">
            <div className="hero-copy reveal">
              <p className="kicker">AI quality control for serialized audio</p>
              <h1 id="hero-title">The pre-release wind tunnel for story endings.</h1>
              <p className="hero-text">
                CanonPulse checks whether a draft episode breaks canon, abandons an
                emotional promise, or creates a cliffhanger listeners will find unfair.
              </p>
              <div className="proof-strip" aria-label="CanonPulse core checks">
                <span>Canon breaks</span>
                <span>Promise debt</span>
                <span>Audience hesitation</span>
              </div>
              <div className="hero-actions" aria-label="Primary actions">
                <a className="primary-button" href="#demo">See the demo flow</a>
                <a className="secondary-button" href="#court">Meet the court</a>
              </div>
            </div>

            <div className="hero-stage reveal" aria-label="Animated CanonPulse product preview">
              <div className="orbit-ring ring-one"></div>
              <div className="orbit-ring ring-two"></div>
              <div className="code-card audit-console tilt-card">
                <div className="panel-bar">
                  <span>The Last Monsoon</span>
                  <strong>Ending A audit</strong>
                </div>
                <div className="audit-row">
                  <span>Canon Integrity</span>
                  <strong>91</strong>
                </div>
                <div className="audit-row warning">
                  <span>Promise Payoff</span>
                  <strong>62</strong>
                </div>
                <div className="audit-row">
                  <span>Emotional Continuity</span>
                  <strong>84</strong>
                </div>
                <div className="evidence-strip">
                  Episode 2: Tara cannot swim · Episode 4: cassette clue · Episode 7:
                  grief arc unresolved
                </div>
              </div>
              <div className="signal-card float-card">
                <span className="signal-dot"></span>
                <strong>Producer&apos;s Verdict</strong>
                <small>Ending B repairs the clue trail with the smallest safe edit.</small>
              </div>
              <div className="metric-card float-card">
                <span>Binge Momentum Proxy</span>
                <strong>+18%</strong>
              </div>
            </div>
          </section>

          <section className="section-band" id="ledgers" aria-labelledby="ledgers-title">
            <div className="section-heading reveal">
              <p className="kicker">Stories make promises</p>
              <h2 id="ledgers-title">CanonPulse remembers what the audience was taught to expect.</h2>
            </div>
            <div className="track-grid">
              <article className="track-card reveal">
                <span className="ledger-label">Fact memory</span>
                <h3>Canon Ledger</h3>
                <p>Facts, dates, abilities, locations, and relationships checked against cited episode evidence.</p>
              </article>
              <article className="track-card reveal">
                <span className="ledger-label">Unpaid setup</span>
                <h3>Promise Ledger</h3>
                <p>Mysteries, planted clues, emotional obligations, and foreshadowing tracked until payoff.</p>
              </article>
              <article className="track-card reveal">
                <span className="ledger-label">Feeling curve</span>
                <h3>Emotion Ledger</h3>
                <p>Trust, fear, grief, romance, guilt, and tension mapped episode by episode.</p>
              </article>
            </div>
          </section>

          <section className="court-band" id="court" aria-labelledby="court-title">
            <div className="section-heading reveal">
              <p className="kicker">Audience Court</p>
              <h2 id="court-title">Five listener cohorts argue before the episode goes live.</h2>
            </div>
            <div className="jury-grid">
              <article className="juror-card vote-continue reveal">
                <span>Continue</span>
                <h3>The Binge Listener</h3>
                <p>&quot;The storm ending gives me a reason to start the next episode now.&quot;</p>
              </article>
              <article className="juror-card vote-hesitate reveal">
                <span>Hesitate</span>
                <h3>The Mystery Purist</h3>
                <p>&quot;The surprise villain shocks me, but the clue trail does not earn it.&quot;</p>
              </article>
              <article className="juror-card vote-continue reveal">
                <span>Continue</span>
                <h3>The Romance Listener</h3>
                <p>&quot;The reconciliation works only if the grief beat is acknowledged first.&quot;</p>
              </article>
              <article className="juror-card vote-stop reveal">
                <span>Stop</span>
                <h3>The Skeptic</h3>
                <p>&quot;Rafi needs at least one prior motive scene before this reveal lands.&quot;</p>
              </article>
              <article className="juror-card vote-continue reveal">
                <span>Continue</span>
                <h3>The Late-Night Listener</h3>
                <p>&quot;Ending B is clearer, moodier, and easier to replay in my head.&quot;</p>
              </article>
            </div>
          </section>

          <section className="timeline" id="demo" aria-labelledby="demo-title">
            <div className="section-heading reveal">
              <p className="kicker">The Last Monsoon demo</p>
              <h2 id="demo-title">In under two minutes, judges see the system make a defensible call.</h2>
            </div>
            <div className="timeline-rail">
              <div className="timeline-item reveal">
                <span>Step 1</span>
                <h3>Select a season</h3>
                <p>Open an eight-episode Mumbai thriller with indexed events, clues, relationships, and emotional beats.</p>
              </div>
              <div className="timeline-item reveal">
                <span>Step 2</span>
                <h3>Compare endings</h3>
                <p>Test &quot;The Surprise Villain&quot; against &quot;The Earned Storm&quot; before release.</p>
              </div>
              <div className="timeline-item reveal">
                <span>Step 3</span>
                <h3>Apply safe edits</h3>
                <p>Use three minimal revisions tied to exact contradictions or unresolved promises.</p>
              </div>
            </div>
          </section>

          <section className="prize-band" aria-labelledby="stack-title">
            <div className="prize-copy reveal">
              <p className="kicker">Built for a real creator workflow</p>
              <h2 id="stack-title">Structured AI output, cited evidence, and local demo resilience.</h2>
            </div>
            <div className="prize-stack reveal" aria-label="System capabilities">
              <span>OpenAI extracts claims, promises, and emotional beats into JSON</span>
              <span>Databricks stores long-story memory and evaluation traces</span>
              <span>Offline demo mode keeps the pitch stable without credentials</span>
            </div>
          </section>

          <section className="apply" id="apply" aria-labelledby="apply-title">
            <div className="apply-panel reveal">
              <div>
                <p className="kicker">Creator-side pre-publication tool</p>
                <h2 id="apply-title">Find the smallest change that makes a cliffhanger feel earned.</h2>
              </div>
              <form className="signup-form">
                <label htmlFor="email">Email address</label>
                <div className="form-row">
                  <input id="email" name="email" type="email" placeholder="creator@example.com" />
                  <button type="submit">Request demo</button>
                </div>
              </form>
            </div>
          </section>
        </main>
      </div>

      <script type="module" src="/landing.js?v=20260725-remix"></script>
    </Document>
  )
}

function HomeHead() {
  return () => (
    <>
      <meta
        name="description"
        content="CanonPulse is an AI quality-control and audience-testing studio for long-form audio series."
      />
      <meta name="color-scheme" content="dark" />
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,600;6..72,700&display=swap"
      />
      <link rel="stylesheet" href="/landing.css?v=20260725-remix" />
    </>
  )
}
