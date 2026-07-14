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
