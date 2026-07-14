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
