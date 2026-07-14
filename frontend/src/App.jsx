import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Categories from "./pages/Categories";
import RecurringRules from "./pages/RecurringRules";
import ProtectedRoute from "./components/ProtectedRoute";
import Nav from "./components/Nav";
import { useAuth } from "./hooks/useAuth";
import "./App.css";

function Layout({ children, onLogout }) {
  return (
    <>
      <Nav onLogout={onLogout} />
      <main>{children}</main>
    </>
  );
}

export default function App() {
  const { logout } = useAuth();

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout onLogout={logout}>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/transactions"
          element={
            <ProtectedRoute>
              <Layout onLogout={logout}>
                <Transactions />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/categories"
          element={
            <ProtectedRoute>
              <Layout onLogout={logout}>
                <Categories />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/recurring-rules"
          element={
            <ProtectedRoute>
              <Layout onLogout={logout}>
                <RecurringRules />
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
