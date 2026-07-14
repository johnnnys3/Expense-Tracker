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
