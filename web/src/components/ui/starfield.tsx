import { useEffect, useRef } from "react"

type Star = { x: number; y: number; z: number; phase: number; tint: string }

const TINTS = ["255,255,255", "255,255,255", "255,255,255", "6,182,212", "168,85,247"]

/**
 * Page-wide starfield. Fixed to the viewport and parallaxed by scroll position, so every
 * section sits on the same sky instead of each one owning a copy.
 *
 * ponytail: canvas-2D instead of three.js + EffectComposer. Same look, no deps, ~70 lines.
 */
export function Starfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches
    let stars: Star[] = []
    let w = 0
    let h = 0
    let scrollY = 0
    let frame = 0

    const resize = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2)
      w = canvas.clientWidth
      h = canvas.clientHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      stars = Array.from({ length: Math.round((w * h) / 2400) }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        z: Math.random(), // depth — drives size, parallax speed, brightness
        phase: Math.random() * Math.PI * 2,
        tint: TINTS[(Math.random() * TINTS.length) | 0],
      }))
    }

    const draw = (t: number) => {
      ctx.clearRect(0, 0, w, h)
      for (const s of stars) {
        const parallax = scrollY * (0.04 + s.z * 0.22)
        const y = (((s.y - parallax) % h) + h) % h // wrap, never negative
        const twinkle = reduce ? 1 : 0.75 + 0.25 * Math.sin(t * 0.001 + s.phase)
        ctx.fillStyle = `rgba(${s.tint},${(0.22 + s.z * 0.6) * twinkle})`
        ctx.beginPath()
        ctx.arc(s.x, y, 0.3 + s.z * 1.5, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const onScroll = () => {
      scrollY = window.scrollY
      if (reduce) draw(0)
    }
    const onResize = () => {
      resize()
      if (reduce) draw(0)
    }

    resize()
    addEventListener("resize", onResize)
    addEventListener("scroll", onScroll, { passive: true })

    if (reduce) draw(0)
    else {
      const loop = (t: number) => {
        draw(t)
        frame = requestAnimationFrame(loop)
      }
      frame = requestAnimationFrame(loop)
    }

    return () => {
      cancelAnimationFrame(frame)
      removeEventListener("resize", onResize)
      removeEventListener("scroll", onScroll)
    }
  }, [])

  return (
    <>
      <canvas ref={canvasRef} aria-hidden className="fixed inset-0 -z-20 h-full w-full" />
      {/* Nebula wash — fixed too, so the colour follows you down the page. */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background: [
            "radial-gradient(60% 45% at 50% 20%, rgba(99,102,241,.22), transparent 70%)",
            "radial-gradient(45% 40% at 12% 70%, rgba(6,182,212,.14), transparent 70%)",
            "radial-gradient(40% 35% at 88% 55%, rgba(168,85,247,.14), transparent 70%)",
          ].join(","),
        }}
      />
    </>
  )
}
