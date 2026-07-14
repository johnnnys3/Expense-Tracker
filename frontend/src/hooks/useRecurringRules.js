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
