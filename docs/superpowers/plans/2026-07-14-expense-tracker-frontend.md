# Expense Tracker Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add category edit/delete endpoints to the Flask API, enable CORS, and build a React (Vite) frontend covering auth, dashboard, transactions, categories, and recurring rules.

**Architecture:** Two small backend endpoints follow the existing route/test patterns in `app/routes/categories.py`. The frontend is a separate `frontend/` Vite React app that talks to the Flask API directly (via `flask-cors` in dev), with a single `apiFetch` wrapper for auth headers/error handling and one hook per resource — no global store or query library.

**Tech Stack:** Flask, SQLAlchemy, pytest (backend, existing); React 18, Vite, react-router-dom (frontend, new).

---

## Part 1: Backend

### Task 1: Category rename (PATCH /categories/<id>)

**Files:**
- Modify: `app/routes/categories.py`
- Test: `tests/test_categories.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_categories.py`:

```python
def test_rename_category_requires_auth(client):
    resp = client.patch("/categories/1", json={"name": "New"})
    assert resp.status_code == 401


def test_rename_category(client, auth_headers):
    headers = auth_headers()
    created = client.post("/categories", headers=headers, json={"name": "Groceries"})
    cat_id = created.get_json()["id"]

    resp = client.patch(f"/categories/{cat_id}", headers=headers, json={"name": "Food"})
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Food"


def test_rename_category_not_owned_returns_404(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    created = client.post("/categories", headers=headers_a, json={"name": "Rent"})
    cat_id = created.get_json()["id"]

    resp = client.patch(f"/categories/{cat_id}", headers=headers_b, json={"name": "X"})
    assert resp.status_code == 404


def test_rename_category_to_duplicate_name_returns_409(client, auth_headers):
    headers = auth_headers()
    client.post("/categories", headers=headers, json={"name": "Rent"})
    created = client.post("/categories", headers=headers, json={"name": "Utilities"})
    cat_id = created.get_json()["id"]

    resp = client.patch(f"/categories/{cat_id}", headers=headers, json={"name": "Rent"})
    assert resp.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_categories.py -k rename -v`
Expected: FAIL (404 route not found — no PATCH handler yet)

- [ ] **Step 3: Implement the endpoint**

In `app/routes/categories.py`, add after `list_categories`:

```python
@categories_bp.route("/<int:category_id>", methods=["PATCH"])
@jwt_required()
def rename_category(category_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if error := require_fields(data, "name"):
        return error

    with SessionLocal() as session:
        category = session.get(Category, category_id)
        if category is None or category.user_id != user_id:
            return jsonify({"error": "not found"}), 404

        existing = session.execute(
            select(Category).where(
                Category.user_id == user_id,
                Category.name == data["name"],
                Category.id != category_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return jsonify({"error": "category already exists"}), 409

        category.name = data["name"]
        session.commit()
        return jsonify({"id": category.id, "name": category.name})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_categories.py -k rename -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/routes/categories.py tests/test_categories.py
git commit -m "Add PATCH /categories/<id> to rename a category"
```

### Task 2: Category delete (DELETE /categories/<id>)

**Files:**
- Modify: `app/routes/categories.py`
- Test: `tests/test_categories.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_categories.py`:

```python
def test_delete_category_requires_auth(client):
    resp = client.delete("/categories/1")
    assert resp.status_code == 401


def test_delete_category(client, auth_headers):
    headers = auth_headers()
    created = client.post("/categories", headers=headers, json={"name": "Groceries"})
    cat_id = created.get_json()["id"]

    resp = client.delete(f"/categories/{cat_id}", headers=headers)
    assert resp.status_code == 204

    resp = client.get("/categories", headers=headers)
    assert resp.get_json() == []


def test_delete_category_not_owned_returns_404(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    created = client.post("/categories", headers=headers_a, json={"name": "Rent"})
    cat_id = created.get_json()["id"]

    resp = client.delete(f"/categories/{cat_id}", headers=headers_b)
    assert resp.status_code == 404


def test_delete_category_used_by_recurring_rule_returns_409(client, auth_headers):
    headers = auth_headers()
    created = client.post("/categories", headers=headers, json={"name": "Rent"})
    cat_id = created.get_json()["id"]
    client.post(
        "/recurring-rules",
        headers=headers,
        json={
            "category_id": cat_id,
            "amount": "10.00",
            "frequency": "monthly",
            "start_date": "2026-01-01",
        },
    )

    resp = client.delete(f"/categories/{cat_id}", headers=headers)
    assert resp.status_code == 409
    assert "recurring rule" in resp.get_json()["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_categories.py -k delete_category -v`
