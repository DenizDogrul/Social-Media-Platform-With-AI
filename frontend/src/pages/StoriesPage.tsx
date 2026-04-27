import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";

type Story = {
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

export function StoriesPage() {
  const navigate = useNavigate();
  const [stories, setStories] = useState<Story[]>([]);
  const [myStories, setMyStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showComposer, setShowComposer] = useState(false);
  const [formData, setFormData] = useState({ content: "", media_url: "", media_type: "" });
  const [error, setError] = useState("");

  const groupedStories = useMemo(() => {
    const byAuthor = new Map<number, Story[]>();
    for (const item of stories) {
      if (!byAuthor.has(item.author_id)) byAuthor.set(item.author_id, []);
      byAuthor.get(item.author_id)!.push(item);
    }
    return Array.from(byAuthor.entries());
  }, [stories]);

  useEffect(() => {
    const loadStories = async () => {
      try {
        setLoading(true);
        const [storiesRes, myStoriesRes] = await Promise.all([
          api.get<Story[]>("/stories"),
          api.get<Story[]>("/stories/my"),
        ]);
        setStories(storiesRes.data);
        setMyStories(myStoriesRes.data);
      } catch {
        setError("Failed to load stories");
      } finally {
        setLoading(false);
      }
    };
    void loadStories();
  }, []);

  const onCreateStory = async () => {
    if (!formData.content.trim()) {
      setError("Story content cannot be empty");
      return;
    }
    try {
      setCreating(true);
      const res = await api.post<Story>("/stories", {
        content: formData.content,
        media_url: formData.media_url || undefined,
        media_type: formData.media_type || undefined,
      });
      setMyStories((prev) => [res.data, ...prev]);
      setFormData({ content: "", media_url: "", media_type: "" });
      setShowComposer(false);
      setError("");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to create story");
    } finally {
      setCreating(false);
    }
  };

  const onDeleteStory = async (storyId: number) => {
    if (!window.confirm("Delete this story?")) return;
    try {
      await api.delete(`/stories/${storyId}`);
      setMyStories((prev) => prev.filter((s) => s.id !== storyId));
    } catch {
      setError("Failed to delete story");
    }
  };

  const formatTime = (dateStr: string) => {
    const date = parseServerDate(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.max(0, Math.floor(diffMs / (1000 * 60)));
    const diffHours = Math.floor(diffMins / 60);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  const formatExpiry = (expiresStr: string) => {
    const expires = parseServerDate(expiresStr);
    const now = new Date();
    const diffMs = Math.max(0, expires.getTime() - now.getTime());
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    if (diffHours > 0) return `${diffHours}h ${diffMins}m left`;
    return `${diffMins}m left`;
  };

  return (
    <section className="social-grid single-col">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 20,
          paddingBottom: 14,
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="btn-ghost" onClick={() => navigate("/")}>Back</button>
          <h1 style={{ margin: 0, fontSize: 28 }}>Stories</h1>
        </div>
        <button className="btn" onClick={() => setShowComposer((v) => !v)}>
          {showComposer ? "Close" : "New Story"}
        </button>
      </div>

      <section className="feed-layout" style={{ width: "100%" }}>
        {showComposer && (
          <section className="card post-card" style={{ marginBottom: 10 }}>
            <h3 style={{ marginTop: 0, marginBottom: 12 }}>Create a Story</h3>
            <textarea
              value={formData.content}
              onChange={(e) => {
                setFormData({ ...formData, content: e.target.value });
                setError("");
              }}
              placeholder="What is on your mind? (stories disappear after 24 hours)"
              maxLength={500}
              style={{
                width: "100%",
                minHeight: 92,
                padding: 12,
                borderRadius: 8,
                border: "1px solid var(--line)",
                fontFamily: "inherit",
                fontSize: "inherit",
                marginBottom: 10,
                boxSizing: "border-box",
              }}
            />
            <div style={{ fontSize: 12, color: "var(--meta)", marginBottom: 10 }}>
              {formData.content.length} / 500
            </div>
            <input
              type="url"
              value={formData.media_url}
              onChange={(e) => setFormData({ ...formData, media_url: e.target.value })}
              placeholder="Media URL (optional)"
              style={{
                width: "100%",
                padding: 8,
                marginBottom: 8,
                borderRadius: 6,
                border: "1px solid var(--line)",
                boxSizing: "border-box",
                fontSize: "inherit",
              }}
            />
            <select
              value={formData.media_type}
              onChange={(e) => setFormData({ ...formData, media_type: e.target.value })}
              style={{
                width: "100%",
                padding: 8,
                marginBottom: 10,
                borderRadius: 6,
                border: "1px solid var(--line)",
                fontSize: "inherit",
              }}
            >
              <option value="">No media</option>
              <option value="image">Image</option>
              <option value="video">Video</option>
            </select>
            {error && <p style={{ color: "var(--error)", margin: "0 0 10px 0" }}>{error}</p>}
            <button className="btn" onClick={() => void onCreateStory()} disabled={creating} style={{ width: "100%" }}>
              {creating ? "Posting..." : "Post Story"}
            </button>
          </section>
        )}

        <section className="card post-card">
          <h2 style={{ marginTop: 0, marginBottom: 12 }}>My Stories ({myStories.length})</h2>
          {myStories.length === 0 && <p className="meta">No stories yet.</p>}
          {myStories.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12 }}>
              {myStories.map((story) => (
                <div
                  key={story.id}
                  style={{
                    padding: 12,
                    borderRadius: 10,
                    border: "1px solid var(--line)",
                    backgroundColor: "var(--paper)",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                  }}
                >
                  {story.media_url && (
                    <img
                      src={story.media_url}
                      alt="story"
                      style={{ width: "100%", height: 96, borderRadius: 6, objectFit: "cover" }}
                    />
                  )}
                  <p style={{ margin: 0, fontSize: 13, flex: 1 }}>{story.content}</p>
                  <div style={{ fontSize: 11, color: "var(--meta)" }}>
                    <div>{formatTime(story.created_at)}</div>
                    <div style={{ marginTop: 3 }}>Expires: {formatExpiry(story.expires_at)}</div>
                  </div>
                  <button className="btn-ghost" onClick={() => void onDeleteStory(story.id)} style={{ fontSize: 12 }}>
                    Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="card post-card">
          <h2 style={{ marginTop: 0, marginBottom: 12 }}>From Following</h2>
          {loading && <p className="meta">Loading stories...</p>}
          {!loading && groupedStories.length === 0 && <p className="meta">No stories from people you follow yet.</p>}
          {!loading && groupedStories.length > 0 && (
            <div style={{ display: "grid", gap: 16 }}>
              {groupedStories.map(([authorId, authorStories]) => (
                <div key={authorId}>
                  <h4 style={{ margin: "0 0 8px 0", fontSize: 14 }}>
                    @{authorStories[0]?.author_username || "unknown"}
                  </h4>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12 }}>
                    {authorStories.map((story) => (
                      <div
                        key={story.id}
                        style={{
                          padding: 12,
                          borderRadius: 10,
                          border: "1px solid var(--line)",
                          backgroundColor: "var(--paper)",
                          display: "flex",
                          flexDirection: "column",
                          gap: 8,
                          minHeight: 165,
                        }}
                      >
                        {story.media_url && (
                          <img
                            src={story.media_url}
                            alt="story"
                            style={{ width: "100%", height: 96, borderRadius: 6, objectFit: "cover" }}
                          />
                        )}
                        <p style={{ margin: 0, fontSize: 13, flex: 1 }}>{story.content}</p>
                        <span className="meta" style={{ fontSize: 11 }}>
                          {formatTime(story.created_at)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </section>
    </section>
  );
}
