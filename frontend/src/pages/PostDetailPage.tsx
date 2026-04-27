import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
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
  author: {
    id: number;
    username: string;
    is_verified?: boolean;
  };
  tags: string[];
  likes: number;
  is_liked: boolean;
  created_at: string | null;
  media_url?: string | null;
  thumbnail_url?: string | null;
  media_type?: "image" | "video" | null;
};

type CommentItem = {
  id: number;
  content: string;
  user_id: number;
  author_username: string;
  post_id: number;
  parent_id: number | null;
  likes: number;
  is_liked: boolean;
  created_at: string;
};

type LocationState = {
  post?: FeedPost;
};

export default function PostDetailPage() {
  const { postId } = useParams();
  const location = useLocation();
  const { post: statePost } = (location.state as LocationState | null) ?? {};
  const user = useAuthStore((s) => s.user);

  const numericPostId = useMemo(() => Number(postId), [postId]);

  const [post, setPost] = useState<FeedPost | null>(statePost ?? null);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [commentText, setCommentText] = useState("");
  const [loadingPost, setLoadingPost] = useState(true);
  const [loadingComments, setLoadingComments] = useState(true);
  const [posting, setPosting] = useState(false);
  const [deletingCommentId, setDeletingCommentId] = useState<number | null>(null);
  const [replyingToId, setReplyingToId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState("");
  const [likingCommentId, setLikingCommentId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const getErrorMessage = (fallback: string, err: unknown) => {
    if (typeof err === "object" && err && "response" in err) {
      const response = (err as { response?: { data?: { detail?: string } | string } }).response;
      const data = response?.data;
      if (typeof data === "string" && data.trim()) return data;
      if (typeof data === "object" && data?.detail) return data.detail;
    }
    return fallback;
  };

  const loadPost = async () => {
    setError("");
    setLoadingPost(true);
    try {
      if (!Number.isFinite(numericPostId)) {
        throw new Error("Invalid post id");
      }
      const response = await api.get<FeedPost>(`/posts/${numericPostId}`);
      setPost(response.data);
    } catch (err) {
      setError(getErrorMessage("Post could not be loaded.", err));
    } finally {
      setLoadingPost(false);
    }
  };

  const loadComments = async () => {
    setError("");
    setLoadingComments(true);
    try {
      if (!Number.isFinite(numericPostId)) {
        throw new Error("Invalid post id");
      }
      const response = await api.get<CommentItem[]>(`/comments/posts/${numericPostId}`);
      setComments(response.data);
    } catch (err) {
      setError(getErrorMessage("Comments could not be loaded.", err));
    } finally {
      setLoadingComments(false);
    }
  };

  useEffect(() => {
    void loadPost();
    void loadComments();
  }, [numericPostId]);

  const onSubmitComment = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const content = commentText.trim();
    if (!content) {
      setError("Comment cannot be empty.");
      return;
    }

    setPosting(true);
    try {
      await api.post(`/comments/posts/${numericPostId}`, { content });
      setCommentText("");
      await loadComments();
    } catch (err) {
      setError(getErrorMessage("Comment publish failed.", err));
    } finally {
      setPosting(false);
    }
  };

  const onDeleteComment = async (commentId: number) => {
    setError("");
    setDeletingCommentId(commentId);
    try {
      await api.delete(`/comments/${commentId}`);
      setComments((current) => current.filter((comment) => comment.id !== commentId));
    } catch (err) {
      setError(getErrorMessage("Comment delete failed.", err));
    } finally {
      setDeletingCommentId(null);
    }
  };

  const onLikeComment = async (comment: CommentItem) => {
    if (likingCommentId !== null) return;
    setLikingCommentId(comment.id);
    try {
      if (comment.is_liked) {
        await api.delete(`/comments/${comment.id}/like`);
        setComments((prev) => prev.map((c) => c.id === comment.id ? { ...c, likes: c.likes - 1, is_liked: false } : c));
      } else {
        await api.post(`/comments/${comment.id}/like`);
        setComments((prev) => prev.map((c) => c.id === comment.id ? { ...c, likes: c.likes + 1, is_liked: true } : c));
      }
    } catch {
      setError("Like action failed.");
    } finally {
      setLikingCommentId(null);
    }
  };

  const onSubmitReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || !replyingToId) return;
    setPosting(true);
    setError("");
    try {
      const res = await api.post<CommentItem>(`/comments/posts/${numericPostId}`, {
        content: replyText.trim(),
        parent_id: replyingToId,
      });
      setComments((prev) => [...prev, res.data]);
      setReplyText("");
      setReplyingToId(null);
    } catch (err) {
      setError(getErrorMessage("Reply failed.", err));
    } finally {
      setPosting(false);
    }
  };

  const topLevelComments = comments.filter((c) => !c.parent_id);
  const commentReplies = new Map<number, CommentItem[]>();
  for (const c of comments) {
    if (c.parent_id) {
      const arr = commentReplies.get(c.parent_id) ?? [];
      arr.push(c);
      commentReplies.set(c.parent_id, arr);
    }
  }

  return (
    <main className="app-shell social-shell">
      <SocialTopNav title="Post Detail" subtitle={user ? `Viewing as @${user.username}` : undefined} />
      <div className="row"><Link to="/">Back to feed</Link></div>

      <article className="card post-card" style={{ animationDelay: "60ms" }}>
        {post?.media_url && (
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
                <img className="uploaded-media" src={post.media_url} alt={post.title} loading="lazy" />
              </a>
            )}
          </div>
        )}
        <h2>{post?.title ?? `Post #${postId}`}</h2>
        <p style={{ marginTop: 8 }}>{parseMentions(post?.content ?? "Post content is not available on this page yet.")}</p>
        {post?.author?.username && (
          <p className="meta" style={{ marginTop: 10 }}>
            by <Link to={`/users/${post.author.id}`}>@{post.author.username}</Link>
            <VerificationBadge verified={post.author.is_verified} compact />
            {post.created_at ? ` • ${new Date(post.created_at).toLocaleString()}` : ""}
          </p>
        )}
        {post?.tags?.length ? (
          <div className="tag-list" style={{ marginTop: 10 }}>
            {post.tags.map((tag) => (
              <span key={tag} className="tag">#{tag}</span>
            ))}
          </div>
        ) : null}
        {loadingPost && <p className="meta" style={{ marginTop: 10 }}>Refreshing post details...</p>}
      </article>

      <form onSubmit={onSubmitComment} className="card composer form-grid">
        <h2>Add Comment</h2>
        <textarea
          value={commentText}
          onChange={(e) => setCommentText(e.target.value)}
          placeholder="Write your comment"
          rows={4}
        />
        <button type="submit" disabled={posting}>
          {posting ? "Posting..." : "Post Comment"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      <section className="feed-layout">
        <h2>Comments ({comments.length})</h2>
        {loadingComments && <p>Loading comments...</p>}
        {!loadingComments && topLevelComments.length === 0 && <p>No comments yet.</p>}

        {!loadingComments && topLevelComments.map((comment) => (
          <div key={comment.id}>
            <article className="card comment-card">
              <p className="meta" style={{ marginBottom: 4, fontWeight: 600 }}>@{comment.author_username}</p>
              <p style={{ marginBottom: 8 }}>{comment.content}</p>
              <div className="row-between">
                <p className="meta">{new Date(comment.created_at).toLocaleString()}</p>
                <div className="row">
                  <button
                    className="btn-ghost"
                    style={{ padding: "5px 10px", fontSize: 13 }}
                    disabled={likingCommentId === comment.id}
                    onClick={() => void onLikeComment(comment)}
                  >
                    {comment.is_liked ? "♥" : "♡"} {comment.likes}
                  </button>
                  {user && (
                    <button
                      className="btn-ghost"
                      style={{ padding: "5px 10px", fontSize: 13 }}
                      onClick={() => setReplyingToId(replyingToId === comment.id ? null : comment.id)}
                    >
                      ↩ Reply
                    </button>
                  )}
                  {user && comment.user_id === user.id && (
                    <button
                      className="btn-danger"
                      style={{ padding: "5px 10px", fontSize: 13 }}
                      disabled={deletingCommentId === comment.id}
                      onClick={() => void onDeleteComment(comment.id)}
                    >
                      {deletingCommentId === comment.id ? "..." : "Delete"}
                    </button>
                  )}
                </div>
              </div>
            </article>

            {(commentReplies.get(comment.id) ?? []).map((reply) => (
              <article key={reply.id} className="card comment-card" style={{ marginLeft: 28, borderLeft: "3px solid var(--brand)" }}>
                <p className="meta" style={{ marginBottom: 4, fontWeight: 600 }}>↩ @{reply.author_username}</p>
                <p style={{ marginBottom: 8 }}>{reply.content}</p>
                <div className="row-between">
                  <p className="meta">{new Date(reply.created_at).toLocaleString()}</p>
                  <div className="row">
                    <button
                      className="btn-ghost"
                      style={{ padding: "5px 10px", fontSize: 13 }}
                      disabled={likingCommentId === reply.id}
                      onClick={() => void onLikeComment(reply)}
                    >
                      {reply.is_liked ? "♥" : "♡"} {reply.likes}
                    </button>
                    {user && reply.user_id === user.id && (
                      <button
                        className="btn-danger"
                        style={{ padding: "5px 10px", fontSize: 13 }}
                        disabled={deletingCommentId === reply.id}
                        onClick={() => void onDeleteComment(reply.id)}
                      >
                        {deletingCommentId === reply.id ? "..." : "Delete"}
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))}

            {replyingToId === comment.id && (
              <form onSubmit={(e) => void onSubmitReply(e)} className="row" style={{ marginLeft: 28, marginTop: 4 }}>
                <input
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder={`Reply to @${comment.author_username}...`}
                  style={{ flex: 1 }}
                  autoFocus
                />
                <button type="submit" disabled={posting}>Reply</button>
                <button type="button" className="btn-ghost" onClick={() => { setReplyingToId(null); setReplyText(""); }}>Cancel</button>
              </form>
            )}
          </div>
        ))}
      </section>
    </main>
  );
}
