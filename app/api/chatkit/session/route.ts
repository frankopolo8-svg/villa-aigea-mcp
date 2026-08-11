import { NextResponse } from "next/server"

// Create a short-lived ChatKit client secret for the browser.
// The OpenAI API key stays server-side and is never exposed to the client.
export async function POST(request: Request) {
  const apiKey = process.env.OPENAI_API_KEY
  const workflowId = process.env.NEXT_PUBLIC_CHATKIT_WORKFLOW_ID

  if (!apiKey) {
    return NextResponse.json({ error: "OPENAI_API_KEY is not set" }, { status: 500 })
  }
  if (!workflowId) {
    return NextResponse.json({ error: "NEXT_PUBLIC_CHATKIT_WORKFLOW_ID is not set" }, { status: 500 })
  }

  // A stable per-user identifier. In a real app, derive this from your auth
  // session. Here we accept one from the client or fall back to "anonymous".
  let user = "anonymous"
  try {
    const body = await request.json()
    if (body?.user && typeof body.user === "string") {
      user = body.user
    }
  } catch {
    // no body sent — use the fallback user
  }

  const response = await fetch("https://api.openai.com/v1/chatkit/sessions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "OpenAI-Beta": "chatkit_beta=v1",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      workflow: { id: workflowId },
      user,
    }),
  })

  if (!response.ok) {
    const detail = await response.text()
    console.log("[v0] ChatKit session error:", response.status, detail)
    return NextResponse.json({ error: "Failed to create ChatKit session" }, { status: 502 })
  }

  const { client_secret } = await response.json()
  return NextResponse.json({ client_secret })
}
