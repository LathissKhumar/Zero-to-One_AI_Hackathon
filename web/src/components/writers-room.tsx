import { Section } from "@/components/section"

const PERSONAS = [
  { role: "Director", job: "Macro pacing and structural vision across the arc." },
  { role: "Editor", job: "Prose tightness, dialogue flow, scene transitions." },
  { role: "Critic", job: "Clichés, tired tropes, gaps in narrative logic." },
  { role: "Psychologist", job: "Character motivation and emotional plausibility." },
  { role: "Historian", job: "Lore rules, world consistency, period fact." },
]

export function WritersRoom() {
  return (
    <Section
      id="room"
      title="Five specialists, not one general-purpose prompt"
      lead="Each persona reads the script in parallel and writes structured annotations straight back to the graph — so a note is always attached to a node, never floating in a chat log somebody has to remember to read."
    >
      <div className="grid divide-y divide-white/8 border-y border-white/8 sm:grid-cols-5 sm:divide-x sm:divide-y-0">
        {PERSONAS.map((p) => (
          <div key={p.role} className="py-5 sm:px-5 sm:py-2 sm:first:pl-0 sm:last:pr-0">
            <h3 className="text-[17px] font-semibold tracking-[-0.01em]">{p.role}</h3>
            <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">{p.job}</p>
          </div>
        ))}
      </div>
    </Section>
  )
}
