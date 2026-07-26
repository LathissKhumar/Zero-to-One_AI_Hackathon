export type Era = "early" | "middle" | "late"
export type Beat = { id: number; era: Era; label: string; episodeRange: string }

/**
 * Chronological reality — G_true. This order never changes; it is the physical truth.
 * Labels are deliberately archetypal (a story beat anyone recognizes), not tied to any
 * one plot — the diagram should read the same to someone who has never seen the show.
 */
export const BEATS: Beat[] = [
  { id: 1, era: "early", label: "Mentor introduced", episodeRange: "Ep 1–40" },
  { id: 2, era: "early", label: "Object hidden", episodeRange: "Ep 41–80" },
  { id: 3, era: "middle", label: "Disaster strikes", episodeRange: "Ep 81–120" },
  { id: 4, era: "middle", label: "Deal is made", episodeRange: "Ep 121–160" },
  { id: 5, era: "middle", label: "Truth admitted", episodeRange: "Ep 161–200" },
  { id: 6, era: "late", label: "Hero returns", episodeRange: "Ep 201–240" },
  { id: 7, era: "late", label: "Door is sealed", episodeRange: "Ep 241–280" },
  { id: 8, era: "late", label: "Object revealed", episodeRange: "Ep 281–312" },
]

/** Presentation order — G_perceived. Only this layer is allowed to move. */
export const ORDERS = {
  linear: [1, 2, 3, 4, 5, 6, 7, 8],
  nonlinear: [1, 2, 6, 7, 3, 4, 5, 8],
} as const

export type OrderKey = keyof typeof ORDERS

export const GRAPH = {
  width: 680,
  height: 280,
  topY: 56,
  bottomY: 224,
  colStart: 40,
  colStep: 85,
} as const

/** x position of the i'th chronological slot (top rail; this rail never moves). */
export function chronoX(index: number): number {
  return GRAPH.colStart + index * GRAPH.colStep
}

/** x position of beat `id`'s bottom-rail slot under presentation order `order`. */
export function slotX(id: number, order: readonly number[]): number {
  const slot = order.indexOf(id)
  if (slot === -1) throw new Error(`beat ${id} not present in order`)
  return chronoX(slot)
}

/** Linear interpolation between two slotX results, for animating a toggle. */
export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

/** Vertical-control-point cubic Bézier path between the two rails for one beat. */
export function edgePath(x1: number, x2: number): string {
  const y1 = GRAPH.topY
  const y2 = GRAPH.bottomY
  const c1y = y1 + 60
  const c2y = y2 - 60
  return `M ${x1} ${y1} C ${x1} ${c1y}, ${x2} ${c2y}, ${x2} ${y2}`
}

function beat(id: number): Beat {
  const b = BEATS.find((x) => x.id === id)
  if (!b) throw new Error(`beat ${id} not found`)
  return b
}

/** 1-indexed position of `id` in chronological reality — never changes. */
export function chronoPosition(id: number): number {
  return BEATS.findIndex((b) => b.id === id) + 1
}

/** 1-indexed position of `id` in a given presentation order. */
export function perceivedPosition(id: number, order: readonly number[]): number {
  const i = order.indexOf(id)
  if (i === -1) throw new Error(`beat ${id} not present in order`)
  return i + 1
}

/**
 * The graph-RAG framing: a canned question, and the beat ids retrieved from the graph
 * to answer it. `answerFor` below grounds the answer in each retrieved beat's actual
 * chronological and revealed position, so the text changes when the order toggle does —
 * it is read off the data, not written as flavor text.
 */
export type Query = { id: string; chip: string; text: string; retrieve: number[] }

export const QUERIES: Query[] = [
  {
    id: "hidden-object",
    chip: "Hidden object → payoff",
    text: "What gets hidden early, and when does the audience see it resolved?",
    retrieve: [2, 8],
  },
  {
    id: "mentor-loop",
    chip: "Mentor's loop",
    text: "Which beat closes the loop the mentor opens?",
    retrieve: [1, 6],
  },
  {
    id: "withheld-window",
    chip: "Withheld window",
    text: "Which beats get withheld until late in the run?",
    retrieve: [3, 4, 5],
  },
]

export function answerFor(query: Query, order: readonly number[]): string {
  return (
    query.retrieve
      .map((id) => {
        const b = beat(id)
        return `${b.label} (${b.episodeRange}) — beat ${chronoPosition(id)} of 8 chronologically, seen at position ${perceivedPosition(id, order)} of 8`
      })
      .join("; ") + "."
  )
}
