import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import SocialTopNav from "../components/SocialTopNav";
import VerificationBadge from "../components/VerificationBadge";
import { api } from "../lib/api";

// Parse @mentions in text and return JSX with links
const parseMentions = (text: string): (string | ReactNode)[] | string => {
  const mentionRegex = /@(\w+)/g;
  const parts: (string | ReactNode)[] = [];
  let lastIndex = 0;
  let match;

  while ((match = mentionRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    const username = match[1];
    parts.push(
      <Link key={`${match.index}-${username}`} to={`/users?search=${username}`} style={{ color: "#0066cc", fontWeight: "bold" }}>
        @{username}
      </Link>
    );
    lastIndex = mentionRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
};

type SearchResult = {
  users: Array<{ id: number; username: string; bio?: string | null; avatar_url?: string | null; is_verified?: boolean }>;
  tags: Array<{ name: string }>;
  posts: Array<{ post_id: number; title: string; content: string; author_username: string; author_id: number }>;
};

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [draftQuery, setDraftQuery] = useState(searchParams.get("q") ?? "");
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const q = searchParams.get("q") ?? "";
    setQuery(q);
    setDraftQuery(q);
    if (!q.trim()) {
      setResults(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .get<SearchResult>("/users/search", { params: { q } })
      .then((res) => {
        if (!cancelled) setResults(res.data);
      })
      .catch(() => {
        if (!cancelled) setError("Search failed.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  useEffect(() => {
    const next = draftQuery.trim();
    const timer = window.setTimeout(() => {
      if (!next) {
        setSearchParams({});
        return;
      }
      if (next !== query) {
        setSearchParams({ q: next });
      }
    }, 300);

    return () => window.clearTimeout(timer);
  }, [draftQuery, query, setSearchParams]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const next = draftQuery.trim();
    if (next) {
      setSearchParams({ q: next });
    }
  };

  const empty = results && results.users.length === 0 && results.tags.length === 0 && results.posts.length === 0;

  return (
    <main className="app-shell social-shell">
      <SocialTopNav title="Search" />

      <form onSubmit={handleSubmit} className="row" style={{ marginBottom: 16 }}>
        <input
          value={draftQuery}
          onChange={(e) => setDraftQuery(e.target.value)}
          placeholder="Search users, tags, posts…"
          style={{ flex: 1 }}
          autoFocus
        />
        <button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {empty && <p className="card empty-state">No results for "{searchParams.get("q")}".</p>}

      {results && results.users.length > 0 && (
        <section>
          <h3 style={{ marginBottom: 8 }}>People</h3>
          {results.users.map((u) => (
            <article key={u.id} className="card post-card" style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: "50%",
                  overflow: "hidden",
                  background: "#374151",
                  flexShrink: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 20,
                  color: "#9ca3af",
                }}
              >
                {u.avatar_url ? (
                  <img src={u.avatar_url} alt={u.username} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  u.username[0]?.toUpperCase()
                )}
              </div>
              <div style={{ flex: 1 }}>
                <Link to={`/users/${u.id}`} style={{ fontWeight: 600 }}>@{u.username}</Link>
                <VerificationBadge verified={u.is_verified} compact />
                {u.bio && <p className="meta" style={{ marginTop: 2 }}>{u.bio}</p>}
              </div>
            </article>
          ))}
        </section>
      )}

      {results && results.tags.length > 0 && (
        <section style={{ marginTop: 16 }}>
          <h3 style={{ marginBottom: 8 }}>Tags</h3>
          <div className="row" style={{ flexWrap: "wrap" }}>
            {results.tags.map((t) => (
              <Link key={t.name} className="tag" to={`/tags/${encodeURIComponent(t.name)}`}>#{t.name}</Link>
            ))}
          </div>
        </section>
      )}

      {results && results.posts.length > 0 && (
        <section style={{ marginTop: 16 }}>
          <h3 style={{ marginBottom: 8 }}>Posts</h3>
          {results.posts.map((p) => (
            <article key={p.post_id} className="card post-card">
              <h4 style={{ margin: 0 }}>
                <Link to={`/posts/${p.post_id}`}>{p.title}</Link>
              </h4>
              <p className="meta" style={{ marginTop: 4 }}>
                by <Link to={`/users/${p.author_id}`}>@{p.author_username}</Link>
              </p>
              <p style={{ marginTop: 6 }}>{parseMentions(p.content)}</p>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
