import { BedDouble, UtensilsCrossed, Sparkles, Clock } from "lucide-react"

const highlights = [
  { icon: BedDouble, label: "Rooms & Suites" },
  { icon: UtensilsCrossed, label: "Dining" },
  { icon: Sparkles, label: "Spa & Wellness" },
  { icon: Clock, label: "24/7 Concierge" },
]

export function ConciergeHeader() {
  return (
    <header className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-border bg-card font-serif text-lg font-semibold text-primary shadow-sm sm:h-12 sm:w-12"
            aria-hidden="true"
          >
            A
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-lg font-semibold leading-none tracking-tight text-foreground sm:text-xl">
              Aigean Hotel
            </span>
            <span className="mt-1 text-[0.7rem] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Private Concierge
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 shadow-sm">
          <span className="relative flex h-2 w-2" aria-hidden="true">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
          </span>
          <span className="text-xs font-medium text-muted-foreground">Available now</span>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <h1 className="font-serif text-3xl font-semibold leading-[1.1] tracking-tight text-foreground text-balance sm:text-4xl">
          Welcome to Aigean Hotel
        </h1>
        <p className="max-w-xl text-sm leading-relaxed text-muted-foreground text-pretty sm:text-base">
          Your personal concierge is here to craft an effortless stay — from suites and dining to spa
          reservations and every detail in between.
        </p>
      </div>

      <ul className="flex flex-wrap gap-2">
        {highlights.map(({ icon: Icon, label }) => (
          <li
            key={label}
            className="flex items-center gap-2 rounded-full border border-border bg-card/60 px-3.5 py-1.5 text-xs font-medium text-secondary-foreground shadow-sm backdrop-blur-sm transition-colors hover:border-primary/30"
          >
            <Icon className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
            {label}
          </li>
        ))}
      </ul>
    </header>
  )
}
