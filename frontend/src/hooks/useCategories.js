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
