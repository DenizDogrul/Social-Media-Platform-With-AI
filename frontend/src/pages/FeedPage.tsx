import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import SocialTopNav from "../components/SocialTopNav";
import VerificationBadge from "../components/VerificationBadge";
import { QuoteRepostModal } from "../components/QuoteRepostModal";
import { api } from "../lib/api";
import { useAuthStore } from "../store/auth";

const PAGE_SIZE = 10;

// Parse @mentions in text and return JSX with links
const parseMentions = (text: string): (string | ReactNode)[] | string => {
  const mentionRegex = /@(\w+)/g;
  const parts: (string | ReactNode)[] = [];
  let lastIndex = 0;
  let match;

  while ((match = mentionRegex.exec(text)) !== null) {
    // Add text before mention
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    // Add mention as link
    const username = match[1];
    parts.push(
      <Link key={`${match.index}-${username}`} to={`/users?search=${username}`} style={{ color: "#0066cc", fontWeight: "bold" }}>
        @{username}
      </Link>
    );
    lastIndex = mentionRegex.lastIndex;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
};

type FeedPost = {
  post_id: number;
  title: string;
  content: string;
  author: {
    id: number;
    username: string;
    is_verified?: boolean;
  };
  tags: string[];
  likes: number;
  is_liked: boolean;
  is_bookmarked?: boolean;
  created_at: string | null;
  media_url?: string | null;
  thumbnail_url?: string | null;
  media_type?: "image" | "video" | null;
};

type SuggestedUser = {
  id: number;
  username: string;
  email: string;
  is_verified?: boolean;
  reason?: string;
};

type TrendingTag = {
  tag: string;
  post_count: number;
  likes_count: number;
  score: number;
};

const validateVideoDuration = (file: File): Promise<boolean> => {
  return new Promise((resolve) => {
    if (!file.type.startsWith("video/")) {
      resolve(true);
      return;
    }
    const video = document.createElement("video");
    const url = URL.createObjectURL(file);
    video.src = url;
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(video.duration >= 6 && video.duration <= 8);
    };
    video.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(false);
    };
  });
};

