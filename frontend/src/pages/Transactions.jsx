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
