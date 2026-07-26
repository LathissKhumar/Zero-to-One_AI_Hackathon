import { useId, useState } from "react"
import { Section, focusRing } from "@/components/section"
import { cn } from "@/lib/utils"

type Row = { k: string; v: string; tone?: "warn" | "bad" | "ok" }

type Surface = {
  name: string
  persona: string
  blurb: string
  panel: string
  rows: Row[]
}

const SURFACES: Surface[] = [
  {
    name: "Series Memory",
    persona: "Writer / showrunner",
    blurb:
      "A searchable ledger of everything the series has ever established. Ask what was planted in Episode 47 while you're writing Episode 312, and get the line, the state and the open promise back.",
    panel: "Query · “locked object”",
    rows: [
      { k: "Ep 047 · planted", v: "A character's locked heirloom", tone: "ok" },
      { k: "Ep 112 · referenced", v: "“I still can't get it open.”" },
      { k: "Ep 203 · state", v: "Still closed · owner unchanged" },
      { k: "Obligation", v: "Open · 265 episodes", tone: "bad" },
    ],
  },
  {
    name: "Pre-Publish Check",
    persona: "Writer",
    blurb:
      "The sidebar that runs before you hit publish: twists separated from holes, corrupt nodes patched, and a retention delta attached to every fix so you can see what shipping unfixed would cost.",
    panel: "Episode 312 · draft 4",
    rows: [
      { k: "Canon breaks", v: "1 found · 1 repaired", tone: "warn" },
      { k: "Protected twists", v: "2 locked, left alone", tone: "ok" },
      { k: "Open obligations", v: "6 · 2 overdue", tone: "warn" },
      { k: "Retention delta", v: "+4.1 pts if shipped as patched", tone: "ok" },
    ],
  },
  {
    name: "Writer Handoff Sheet",
    persona: "Multi-writer team",
    blurb:
      "Generated the moment a writer rotates off. Everything they opened, everything they inherited, everything now overdue — explicit, in one page, instead of living as folklore in a group chat.",
    panel: "Handoff · Writer A → Writer B",
    rows: [
      { k: "Inherited open", v: "14 obligations" },
      { k: "Opened this run", v: "9 · 3 unpaid", tone: "warn" },
      { k: "Overdue > 100 eps", v: "2 obligations", tone: "bad" },
      { k: "Protected twists", v: "4 · do not “fix”", tone: "ok" },
    ],
  },
  {
    name: "Showrunner Debt Board",
    persona: "Studio executive",
    blurb:
      "Portfolio view. A Narrative Debt Index per running series, so a studio sees which show is quietly accumulating churn a season before the retention numbers say so.",
    panel: "Slate · 6 series live",
    rows: [
      { k: "Series A", v: "NDI 0.71 · rising", tone: "bad" },
      { k: "Series B", v: "NDI 0.34 · stable" },
      { k: "Series C", v: "NDI 0.19 · falling", tone: "ok" },
      { k: "Slate average", v: "NDI 0.41", tone: "warn" },
    ],
  },
  {
    name: "Localization Check",
    persona: "Localization team",
    blurb:
      "The graph is language-agnostic, so a translated script gets validated edge for edge against canonical story logic — a dropped causal link in Bahasa is a diff, not a hunch.",
    panel: "Episode 312 · 4 locales",
    rows: [
      { k: "Hindi", v: "1:1 edge alignment", tone: "ok" },
      { k: "Spanish", v: "1:1 edge alignment", tone: "ok" },
      { k: "Bahasa", v: "1 dropped causal edge", tone: "bad" },
      { k: "Portuguese", v: "Pending deep pass" },
    ],
  },
]

const TONE = {
  ok: "text-emerald-300",
  warn: "text-amber-300",
  bad: "text-rose-300",
}

export function Surfaces() {
  const [active, setActive] = useState(0)
  const id = useId()
  const s = SURFACES[active]

  return (
    <Section
      id="surfaces"
      title="The same graph, pointed at five different jobs"
      lead="Nobody maintains a second source of truth. The writer's sidebar and the executive's debt board are the same ledger, read at different altitudes."
    >
      <div className="grid gap-x-10 gap-y-6 lg:grid-cols-[minmax(0,18rem)_minmax(0,1fr)]">
        <div role="tablist" aria-label="Product surfaces" className="flex flex-col">
          {SURFACES.map((item, i) => {
            const selected = i === active
            return (
              <button
                key={item.name}
                role="tab"
                id={`${id}-tab-${i}`}
                aria-selected={selected}
                aria-controls={`${id}-panel`}
                onClick={() => setActive(i)}
                className={cn(
                  "border-b border-white/8 py-3.5 text-left transition-colors first:border-t",
                  focusRing,
                  selected ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                )}
              >
                <span className={cn("text-[17px] tracking-[-0.01em]", selected && "font-semibold")}>
                  {item.name}
                </span>
                <span className="mt-0.5 block text-[13px] text-muted-foreground">{item.persona}</span>
              </button>
            )
          })}
        </div>

        <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-tab-${active}`}>
          <p className="mb-7 max-w-[62ch] text-[17px] leading-relaxed text-pretty">{s.blurb}</p>

          <div className="overflow-hidden rounded-xl border border-white/10 bg-card">
            <div className="border-b border-white/8 px-5 py-3 font-mono text-[12px] text-muted-foreground">
              {s.panel}
            </div>
            <dl className="divide-y divide-white/8">
              {s.rows.map((r) => (
                <div
                  key={r.k}
                  className="flex items-center justify-between gap-6 px-5 py-3.5 text-[14px]"
                >
                  <dt className="text-muted-foreground">{r.k}</dt>
                  <dd className={cn("text-right font-medium", r.tone && TONE[r.tone])}>{r.v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>
    </Section>
  )
}
