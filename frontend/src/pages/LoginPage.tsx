import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  if (isAuthenticated) return <Navigate to="/" replace />;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    try {
      await login(username, password);
      navigate("/");
    } catch (error: unknown) {
      const maybeResponse = (error as { response?: { data?: { detail?: string } | string } })?.response;
      const data = maybeResponse?.data;
      if (typeof data === "string" && data.trim()) {
        setErr(data);
      } else if (typeof data === "object" && data?.detail) {
        setErr(data.detail);
      } else {
        setErr("Invalid username or password");
      }
    }
  };

  return (
    <main className="app-shell">
      <section className="card auth-wrap">
        <h1>Login</h1>
        <p className="meta">Welcome back. Sign in to continue.</p>
        <form onSubmit={onSubmit} className="form-grid">
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username or email" />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
        <button type="submit">Login</button>
      </form>
        {err && <p className="error">{err}</p>}
        <p>
          No account yet? <Link to="/register">Create one</Link>
        </p>
      </section>
    </main>
  );
}