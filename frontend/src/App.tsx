import { Navigate, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import FeedPage from "./pages/FeedPage";
import LoginPage from "./pages/LoginPage";
import MessagesPage from "./pages/MessagesPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { StoriesPage } from "./pages/StoriesPage";
import ProfilePage from "./pages/ProfilePage";
import PostDetailPage from "./pages/PostDetailPage";
import RegisterPage from "./pages/RegisterPage";
import SavedPostsPage from "./pages/SavedPostsPage";
import SearchPage from "./pages/SearchPage";
import TagPage from "./pages/TagPage";
import UserProfilePage from "./pages/UserProfilePage";
import { useAuthStore } from "./store/auth";

export default function App() {
  const [hydrationDone, setHydrationDone] = useState(false);

  useEffect(() => {
    const run = async () => {
      try {
        // Timeout hydration after 5 seconds
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error("Hydration timeout")), 5000)
        );
        await Promise.race([useAuthStore.getState().hydrate(), timeoutPromise]);
      } catch (err) {
        console.error("Hydration failed:", err);
      } finally {
        setHydrationDone(true);
      }
    };
    void run();
  }, []);

  if (!hydrationDone) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "var(--bg)" }}>
        <p style={{ color: "var(--ink)", fontSize: 18 }}>Loading...</p>
      </div>
    );
  }
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AdminDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <FeedPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/messages"
        element={
          <ProtectedRoute>
            <MessagesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/posts/:postId"
        element={
          <ProtectedRoute>
            <PostDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/saved"
        element={
          <ProtectedRoute>
            <SavedPostsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedRoute>
            <SearchPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/notifications"
        element={
          <ProtectedRoute>
            <NotificationsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/stories"
        element={
          <ProtectedRoute>
            <StoriesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tags/:tagName"
        element={
          <ProtectedRoute>
            <TagPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/users/:userId"
        element={
          <ProtectedRoute>
            <UserProfilePage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
