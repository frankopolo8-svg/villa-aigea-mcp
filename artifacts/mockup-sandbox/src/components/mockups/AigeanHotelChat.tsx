import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import {
  ArrowUp,
  BedDouble,
  Bell,
  CalendarDays,
  Check,
  ChevronRight,
  Clock3,
  Coffee,
  Compass,
  ImageOff,
  MapPin,
  Paperclip,
  Sparkles,
  Waves,
  Wifi,
  X,
  type LucideIcon,
} from "lucide-react";

type MediaItem = {
  url: string;
  alt?: string;
  caption?: string;
  mimeType?: string;
};

type Message = {
  id: string;
  role: "assistant" | "user";
  text: string;
  time: string;
  media?: MediaItem[];
};

type Suggestion = {
  label: string;
  prompt: string;
  icon: LucideIcon;
};

const suggestions: Suggestion[] = [
  { label: "Rooms & suites", prompt: "What rooms and suites are available?", icon: BedDouble },
  { label: "Hotel amenities", prompt: "Which amenities does Aigean Hotel offer?", icon: Waves },
  { label: "Check-in times", prompt: "What are the check-in and check-out times?", icon: Clock3 },
  { label: "Breakfast", prompt: "Tell me about breakfast at the hotel.", icon: Coffee },
  { label: "Location", prompt: "Where is Aigean Hotel located?", icon: MapPin },
  { label: "Reservations", prompt: "I would like help with a reservation.", icon: CalendarDays },
];

const answers: Record<string, string> = {
  "What rooms and suites are available?":
    "I can help you explore our rooms and suites. Share your travel dates and number of guests, and I’ll find the most suitable options for your stay.",
  "Which amenities does Aigean Hotel offer?":
    "Aigean Hotel offers thoughtfully selected amenities for a relaxed stay, including complimentary Wi-Fi and personalized concierge assistance. I can also help with any specific amenity you have in mind.",
  "What are the check-in and check-out times?":
    "Standard check-in begins at 3:00 PM and check-out is by 11:00 AM. Early arrival or late departure may be arranged subject to availability.",
  "Tell me about breakfast at the hotel.":
    "Breakfast is served each morning with a selection of fresh local produce and Mediterranean favorites. Let me know about any dietary preferences and I’ll help with the details.",
  "Where is Aigean Hotel located?":
    "I can provide directions, nearby landmarks, and transfer guidance. Tell me where you’ll be arriving from and I’ll suggest the easiest route.",
  "I would like help with a reservation.":
    "It would be my pleasure. Please share your preferred dates, number of guests, and room preferences, and I’ll guide you through the reservation options.",
};

const rtlPattern = /[\u0590-\u08FF\uFB1D-\uFDFD\uFE70-\uFEFC]/;
const imageExtensionPattern = /\.(avif|gif|jpe?g|png|webp)(?:\?.*)?$/i;
const urlPattern = /https?:\/\/[^\s<>()]+/g;

function getDirection(text: string) {
  return rtlPattern.test(text) ? "rtl" : "ltr";
}

function extractImages(text: string): MediaItem[] {
  return (text.match(urlPattern) ?? [])
    .filter((url) => imageExtensionPattern.test(url))
    .map((url) => ({ url, alt: "Image shared by the hotel concierge" }));
}

function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className={compact ? "brand-mark brand-mark--compact" : "brand-mark"} aria-hidden="true">
      <span className="brand-mark__arch" />
      <span className="brand-mark__wave" />
    </div>
  );
}

function MediaCard({ item }: { item: MediaItem }) {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  return (
    <figure className="media-card">
      <div className="media-card__frame">
        {status === "loading" && <div className="media-card__skeleton" aria-label="Loading image" />}
        {status === "error" ? (
          <div className="media-card__error" role="status">
            <ImageOff aria-hidden="true" />
            <span>This image could not be displayed</span>
            <button type="button" onClick={() => setStatus("loading")}>Try again</button>
          </div>
        ) : (
          <img
            src={item.url}
            alt={item.alt || item.caption || "Hotel image"}
            loading="lazy"
            onLoad={() => setStatus("ready")}
            onError={() => setStatus("error")}
            className={status === "ready" ? "media-card__image is-ready" : "media-card__image"}
          />
        )}
      </div>
      {item.caption && <figcaption>{item.caption}</figcaption>}
    </figure>
  );
}

function ResponseContent({ message }: { message: Message }) {
  const images = useMemo(() => {
    const seen = new Set<string>();
    return [...(message.media ?? []), ...extractImages(message.text)].filter((item) => {
      if (seen.has(item.url)) return false;
      seen.add(item.url);
      return true;
    });
  }, [message]);

  const cleanText = message.text.replace(urlPattern, (url) => imageExtensionPattern.test(url) ? "" : url).trim();

  return (
    <>
      {cleanText && <p>{cleanText}</p>}
      {images.length > 0 && (
        <div className={images.length > 1 ? "media-grid media-grid--multiple" : "media-grid"}>
          {images.map((item) => <MediaCard key={item.url} item={item} />)}
        </div>
      )}
    </>
  );
}

function MessageRow({ message, isNewest }: { message: Message; isNewest: boolean }) {
  const direction = getDirection(message.text);
  const isAssistant = message.role === "assistant";

  return (
    <article
      className={`message-row message-row--${message.role}${isNewest ? " message-row--new" : ""}`}
      dir={direction}
      aria-label={`${isAssistant ? "Concierge" : "You"} at ${message.time}`}
    >
      {isAssistant && (
        <div className="concierge-avatar"><BrandMark compact /></div>
      )}
      <div className="message-row__content">
        <div className="message-meta">
          <span>{isAssistant ? "Aigean Concierge" : "You"}</span>
          <time>{message.time}</time>
        </div>
        <div className="message-bubble">
          <ResponseContent message={message} />
        </div>
        {!isAssistant && <span className="delivery-status"><Check aria-hidden="true" /> Delivered</span>}
      </div>
    </article>
  );
}

