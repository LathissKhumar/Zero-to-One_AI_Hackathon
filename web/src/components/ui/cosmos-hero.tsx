import { useEffect, useState } from "react"

/**
 * Hero copy block. The sky behind it is <Starfield />, mounted once at page level.
 * The promise leads; the product name lives in the header where a name belongs.
 */
export function CosmosHero({
  headline,
  sub,
  children,
  note,
}: {
  headline: string
  sub: string
  children?: React.ReactNode
  note?: string
}) {
  const [local, setLocal] = useState(0) // 0 → 1 as the hero scrolls away

  useEffect(() => {
    const onScroll = () => setLocal(Math.min(window.scrollY / innerHeight, 1))
    addEventListener("scroll", onScroll, { passive: true })
    onScroll()
    return () => removeEventListener("scroll", onScroll)
  }, [])

  const words = headline.split(" ")

  return (
    <section className="relative flex min-h-svh items-center overflow-hidden px-6 pt-36 pb-32">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-[1]"
        style={{
          background: "radial-gradient(60% 46% at 32% 78%, rgba(99,102,241,.28), transparent 72%)",
        }}
      />

      <div
        className="mx-auto w-full max-w-5xl will-change-transform motion-reduce:!transform-none motion-reduce:!opacity-100"
        style={{
          transform: `translateY(${local * 70}px)`,
          opacity: 1 - local * 0.9,
        }}
      >
        <h1 className="max-w-[16ch] text-[clamp(2.75rem,8.5vw,5.75rem)] leading-[0.98] font-extrabold tracking-[-0.045em] text-balance">
          {words.map((w, i) => (
            <span
              key={i}
              className="inline-block [animation:riseBlur_1.1s_cubic-bezier(.16,1,.3,1)_both] motion-reduce:[animation:none]"
              style={{ animationDelay: `${0.06 * i}s` }}
            >
              {w}
              {i < words.length - 1 ? " " : ""}
            </span>
          ))}
        </h1>

        <p
          className="mt-7 max-w-[58ch] text-[clamp(1.05rem,1.9vw,1.3rem)] leading-relaxed text-pretty text-muted-foreground [animation:riseBlur_1.1s_cubic-bezier(.16,1,.3,1)_both] motion-reduce:[animation:none]"
          style={{ animationDelay: "0.42s" }}
        >
          {sub}
        </p>

        <div
          className="mt-9 flex flex-wrap gap-3 [animation:riseBlur_1.1s_cubic-bezier(.16,1,.3,1)_both] motion-reduce:[animation:none]"
          style={{ animationDelay: "0.54s" }}
        >
          {children}
        </div>

        {note && (
          <p
            className="mt-5 text-[14px] text-muted-foreground [animation:riseBlur_1.1s_cubic-bezier(.16,1,.3,1)_both] motion-reduce:[animation:none]"
            style={{ animationDelay: "0.64s" }}
          >
            {note}
          </p>
        )}
      </div>
    </section>
  )
}
