import assert from "node:assert/strict"
import { test } from "node:test"
import {
  BEATS,
  ORDERS,
  QUERIES,
  answerFor,
  chronoPosition,
  chronoX,
  lerp,
  perceivedPosition,
  slotX,
} from "./graph-layout.ts"

test("slotX at the linear order matches chronological position", () => {
  for (const beat of BEATS) {
    assert.equal(slotX(beat.id, ORDERS.linear), chronoX(beat.id - 1))
  }
})

test("slotX at the non-linear order places each beat at its scrambled slot", () => {
  ORDERS.nonlinear.forEach((id, slot) => {
    assert.equal(slotX(id, ORDERS.nonlinear), chronoX(slot))
  })
})

test("lerp(a, b, 0) is a and lerp(a, b, 1) is b — the two toggle endpoints", () => {
  for (const beat of BEATS) {
    const a = slotX(beat.id, ORDERS.linear)
    const b = slotX(beat.id, ORDERS.nonlinear)
    assert.equal(lerp(a, b, 0), a)
    assert.equal(lerp(a, b, 1), b)
  }
})

test("both orders are permutations of the same eight beat ids", () => {
  const ids = BEATS.map((b) => b.id).sort()
  assert.deepEqual([...ORDERS.linear].sort(), ids)
  assert.deepEqual([...ORDERS.nonlinear].sort(), ids)
})

test("no two beats share a slot, in either order", () => {
  assert.equal(new Set(ORDERS.linear).size, ORDERS.linear.length)
  assert.equal(new Set(ORDERS.nonlinear).size, ORDERS.nonlinear.length)
})

test("slotX throws on an id absent from the order", () => {
  assert.throws(() => slotX(99, ORDERS.linear))
})

test("chronoPosition is 1-indexed and matches BEATS order", () => {
  BEATS.forEach((b, i) => assert.equal(chronoPosition(b.id), i + 1))
})

test("perceivedPosition matches each order's own indexing", () => {
  for (const order of [ORDERS.linear, ORDERS.nonlinear]) {
    order.forEach((id, i) => assert.equal(perceivedPosition(id, order), i + 1))
  }
})

test("every query retrieves beat ids that actually exist", () => {
  const ids = new Set(BEATS.map((b) => b.id))
  for (const q of QUERIES) {
    for (const id of q.retrieve) assert.ok(ids.has(id), `${q.id} retrieves unknown beat ${id}`)
  }
})

test("answerFor grounds its answer in every retrieved beat's own label", () => {
  for (const q of QUERIES) {
    const answer = answerFor(q, ORDERS.nonlinear)
    for (const id of q.retrieve) {
      const b = BEATS.find((x) => x.id === id)!
      assert.ok(answer.includes(b.label), `answer for ${q.id} missing "${b.label}"`)
    }
  }
})

test("the withheld-window query is actually withheld in the non-linear cut", () => {
  const q = QUERIES.find((q) => q.id === "withheld-window")!
  for (const id of q.retrieve) {
    assert.ok(
      perceivedPosition(id, ORDERS.nonlinear) > chronoPosition(id),
      `beat ${id} should air later than its chronological position under non-linear order`
    )
  }
})

test("the withheld-window query is NOT withheld in the linear cut", () => {
  const q = QUERIES.find((q) => q.id === "withheld-window")!
  for (const id of q.retrieve) {
    assert.equal(perceivedPosition(id, ORDERS.linear), chronoPosition(id))
  }
})
