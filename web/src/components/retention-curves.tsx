import { useEffect, useRef, useState } from "react"
import { Panel, Section, Segmented } from "@/components/section"
import { cn } from "@/lib/utils"

const EPISODES = [1, 25, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300]

type Cohort = { name: string; stroke: string; text: string; before: number[]; after: number[] }

/** 1,000 parallel persona agents, sampled every 25 episodes. Retention %, floor 40. */
const COHORTS: Cohort[] = [
  {
    name: "Binge listeners",
    stroke: "stroke-cyan-400",
    text: "text-cyan-300",
    before: [100, 96, 93, 91, 89, 87, 84, 82, 78, 71, 66, 62, 59],
    after: [100, 96, 93, 91, 90, 88, 87, 86, 85, 83, 81, 80, 79],
  },
  {
    name: "Casual commuters",
    stroke: "stroke-indigo-400",
    text: "text-indigo-300",
    before: [100, 92, 86, 81, 77, 73, 70, 67, 63, 59, 56, 53, 51],
    after: [100, 92, 86, 82, 78, 75, 72, 70, 68, 66, 64, 62, 61],
  },
  {
    name: "Lore hardcores",
    stroke: "stroke-purple-400",
    text: "text-purple-300",
    before: [100, 98, 97, 96, 95, 94, 92, 88, 76, 64, 55, 49, 45],
    after: [100, 98, 97, 96, 95, 95, 94, 93, 92, 91, 90, 89, 88],
  },
  {
    name: "Character fans",
    stroke: "stroke-amber-400",
    text: "text-amber-300",
    before: [100, 95, 91, 88, 85, 82, 79, 75, 70, 65, 61, 57, 54],
    after: [100, 95, 92, 89, 87, 85, 83, 81, 79, 77, 75, 74, 73],
  },
  {
    name: "Aggregate health",
    stroke: "stroke-foreground",
    text: "text-foreground",
    before: [100, 95, 92, 89, 87, 84, 81, 78, 72, 65, 60, 55, 52],
    after: [100, 95, 92, 90, 88, 86, 84, 83, 81, 79, 78, 76, 75],
  },
]

const W = 320
const H = 150
const PAD = { l: 24, r: 8, t: 8, b: 20 }
const MIN = 40

const x = (i: number) => PAD.l + (i * (W - PAD.l - PAD.r)) / (EPISODES.length - 1)
const y = (v: number) => PAD.t + ((100 - v) / (100 - MIN)) * (H - PAD.t - PAD.b)
const points = (vals: number[]) => vals.map((v, i) => `${x(i)},${y(v)}`).join(" ")

export function RetentionCurves() {
  const [scenario, setScenario] = useState<"before" | "after">("after")
  const [drawn, setDrawn] = useState(false)
  const figureRef = useRef<HTMLDivElement>(null)

  // Draw when the chart is actually on screen — animating below the fold is animating to nobody.
  useEffect(() => {
    const node = figureRef.current
    if (!node) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setDrawn(true)
          io.disconnect()
        }
      },
      { threshold: 0.35 }
    )
    io.observe(node)
    return () => io.disconnect()
  }, [])

  const aggregate = COHORTS[COHORTS.length - 1]
  const delta = aggregate.after.at(-1)! - aggregate.before.at(-1)!

  return (
    <Section
      id="simulator"
      title="Prove the fix before you ship the episode"
      lead="A thousand persona agents listen to the series and stream five retention curves. The regressor reads structural graph features only — open obligations, payoff distance, urgency weight — so prose can't flatter the score. Only fixing the graph moves the line."
    >
      <Panel>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-x-5 gap-y-2 text-[13px]">
            {COHORTS.map((c) => (
              <span key={c.name} className={cn("flex items-center gap-1.5", c.text)}>
                <span className="h-px w-4 bg-current" />
                {c.name}
              </span>
            ))}
          </div>

          <Segmented
            label="Scenario"
            value={scenario}
            onChange={setScenario}
            options={[
              { value: "before", label: "Debt unpaid" },
              { value: "after", label: "After repair" },
            ]}
          />
        </div>

        <div ref={figureRef}>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="w-full"
            role="img"
            aria-label={`Retention by cohort, ${
              scenario === "after" ? "after repair" : "with narrative debt unpaid"
            }. Aggregate health ends at ${aggregate[scenario].at(-1)} percent at episode 300.`}
          >
            {[100, 80, 60, 40].map((v) => (
              <g key={v}>
                <line
                  x1={PAD.l}
                  x2={W - PAD.r}
                  y1={y(v)}
                  y2={y(v)}
                  className="stroke-white/8"
                  strokeWidth={0.5}
                />
                <text
                  x={PAD.l - 6}
                  y={y(v) + 2.5}
                  textAnchor="end"
                  className="fill-muted-foreground text-[7px]"
                >
                  {v}
                </text>
              </g>
            ))}

            {[0, 4, 8, 12].map((i) => (
              <text
                key={i}
                x={x(i)}
                y={H - 6}
                textAnchor="middle"
                className="fill-muted-foreground text-[7px]"
              >
                Ep {EPISODES[i]}
              </text>
            ))}

            {/* Remounting on scenario change replays the draw. */}
            <g key={scenario}>
              {COHORTS.map((c, i) => (
                <polyline
                  key={c.name}
                  points={points(c[scenario])}
                  fill="none"
                  pathLength={1}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={c.name === "Aggregate health" ? 1.9 : 1.1}
                  className={cn(
                    c.stroke,
                    "[stroke-dasharray:1]",
                    drawn
                      ? "[animation:draw_1.5s_cubic-bezier(.16,1,.3,1)_both] motion-reduce:[animation:none]"
                      : "[stroke-dashoffset:1] motion-reduce:[stroke-dashoffset:0]"
                  )}
                  style={{ animationDelay: `${i * 0.1}s` }}
                />
              ))}
            </g>
          </svg>
        </div>

        <p className="mt-6 border-t border-white/8 pt-5 text-[15px] leading-relaxed text-muted-foreground">
          <span className="font-semibold text-emerald-300">+{delta} points of aggregate retention</span>{" "}
          at Episode 300. Paying off the one obligation opened in Episode 47 recovers the lore
          hardcores, who were carrying the sharpest drop from Episode 200 on.
        </p>
      </Panel>
    </Section>
  )
}
