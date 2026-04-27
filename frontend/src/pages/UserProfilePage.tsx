import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import SocialTopNav from "../components/SocialTopNav";
import VerificationBadge from "../components/VerificationBadge";
import { api } from "../lib/api";
import { useAuthStore } from "../store/auth";

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
  author: { id: number; username: string };
  tags: string[];
  likes: number;
  created_at: string | null;
  media_url?: string | null;
  thumbnail_url?: string | null;
  media_type?: "image" | "video" | null;
};

type UserProfile = {
  id: number;
  username: string;
  email: string;
  followers_count: number;
  following_count: number;
  posts_count: number;
  is_following: boolean;
  is_me: boolean;
  bio?: string | null;
  avatar_url?: string | null;
  cover_url?: string | null;
  badges?: string[];
  is_verified?: boolean;
};

type UserStory = {
  id: number;
  author_id: number;
  author_username: string | null;
  content: string;
  media_url: string | null;
  media_type: string | null;
  created_at: string;
  expires_at: string;
};

const parseServerDate = (value: string) => {
  const hasTimezone = /Z$|[+-]\d\d:\d\d$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
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

export default function UserProfilePage() {
  const { userId } = useParams();
  const me = useAuthStore((s) => s.user);

  const numericUserId = useMemo(() => Number(userId), [userId]);

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [stories, setStories] = useState<UserStory[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isBlocked, setIsBlocked] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  const load = async () => {
    if (!Number.isFinite(numericUserId)) {
      setError("Invalid user id.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [profileRes, postsRes, storiesRes] = await Promise.all([
        api.get<UserProfile>(`/users/${numericUserId}`),
        api.get<FeedPost[]>(`/posts/user/${numericUserId}`, { params: { limit: 20, offset: 0 } }),
        api.get<UserStory[]>(`/stories/user/${numericUserId}`),
      ]);
      setProfile(profileRes.data);
      setPosts(postsRes.data);
      setStories(storiesRes.data);

      if (me?.id && numericUserId !== me.id) {
        const [blocksRes, mutesRes] = await Promise.all([
          api.get<Array<{ id: number }>>("/moderation/blocks"),
          api.get<Array<{ id: number }>>("/moderation/mutes"),
        ]);
        setIsBlocked(blocksRes.data.some((u) => u.id === numericUserId));
        setIsMuted(mutesRes.data.some((u) => u.id === numericUserId));
      }
    } catch {
      setError("User profile could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [numericUserId]);

  const toggleBlock = async () => {
    if (!profile || profile.is_me) return;
    setWorking(true);
    setError("");
    try {
      if (isBlocked) {
        await api.delete(`/moderation/block/${profile.id}`);
        setSuccess("User unblocked.");
      } else {
        await api.post(`/moderation/block/${profile.id}`);
        setSuccess("User blocked.");
      }
      setIsBlocked((v) => !v);
      if (!isBlocked) {
        setProfile((current) => (current ? { ...current, is_following: false } : current));
      }
    } catch {
      setError("Block action failed.");
    } finally {
      setWorking(false);
    }
  };

  const toggleMute = async () => {
    if (!profile || profile.is_me) return;
    setWorking(true);
    setError("");
    try {
      if (isMuted) {
        await api.delete(`/moderation/mute/${profile.id}`);
        setSuccess("User unmuted.");
      } else {
        await api.post(`/moderation/mute/${profile.id}`);
        setSuccess("User muted.");
      }
      setIsMuted((v) => !v);
    } catch {
      setError("Mute action failed.");
    } finally {
      setWorking(false);
    }
  };

  const reportUser = async () => {
    if (!profile || profile.is_me) return;
    const reason = window.prompt("Report reason", "abuse")?.trim();
    if (!reason) return;
    setWorking(true);
    setError("");
    try {
      await api.post("/moderation/report", {
        target_type: "user",
        target_id: profile.id,
        reason,
        details: `Reported from profile @${profile.username}`,
      });
      setSuccess("Report submitted.");
    } catch {
      setError("Report action failed.");
    } finally {
      setWorking(false);
    }
  };

  const toggleFollow = async () => {
    if (!profile || profile.is_me) return;
    setWorking(true);
    setError("");
    try {
      const endpoint = profile.is_following ? `/users/${profile.id}/unfollow` : `/users/${profile.id}/follow`;
      await api.post(endpoint);
      setProfile((current) => {
        if (!current) return current;
        return {
          ...current,
          is_following: !current.is_following,
          followers_count: current.is_following ? Math.max(0, current.followers_count - 1) : current.followers_count + 1,
        };
      });
      setSuccess(profile.is_following ? "Unfollowed." : "Followed.");
    } catch (err) {
      const detail = getApiErrorDetail(err);
      if (detail.includes("Already following")) {
        setProfile((current) => (current ? { ...current, is_following: true } : current));
        setSuccess("You are already following this user.");
        return;
      }
      setError(detail || "Follow action failed.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <main className="app-shell social-shell">
      <SocialTopNav title="Creator Profile" subtitle={profile ? `@${profile.username}` : "Loading..."} />

      {error && <p className="error">{error}</p>}
      {success && <p className="success">{success}</p>}

      <section className="social-grid">
        <section className="feed-layout">
          <article className="card post-card" style={{ padding: 0, overflow: "hidden" }}>
            {/* Cover photo */}
            <div
              style={{
                height: 120,
                background: profile?.cover_url
                  ? `url(${profile.cover_url}) center/cover no-repeat`
                  : "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                position: "relative",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  bottom: -36,
                  left: 16,
                  width: 72,
                  height: 72,
                  borderRadius: "50%",
                  border: "3px solid var(--bg-card, #1e1e2e)",
                  overflow: "hidden",
                  background: "#374151",
                }}
              >
                {profile?.avatar_url ? (
                  <img src={profile.avatar_url} alt="avatar" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, color: "#9ca3af" }}>
                    {profile?.username?.[0]?.toUpperCase() ?? "?"}
                  </div>
                )}
              </div>
            </div>

            <div style={{ padding: "46px 16px 16px" }}>
              <h2 style={{ margin: 0 }}>{profile?.username ?? "Unknown user"}<VerificationBadge verified={profile?.is_verified} /></h2>
              <p className="meta" style={{ marginTop: 4 }}>{profile?.email}</p>
              {profile?.bio && <p style={{ marginTop: 8, maxWidth: 400 }}>{profile.bio}</p>}
              <div className="row" style={{ marginTop: 12 }}>
                <span className="tag">posts {profile?.posts_count ?? 0}</span>
                <span className="tag">followers {profile?.followers_count ?? 0}</span>
                <span className="tag">following {profile?.following_count ?? 0}</span>
              </div>
              {profile?.badges && profile.badges.length > 0 && (
                <div className="row" style={{ marginTop: 8 }}>
                  {profile.badges.map((badge) => (
                    <Link key={badge} to={`/tags/${badge}`} className="tag" style={{ opacity: 0.8 }}>
                      #{badge}
                    </Link>
                  ))}
                </div>
              )}
            {profile && !profile.is_me && (
              <div className="row" style={{ marginTop: 12 }}>
                <button onClick={() => void toggleFollow()} disabled={working || isBlocked}>
                  {working ? "Working..." : profile.is_following ? "Unfollow" : "Follow"}
                </button>
                <Link to={`/messages?user=${profile.id}`}>Message</Link>
                <button className="btn-ghost" onClick={() => void toggleMute()} disabled={working}>
                  {isMuted ? "Unmute" : "Mute"}
                </button>
                <button className="btn-danger" onClick={() => void toggleBlock()} disabled={working}>
                  {isBlocked ? "Unblock" : "Block"}
                </button>
                <button className="btn-ghost" onClick={() => void reportUser()} disabled={working}>Report</button>
              </div>
            )}
            {profile?.is_me && (
              <div className="row" style={{ marginTop: 12 }}>
                <Link to="/profile">Open my profile dashboard</Link>
              </div>
            )}
            </div>
          </article>

          <section className="feed-layout">
            <h2>Active Stories</h2>
            {!loading && stories.length === 0 && <p className="card empty-state">No active stories.</p>}
            {stories.length > 0 && (
              <section className="card post-card" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12 }}>
                {stories.map((story) => (
                  <article key={story.id} style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 10, display: "grid", gap: 8 }}>
                    {story.media_url && (
                      <img
                        src={story.media_url}
                        alt="story"
                        style={{ width: "100%", height: 98, objectFit: "cover", borderRadius: 6 }}
                      />
                    )}
                    <p style={{ margin: 0, fontSize: 13 }}>{story.content}</p>
                    <p className="meta" style={{ margin: 0, fontSize: 12 }}>
                      {parseServerDate(story.created_at).toLocaleString()}
                    </p>
                  </article>
                ))}
              </section>
            )}

            <h2>Posts</h2>
            {!loading && posts.length === 0 && <p className="card empty-state">This user has no posts yet.</p>}
            {posts.map((post) => (
              <article key={post.post_id} className="card post-card">
                {post.media_url && (
                  <div className="media-frame" style={{ marginBottom: 10 }}>
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
                )}
                <h3>{post.title}</h3>
                <p style={{ marginTop: 8 }}>{parseMentions(post.content)}</p>
                <p className="meta" style={{ marginTop: 8 }}>
                  {post.created_at ? new Date(post.created_at).toLocaleString() : ""} • likes {post.likes}
                </p>
                <div className="row" style={{ marginTop: 10 }}>
                  <Link to={`/posts/${post.post_id}`}>Open thread</Link>
                </div>
              </article>
            ))}
          </section>
        </section>

        <aside className="feed-layout side-panel">
          <section className="card side-card">
            <h3>Shortcuts</h3>
            <div className="feed-layout" style={{ marginTop: 10 }}>
              <Link to="/">Back to feed</Link>
              {me && <Link to="/profile">My profile</Link>}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
