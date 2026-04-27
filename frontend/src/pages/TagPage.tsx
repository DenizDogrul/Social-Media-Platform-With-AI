import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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

type FeedPost = {
  post_id: number;
  title: string;
  content: string;
  author: { id: number; username: string; is_verified?: boolean };
  tags: string[];
  likes: number;
  is_liked: boolean;
  is_bookmarked?: boolean;
  created_at: string | null;
  media_url?: string | null;
  thumbnail_url?: string | null;
  media_type?: "image" | "video" | null;
};

export default function TagPage() {
  const { tagName } = useParams();
  const navigate = useNavigate();
  const decodedTag = useMemo(() => decodeURIComponent(tagName ?? "").trim(), [tagName]);
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!decodedTag) return;
    let cancelled = false;
    setLoading(true);
    setError("");

    api
      .get<FeedPost[]>(`/posts/tag/${encodeURIComponent(decodedTag)}`, { params: { limit: 30, offset: 0 } })
      .then((res) => {
        if (!cancelled) setPosts(res.data);
      })
      .catch(() => {
        if (!cancelled) setError("Tag posts could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [decodedTag]);

  return (
    <main className="app-shell social-shell">
      <SocialTopNav title={`#${decodedTag || "tag"}`} subtitle="Trending conversations" />
      <div className="row">
        <Link to="/search">Back to search</Link>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="meta">Loading posts...</p>}
      {!loading && posts.length === 0 && <p className="card empty-state">No posts found for this tag yet.</p>}

      {posts.map((post) => (
        <article key={post.post_id} className="card post-card">
          {post.media_url && (
            <div className="media-frame" style={{ marginBottom: 10 }}>
              {post.media_type === "video" ? (
                <video className="uploaded-media" src={post.media_url} controls preload="metadata" poster={post.thumbnail_url ?? undefined} />
              ) : (
                <a href={post.media_url} target="_blank" rel="noreferrer" aria-label="Open full image">
                  <img className="uploaded-media" src={post.media_url} alt={post.title} loading="lazy" />
                </a>
              )}
            </div>
          )}
          <h2>{post.title}</h2>
          <p style={{ marginTop: 8 }}>{parseMentions(post.content)}</p>
          <p className="meta" style={{ marginTop: 8 }}>
            by <Link to={`/users/${post.author.id}`}>@{post.author.username}</Link>
            <VerificationBadge verified={post.author.is_verified} compact />
            {post.created_at ? ` | ${new Date(post.created_at).toLocaleString()}` : ""}
          </p>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn-ghost" onClick={() => navigate(`/posts/${post.post_id}`, { state: { post } })}>
              Open thread
            </button>
          </div>
        </article>
      ))}
    </main>
  );
}
