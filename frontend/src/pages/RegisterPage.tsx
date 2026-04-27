import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const register = useAuthStore((s) => s.register);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  if (isAuthenticated) return <Navigate to="/" replace />;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    try {
      await register(username, email, password);
      navigate("/");
    } catch {
      setErr("Registration failed");
    }
  };

  return (
    <main className="app-shell">
      <section className="card auth-wrap">
        <h1>Register</h1>
        <p className="meta">Create your account and jump into the feed.</p>
        <form onSubmit={onSubmit} className="form-grid">
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" type="email" />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
        <button type="submit">Create account</button>
      </form>
        {err && <p className="error">{err}</p>}
        <p>
          Already have an account? <Link to="/login">Go to login</Link>
        </p>
      </section>
    </main>
  );
}