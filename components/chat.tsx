"use client"

import { useEffect, useMemo, useState } from "react"
import { ChatKit, useChatKit } from "@openai/chatkit-react"

function getOrCreateDeviceId() {
  if (typeof window === "undefined") return "anonymous"
  const key = "chatkit-device-id"
  let id = window.localStorage.getItem(key)
  if (!id) {
    id = crypto.randomUUID()
    window.localStorage.setItem(key, id)
  }
  return id
}

export function Chat() {
  const [error, setError] = useState<string | null>(null)
  const [scheme, setScheme] = useState<"light" | "dark">("dark")

  // Match ChatKit's theme to the user's system preference.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const update = () => setScheme(mq.matches ? "dark" : "light")
    update()
    mq.addEventListener("change", update)
    return () => mq.removeEventListener("change", update)
  }, [])

  const deviceId = useMemo(getOrCreateDeviceId, [])

  const { control } = useChatKit({
    theme: {
      colorScheme: scheme,
      radius: "round",
      density: "normal",
      typography: { baseSize: 16 },
      color: {
        // Warm neutral grayscale with a subtle blue accent.
        grayscale: { hue: 75, tint: 2 },
        accent: { primary: "#5578bd", level: 2 },
      },
    },
    startScreen: {
      greeting: "Welcome to Aigean Hotel — how may I help with your stay?",
      prompts: [
        { label: "Explore rooms & suites", prompt: "Show me your rooms and suites." },
        { label: "Check availability & rates", prompt: "What rooms are available and what are the rates?" },
        { label: "Dining & spa", prompt: "Tell me about your dining and spa experiences." },
        { label: "Plan my arrival", prompt: "Help me plan my arrival and check-in." },
      ],
    },
    composer: {
      placeholder: "Ask about rooms, dining, or your stay…",
    },
    api: {
      async getClientSecret() {
        const res = await fetch("/api/chatkit/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user: deviceId }),
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          const message = data?.error ?? "Unable to start chat session"
          setError(message)
          throw new Error(message)
        }
        setError(null)
        const { client_secret } = await res.json()
        return client_secret
      },
    },
    onError: ({ error }: { error: { name?: string } }) => {
      if (error?.name === "IntegrationError") {
        setError(
          "ChatKit could not verify this domain. Add the domain that serves this app to your OpenAI domain allowlist, then reload.",
        )
      } else {
        setError("Something went wrong loading the chat. Please reload and try again.")
      }
    },
  })

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-3xl border border-border bg-card shadow-[0_1px_2px_rgba(0,0,0,0.04),0_12px_32px_-12px_rgba(0,0,0,0.18)] ring-1 ring-black/[0.02] transition-shadow duration-300">
      {error ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
          <p className="max-w-md text-sm font-medium text-destructive text-pretty">{error}</p>
          <a
            href="https://platform.openai.com/settings/organization/security/domain-allowlist"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-primary underline underline-offset-4 transition-colors hover:text-primary/80"
          >
            Open OpenAI domain allowlist
          </a>
        </div>
      ) : (
        <ChatKit control={control} className="min-h-0 flex-1" />
      )}
    </div>
  )
}
