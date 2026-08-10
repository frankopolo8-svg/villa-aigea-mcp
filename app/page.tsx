import { Chat } from "@/components/chat"
import { ConciergeHeader } from "@/components/concierge-header"

export default function Page() {
  return (
    <div className="relative flex min-h-dvh flex-col">
      {/* soft ambient backdrop */}
      <div
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_50%_at_50%_0%,var(--accent)_0%,transparent_70%)] opacity-60"
        aria-hidden="true"
      />

      <main className="mx-auto flex h-dvh w-full max-w-3xl flex-col px-4 py-6 sm:px-6 sm:py-9">
        <div className="animate-in fade-in slide-in-from-top-2 duration-700">
          <ConciergeHeader />
        </div>

        <div className="mt-6 flex min-h-0 flex-1 flex-col animate-in fade-in slide-in-from-bottom-3 duration-700 sm:mt-8">
          <Chat />
        </div>

        <footer className="mt-4 flex items-center justify-center gap-2 text-center text-xs text-muted-foreground/80">
          <span>Aigean Hotel</span>
          <span aria-hidden="true">·</span>
          <span>Concierge available around the clock</span>
        </footer>
      </main>
    </div>
  )
}
