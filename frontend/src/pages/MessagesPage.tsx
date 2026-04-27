import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import SocialTopNav from "../components/SocialTopNav";
import { api } from "../lib/api";
import { useAuthStore } from "../store/auth";

type Conversation = {
  id: number;
  user1_id: number;
  user2_id: number;
  created_at: string | null;
};

type Message = {
  id: number;
  conversation_id: number;
  sender_id: number;
  content: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string | null;
};

type PublicUser = {
  id: number;
  username: string;
};

type ConversationMeta = {
  username: string;
  preview: string;
};

const getApiErrorDetail = (error: unknown): string => {
  const detail = (error as { response?: { data?: { detail?: string } | string } })?.response?.data;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (typeof detail === "object" && detail?.detail) {
    return detail.detail;
  }
  return "";
};

export default function MessagesPage() {
  const me = useAuthStore((s) => s.user);
  const [searchParams] = useSearchParams();
  const targetUserId = Number(searchParams.get("user"));

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [counterparty, setCounterparty] = useState<PublicUser | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [conversationMeta, setConversationMeta] = useState<Record<number, ConversationMeta>>({});
  const [showConvList, setShowConvList] = useState(false);
  const threadEndRef = useRef<HTMLDivElement>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const selectedConvIdRef = useRef<number | null>(null);

  const currentConversation = useMemo(
    () => conversations.find((c) => c.id === selectedConversationId) ?? null,
    [conversations, selectedConversationId]
  );

  const otherUserId = useMemo(() => {
    if (!me?.id || !currentConversation) return null;
    return currentConversation.user1_id === me.id ? currentConversation.user2_id : currentConversation.user1_id;
  }, [currentConversation, me?.id]);

  const loadConversations = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<Conversation[]>("/messages/conversations");
      setConversations(response.data);
      if (!selectedConversationId && response.data.length > 0) {
        setSelectedConversationId(response.data[0].id);
      }
    } catch {
      setError("Conversations could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async (conversationId: number) => {
    try {
      const response = await api.get<Message[]>(`/messages/conversations/${conversationId}/messages`);
      setMessages(response.data);
    } catch {
      setError("Messages could not be loaded.");
    }
  };

  const ensureConversationFromQuery = async () => {
    if (!Number.isFinite(targetUserId) || !targetUserId) return;
    try {
      const response = await api.post<{ id: number }>(`/messages/conversations/${targetUserId}`);
      const id = response.data.id;
      setSelectedConversationId(id);
      await loadConversations();
      await loadMessages(id);
    } catch {
      setError("Conversation could not be created.");
    }
  };

  useEffect(() => {
    void (async () => {
      await loadConversations();
      await ensureConversationFromQuery();
    })();
  }, []);

  useEffect(() => {
    if (!selectedConversationId) return;
    void loadMessages(selectedConversationId);
  }, [selectedConversationId]);

  useEffect(() => {
    if (!me?.id || conversations.length === 0) {
      setConversationMeta({});
      return;
    }

    const run = async () => {
      const rows = await Promise.all(
        conversations.map(async (conversation) => {
          const peerId = conversation.user1_id === me.id ? conversation.user2_id : conversation.user1_id;

          const [userResult, msgResult] = await Promise.allSettled([
            api.get<{ username: string }>(`/users/${peerId}`),
            api.get<Message[]>(`/messages/conversations/${conversation.id}/messages`),
          ]);

          const username = userResult.status === "fulfilled" ? userResult.value.data.username : `user-${peerId}`;
          const previewSource = msgResult.status === "fulfilled" ? msgResult.value.data : [];
          const latest = previewSource.length > 0 ? previewSource[previewSource.length - 1].content : "No messages yet";
          return [conversation.id, { username, preview: latest.slice(0, 56) }] as const;
        })
      );

      setConversationMeta(Object.fromEntries(rows));
    };

    void run();
  }, [conversations, me?.id]);

  useEffect(() => {
    if (!otherUserId) {
      setCounterparty(null);
      return;
    }

    const run = async () => {
      try {
        const response = await api.get<{ id: number; username: string }>(`/users/${otherUserId}`);
        setCounterparty({ id: response.data.id, username: response.data.username });
      } catch {
        setCounterparty({ id: otherUserId, username: `user-${otherUserId}` });
      }
    };

    void run();
  }, [otherUserId]);

  // Keep ref in sync so WS handler always reads the latest selected conversation
  useEffect(() => {
    selectedConvIdRef.current = selectedConversationId;
  }, [selectedConversationId]);

  // Real-time message delivery via WebSocket
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const wsBase = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/^http/, "ws");
    const ws = new WebSocket(`${wsBase}/ws/messages?token=${encodeURIComponent(token)}`);
    wsRef.current = ws;

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as { type: string; message?: Message };
        if (data.type === "new_message" && data.message) {
          const msg = data.message;
          if (msg.conversation_id === selectedConvIdRef.current) {
            setMessages((prev) => {
              if (prev.some((m) => m.id === msg.id)) return prev;
              return [...prev, msg];
            });
          }
        }
      } catch {
        // ignore malformed frames
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, []); // intentionally mount-only; selectedConvIdRef provides fresh value

  // auto-scroll thread to bottom when messages change
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const onSend = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedConversationId) return;
    const text = draft.trim();
    if (!text) return;

    setSending(true);
    setError("");
    try {
      const res = await api.post<Message>(`/messages/conversations/${selectedConversationId}/messages`, { content: text });
      setDraft("");
      setMessages((prev) => {
        if (prev.some((m) => m.id === res.data.id)) return prev;
        return [...prev, res.data];
      });
    } catch (err) {
      setError(getApiErrorDetail(err) || "Message could not be sent.");
    } finally {
      setSending(false);
    }
  };

  return (
    <main className="app-shell social-shell">
      <SocialTopNav title="Direct Messages" subtitle={counterparty ? `Chatting with @${counterparty.username}` : "Choose a conversation"} />

      {error && <p className="error">{error}</p>}

      <section className="social-grid messages-grid">
        <aside className="feed-layout side-panel" style={{ display: showConvList ? undefined : undefined }}>
          <section className="card side-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>Conversations</h3>
              <button
                className="btn-ghost mobile-toggle"
                style={{ padding: "4px 10px", fontSize: 13 }}
                onClick={() => setShowConvList((v) => !v)}
              >
                {showConvList ? "▲ Hide" : "▼ Show"}
              </button>
            </div>
            <div className={`conv-list-body${showConvList ? " conv-open" : ""}`}>
              {loading && <p className="meta" style={{ marginTop: 8 }}>Loading...</p>}
              <div className="feed-layout" style={{ marginTop: 10 }}>
                {conversations.map((c) => (
                  <button
                    key={c.id}
                    className={selectedConversationId === c.id ? "btn-ghost" : ""}
                    onClick={() => { setSelectedConversationId(c.id); setShowConvList(false); }}
                  >
                    @{conversationMeta[c.id]?.username ?? `user-${c.id}`}
                    <span className="meta" style={{ display: "block", marginTop: 4 }}>
                      {conversationMeta[c.id]?.preview ?? "Loading preview..."}
                    </span>
                  </button>
                ))}
                {conversations.length === 0 && !loading && <p className="meta">No conversations yet.</p>}
              </div>
            </div>
          </section>
        </aside>

        <section className="feed-layout">
          <section className="card post-card thread-card">
            <h2>Thread</h2>
            {!selectedConversationId && <p className="meta" style={{ marginTop: 10 }}>Open a profile and click Message to start.</p>}
            <div className="thread-list" style={{ marginTop: 12 }}>
              {messages.map((m) => {
                const mine = m.sender_id === me?.id;
                const senderName = mine ? (me?.username ?? "Me") : (counterparty?.username ?? "?");
                return (
                  <div key={m.id} className={`bubble ${mine ? "bubble-mine" : "bubble-peer"}`}>
                    <p className="bubble-sender">@{senderName}</p>
                    <p>{m.content}</p>
                    <p className="meta" style={{ marginTop: 6 }}>
                      {m.created_at ? new Date(m.created_at).toLocaleString() : ""}
                      {mine ? ` | ${m.is_read ? `Seen ${m.read_at ? new Date(m.read_at).toLocaleTimeString() : ""}` : "Sent"}` : ""}
                    </p>
                  </div>
                );
              })}
              {selectedConversationId && messages.length === 0 && <p className="meta">No messages in this conversation yet.</p>}
              <div ref={threadEndRef} />
            </div>

            <form onSubmit={onSend} className="row" style={{ marginTop: 12 }}>
              <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Write a message" />
              <button type="submit" disabled={sending || !selectedConversationId}>
                {sending ? "Sending..." : "Send"}
              </button>
            </form>
          </section>

          <section className="card side-card">
            <h3>Quick links</h3>
            <div className="row" style={{ marginTop: 10 }}>
              <Link to="/">Feed</Link>
              <Link to="/profile">My profile</Link>
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}
