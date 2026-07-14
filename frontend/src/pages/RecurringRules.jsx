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
