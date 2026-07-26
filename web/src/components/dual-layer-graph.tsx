import { useEffect, useRef, useState } from "react"
import { Panel, Section, Segmented, focusRing } from "@/components/section"
import {
  BEATS,
  GRAPH,
  ORDERS,
  QUERIES,
  answerFor,
  edgePath,
  lerp,
  slotX,
  type Era,
  type OrderKey,
} from "@/lib/graph-layout"
import { cn } from "@/lib/utils"

const ERAS: Record<Era, { name: string; dot: string; stroke: string; fill: string }> = {
  early: { name: "2000 – 2004", dot: "bg-cyan-400", stroke: "stroke-cyan-400", fill: "fill-cyan-300" },
  middle: {
    name: "2004 – 2010",
    dot: "bg-purple-400",
    stroke: "stroke-purple-400",
    fill: "fill-purple-300",
  },
  late: {
    name: "2010 – 2014",
    dot: "bg-indigo-400",
    stroke: "stroke-indigo-400",
    fill: "fill-indigo-300",
  },
}

const EASE_OUT_EXPO = (t: number) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t))
const DURATION_MS = 900

function describeOrder(order: readonly number[]): string {
  return order.map((id) => BEATS.find((b) => b.id === id)?.label ?? id).join(", ")
}

export function DualLayerGraph() {
  const [mode, setMode] = useState<OrderKey>("nonlinear")
  const [progress, setProgress] = useState(1) // 0 = linear layout, 1 = current `mode` layout
  const [hovered, setHovered] = useState<number | null>(null)
  const [queryId, setQueryId] = useState(QUERIES[0].id)
  const fromOrder = useRef<OrderKey>("nonlinear")
  const frame = useRef<number>(0)

  const reduce =
    typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches

  const activeQuery = QUERIES.find((q) => q.id === queryId) ?? QUERIES[0]
  const retrieved = new Set(activeQuery.retrieve)
  const answer = answerFor(activeQuery, ORDERS[mode])

  function goTo(next: OrderKey) {
    if (next === mode) return
    const startFrom = mode
    fromOrder.current = startFrom
    setMode(next)

    if (reduce) {
      setProgress(1)
      return
    }

    cancelAnimationFrame(frame.current)
    const startProgress = progress
    const start = performance.now()

    const tick = (now: number) => {
      const elapsed = now - start
      // Re-target from wherever the previous animation was interrupted, not from 0.
      const t = Math.min(elapsed / DURATION_MS, 1)
      setProgress(startProgress + (1 - startProgress) * EASE_OUT_EXPO(t))
      if (t < 1) frame.current = requestAnimationFrame(tick)
    }
    frame.current = requestAnimationFrame(tick)
  }

  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  const bottomX = (id: number) => {
    if (reduce) return slotX(id, ORDERS[mode])
    const a = slotX(id, ORDERS[fromOrder.current])
    const b = slotX(id, ORDERS[mode])
    return lerp(a, b, progress)
  }

  return (
    <Section
      id="graph"
      title="What happened, and when the audience found out"
      lead="This is a graph RAG: the same knowledge graph answers a question two ways, because the question and the retrieval both know the difference between reality and revelation. Ask it something, and the answer is grounded in exactly the nodes it retrieved."
    >
      <Panel>
        <div className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-x-5 gap-y-2 text-[13px] text-muted-foreground">
            {Object.values(ERAS).map((e) => (
              <span key={e.name} className="flex items-center gap-1.5">
                <span className={cn("size-1.5 rounded-full", e.dot)} />
                {e.name}
              </span>
            ))}
          </div>

          <Segmented
            label="Presentation order"
            value={mode}
            onChange={goTo}
            options={[
              { value: "linear", label: "Linear" },
              { value: "nonlinear", label: "Non-linear" },
            ]}
          />
        </div>

        <div className="mb-6">
          <p className="mb-2 text-[13px] font-medium text-muted-foreground">Ask the graph</p>
          <div role="group" aria-label="Ask the graph" className="flex flex-wrap gap-2">
            {QUERIES.map((q) => (
              <button
                key={q.id}
                onClick={() => setQueryId(q.id)}
                aria-pressed={q.id === queryId}
                className={cn(
                  "rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition-colors",
                  focusRing,
                  q.id === queryId
                    ? "border-white/30 bg-white/10 text-foreground"
                    : "border-white/10 text-muted-foreground hover:border-white/20 hover:text-foreground"
                )}
              >
                {q.chip}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-5 text-center">
          <p className="text-[15px] text-foreground">
            Query — <span className="font-medium">“{activeQuery.text}”</span>
          </p>
          <p className="mt-1 text-[11px] font-semibold tracking-[0.1em] text-muted-foreground/70 uppercase">
            retrieves ▾
          </p>
        </div>

        <div className="-mx-1 overflow-x-auto pb-1">
          <div style={{ minWidth: GRAPH.width }} className="px-1">
            <svg
              viewBox={`0 0 ${GRAPH.width} ${GRAPH.height}`}
              className="w-full"
              role="img"
              aria-label={`Two orderings of the same eight story beats, queried as a knowledge graph. Chronological reality: ${describeOrder(
                ORDERS.linear
              )}. Revelation order in ${mode === "linear" ? "linear" : "non-linear"} mode: ${describeOrder(
                ORDERS[mode]
              )}. Current query: ${activeQuery.text} Answer: ${answer}`}
            >
              <text
                x={GRAPH.colStart}
                y={GRAPH.topY - 34}
                className="fill-muted-foreground text-[11px] font-medium"
              >
                G_true — chronological reality
              </text>
              <text
                x={GRAPH.colStart}
                y={GRAPH.bottomY + 44}
                className="fill-muted-foreground text-[11px] font-medium"
              >
                G_perceived — revelation order
              </text>

              {BEATS.map((beat, i) => {
                const topX = GRAPH.colStart + i * GRAPH.colStep
                const btmX = bottomX(beat.id)
                const era = ERAS[beat.era]
                const isRetrieved = retrieved.has(beat.id)
                const isHoveredSelf = hovered === beat.id
                const isHoveredOther = hovered !== null && !isHoveredSelf
                // Retrieval sets the base emphasis; hovering one beat always wins, hovering
                // another always loses — so the two interactions never fight for the eye.
                const opacity = isHoveredOther ? 0.15 : isHoveredSelf ? 1 : isRetrieved ? 1 : 0.28
                const strokeWidth = isHoveredSelf || isRetrieved ? 2 : 1.25

                return (
                  <g
                    key={beat.id}
                    className="cursor-default transition-opacity duration-200"
                    style={{ opacity }}
                    onMouseEnter={() => setHovered(beat.id)}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <path
                      d={edgePath(topX, btmX)}
                      fill="none"
                      className={era.stroke}
                      strokeWidth={strokeWidth}
                    />

                    {isRetrieved && (
                      <>
                        <circle
                          cx={topX}
                          cy={GRAPH.topY}
                          r={8}
                          fill="none"
                          className={era.stroke}
                          strokeWidth={1.5}
                          strokeOpacity={0.55}
                        />
                        <circle
                          cx={btmX}
                          cy={GRAPH.bottomY}
                          r={8}
                          fill="none"
                          className={era.stroke}
                          strokeWidth={1.5}
                          strokeOpacity={0.55}
                        />
                      </>
                    )}

                    <circle cx={topX} cy={GRAPH.topY} r={4} className={era.fill} />
                    <text
                      x={topX}
                      y={GRAPH.topY - 14}
                      textAnchor="middle"
                      className="fill-foreground text-[11px] leading-tight font-medium"
                    >
                      {beat.label}
                    </text>

                    <circle cx={btmX} cy={GRAPH.bottomY} r={4} className={era.fill} />
                    <text
                      x={btmX}
                      y={GRAPH.bottomY + 18}
                      textAnchor="middle"
                      className="fill-foreground text-[11px] leading-tight font-medium"
                    >
                      {beat.label}
                    </text>
                    <text
                      x={btmX}
                      y={GRAPH.bottomY + 30}
                      textAnchor="middle"
                      className="fill-muted-foreground text-[10px]"
                    >
                      {beat.episodeRange}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
        </div>

        <p className="mt-2 border-t border-white/8 pt-5 text-[15px] leading-relaxed">
          <span className="font-semibold text-cyan-300">Answer.</span>{" "}
          <span className="text-muted-foreground">{answer}</span>
        </p>
        <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground/75">
          <span className="font-semibold text-emerald-400">Zero timeline contradictions.</span>{" "}
          {mode === "linear"
            ? "Presentation matches reality one-to-one — the baseline every serial starts from, and the only mode other tools can hold."
            : "The middle era is withheld until late in the run. Character knowledge, ageing and state are re-validated against G_true on every move, so suspense costs you nothing in logic."}
        </p>
      </Panel>
    </Section>
  )
}
