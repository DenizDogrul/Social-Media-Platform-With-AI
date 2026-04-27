import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
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
  media_type?: "image" | "video" | null;
};

export default function SavedPostsPage() {
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<FeedPost[]>("/posts/bookmarks/list", { params: { limit: 30, offset: 0 } });
      setPosts(response.data);
    } catch {
      setError("Saved posts could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const removeBookmark = async (postId: number) => {
    try {
      await api.delete(`/posts/${postId}/bookmark`);
      setPosts((current) => current.filter((post) => post.post_id !== postId));
    } catch {
      setError("Could not remove bookmark.");
    }
  };

  return (
    <main className="app-shell social-shell">
      <SocialTopNav title="Saved Posts" subtitle="Your private bookmark collection" />

      {error && <p className="error">{error}</p>}
      {loading && <p className="meta">Loading saved posts...</p>}
      {!loading && posts.length === 0 && <p className="card empty-state">No saved posts yet.</p>}

      <section className="feed-layout">
        {posts.map((post) => (
          <article key={post.post_id} className="card post-card">
            {post.media_url && (
              <div className="media-frame" style={{ marginBottom: 10 }}>
                {post.media_type === "video" ? (
                  <video className="uploaded-media" src={post.media_url} controls preload="metadata" />
                ) : (
                  <img className="uploaded-media" src={post.media_url} alt={post.title} loading="lazy" />
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
              <Link to={`/posts/${post.post_id}`}>Open thread</Link>
              <button className="btn-danger" onClick={() => void removeBookmark(post.post_id)}>
                Remove bookmark
              </button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
