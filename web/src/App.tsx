import { CosmosHero } from "@/components/ui/cosmos-hero"
import { Starfield } from "@/components/ui/starfield"
import { ScrollRail } from "@/components/scroll-rail"
import { Section, focusRing } from "@/components/section"
import { Problem } from "@/components/problem"
import { DualLayerGraph } from "@/components/dual-layer-graph"
import { TwistHoleDiff } from "@/components/twist-hole-diff"
import { WritersRoom } from "@/components/writers-room"
import { RetentionCurves } from "@/components/retention-curves"
import { Surfaces } from "@/components/surfaces"
import { cn } from "@/lib/utils"

const READS = [
  {
    title: "Canon breaks",
    body: "Timelines, injuries, who knows what and when — checked against the new episode and flagged with the earlier line it contradicts.",
  },
  {
    title: "Emotional promises",
    body: "The setup in Episode 4 the audience is still holding, with how long it has been open and how hot it still runs.",
  },
  {
    title: "Cliffhanger fairness",
    body: "A fair cliffhanger withholds an outcome. An unfair one withholds information the listener needed. We score which you wrote.",
  },
  {
    title: "A canon bible, unwritten",
    body: "Characters, places and rules built from the back-catalog on first ingest. No spreadsheet to maintain, no showrunner memory to trust.",
  },
  {
    title: "Script or finished audio",
    body: "Fountain, Final Draft, plain text, or the mixed episode. Improvised and ad-libbed lines get caught the same way.",
  },
  {
    title: "Unreleased stays unreleased",
    body: "Private workspaces, no training on your material, per-season access for writer rooms. Your finale is not our dataset.",
  },
]

const GENRES = ["Mystery serials", "Romance dramas", "Crime procedurals", "Fantasy sagas", "Sci-fi epics"]

const NAV = [
  { id: "problem", label: "Problem" },
  { id: "graph", label: "Dual-layer graph" },
  { id: "classifier", label: "Classifier" },
  { id: "reads", label: "What it reads" },
  { id: "room", label: "Writers room" },
  { id: "simulator", label: "Simulator" },
  { id: "surfaces", label: "Product" },
]

function Btn({
  href,
  children,
  variant = "solid",
}: {
  href: string
  children: React.ReactNode
  variant?: "solid" | "ghost"
}) {
  return (
    <a
      href={href}
      className={cn(
        "rounded-lg px-5 py-2.5 text-[15px] font-semibold transition-colors",
        focusRing,
        variant === "solid"
          ? "bg-foreground text-background hover:bg-white"
          : "border border-white/15 text-foreground hover:border-white/35 hover:bg-white/5"
      )}
    >
      {children}
    </a>
  )
}

export default function App() {
  return (
    <>
      <Starfield />

      <header className="absolute inset-x-0 top-0 z-30">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
          <a
            href="#"
            className={cn(
              "flex items-center gap-2.5 rounded-md text-[19px] font-bold tracking-[-0.03em]",
              focusRing
            )}
          >
            <img src="/logo.svg" alt="" width={28} height={28} />
            CanonPulse
          </a>
          <nav className="flex items-center gap-7 text-[15px]">
            {NAV.slice(0, 3).map((n) => (
              <a
                key={n.id}
                href={`#${n.id}`}
                className={cn(
                  "hidden rounded-md text-muted-foreground transition-colors hover:text-foreground lg:block",
                  focusRing
                )}
              >
                {n.label}
              </a>
            ))}
            <Btn href="#">Run an episode</Btn>
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-6">
        <CosmosHero
          headline="Test the story before the audience does."
          sub="CanonPulse reads your whole back-catalog into a dual-layer story graph, then catches the canon breaks, the promises you left hanging and the cliffhangers that aren't playing fair — while there's still time to fix them."
          note="First episode free · Script or audio · Nothing leaves your workspace"
        >
          <Btn href="#">Run an episode free</Btn>
          <Btn href="#classifier" variant="ghost">
            See what it catches
          </Btn>
        </CosmosHero>

        <div className="flex flex-wrap items-center gap-x-8 gap-y-3 pb-20 text-[14px] text-muted-foreground">
          <span className="text-foreground/50">Built for long-running serials, any genre —</span>
          {GENRES.map((g) => (
            <span key={g} className="font-medium">
              {g}
            </span>
          ))}
        </div>

        <Problem />

        <DualLayerGraph />

        <TwistHoleDiff />

        <Section
          id="reads"
          title="What it reads on every pass"
          lead="Three checks against the graph, three things it builds while it's in there. All of it runs before publish, none of it needs a spreadsheet."
        >
          <div className="grid divide-y divide-white/8 border-y border-white/8 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            {READS.slice(0, 3).map((f) => (
              <div key={f.title} className="py-6 sm:px-6 sm:py-3 sm:first:pl-0 sm:last:pr-0">
                <h3 className="text-[17px] font-semibold tracking-[-0.01em]">{f.title}</h3>
                <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">{f.body}</p>
              </div>
            ))}
          </div>
          <div className="grid divide-y divide-white/8 border-b border-white/8 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            {READS.slice(3).map((f) => (
              <div key={f.title} className="py-6 sm:px-6 sm:py-3 sm:first:pl-0 sm:last:pr-0">
                <h3 className="text-[17px] font-semibold tracking-[-0.01em]">{f.title}</h3>
                <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">{f.body}</p>
              </div>
            ))}
          </div>
        </Section>

        <WritersRoom />

        <RetentionCurves />

        <Surfaces />

        <section className="border-t border-white/8 py-24 sm:py-28">
          <blockquote className="max-w-[34ch] text-[clamp(1.5rem,3.4vw,2.1rem)] leading-[1.2] font-semibold tracking-[-0.03em] text-balance">
            “It caught a character mourning someone who was still alive for two more episodes. We'd
            have shipped it, and listeners would have found it in minutes.”
          </blockquote>
          <cite className="mt-6 block text-[15px] text-muted-foreground not-italic">
            Illustrative example — showrunner reviewing a 300-episode drama
          </cite>
        </section>

        <section className="border-t border-white/8 py-24 sm:py-28">
          <h2 className="max-w-[18ch] text-[clamp(1.9rem,4.6vw,3rem)] leading-[1.05] font-bold tracking-[-0.04em] text-balance">
            The listeners will find it either way
          </h2>
          <p className="mt-4 max-w-[52ch] text-[17px] leading-relaxed text-muted-foreground">
            Better it's a note in your workspace on Tuesday than a pinned thread on Friday.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Btn href="#">Run an episode free</Btn>
            <Btn href="#surfaces" variant="ghost">
              See the studio view
            </Btn>
          </div>
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-white/8 py-8 pb-24 text-[14px] text-muted-foreground">
          <span>© 2026 CanonPulse</span>
          <span className="flex gap-5">
            <a href="#" className={cn("rounded-md hover:text-foreground", focusRing)}>
              Privacy
            </a>
            <a href="#" className={cn("rounded-md hover:text-foreground", focusRing)}>
              Terms
            </a>
            <a href="#" className={cn("rounded-md hover:text-foreground", focusRing)}>
              Status
            </a>
          </span>
        </footer>
      </div>

      <ScrollRail sections={NAV} />
    </>
  )
}
