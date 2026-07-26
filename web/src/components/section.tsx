import { cn } from "@/lib/utils"

/**
 * One heading treatment for the whole page. Left-aligned and hairline-separated —
 * the rhythm comes from the rules and the space above each heading, not from chrome.
 */
export function Section({
  id,
  title,
  lead,
  children,
  className,
}: {
  id?: string
  title: string
  lead?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <section id={id} className={cn("border-t border-white/8 pt-16 pb-24 sm:pt-20 sm:pb-28", className)}>
      <div className="mb-12 max-w-[54ch] sm:mb-14">
        <h2 className="text-[clamp(1.9rem,4.2vw,2.7rem)] leading-[1.08] font-bold tracking-[-0.035em] text-balance">
          {title}
        </h2>
        {lead && (
          <p className="mt-4 text-[17px] leading-relaxed text-pretty text-muted-foreground">{lead}</p>
        )}
      </div>
      {children}
    </section>
  )
}

/** The single bordered surface a section is allowed to have. Never nested inside another. */
export function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-xl border border-white/10 bg-card p-5 sm:p-7", className)}>
      {children}
    </div>
  )
}

export const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"

/** Segmented control shared by the graph and the simulator, so both toggles behave identically. */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div role="group" aria-label={label} className="flex rounded-lg border border-white/10 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          aria-pressed={value === o.value}
          className={cn(
            "rounded-md px-3 py-1.5 text-[13px] font-semibold transition-colors",
            focusRing,
            value === o.value
              ? "bg-foreground text-background"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
