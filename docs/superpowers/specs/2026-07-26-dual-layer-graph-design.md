# Dual-layer graph as a bipartite figure

**Date:** 2026-07-26
**Surface:** CanonPulse landing page — the "What happened, and when the audience found out" section
**File:** `web/src/components/dual-layer-graph.tsx`

## Problem

The section that carries CanonPulse's core technical claim — that story truth and story
presentation are two separate graphs — currently renders as two rails of coloured blocks that
re-order on a toggle. The word "graph" appears in the heading and the labels, but nothing on
screen is a graph. A reader has to hold both rails in memory and diff them to see the
reordering, which is exactly the cognitive work the product exists to remove.

## Goal

Draw the relationship. The reordering should be visible in a single glance, without reading
either rail in sequence.

## Design

### Representation

A bipartite graph: two node rails joined by one edge per beat.

- **Top rail** is `G_true`, chronological reality. Fixed order, never moves.
- **Bottom rail** is `G_perceived`, revelation order. Each beat sits at its slot in the
  presentation order.
- **Edges** connect each beat's chronological position to its episode slot.

In Linear mode every edge is vertical and nothing crosses. In Non-linear mode four edges cross.
The crossings are the argument — they are what the surrounding prose currently has to assert.

### Geometry

- SVG `viewBox="0 0 680 280"`, inside the section's existing `overflow-x-auto` wrapper with
  `min-w-[680px]`, so the figure scrolls as one unit on narrow screens rather than reflowing.
- Top rail nodes at `y = 56`, bottom rail at `y = 224`; column `x = 40 + i * 85` for eight beats.
- Edges are cubic Béziers with vertical control points (`c1 = (x1, y1 + 60)`,
  `c2 = (x2, y2 - 60)`), giving an S-curve that reads as a connection rather than a wire.
- Stroke coloured by era, 1.25px at 45% opacity; the emphasized edge goes 2px at full opacity.

### Labels

Beat labels shorten to fit an 85px column at ~11px:

| # | Long form (current) | Short form |
|---|---|---|
| 1 | Anand takes the school | Anand's school |
| 2 | The locket is left behind | The locket |
| 3 | The night of the fire | The fire |
| 4 | Ravi signs the ledger | The ledger |
| 5 | Anand's confession | Confession |
| 6 | Mira returns to Ashfield | Mira returns |
| 7 | The gate is bolted | Gate bolted |
| 8 | The locket opens | Locket opens |

Top-rail labels sit above their nodes. Bottom-rail labels are episode ranges (Ep 1–40, 41–80, …),
which is what makes the lower rail read as *when the audience found out* rather than as a second
arbitrary ordering.

### Motion

SVG path `d` cannot be transitioned in CSS. The toggle drives a `0 → 1` progress value on
`requestAnimationFrame`; each frame interpolates every beat's x position between its old and new
slot and re-renders both the nodes and the curves, so endpoints and edges travel together.

- Duration 900ms, exponential ease-out.
- `prefers-reduced-motion: reduce` skips the animation and applies the end state directly.
- The animation is interruptible: toggling mid-flight re-targets from current positions.

### Interaction

Hovering a node or its label thickens that beat's edge and dims the other seven. This is
emphasis only — every label and both orderings are visible without it, so nothing is hidden
behind a pointer. No per-node tab stops; the figure carries `role="img"` with an `aria-label`
stating both orderings in full.

### Out of scope

Everything else in the section is preserved unchanged: heading, lead paragraph, era legend,
segmented toggle, and the "Zero timeline contradictions" line beneath the figure.

## Verification

The geometry moves into `web/src/lib/graph-layout.ts` as pure functions, leaving the component
to render only. One `assert`-based self-check lives in `web/src/lib/graph-layout.test.ts` and
runs with `node --test` — Node 26 on this machine strips TypeScript types natively, so no
loader, runner, or dependency is involved. It asserts:

1. `slotX(beat, order)` at progress 0 returns exactly the linear layout, and at progress 1
   exactly the non-linear layout.
2. No two beats resolve to the same slot in either order.
3. Both orders are permutations of the same eight beat ids.

Plus `npm run build` (tsc strict + vite) and a visual check at desktop and phone widths.

## Risks

- **Label crowding.** Eight columns at 85px is tight; if the short forms still wrap past two
  lines, the fallback is seven beats rather than smaller type.
- **Curve legibility.** Four crossing edges in similar era colours could read as noise. If so,
  reduce base opacity and rely more on the hover emphasis.
