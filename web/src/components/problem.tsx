import { Section } from "@/components/section"

const PROBLEMS = [
  {
    title: "Nobody remembers Episode 47",
    body: "By Episode 312 the clue planted in 47 exists in no one's head. Writers rotate, series get handed off mid-run, and every unpaid setup compounds into narrative debt — broken arcs, plot holes, churn that shows up in the numbers a season late.",
  },
  {
    title: "Generic AI flattens the twist",
    body: "Assistants that read one episode at a time assume time moves forward. Hand them a deliberate contradiction — the reveal you've been building for twenty episodes — and they file it as an error and offer to fix it.",
  },
  {
    title: "Non-linear costs you the plot",
    body: "Cutting 2000–04 against 2010–14 and paying off the middle decade at the climax means tracking who knows what, who aged how, and which state changed when, across gaps no outline survives.",
  },
  {
    title: "The context wall",
    body: "Half a million words won't fit in a prompt, and stuffing them in degrades attention while burning latency and cost. What a studio actually needs is a ledger it can query, diff and audit — not a bigger window.",
  },
]

export function Problem() {
  return (
    <Section
      id="problem"
      title="Serialized fiction outgrew the people writing it"
      lead="Three hundred episodes. Half a million words. Twelve writers, four of whom have left. Four breakdowns compound on every release treadmill, and none of them are prose problems — which is why prose tools cannot see them."
    >
      <dl className="divide-y divide-white/8 border-y border-white/8">
        {PROBLEMS.map((p) => (
          <div
            key={p.title}
            className="grid gap-x-12 gap-y-2 py-7 sm:grid-cols-[minmax(0,24ch)_minmax(0,1fr)]"
          >
            <dt className="text-[19px] leading-snug font-semibold tracking-[-0.02em] text-balance">
              {p.title}
            </dt>
            <dd className="max-w-[68ch] text-[16px] leading-relaxed text-muted-foreground">{p.body}</dd>
          </div>
        ))}
      </dl>
    </Section>
  )
}