Expected: FAIL (404 route not found — no DELETE handler yet)

- [ ] **Step 3: Implement the endpoint**

In `app/routes/categories.py`, add the `IntegrityError` import at the top:

```python
from sqlalchemy.exc import IntegrityError
```

Then add after `rename_category`:

```python
@categories_bp.route("/<int:category_id>", methods=["DELETE"])
@jwt_required()
def delete_category(category_id):
    user_id = int(get_jwt_identity())

    with SessionLocal() as session:
        category = session.get(Category, category_id)
        if category is None or category.user_id != user_id:
            return jsonify({"error": "not found"}), 404

        session.delete(category)
        try:
            session.commit()
        except IntegrityError:
            # RecurringRule.category_id is ON DELETE RESTRICT, so the DB
            # blocks this instead of leaving a rule pointing at nothing.
            session.rollback()
            return jsonify({"error": "category is used by a recurring rule"}), 409

        return "", 204
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_categories.py -v`
Expected: PASS (all tests in file pass)

- [ ] **Step 5: Commit**

```bash
git add app/routes/categories.py tests/test_categories.py
git commit -m "Add DELETE /categories/<id> with RESTRICT-conflict handling"
```

### Task 3: Enable CORS for the frontend dev origin

**Files:**
- Modify: `requirements.txt`
- Modify: `app/__init__.py`

- [ ] **Step 1: Add the dependency**

Append to `requirements.txt`:

```
Flask-Cors==5.0.0
```

Run: `pip install Flask-Cors==5.0.0`

- [ ] **Step 2: Wire it into the app factory**

In `app/__init__.py`, add the import at the top:

```python
from flask_cors import CORS
```

And inside `create_app`, right after `JWTManager(app)`:

```python
    # Allows the Vite dev server (different origin/port) to call this API
    # directly in development.
    CORS(app, origins=["http://localhost:5173"])
```

- [ ] **Step 3: Verify the app still boots**

