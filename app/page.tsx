import { Chat } from "@/components/chat"

export default function Page() {
  return (
    <main className="mx-auto flex h-dvh w-full max-w-3xl flex-col px-4 py-5 sm:px-6 sm:py-8">
      <header className="mb-5 flex items-center gap-4 sm:mb-6">
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-border bg-card font-serif text-lg font-semibold text-primary shadow-sm sm:h-12 sm:w-12"
          aria-hidden="true"
        >
          A
        </div>
        <div className="flex flex-col gap-0.5">
          <h1 className="font-serif text-2xl font-semibold leading-tight tracking-tight text-foreground text-balance sm:text-3xl">
            Aigean Hotel
          </h1>
          <p className="text-sm text-muted-foreground text-pretty">
            Your personal concierge — here to make every moment of your stay effortless.
          </p>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col">
        <Chat />
      </div>

      <p className="mt-3 text-center text-xs text-muted-foreground/80">
        Aigean Hotel Concierge · available around the clock
      </p>
    </main>
  )
}
