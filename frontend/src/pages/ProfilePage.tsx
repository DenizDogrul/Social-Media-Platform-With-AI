import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import SocialTopNav from "../components/SocialTopNav";
import VerificationBadge from "../components/VerificationBadge";
import { api } from "../lib/api";
import { useAuthStore } from "../store/auth";

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
  is_private?: boolean;
  is_verified?: boolean;
  allow_dms_from?: string;
};

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

export default function ProfilePage() {
  const me = useAuthStore((s) => s.user);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingPostId, setEditingPostId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editMediaFile, setEditMediaFile] = useState<File | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // profile edit state
  const [editingProfile, setEditingProfile] = useState(false);
  const [editBio, setEditBio] = useState("");
  const [editIsPrivate, setEditIsPrivate] = useState(false);
  const [editAllowDmsFrom, setEditAllowDmsFrom] = useState("everyone");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [profileWorking, setProfileWorking] = useState(false);

  useEffect(() => {
    const run = async () => {
      if (!me?.id) {
        // If no user id yet, don't error - auth store is still loading
        return;
      }
      setLoading(true);
      setError("");
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);

        const [profileRes, postsRes] = await Promise.all([
          api.get<UserProfile>(`/users/${me.id}`, { signal: controller.signal as any }),
          api.get<FeedPost[]>(`/posts/user/${me.id}`, { 
            params: { limit: 20, offset: 0 },
            signal: controller.signal as any,
          }),
        ]);

        clearTimeout(timeout);
        setProfile(profileRes.data);
        setPosts(postsRes.data);
      } catch (err: any) {
        console.error("Profile error:", err);
        if (err.name === "AbortError") {
          setError("Profile loading timed out. Please refresh.");
        } else {
          const errorMsg = err?.response?.data?.detail || err?.message || "Profile could not be loaded.";
          setError(errorMsg);
        }
      } finally {
        setLoading(false);
      }
    };

    void run();
  }, [me?.id]);

  const startEdit = (post: FeedPost) => {
    setEditingPostId(post.post_id);
    setEditTitle(post.title);
    setEditContent(post.content);
    setEditMediaFile(null);
  };

  const cancelEdit = () => {
    setEditingPostId(null);
    setEditTitle("");
    setEditContent("");
    setEditMediaFile(null);
  };

  const startProfileEdit = () => {
    setEditBio(profile?.bio ?? "");
    setEditIsPrivate(profile?.is_private ?? false);
    setEditAllowDmsFrom((profile as any)?.allow_dms_from ?? "everyone");
    setAvatarFile(null);
    setCoverFile(null);
    setEditingProfile(true);
  };

  const saveProfile = async () => {
    setProfileWorking(true);
    setError("");
    setSuccess("");
    try {
      let avatar_url: string | undefined;
      let cover_url: string | undefined;

      if (avatarFile) {
        const form = new FormData();
        form.append("media", avatarFile);
        const res = await api.post<{ media_url: string }>("/posts/upload-media", form);
        avatar_url = res.data.media_url;
      }
      if (coverFile) {
        const form = new FormData();
        form.append("media", coverFile);
        const res = await api.post<{ media_url: string }>("/posts/upload-media", form);
        cover_url = res.data.media_url;
      }

      await api.patch("/users/me", {
        bio: editBio.trim() || null,
        is_private: editIsPrivate,
        allow_dms_from: editAllowDmsFrom,
        ...(avatar_url ? { avatar_url } : {}),
        ...(cover_url ? { cover_url } : {}),
      });

      setProfile((prev) =>
        prev
          ? {
              ...prev,
              bio: editBio.trim() || null,
              avatar_url: avatar_url ?? prev.avatar_url,
              cover_url: cover_url ?? prev.cover_url,
              is_private: editIsPrivate,
            }
          : prev
      );
      setSuccess("Profile updated.");
      setEditingProfile(false);
    } catch {
      setError("Profile update failed.");
    } finally {
      setProfileWorking(false);
    }
  };

  const saveEdit = async (postId: number) => {
    setWorking(true);
    setError("");
    try {
      let media_url: string | undefined;
      let thumbnail_url: string | undefined;
      let media_type: "image" | "video" | undefined;
      if (editMediaFile) {
        const form = new FormData();
        form.append("media", editMediaFile);
        const uploadRes = await api.post<{ media_url: string; thumbnail_url?: string | null; media_type: "image" | "video" }>("/posts/upload-media", form);
        media_url = uploadRes.data.media_url;
        thumbnail_url = uploadRes.data.thumbnail_url ?? undefined;
        media_type = uploadRes.data.media_type;
      }

      await api.patch(`/posts/${postId}`, {
        title: editTitle.trim(),
        content: editContent.trim(),
        ...(media_url && media_type ? { media_url, thumbnail_url, media_type } : {}),
      });

      setPosts((current) =>
        current.map((post) =>
          post.post_id === postId
            ? {
                ...post,
                title: editTitle.trim(),
                content: editContent.trim(),
                media_url: media_url ?? post.media_url,
                thumbnail_url: thumbnail_url ?? post.thumbnail_url,
                media_type: media_type ?? post.media_type,
              }
            : post
        )
      );

      cancelEdit();
    } catch {
      setError("Post update failed.");
    } finally {
      setWorking(false);
    }
  };

  const deletePost = async (postId: number) => {
    setWorking(true);
    setError("");
    try {
      await api.delete(`/posts/${postId}`);
      setPosts((current) => current.filter((post) => post.post_id !== postId));
    } catch {
      setError("Post delete failed.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <main className="app-shell social-shell">
      <SocialTopNav title="My Profile" subtitle={me ? `@${me.username}` : undefined} />

      {error && <p className="error">{error}</p>}
      {success && <p className="success">{success}</p>}

      <section className="social-grid">
        <section className="feed-layout">
          <article className="card post-card" style={{ padding: 0, overflow: "hidden" }}>
            {/* Cover photo */}
            <div
              style={{
                height: 140,
                background: profile?.cover_url
                  ? `url(${profile.cover_url}) center/cover no-repeat`
                  : "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                position: "relative",
              }}
            >
              {/* Avatar */}
              <div
                style={{
                  position: "absolute",
                  bottom: -40,
                  left: 20,
                  width: 80,
                  height: 80,
                  borderRadius: "50%",
                  border: "3px solid var(--bg-card, #1e1e2e)",
                  overflow: "hidden",
                  background: "#374151",
                }}
              >
                {profile?.avatar_url ? (
                  <img src={profile.avatar_url} alt="avatar" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 32, color: "#9ca3af" }}>
                    {profile?.username?.[0]?.toUpperCase() ?? "?"}
                  </div>
                )}
              </div>
            </div>

            <div style={{ padding: "52px 20px 20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h2 style={{ margin: 0 }}>{profile?.username ?? "Loading..."}<VerificationBadge verified={profile?.is_verified} /></h2>
                  <p className="meta" style={{ marginTop: 4 }}>{profile?.email}</p>
                  {profile?.bio && <p style={{ marginTop: 8, maxWidth: 420 }}>{profile.bio}</p>}
                </div>
                <button className="btn-ghost" style={{ flexShrink: 0 }} onClick={startProfileEdit}>Edit Profile</button>
              </div>
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
            </div>
          </article>

          {editingProfile && (
            <article className="card post-card">
              <h3 style={{ marginBottom: 12 }}>Edit Profile</h3>
              <div className="form-grid">
                <label>
                  <span className="meta">Bio</span>
                  <textarea
                    value={editBio}
                    onChange={(e) => setEditBio(e.target.value)}
                    rows={3}
                    maxLength={300}
                    placeholder="Tell something about yourself..."
                  />
                </label>
                <label>
                  <span className="meta">Privacy</span>
                  <select value={editIsPrivate ? "private" : "public"} onChange={(e) => setEditIsPrivate(e.target.value === "private")}>
                    <option value="public">Public</option>
                    <option value="private">Private</option>
                  </select>
                </label>
                <label>
                  <span className="meta">Allow DMs from</span>
                  <select value={editAllowDmsFrom} onChange={(e) => setEditAllowDmsFrom(e.target.value)}>
                    <option value="everyone">Everyone</option>
                    <option value="followers">Followers only</option>
                    <option value="none">Nobody</option>
                  </select>
                </label>
                <label>
                  <span className="meta">Avatar image</span>
                  <input type="file" accept="image/*" onChange={(e) => setAvatarFile(e.target.files?.[0] ?? null)} />
                </label>
                <label>
                  <span className="meta">Cover photo</span>
                  <input type="file" accept="image/*" onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)} />
                </label>
                <div className="row">
                  <button disabled={profileWorking} onClick={() => void saveProfile()}>
                    {profileWorking ? "Saving..." : "Save"}
                  </button>
                  <button className="btn-ghost" disabled={profileWorking} onClick={() => setEditingProfile(false)}>Cancel</button>
                </div>
              </div>
            </article>
          )}

          <section className="feed-layout">
            <h2>My Posts</h2>
            {!loading && posts.length === 0 && <p className="card empty-state">No posts yet.</p>}
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

                {editingPostId === post.post_id ? (
                  <div className="form-grid">
                    <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                    <textarea value={editContent} onChange={(e) => setEditContent(e.target.value)} rows={4} />
                    <input type="file" accept="image/*,video/*" onChange={(e) => setEditMediaFile(e.target.files?.[0] ?? null)} />
                    <div className="row">
                      <button disabled={working} onClick={() => void saveEdit(post.post_id)}>Save</button>
                      <button className="btn-ghost" disabled={working} onClick={cancelEdit}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <h3>{post.title}</h3>
                    <p style={{ marginTop: 8 }}>{parseMentions(post.content)}</p>
                  </>
                )}
                <p className="meta" style={{ marginTop: 8 }}>
                  {post.created_at ? new Date(post.created_at).toLocaleString() : ""} • likes {post.likes}
                </p>
                <div className="row" style={{ marginTop: 10 }}>
                  <Link to={`/posts/${post.post_id}`}>Open thread</Link>
                  {editingPostId !== post.post_id && (
                    <button className="btn-ghost" onClick={() => startEdit(post)}>Edit</button>
                  )}
                  <button className="btn-danger" disabled={working} onClick={() => void deletePost(post.post_id)}>Delete</button>
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
              <Link to="/register">Create another account</Link>
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
