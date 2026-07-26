import { useEffect, useState } from "react"

/**
 * Fixed progress pill. Names the section you're in rather than counting them — the
 * position is the useful part, the ordinal never was.
 */
export function ScrollRail({ sections }: { sections: { id: string; label: string }[] }) {
  const [progress, setProgress] = useState(0)
  const [current, setCurrent] = useState(sections[0]?.label ?? "")

  useEffect(() => {
    const onScroll = () => {
      const max = document.documentElement.scrollHeight - innerHeight
      setProgress(max > 0 ? Math.min(window.scrollY / max, 1) : 0)
    }
    addEventListener("scroll", onScroll, { passive: true })
    onScroll()
    return () => removeEventListener("scroll", onScroll)
  }, [])

  useEffect(() => {
    const nodes = sections
      .map((s) => ({ ...s, el: document.getElementById(s.id) }))
      .filter((s): s is typeof s & { el: HTMLElement } => Boolean(s.el))
    if (!nodes.length) return

    const io = new IntersectionObserver(
      (entries) => {
        // Topmost intersecting section wins, so the label matches what fills the screen.
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]
        if (!visible) return
        const match = nodes.find((n) => n.el === visible.target)
        if (match) setCurrent(match.label)
      },
      { rootMargin: "-45% 0px -45% 0px" }
    )
    nodes.forEach((n) => io.observe(n.el))
    return () => io.disconnect()
  }, [sections])

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-x-0 bottom-5 z-40 flex justify-center px-4"
    >
      <div className="flex max-w-full items-center gap-3.5 rounded-full border border-white/10 bg-[#05070f]/80 px-4 py-2.5 backdrop-blur-md">
        <span className="truncate text-[12px] font-medium text-foreground">{current}</span>
        <div className="h-px w-[clamp(56px,18vw,160px)] shrink-0 bg-white/15">
          <div
            className="h-full bg-foreground/70 transition-[width] duration-150"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
        <span className="shrink-0 text-[12px] tabular-nums text-muted-foreground">
          {Math.round(progress * 100)}%
        </span>
      </div>
    </div>
  )
}
