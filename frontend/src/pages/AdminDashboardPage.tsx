import { useEffect, useState } from "react";
import SocialTopNav from "../components/SocialTopNav";
import VerificationBadge from "../components/VerificationBadge";
import { api } from "../lib/api";

type AdminMetrics = {
  total_users: number;
  verified_users: number;
  total_posts: number;
  open_reports: number;
  total_follows: number;
};

type ReportItem = {
  id: number;
  reason: string;
  details: string;
  status: string;
  reporter_id: number;
  target_user_id: number | null;
  target_post_id: number | null;
  target_comment_id: number | null;
  created_at: string | null;
};

type AdminOverview = {
  metrics: AdminMetrics;
  recent_reports: ReportItem[];
};

type AdminUser = {
  id: number;
  username: string;
  email: string;
  is_verified: boolean;
  is_admin: boolean;
  posts_count: number;
  followers_count: number;
};

export default function AdminDashboardPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [workingId, setWorkingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [userQuery, setUserQuery] = useState("");
  const [verificationFilter, setVerificationFilter] = useState<"all" | "verified" | "unverified">("all");
  const [reportStatusFilter, setReportStatusFilter] = useState<"all" | "open" | "reviewed" | "resolved">("all");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [overviewRes, usersRes] = await Promise.all([
        api.get<AdminOverview>("/admin/overview"),
        api.get<AdminUser[]>("/admin/users"),
      ]);
      setOverview(overviewRes.data);
      setUsers(usersRes.data);
    } catch (err) {
      setError("Admin dashboard could not be loaded. Make sure your account has admin access.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const toggleVerify = async (userId: number) => {
    setWorkingId(userId);
    setError("");
    setSuccess("");
    try {
      const response = await api.post<{ id: number; is_verified: boolean }>(`/admin/users/${userId}/verify`);
      setUsers((current) => current.map((user) => (user.id === userId ? { ...user, is_verified: response.data.is_verified } : user)));
      setSuccess("Verification status updated.");
    } catch {
      setError("Could not update verification status.");
    } finally {
      setWorkingId(null);
    }
  };

  const updateReportStatus = async (reportId: number, status: string) => {
    setWorkingId(reportId);
    setError("");
    setSuccess("");
    try {
      await api.post(`/admin/reports/${reportId}/status`, { status });
      setOverview((current) =>
        current
          ? {
              ...current,
              recent_reports: current.recent_reports.map((report) =>
                report.id === reportId ? { ...report, status } : report,
              ),
            }
          : current,
      );
      setSuccess("Report status updated.");
    } catch {
      setError("Could not update report status.");
    } finally {
      setWorkingId(null);
    }
  };

  const visibleUsers = users.filter((user) => {
    const query = userQuery.trim().toLowerCase();
    const matchesQuery = !query || user.username.toLowerCase().includes(query) || user.email.toLowerCase().includes(query);
    const matchesVerification = verificationFilter === "all"
      || (verificationFilter === "verified" && user.is_verified)
      || (verificationFilter === "unverified" && !user.is_verified);
    return matchesQuery && matchesVerification;
  });

  const visibleReports = (overview?.recent_reports ?? []).filter((report) => {
    return reportStatusFilter === "all" || report.status === reportStatusFilter;
  });

  return (
    <main className="app-shell social-shell">
      <SocialTopNav title="Admin Dashboard" subtitle="Users, verification and moderation overview" />

      {error && <p className="error">{error}</p>}
      {success && <p className="success">{success}</p>}
      {loading && <p className="meta">Loading dashboard...</p>}

      {overview && (
        <section className="social-grid">
          <section className="feed-layout">
            <section className="card post-card">
              <h2 style={{ marginBottom: 12 }}>Platform Metrics</h2>
              <div className="admin-metrics-grid">
                <div className="admin-metric-card">
                  <span className="meta">Users</span>
                  <strong>{overview.metrics.total_users}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="meta">Verified</span>
                  <strong>{overview.metrics.verified_users}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="meta">Posts</span>
                  <strong>{overview.metrics.total_posts}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="meta">Open Reports</span>
                  <strong>{overview.metrics.open_reports}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="meta">Follows</span>
                  <strong>{overview.metrics.total_follows}</strong>
                </div>
              </div>
            </section>

            <section className="card post-card">
              <div className="row-between" style={{ marginBottom: 12 }}>
                <h2>User Verification</h2>
                <button className="btn-ghost" onClick={() => void load()}>Refresh</button>
              </div>
              <div className="row" style={{ marginBottom: 10 }}>
                <input
                  value={userQuery}
                  onChange={(e) => setUserQuery(e.target.value)}
                  placeholder="Search username or email"
                  style={{ flex: 1 }}
                />
                <select
                  value={verificationFilter}
                  onChange={(e) => setVerificationFilter(e.target.value as "all" | "verified" | "unverified")}
                >
                  <option value="all">All users</option>
                  <option value="verified">Verified only</option>
                  <option value="unverified">Unverified only</option>
                </select>
              </div>
              <div className="admin-table">
                {visibleUsers.map((user) => (
                  <div key={user.id} className="admin-table-row">
                    <div>
                      <strong>@{user.username}</strong> <VerificationBadge verified={user.is_verified} compact />
                      <p className="meta">{user.email}</p>
                    </div>
                    <div className="meta">posts {user.posts_count} | followers {user.followers_count}</div>
                    <button disabled={workingId === user.id || user.is_admin} onClick={() => void toggleVerify(user.id)}>
                      {user.is_admin ? "Admin" : user.is_verified ? "Remove verify" : "Verify"}
                    </button>
                  </div>
                ))}
              </div>
            </section>
          </section>

          <aside className="feed-layout side-panel">
            <section className="card side-card">
              <div className="row-between" style={{ marginBottom: 10 }}>
                <h3>Recent Reports</h3>
                <select
                  value={reportStatusFilter}
                  onChange={(e) => setReportStatusFilter(e.target.value as "all" | "open" | "reviewed" | "resolved")}
                >
                  <option value="all">All</option>
                  <option value="open">Open</option>
                  <option value="reviewed">Reviewed</option>
                  <option value="resolved">Resolved</option>
                </select>
              </div>
              <div className="feed-layout moderation-list">
                {visibleReports.length === 0 && <p className="meta">No reports for this filter.</p>}
                {visibleReports.map((report) => (
                  <div key={report.id} className="notification-item">
                    <strong>{report.reason}</strong>
                    <p className="meta" style={{ marginTop: 6 }}>{report.details || "No details provided."}</p>
                    <p className="meta" style={{ marginTop: 6 }}>Status: {report.status}</p>
                    <div className="row" style={{ marginTop: 8 }}>
                      <button className="btn-ghost" disabled={workingId === report.id} onClick={() => void updateReportStatus(report.id, "reviewed")}>
                        Review
                      </button>
                      <button disabled={workingId === report.id} onClick={() => void updateReportStatus(report.id, "resolved")}>
                        Resolve
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </section>
      )}
    </main>
  );
}