Run: `pytest -v`
Expected: all existing tests still PASS (CORS doesn't affect server-side test client calls, this just confirms nothing broke on import)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt app/__init__.py
git commit -m "Enable CORS for the Vite dev origin"
```

---

## Part 2: Frontend

### Task 4: Scaffold the Vite React app

**Files:**
- Create: `frontend/` (via Vite scaffold)

- [ ] **Step 1: Scaffold the project**

Run from the repo root:

```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install react-router-dom
```

- [ ] **Step 2: Verify it builds and runs**

Run: `npm run build`
Expected: `build` completes with no errors, `frontend/dist/` created

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend
git commit -m "Scaffold Vite React frontend"
```

### Task 5: API client and auth hook

**Files:**
- Create: `frontend/src/api.js`
- Create: `frontend/src/hooks/useAuth.js`

- [ ] **Step 1: Write the API client**

Create `frontend/src/api.js`:

```javascript
const BASE_URL = "http://localhost:5000";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new ApiError("session expired", 401);
  }

  if (response.status === 204) {
    return null;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(body?.error ?? "request failed", response.status);
  }

  return body;
}
```

- [ ] **Step 2: Write the auth hook**

Create `frontend/src/hooks/useAuth.js`:

```javascript
import { useCallback, useState } from "react";
import { apiFetch } from "../api";

export function useAuth() {
  const [token, setToken] = useState(localStorage.getItem("token"));

  const login = useCallback(async (email, password) => {
    const body = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("token", body.access_token);
    setToken(body.access_token);
  }, []);

  const register = useCallback(async (email, password) => {
    const body = await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("token", body.access_token);
    setToken(body.access_token);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
  }, []);

  return { token, login, register, logout };
}
```

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api.js frontend/src/hooks/useAuth.js
git commit -m "Add API client and auth hook"
```

### Task 6: Routing skeleton and Login/Register page

**Files:**
- Modify: `frontend/src/main.jsx`
- Modify: `frontend/src/App.jsx`
- Create: `frontend/src/pages/Login.jsx`
- Create: `frontend/src/components/ProtectedRoute.jsx`
- Create: `frontend/src/components/Nav.jsx`

- [ ] **Step 1: Write the Login/Register page**

Create `frontend/src/pages/Login.jsx`:

```javascript
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="auth-page">
      <h1>{mode === "login" ? "Log in" : "Register"}</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">{mode === "login" ? "Log in" : "Register"}</button>
      </form>
      <button
        type="button"
        className="link-button"
        onClick={() => setMode(mode === "login" ? "register" : "login")}
      >
        {mode === "login" ? "Need an account? Register" : "Have an account? Log in"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Write the protected route wrapper**

Create `frontend/src/components/ProtectedRoute.jsx`:

```javascript
import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
```

- [ ] **Step 3: Write the nav bar**

Create `frontend/src/components/Nav.jsx`:

```javascript
import { NavLink, useNavigate } from "react-router-dom";

export default function Nav({ onLogout }) {
  const navigate = useNavigate();

  function handleLogout() {
    onLogout();
    navigate("/login");
  }

  return (
    <nav className="nav">
      <NavLink to="/">Dashboard</NavLink>
      <NavLink to="/transactions">Transactions</NavLink>
      <NavLink to="/categories">Categories</NavLink>
      <NavLink to="/recurring-rules">Recurring Rules</NavLink>
      <button onClick={handleLogout}>Log out</button>
    </nav>
  );
}
```

- [ ] **Step 4: Wire up routing in App.jsx**

Replace the contents of `frontend/src/App.jsx`:

```javascript
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
```

- [ ] **Step 5: Simplify main.jsx**

Replace the contents of `frontend/src/main.jsx`:

```javascript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

Note: `App.jsx` references `Dashboard`, `Transactions`, `Categories`, `RecurringRules` pages that don't exist yet — this will not build until Tasks 7-10 add them. That's expected; the next tasks add them immediately.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx frontend/src/main.jsx frontend/src/pages/Login.jsx frontend/src/components
git commit -m "Add routing skeleton, login/register page, and nav"
```

### Task 7: Categories hook and page

**Files:**
- Create: `frontend/src/hooks/useCategories.js`
- Create: `frontend/src/pages/Categories.jsx`

- [ ] **Step 1: Write the categories hook**

Create `frontend/src/hooks/useCategories.js`:

```javascript
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../api";

export function useCategories() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const data = await apiFetch("/categories");
    setCategories(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function createCategory(name) {
    await apiFetch("/categories", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    await refresh();
  }

  async function renameCategory(id, name) {
    await apiFetch(`/categories/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    });
    await refresh();
  }

  async function deleteCategory(id) {
    await apiFetch(`/categories/${id}`, { method: "DELETE" });
    await refresh();
  }

  return { categories, loading, createCategory, renameCategory, deleteCategory };
}
```

- [ ] **Step 2: Write the categories page**

Create `frontend/src/pages/Categories.jsx`:

```javascript
import { useState } from "react";
import { useCategories } from "../hooks/useCategories";

