import { useState } from "react";
import { api } from "../lib/api";

type QuoteRepostModalProps = {
  postId: number;
  postTitle: string;
  onSuccess?: () => void;
  onClose: () => void;
};

export function QuoteRepostModal({
  postId,
  postTitle,
  onSuccess,
  onClose,
}: QuoteRepostModalProps) {
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async () => {
    if (!comment.trim()) {
      setError("Quote comment cannot be empty");
      return;
    }

    try {
      setLoading(true);
      await api.post(`/posts/${postId}/repost`, {
        comment: comment.trim(),
      });

      setComment("");
      onSuccess?.();
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail || "Failed to repost";
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          maxWidth: 400,
          padding: 20,
          borderRadius: 8,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3>Quote Repost</h3>
        <p className="meta" style={{ marginBottom: 16 }}>
          Add your thoughts to "{postTitle}"
        </p>

        <textarea
          value={comment}
          onChange={(e) => {
            setComment(e.target.value);
            setError("");
          }}
          placeholder="Add a comment (max 500 characters)..."
          maxLength={500}
          style={{
            width: "100%",
            minHeight: 100,
            padding: 10,
            borderRadius: 4,
            border: "1px solid var(--border)",
            fontFamily: "inherit",
            fontSize: "inherit",
            marginBottom: 10,
            boxSizing: "border-box",
          }}
        />

        <div style={{ fontSize: 12, color: "var(--meta)", marginBottom: 10 }}>
          {comment.length} / 500
        </div>

        {error && <p style={{ color: "var(--error)", marginBottom: 10 }}>{error}</p>}

        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn-ghost"
            onClick={onClose}
            disabled={loading}
            style={{ flex: 1 }}
          >
            Cancel
          </button>
          <button
            className="btn"
            onClick={() => void onSubmit()}
            disabled={loading || !comment.trim()}
            style={{ flex: 1 }}
          >
            {loading ? "Posting..." : "Quote Repost"}
          </button>
        </div>
      </div>
    </div>
  );
}