export default function FeedPage() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [creating, setCreating] = useState(false);
  const [feedMode, setFeedMode] = useState<"personal" | "explore" | "trending">("personal");
  const [search, setSearch] = useState("");
  const [mediaFile, setMediaFile] = useState<File | null>(null);
  const [uploadingMedia, setUploadingMedia] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestedUser[]>([]);
  const [trendingTags, setTrendingTags] = useState<TrendingTag[]>([]);
  const [blockedUserIds, setBlockedUserIds] = useState<number[]>([]);
  const [mutedUserIds, setMutedUserIds] = useState<number[]>([]);
  const [moderationNames, setModerationNames] = useState<Record<number, string>>({});
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showQuoteModal, setShowQuoteModal] = useState(false);
  const [quoteRepostPost, setQuoteRepostPost] = useState<FeedPost | null>(null);

  const topTags = useMemo(() => {
    const counts = new Map<string, number>();
    posts.forEach((post) => {
      post.tags.forEach((tag) => {
        counts.set(tag, (counts.get(tag) ?? 0) + 1);
      });
    });
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([tag, count]) => ({ tag, count }));
  }, [posts]);

  const visibleTopTags = trendingTags.length > 0
    ? trendingTags.map((item) => ({ tag: item.tag, count: item.score }))
    : topTags;

  const suggestedCreators = useMemo(() => suggestions.slice(0, 6), [suggestions]);

  const filteredPosts = useMemo(() => {
    const q = search.trim().toLowerCase();
    const visible = posts.filter((post) => !blockedUserIds.includes(post.author.id) && !mutedUserIds.includes(post.author.id));
    if (!q) return visible;
    return visible.filter((post) => {
      const searchable = `${post.title} ${post.content} ${post.author.username} ${post.tags.join(" ")}`.toLowerCase();
      return searchable.includes(q);
    });
  }, [posts, search, blockedUserIds, mutedUserIds]);

  const getErrorMessage = (fallback: string, err: unknown) => {
    if (typeof err === "object" && err && "response" in err) {
      const response = (err as { response?: { data?: { detail?: string } | string } }).response;
      const data = response?.data;
      if (typeof data === "string" && data.trim()) return data;
      if (typeof data === "object" && data?.detail) return data.detail;
    }
    return fallback;
  };

  const loadFeed = async (reset = true) => {
    setError("");
    if (reset) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }

    try {
      const offset = reset ? 0 : posts.length;
      let endpoint = "/posts/feed";
      if (feedMode === "explore") endpoint = "/posts/explore";
      else if (feedMode === "trending") endpoint = "/analytics/trending-posts";
      const response = await api.get<FeedPost[]>(endpoint, {
        params: { limit: PAGE_SIZE, offset },
      });

      setHasMore(response.data.length === PAGE_SIZE);
      if (reset) {
        setPosts(response.data);
      } else {
        setPosts((current) => [...current, ...response.data]);
      }
    } catch (err) {
      setError(getErrorMessage("Feed could not be loaded.", err));
    } finally {
      if (reset) {
        setLoading(false);
      } else {
        setLoadingMore(false);
      }
    }
  };

  useEffect(() => {
    const loadSuggestions = async () => {
      try {
        const response = await api.get<SuggestedUser[]>("/users/discover/follow-suggestions", { params: { limit: 8 } });
        setSuggestions(response.data);
      } catch {
        setSuggestions([]);
      }
    };

    const loadModeration = async () => {
      try {
        const [blocksRes, mutesRes] = await Promise.all([
          api.get<Array<{ id: number }>>("/moderation/blocks"),
          api.get<Array<{ id: number }>>("/moderation/mutes"),
        ]);
        setBlockedUserIds(blocksRes.data.map((u) => u.id));
        setMutedUserIds(mutesRes.data.map((u) => u.id));
      } catch {
        setBlockedUserIds([]);
        setMutedUserIds([]);
      }
    };

    const loadTrendingTags = async () => {
      try {
        const response = await api.get<TrendingTag[]>("/analytics/trending-tags", { params: { limit: 6 } });
        setTrendingTags(response.data);
      } catch {
        setTrendingTags([]);
      }
    };

    void loadFeed(true);
    void loadSuggestions();
    void loadModeration();
    void loadTrendingTags();
  }, [feedMode]);

  useEffect(() => {
    const ids = [...new Set([...blockedUserIds, ...mutedUserIds])];
    if (ids.length === 0) {
      setModerationNames({});
      return;
    }

    const run = async () => {
      const entries = await Promise.all(
        ids.map(async (id) => {
          try {
            const response = await api.get<{ username: string }>(`/users/${id}`);
            return [id, response.data.username] as const;
          } catch {
            return [id, `user-${id}`] as const;
          }
        })
      );
      setModerationNames(Object.fromEntries(entries));
    };

    void run();
  }, [blockedUserIds, mutedUserIds]);

  useEffect(() => {
    if (!sentinelRef.current || loading || loadingMore || !hasMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && !loadingMore) {
          void loadFeed(false);
        }
      },
      { rootMargin: "220px" }
    );

    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [loading, loadingMore, hasMore, posts.length, feedMode]);

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const onToggleLike = async (post: FeedPost) => {
    const endpoint = post.is_liked ? `/posts/${post.post_id}/unlike` : `/posts/${post.post_id}/like`;

    try {
      await api.post(endpoint);
      setPosts((current) =>
        current.map((item) => {
          if (item.post_id !== post.post_id) return item;
          return {
            ...item,
            is_liked: !item.is_liked,
            likes: item.is_liked ? Math.max(0, item.likes - 1) : item.likes + 1,
          };
        })
      );
    } catch (err) {
      setError(getErrorMessage("Like action failed.", err));
    }
  };

  const toggleBookmark = async (post: FeedPost) => {
    const endpoint = `/posts/${post.post_id}/bookmark`;
    try {
      if (post.is_bookmarked) {
        await api.delete(endpoint);
      } else {
        await api.post(endpoint);
      }

      setPosts((current) =>
        current.map((item) =>
          item.post_id === post.post_id
            ? { ...item, is_bookmarked: !item.is_bookmarked }
            : item
        )
      );
      setSuccess(post.is_bookmarked ? "Bookmark removed." : "Post saved to bookmarks.");
    } catch (err) {
      setError(getErrorMessage("Bookmark action failed.", err));
    }
  };

  const onCreatePost = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const payload = {
      title: title.trim(),
      content: content.trim(),
    };

    if (!payload.title || !payload.content) {
      setError("Title and content are required.");
      return;
    }

    setCreating(true);
    try {
      let media_url: string | undefined;
      let media_type: "image" | "video" | undefined;
      let thumbnail_url: string | undefined;

      if (mediaFile) {
        setUploadingMedia(true);
        const form = new FormData();
        form.append("media", mediaFile);
        const uploadRes = await api.post<{ media_url: string; thumbnail_url?: string | null; media_type: "image" | "video" }>("/posts/upload-media", form);
        media_url = uploadRes.data.media_url;
        thumbnail_url = uploadRes.data.thumbnail_url ?? undefined;
        media_type = uploadRes.data.media_type;
      }

      await api.post("/posts/", { ...payload, media_url, thumbnail_url, media_type });
      setTitle("");
      setContent("");
      setMediaFile(null);
      await loadFeed(true);
      setSuccess("Post published successfully.");
    } catch (err) {
      setError(getErrorMessage("Post creation failed.", err));
    } finally {
      setCreating(false);
      setUploadingMedia(false);
    }
  };

  const sharePost = async (post: FeedPost) => {
    const shareUrl = `${window.location.origin}/posts/${post.post_id}`;
    try {
      if (navigator.share) {
        await navigator.share({ title: post.title, text: post.content, url: shareUrl });
      } else {
        await navigator.clipboard.writeText(shareUrl);
      }
    } catch {
      // Ignore user-cancelled share action.
    }
  };

  const reportPost = async (postId: number) => {
    const reason = window.prompt("Report reason", "spam")?.trim();
    if (!reason) return;
    try {
      await api.post("/moderation/report", {
        target_type: "post",
        target_id: postId,
        reason,
        details: `Reported from feed post ${postId}`,
      });
      setSuccess("Report submitted.");
    } catch (err) {
      setError(getErrorMessage("Report action failed.", err));
    }
  };

  const toggleMuteAuthor = async (authorId: number) => {
    const currentlyMuted = mutedUserIds.includes(authorId);
    try {
      if (currentlyMuted) {
        await api.delete(`/moderation/mute/${authorId}`);
        setMutedUserIds((ids) => ids.filter((id) => id !== authorId));
        setSuccess("Author unmuted.");
      } else {
        await api.post(`/moderation/mute/${authorId}`);
        setMutedUserIds((ids) => [...ids, authorId]);
        setSuccess("Author muted.");
      }
    } catch (err) {
      setError(getErrorMessage("Mute action failed.", err));
    }
  };

  const toggleBlockAuthor = async (authorId: number) => {
    const currentlyBlocked = blockedUserIds.includes(authorId);
    try {
      if (currentlyBlocked) {
        await api.delete(`/moderation/block/${authorId}`);
        setBlockedUserIds((ids) => ids.filter((id) => id !== authorId));
        setSuccess("Author unblocked.");
      } else {
        await api.post(`/moderation/block/${authorId}`);
        setBlockedUserIds((ids) => [...ids, authorId]);
        setSuccess("Author blocked.");
      }
    } catch (err) {
      setError(getErrorMessage("Block action failed.", err));
    }
  };

  const toggleRepost = async (post: FeedPost) => {
    // Open quote repost modal
    setQuoteRepostPost(post);
    setShowQuoteModal(true);
  };

  const mediaPreviewStyle = (post: FeedPost) => {
    const hue = (post.post_id * 53) % 360;
    return {
      background: `linear-gradient(130deg, hsl(${hue} 70% 78%), hsl(${(hue + 46) % 360} 68% 63%))`,
    };
  };

  return (
    <main className="app-shell social-shell">
      <SocialTopNav
        title="Explore the community"
        subtitle={user ? `Signed in as @${user.username}` : "Discover the latest posts."}
        searchValue={search}
        onSearchChange={setSearch}
      />

      <section className="card feed-toolbar">
        <div className="feed-mode-switch" role="tablist" aria-label="Feed mode">
          <button
            type="button"
            onClick={() => setFeedMode("personal")}
            className={feedMode === "personal" ? "mode-active" : "btn-ghost"}
          >
            Personal
          </button>
          <button
            type="button"
            onClick={() => setFeedMode("explore")}
            className={feedMode === "explore" ? "mode-active" : "btn-ghost"}
          >
            Explore
          </button>
          <button
            type="button"
            onClick={() => setFeedMode("trending")}
            className={feedMode === "trending" ? "mode-active" : "btn-ghost"}
          >
            Trending
          </button>
        </div>

        <div className="row">
          <p className="meta feed-count">{filteredPosts.length} post shown</p>
          <button className="btn-ghost" onClick={() => void loadFeed(true)} disabled={loading}>
            {loading ? "Loading..." : "Refresh"}
          </button>
          <button className="btn-danger" onClick={() => void onLogout()}>Logout</button>
        </div>
      </section>

      <section className="social-grid">
        <section className="feed-layout">
          <form onSubmit={onCreatePost} className="card composer form-grid">
            <h2>Create Post</h2>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Post title" maxLength={255} />
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Share something interesting..."
              maxLength={1000}
              rows={4}
            />
            <input
              type="file"
              accept="image/*,video/*"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) {
                  setMediaFile(null);
                  setError("");
                  return;
                }
                if (file.type.startsWith("video/")) {
                  const valid = await validateVideoDuration(file);
                  if (!valid) {
                    setError("Video must be between 6 and 8 seconds.");
                    setMediaFile(null);
                    e.target.value = "";
                    return;
                  }
                  setError("");
                }
                setMediaFile(file);
              }}
            />
            <button type="submit" disabled={creating}>
              {creating ? (uploadingMedia ? "Uploading media..." : "Publishing...") : "Publish"}
            </button>
          </form>

          {error && <p className="error">{error}</p>}
          {success && <p className="success">{success}</p>}

          {!loading && filteredPosts.length === 0 && <p className="card empty-state">No posts matched your search.</p>}

          {filteredPosts.map((post, index) => (
            <article key={post.post_id} className="card post-card" style={{ animationDelay: `${index * 45}ms` }}>
              {post.media_url ? (
                <div className="media-frame">
                  {post.media_type === "video" ? (
                    <video
                      className="uploaded-media"
                      src={post.media_url}
                      controls
                      preload="metadata"
                      poster={post.thumbnail_url ?? undefined}
                    />
                  ) : (
                    <a href={post.media_url} target="_blank" rel="noreferrer" aria-label="Open full image">
                      <img
                        className="uploaded-media"
                        src={post.media_url ?? undefined}
                        alt={post.title}
                        loading="lazy"
                      />
                    </a>
                  )}
                </div>
              ) : (
                <div className="media-preview" style={mediaPreviewStyle(post)}>
                  <span>Clip Preview</span>
                </div>
              )}
              <h2>{post.title}</h2>
              <p style={{ marginTop: 8, marginBottom: 10 }}>{parseMentions(post.content)}</p>
              <p className="meta" style={{ marginBottom: 8 }}>
                by <Link to={`/users/${post.author.id}`}>@{post.author.username}</Link>
                <VerificationBadge verified={post.author.is_verified} compact />
                {post.created_at ? ` | ${new Date(post.created_at).toLocaleString()}` : ""}
              </p>
              <div className="tag-list" style={{ marginBottom: 12 }}>
                {post.tags.map((tag) => (
                  <Link key={`${post.post_id}-${tag}`} className="tag" to={`/tags/${encodeURIComponent(tag)}`}>#{tag}</Link>
                ))}
              </div>
              <div className="row action-row">
                <button className="btn-ghost" onClick={() => void onToggleLike(post)}>
                  {post.is_liked ? "Unlike" : "Like"} ({post.likes})
                </button>
                <button onClick={() => navigate(`/posts/${post.post_id}`, { state: { post } })}>Comments</button>
                <button className="btn-ghost" onClick={() => void toggleBookmark(post)}>
                  {post.is_bookmarked ? "Bookmarked" : "Bookmark"}
                </button>
                <button className="btn-ghost" onClick={() => void toggleRepost(post)}>
                  Repost
                </button>
                <button className="btn-ghost" onClick={() => void sharePost(post)}>Share</button>
                {user?.id !== post.author.id && (
                  <>
                    <button className="btn-ghost" onClick={() => void reportPost(post.post_id)}>Report</button>
                    <button className="btn-ghost" onClick={() => void toggleMuteAuthor(post.author.id)}>
                      {mutedUserIds.includes(post.author.id) ? "Unmute author" : "Mute author"}
                    </button>
                    <button className="btn-danger" onClick={() => void toggleBlockAuthor(post.author.id)}>
                      {blockedUserIds.includes(post.author.id) ? "Unblock author" : "Block author"}
                    </button>
                  </>
                )}
              </div>
            </article>
          ))}

          <div ref={sentinelRef} className="feed-sentinel" />
          {loadingMore && <p className="meta">Loading more posts...</p>}
          {!hasMore && posts.length > 0 && <p className="meta">You reached the end of the feed.</p>}
        </section>

        {showQuoteModal && quoteRepostPost && (
          <QuoteRepostModal
            postId={quoteRepostPost.post_id}
            postTitle={quoteRepostPost.title}
            onSuccess={() => {
              setSuccess("Post quoted successfully.");
              void loadFeed(true);
            }}
            onClose={() => {
              setShowQuoteModal(false);
              setQuoteRepostPost(null);
            }}
          />
        )}

        <aside className="feed-layout side-panel">
          <section className="card side-card">
            <h3>Profile Snapshot</h3>
            <p className="meta">{user ? `@${user.username}` : "Guest"}</p>
            <div className="row" style={{ marginTop: 10 }}>
              <span className="tag">posts {posts.length}</span>
              <span className="tag">mode {feedMode}</span>
            </div>
          </section>

          <section className="card side-card">
            <h3>Trending Tags</h3>
            <div className="tag-list" style={{ marginTop: 10 }}>
              {visibleTopTags.length === 0 && <p className="meta">No tags yet.</p>}
              {visibleTopTags.map((item) => (
                <Link key={item.tag} className="tag" to={`/tags/${encodeURIComponent(item.tag)}`}>#{item.tag} | {item.count}</Link>
              ))}
            </div>
          </section>

          <section className="card side-card">
            <h3>Suggested Creators</h3>
            <div className="feed-layout" style={{ marginTop: 10 }}>
              {suggestedCreators.length === 0 && <p className="meta">No creator suggestions yet.</p>}
              {suggestedCreators.map((creator) => (
                <div key={creator.id} className="creator-suggestion-card">
                  <Link to={`/users/${creator.id}`} className="creator-link">
                    @{creator.username}
                    <VerificationBadge verified={creator.is_verified} compact />
                  </Link>
                  {creator.reason && <p className="meta">{creator.reason}</p>}
                </div>
              ))}
            </div>
          </section>

          <section className="card side-card">
            <h3>Moderation</h3>
            <div className="feed-layout moderation-list" style={{ marginTop: 10 }}>
              <p className="meta">Blocked</p>
              {blockedUserIds.length === 0 && <p className="meta">No blocked users.</p>}
              {blockedUserIds.map((id) => (
                <div key={`blocked-${id}`} className="row">
                  <span className="tag">@{moderationNames[id] ?? `user-${id}`}</span>
                  <button className="btn-ghost" onClick={() => void toggleBlockAuthor(id)}>Unblock</button>
                </div>
              ))}

              <p className="meta" style={{ marginTop: 8 }}>Muted</p>
              {mutedUserIds.length === 0 && <p className="meta">No muted users.</p>}
              {mutedUserIds.map((id) => (
                <div key={`muted-${id}`} className="row">
                  <span className="tag">@{moderationNames[id] ?? `user-${id}`}</span>
                  <button className="btn-ghost" onClick={() => void toggleMuteAuthor(id)}>Unmute</button>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