function CategoryRow({ category, onRename, onDelete }) {
  const [name, setName] = useState(category.name);
  const [error, setError] = useState(null);

  async function handleBlur() {
    if (name === category.name) return;
    try {
      setError(null);
      await onRename(category.id, name);
    } catch (err) {
      setError(err.message);
      setName(category.name);
    }
  }

  async function handleDelete() {
    try {
      setError(null);
      await onDelete(category.id);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <li className="category-row">
      <input value={name} onChange={(e) => setName(e.target.value)} onBlur={handleBlur} />
      <button onClick={handleDelete}>Delete</button>
      {error && <span className="error">{error}</span>}
    </li>
  );
}

export default function Categories() {
  const { categories, loading, createCategory, renameCategory, deleteCategory } =
    useCategories();
  const [newName, setNewName] = useState("");
  const [error, setError] = useState(null);

  async function handleCreate(event) {
    event.preventDefault();
    try {
      setError(null);
      await createCategory(newName);
      setNewName("");
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <p>Loading...</p>;

  return (
    <section>
      <h1>Categories</h1>
      <form onSubmit={handleCreate}>
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New category"
          required
        />
        <button type="submit">Add</button>
      </form>
      {error && <p className="error">{error}</p>}
      <ul>
        {categories.map((category) => (
          <CategoryRow
            key={category.id}
            category={category}
            onRename={renameCategory}
            onDelete={deleteCategory}
          />
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npm run build`
Expected: still fails (Transactions/Dashboard/RecurringRules pages missing) — confirm the error is only about those, not Categories

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useCategories.js frontend/src/pages/Categories.jsx
git commit -m "Add categories hook and page"
```

### Task 8: Transactions hook and page

**Files:**
- Create: `frontend/src/hooks/useTransactions.js`
- Create: `frontend/src/pages/Transactions.jsx`

- [ ] **Step 1: Write the transactions hook**

Create `frontend/src/hooks/useTransactions.js`:

```javascript
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../api";

export function useTransactions({ month, categoryId, page = 1, limit = 20 } = {}) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (month) params.set("month", month);
    if (categoryId) params.set("category_id", categoryId);
    params.set("page", page);
    params.set("limit", limit);

    const data = await apiFetch(`/transactions?${params.toString()}`);
    setTransactions(data);
    setLoading(false);
  }, [month, categoryId, page, limit]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function createTransaction(input) {
    await apiFetch("/transactions", {
      method: "POST",
      body: JSON.stringify(input),
    });
    await refresh();
  }

  async function updateTransaction(id, input) {
    await apiFetch(`/transactions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
    await refresh();
  }

  async function deleteTransaction(id) {
    await apiFetch(`/transactions/${id}`, { method: "DELETE" });
    await refresh();
  }

  return {
    transactions,
    loading,
    refresh,
    createTransaction,
    updateTransaction,
    deleteTransaction,
  };
}
```

- [ ] **Step 2: Write the transactions page**

Create `frontend/src/pages/Transactions.jsx`:

```javascript
import { useState } from "react";
import { useCategories } from "../hooks/useCategories";
import { useTransactions } from "../hooks/useTransactions";

export default function Transactions() {
  const [month, setMonth] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [page, setPage] = useState(1);
  const { categories } = useCategories();
  const {
    transactions,
    loading,
    createTransaction,
    updateTransaction,
    deleteTransaction,
  } = useTransactions({ month: month || undefined, categoryId: categoryId || undefined, page });

  const [form, setForm] = useState({ category_id: "", amount: "", occurred_at: "", description: "" });
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    try {
      setError(null);
      const input = {
        category_id: Number(form.category_id),
        amount: form.amount,
        occurred_at: form.occurred_at,
        description: form.description || undefined,
      };
      if (editingId) {
        await updateTransaction(editingId, input);
      } else {
        await createTransaction(input);
      }
      setForm({ category_id: "", amount: "", occurred_at: "", description: "" });
      setEditingId(null);
    } catch (err) {
      setError(err.message);
    }
  }

  function startEdit(transaction) {
    setEditingId(transaction.id);
    setForm({
      category_id: String(transaction.category_id ?? ""),
      amount: transaction.amount,
      occurred_at: transaction.occurred_at,
      description: transaction.description ?? "",
    });
  }

  async function handleDelete(id) {
    try {
      setError(null);
      await deleteTransaction(id);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h1>Transactions</h1>

      <div className="filters">
        <label>
          Month
          <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
        </label>
        <label>
          Category
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">All</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <form onSubmit={handleSubmit}>
        <select
          value={form.category_id}
          onChange={(e) => setForm({ ...form, category_id: e.target.value })}
          required
        >
          <option value="">Category</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input
          type="number"
          step="0.01"
          placeholder="Amount"
          value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })}
          required
        />
        <input
          type="date"
          value={form.occurred_at}
          onChange={(e) => setForm({ ...form, occurred_at: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="Description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <button type="submit">{editingId ? "Save" : "Add"}</button>
        {editingId && (
          <button
            type="button"
            onClick={() => {
              setEditingId(null);
              setForm({ category_id: "", amount: "", occurred_at: "", description: "" });
            }}
          >
            Cancel
          </button>
        )}
      </form>
      {error && <p className="error">{error}</p>}

      {loading ? (
        <p>Loading...</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Category</th>
              <th>Amount</th>
              <th>Description</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((t) => (
              <tr key={t.id}>
                <td>{t.occurred_at}</td>
                <td>{categories.find((c) => c.id === t.category_id)?.name ?? "—"}</td>
                <td>{t.amount}</td>
                <td>{t.description}</td>
                <td>
                  <button onClick={() => startEdit(t)}>Edit</button>
                  <button onClick={() => handleDelete(t.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="pagination">
        <button disabled={page === 1} onClick={() => setPage(page - 1)}>
          Previous
        </button>
        <span>Page {page}</span>
        <button disabled={transactions.length === 0} onClick={() => setPage(page + 1)}>
          Next
        </button>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npm run build`
Expected: still fails (Dashboard/RecurringRules missing) — confirm error is only about those two

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useTransactions.js frontend/src/pages/Transactions.jsx
git commit -m "Add transactions hook and page"
```

### Task 9: Recurring rules hook and page

**Files:**
- Create: `frontend/src/hooks/useRecurringRules.js`
- Create: `frontend/src/pages/RecurringRules.jsx`

- [ ] **Step 1: Write the recurring rules hook**

Create `frontend/src/hooks/useRecurringRules.js`:

```javascript
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../api";

export function useRecurringRules() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const data = await apiFetch("/recurring-rules");
    setRules(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function createRule(input) {
    await apiFetch("/recurring-rules", {
      method: "POST",
      body: JSON.stringify(input),
    });
    await refresh();
  }

  async function updateRule(id, input) {
    await apiFetch(`/recurring-rules/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
    await refresh();
  }

  async function deleteRule(id) {
    await apiFetch(`/recurring-rules/${id}`, { method: "DELETE" });
    await refresh();
  }

  return { rules, loading, createRule, updateRule, deleteRule };
}
```

- [ ] **Step 2: Write the recurring rules page**

Create `frontend/src/pages/RecurringRules.jsx`:

```javascript
import { useState } from "react";
import { useCategories } from "../hooks/useCategories";
import { useRecurringRules } from "../hooks/useRecurringRules";

export default function RecurringRules() {
  const { categories } = useCategories();
  const { rules, loading, createRule, updateRule, deleteRule } = useRecurringRules();
  const [form, setForm] = useState({
    category_id: "",
    amount: "",
    frequency: "monthly",
    start_date: "",
    end_date: "",
  });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    try {
      setError(null);
      const input = {
        category_id: Number(form.category_id),
        amount: form.amount,
        frequency: form.frequency,
        start_date: form.start_date,
        end_date: form.end_date || null,
      };
      if (editingId) {
        await updateRule(editingId, input);
      } else {
        await createRule(input);
      }
      setEditingId(null);
      setForm({ category_id: "", amount: "", frequency: "monthly", start_date: "", end_date: "" });
    } catch (err) {
      setError(err.message);
    }
  }

  function startEdit(rule) {
    setEditingId(rule.id);
    setForm({
      category_id: String(rule.category_id),
      amount: rule.amount,
      frequency: rule.frequency,
      start_date: rule.start_date,
      end_date: rule.end_date ?? "",
    });
  }

  async function handleDelete(id) {
    try {
      setError(null);
      await deleteRule(id);
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <p>Loading...</p>;

  return (
    <section>
      <h1>Recurring Rules</h1>

      <form onSubmit={handleSubmit}>
        <select
          value={form.category_id}
          onChange={(e) => setForm({ ...form, category_id: e.target.value })}
          required
        >
          <option value="">Category</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input
          type="number"
          step="0.01"
          placeholder="Amount"
          value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })}
          required
        />
        <select
          value={form.frequency}
          onChange={(e) => setForm({ ...form, frequency: e.target.value })}
        >
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
        <input
          type="date"
          value={form.start_date}
          onChange={(e) => setForm({ ...form, start_date: e.target.value })}
          required
        />
        <input
          type="date"
          value={form.end_date}
          onChange={(e) => setForm({ ...form, end_date: e.target.value })}
          placeholder="End date (optional)"
        />
        <button type="submit">{editingId ? "Save" : "Add"}</button>
      </form>
      {error && <p className="error">{error}</p>}

      <ul>
        {rules.map((rule) => (
          <li key={rule.id}>
            {categories.find((c) => c.id === rule.category_id)?.name ?? "—"} — {rule.amount} (
            {rule.frequency}) from {rule.start_date}
            {rule.end_date ? ` to ${rule.end_date}` : ""}
            <button onClick={() => startEdit(rule)}>Edit</button>
            <button onClick={() => handleDelete(rule.id)}>Delete</button>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npm run build`
Expected: still fails (Dashboard missing) — confirm error is only about Dashboard

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useRecurringRules.js frontend/src/pages/RecurringRules.jsx
git commit -m "Add recurring rules hook and page"
```

### Task 10: Dashboard page

**Files:**
- Create: `frontend/src/pages/Dashboard.jsx`

- [ ] **Step 1: Write the dashboard page**

Current month is computed once as `YYYY-MM`. The chart is a plain CSS bar list (width % of the max category total) — no charting library needed for a handful of bars.

Create `frontend/src/pages/Dashboard.jsx`:

```javascript
import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import { useTransactions } from "../hooks/useTransactions";

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function Dashboard() {
  const month = currentMonth();
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const { transactions: recent } = useTransactions({ month, limit: 5 });

  useEffect(() => {
    apiFetch(`/transactions/summary?month=${month}`).then((data) => {
      setSummary(data);
      setLoading(false);
    });
  }, [month]);

  const total = summary.reduce((sum, row) => sum + Number(row.total), 0);
  const max = Math.max(1, ...summary.map((row) => Number(row.total)));

  return (
    <section>
      <h1>Dashboard — {month}</h1>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <>
          <p className="total">Total spend: {total.toFixed(2)}</p>
          <ul className="bar-chart">
            {summary.map((row) => (
              <li key={row.category_id}>
                <span className="bar-label">{row.category_name}</span>
                <span
                  className="bar"
                  style={{ width: `${(Number(row.total) / max) * 100}%` }}
                />
                <span className="bar-value">{row.total}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      <h2>Recent transactions</h2>
      <ul>
        {recent.map((t) => (
          <li key={t.id}>
            {t.occurred_at} — {t.amount} — {t.description}
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 2: Verify the full app builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors — all five pages now exist

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.jsx
git commit -m "Add dashboard page"
```

### Task 11: Minimalist editorial styling

**Files:**
- Modify: `frontend/src/index.css`
- Modify/Delete: `frontend/src/App.css`

- [ ] **Step 1: Replace the global stylesheet**

Replace the contents of `frontend/src/index.css`:

```css
:root {
  --ink: #1a1a1a;
  --paper: #faf8f4;
  --line: #e0ddd6;
  --accent: #7a6a53;
  --error: #b3261e;
  font-family: "Georgia", "Iowan Old Style", serif;
  color: var(--ink);
  background: var(--paper);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

main {
  max-width: 720px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

h1 {
  font-weight: 400;
  font-size: 1.75rem;
  border-bottom: 1px solid var(--line);
  padding-bottom: 0.5rem;
}

.nav {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--line);
  font-size: 0.9rem;
}

.nav a {
  color: var(--ink);
  text-decoration: none;
}

.nav a.active {
  color: var(--accent);
  text-decoration: underline;
}

form {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin: 1rem 0;
}

input,
select,
button {
  font-family: inherit;
  font-size: 0.95rem;
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--line);
  background: white;
  color: var(--ink);
}

button {
  cursor: pointer;
  background: var(--ink);
  color: var(--paper);
  border: none;
}

.link-button {
  background: none;
  color: var(--accent);
  text-decoration: underline;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

th,
td {
  text-align: left;
  padding: 0.5rem;
  border-bottom: 1px solid var(--line);
  font-size: 0.9rem;
}

.error {
  color: var(--error);
  font-size: 0.85rem;
}

.bar-chart {
  list-style: none;
  padding: 0;
}

.bar-chart li {
  display: grid;
  grid-template-columns: 120px 1fr 60px;
  align-items: center;
  gap: 0.5rem;
  margin: 0.4rem 0;
}

.bar {
  height: 0.8rem;
  background: var(--accent);
}

.auth-page {
  max-width: 360px;
  margin: 4rem auto;
}

.auth-page form {
  flex-direction: column;
}
```

- [ ] **Step 2: Remove the unused Vite starter stylesheet**

`App.jsx` imports `./App.css` — replace its contents with an empty file (keep the import working, no starter styles):

```css
```

Write this empty content to `frontend/src/App.css`.

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/index.css frontend/src/App.css
git commit -m "Apply minimalist editorial styling"
```

### Task 12: End-to-end smoke test

**Files:** none (manual verification)

- [ ] **Step 1: Start the backend**

Run in one terminal: `flask --app run.py run` (or however `run.py` is normally started — check `README.md` for the exact command used in this repo)
Expected: server listening on port 5000

- [ ] **Step 2: Start the frontend**

Run in another terminal: `cd frontend && npm run dev`
Expected: Vite dev server on `http://localhost:5173`

- [ ] **Step 3: Walk the golden path in a browser**

1. Open `http://localhost:5173` → redirected to `/login`
2. Register a new account → redirected to Dashboard (shows "Total spend: 0.00", empty recent list)
3. Go to Categories → add "Groceries" → rename it to "Food" inline → confirm it saves
4. Go to Transactions → add a transaction in category "Food" → confirm it appears in the table and the month filter works
5. Go to Dashboard → confirm the bar chart and total now reflect the new transaction
6. Go to Recurring Rules → add a monthly rule → confirm it lists; delete the "Food" category and confirm the delete is blocked with the inline 409 message ("category is used by a recurring rule")
7. Delete the recurring rule, then delete the category again → confirms it now succeeds
8. Log out → confirm redirect to `/login` and that `/transactions` redirects to `/login` when visited directly while logged out

- [ ] **Step 4: Note results**

Confirm no console errors in the browser dev tools during the walkthrough above.

---

## Self-Review Notes

- **Spec coverage:** All 5 pages, the `apiFetch` wrapper, `useAuth`, per-resource hooks, CORS, and both new category endpoints are each covered by a task. Historical trend charts and websockets were explicitly out of scope in the spec and are not included here.
- **Placeholder scan:** No TBDs; every step has full file contents or exact commands.
- **Type/name consistency:** Hook return names (`createCategory`, `renameCategory`, `deleteCategory`, `createTransaction`, `updateTransaction`, `deleteTransaction`, `createRule`, `updateRule`, `deleteRule`) match what the pages call. `apiFetch` signature (`path, options`) is used consistently across all hooks.
