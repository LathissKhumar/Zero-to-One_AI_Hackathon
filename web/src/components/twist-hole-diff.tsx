import { useId, useState } from "react"
import { Section, focusRing } from "@/components/section"
import { cn } from "@/lib/utils"

type Verdict = "protected" | "repaired" | "debt"

type Line = { n: string; text: string; flagged?: boolean }

type Case = {
  tab: string
  episode: string
  verdict: Verdict
  claim: string
  passage: Line[]
  /** The backward causal payoff test — the thing that decides the verdict. */
  test: { label: string; value: string }[]
  action: string
  patch?: { removed: string; added: string }
}

const VERDICTS = {
  protected: { label: "Intentional twist · protected", dot: "bg-emerald-400", text: "text-emerald-300" },
  repaired: { label: "Accidental hole · repaired", dot: "bg-amber-400", text: "text-amber-300" },
  debt: { label: "Open obligation · narrative debt", dot: "bg-rose-400", text: "text-rose-300" },
} satisfies Record<Verdict, { label: string; dot: string; text: string }>

const CASES: Case[] = [
  {
    tab: "A lie that pays off later",
    episode: "Episode 02 · line 41",
    verdict: "protected",
    claim: "Character A contradicts the Episode 01 narration. CanonPulse leaves it alone.",
    passage: [
      { n: "39", text: "B:  You were awake. I saw the light under your door." },
      { n: "40", text: "A:  (beat)" },
      { n: "41", text: "A:  I never woke up that night.", flagged: true },
      { n: "42", text: "B:  Then who bolted the gate?" },
    ],
    test: [
      { label: "Contradicts", value: "Ep 01 · A described as awake at 3:14am" },
      { label: "Backward payoff search", value: "Payoff found — Ep 26 · line 118" },
      { label: "Payoff line", value: "“I lied about the sleeping. I saw him leave.”" },
      { label: "Payoff distance", value: "24 episodes · within cohort tolerance" },
    ],
    action:
      "Locked as a protected suspended edge in G_perceived. No rewrite proposed, and no warning shown to the next writer in rotation — the contradiction is the point.",
  },
  {
    tab: "A death reported too early",
    episode: "Episode 31 · line 12",
    verdict: "repaired",
    claim: "Character B mourns someone who stays alive for another two episodes.",
    passage: [
      { n: "10", text: "INT. TEA STALL — DUSK" },
      { n: "11", text: "B:  It's been a long week." },
      { n: "12", text: "B:  Ever since C died, the school's been shut.", flagged: true },
      { n: "13", text: "SHOPKEEPER:  Sit. You look like you haven't slept." },
    ],
    test: [
      { label: "Contradicts", value: "G_true · C dies Ep 33 · line 88" },
      { label: "Knowledge check", value: "No character learns of the death before Ep 34" },
      { label: "Backward payoff search", value: "No payoff in the remaining 190 episodes" },
      { label: "Classification", value: "Accidental — surgical node repair authorised" },
    ],
    action:
      "One sentence rewritten inside the corrupt node. The scene keeps 99.4% of its prose, its dialect and its rhythm; downstream nodes re-validated in 4.1 seconds.",
    patch: {
      removed: "B:  Ever since C died, the school's been shut.",
      added: "B:  Ever since C stopped showing up, the school's been shut.",
    },
  },
  {
    tab: "A promise nobody paid off",
    episode: "Episode 47 · line 203",
    verdict: "debt",
    claim: "A promise the audience is still holding, 265 episodes later.",
    passage: [
      { n: "201", text: "A:  My mother left me exactly one thing." },
      { n: "202", text: "She opens her palm. A locked object, hinge broken." },
      { n: "203", text: "A:  When it opens, I'll know whose side he was on.", flagged: true },
      { n: "204", text: "She closes her hand before B can look." },
    ],
    test: [
      { label: "Obligation opened", value: "Ep 47 · urgency weight 0.81" },
      { label: "Referenced since", value: "6 times · last mention Ep 112" },
      { label: "Backward payoff search", value: "No payoff through Ep 312" },
      { label: "Retention impact", value: "−3.4% Lore Hardcore cohort, compounding" },
    ],
    action:
      "Not a hole — an unpaid promise. It surfaces on the debt board and is written into the next handoff sheet, so the incoming writer inherits it deliberately instead of by accident.",
  },
]