function TypingIndicator() {
  return (
    <div className="message-row message-row--assistant message-row--new" aria-label="Concierge is typing" role="status">
      <div className="concierge-avatar"><BrandMark compact /></div>
      <div className="message-row__content">
        <div className="message-meta"><span>Aigean Concierge</span></div>
        <div className="message-bubble typing-bubble">
          <i /><i /><i />
          <span className="sr-only">Concierge is preparing a response</span>
        </div>
      </div>
    </div>
  );
}

function Welcome({ onSuggestion }: { onSuggestion: (prompt: string) => void }) {
  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <div className="welcome__emblem"><BrandMark /></div>
      <div className="welcome__copy">
        <span className="eyebrow">Your private hotel concierge</span>
        <h1 id="welcome-title">How may we make your stay exceptional?</h1>
        <p>Ask about your stay at Aigean Hotel. I can assist with rooms, hotel details, local guidance, and reservations.</p>
      </div>
      <div className="suggestion-grid" aria-label="Suggested questions">
        {suggestions.map(({ label, prompt, icon: Icon }, index) => (
          <button
            key={label}
            type="button"
            className="suggestion-card"
            onClick={() => onSuggestion(prompt)}
            style={{ "--delay": `${index * 55}ms` } as React.CSSProperties}
          >
            <span className="suggestion-card__icon"><Icon aria-hidden="true" /></span>
            <span>{label}</span>
            <ChevronRight aria-hidden="true" className="suggestion-card__arrow" />
          </button>
        ))}
      </div>
    </section>
  );
}

export function AigeanHotelChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [attachmentName, setAttachmentName] = useState<string | null>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isTyping]);

  function sendMessage(text: string) {
    const content = text.trim();
    if (!content || isTyping) return;

    const now = new Date();
    const userMessage: Message = {
      id: `user-${now.getTime()}`,
      role: "user",
      text: content,
      time: now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setAttachmentName(null);
    setIsTyping(true);

    window.setTimeout(() => {
      const responseTime = new Date();
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${responseTime.getTime()}`,
          role: "assistant",
          text: answers[content] ?? "Thank you for your message. I’m here to help with your Aigean Hotel stay. Could you share a little more detail so I can assist you personally?",
          time: responseTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      setIsTyping(false);
    }, 1150);
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    sendMessage(draft);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      sendMessage(draft);
    }
  }

  function resetConversation() {
    setMessages([]);
    setDraft("");
    setAttachmentName(null);
    setIsTyping(false);
    textareaRef.current?.focus();
  }

  return (
    <main className="hotel-shell">
      <div className="hotel-shell__texture" aria-hidden="true" />
      <section className="chat-window" aria-label="Aigean Hotel concierge chat">
        <header className="chat-header">
          <button className="hotel-identity" type="button" onClick={resetConversation} aria-label="Start a new conversation">
            <BrandMark />
            <span className="hotel-identity__copy">
              <strong>Aigean Hotel</strong>
              <small><span className="status-dot" /> Concierge online</small>
            </span>
          </button>
          <div className="header-actions">
            <span className="availability"><Clock3 aria-hidden="true" /> Available 24/7</span>
            <button type="button" className="icon-button" aria-label="Concierge notifications">
              <Bell aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="concierge-strip">
          <span><Sparkles aria-hidden="true" /> Personal assistance for every part of your stay</span>
          <span className="concierge-strip__secondary"><Wifi aria-hidden="true" /> Secure conversation</span>
        </div>

        <div className="transcript" ref={transcriptRef} aria-live="polite">
          <div className="transcript__inner">
            {messages.length === 0 ? (
              <Welcome onSuggestion={sendMessage} />
            ) : (
              <div className="conversation">
                <div className="conversation-date"><span>Today</span></div>
                {messages.map((message, index) => (
                  <MessageRow key={message.id} message={message} isNewest={index === messages.length - 1} />
                ))}
                {isTyping && <TypingIndicator />}
              </div>
            )}
          </div>
        </div>

        <footer className="composer-area">
          {attachmentName && (
            <div className="attachment-pill">
              <Paperclip aria-hidden="true" />
              <span>{attachmentName}</span>
              <button type="button" onClick={() => setAttachmentName(null)} aria-label="Remove attachment"><X /></button>
            </div>
          )}
          <form className="composer" onSubmit={handleSubmit}>
            <label className="attach-button" aria-label="Attach a file">
              <Paperclip aria-hidden="true" />
              <input
                type="file"
                accept="image/*"
                onChange={(event) => setAttachmentName(event.target.files?.[0]?.name ?? null)}
              />
            </label>
            <textarea
              ref={textareaRef}
              value={draft}
              dir={getDirection(draft)}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask your concierge anything..."
              rows={1}
              aria-label="Message Aigean Hotel concierge"
            />
            <button type="submit" className="send-button" disabled={!draft.trim() || isTyping} aria-label="Send message">
              <ArrowUp aria-hidden="true" />
            </button>
          </form>
          <div className="composer-note">
            <span><Compass aria-hidden="true" /> Local knowledge, thoughtfully delivered</span>
            <span>Enter to send · Shift + Enter for a new line</span>
          </div>
        </footer>
      </section>
    </main>
  );
}

export default AigeanHotelChat;