export function TwistHoleDiff() {
  const [active, setActive] = useState(0)
  const id = useId()
  const c = CASES[active]
  const v = VERDICTS[c.verdict]

  return (
    <Section
      id="classifier"
      title="Every other tool would call this a mistake"
      lead="Before flagging anything, CanonPulse runs a backward causal payoff test. A contradiction that pays off later is your best writing. One that never pays off is the bug. Telling them apart is the entire product."
    >
      <div className="grid gap-x-10 gap-y-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <div role="tablist" aria-label="Flagged passages" className="flex flex-col">
          {CASES.map((item, i) => {
            const iv = VERDICTS[item.verdict]
            const selected = i === active
            return (
              <button
                key={item.tab}
                role="tab"
                id={`${id}-tab-${i}`}
                aria-selected={selected}
                aria-controls={`${id}-panel`}
                onClick={() => setActive(i)}
                className={cn(
                  "group border-b border-white/8 py-4 text-left transition-colors first:border-t",
                  focusRing,
                  selected ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                )}
              >
                <span className="flex items-baseline gap-2.5">
                  <span
                    className={cn(
                      "size-1.5 shrink-0 translate-y-[-2px] rounded-full transition-opacity",
                      iv.dot,
                      selected ? "opacity-100" : "opacity-35 group-hover:opacity-70"
                    )}
                  />
                  <span className={cn("text-[17px] tracking-[-0.01em]", selected && "font-semibold")}>
                    {item.tab}
                  </span>
                </span>
                <span className="mt-0.5 block pl-4 text-[13px] text-muted-foreground">
                  {item.episode}
                </span>
              </button>
            )
          })}
        </div>

        <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-tab-${active}`}>
          <p className={cn("flex items-center gap-2 text-[13px] font-semibold", v.text)}>
            <span className={cn("size-1.5 rounded-full", v.dot)} />
            {v.label}
          </p>

          <p className="mt-3 mb-6 max-w-[52ch] text-[19px] leading-snug tracking-[-0.02em] text-balance">
            {c.claim}
          </p>

          <pre className="overflow-x-auto rounded-lg bg-white/[0.04] py-3 font-mono text-[13px] leading-[1.7]">
            <code>
              {c.passage.map((line) => (
                <div key={line.n} className={cn("px-4", line.flagged && "bg-white/[0.06]")}>
                  <span className="mr-4 inline-block w-9 shrink-0 text-right text-muted-foreground/70 select-none">
                    {line.n}
                  </span>
                  <span className="whitespace-pre-wrap">{line.text}</span>
                </div>
              ))}
            </code>
          </pre>

          <dl className="mt-6 divide-y divide-white/8 border-y border-white/8 text-[14px]">
            {c.test.map((row) => (
              <div key={row.label} className="grid gap-x-8 gap-y-1 py-3 sm:grid-cols-[minmax(0,20ch)_minmax(0,1fr)]">
                <dt className="text-muted-foreground">{row.label}</dt>
                <dd className="font-medium">{row.value}</dd>
              </div>
            ))}
          </dl>

          {c.patch && (
            <pre className="mt-6 overflow-x-auto rounded-lg bg-white/[0.04] py-3 font-mono text-[13px] leading-[1.7]">
              <code>
                <div className="bg-rose-500/10 px-4 text-rose-200">
                  <span className="mr-3 select-none opacity-60">−</span>
                  {c.patch.removed}
                </div>
                <div className="bg-emerald-500/10 px-4 text-emerald-200">
                  <span className="mr-3 select-none opacity-60">+</span>
                  {c.patch.added}
                </div>
              </code>
            </pre>
          )}

          <p className="mt-6 max-w-[68ch] text-[15px] leading-relaxed text-muted-foreground">
            {c.action}
          </p>
        </div>
      </div>
    </Section>
  )
}
