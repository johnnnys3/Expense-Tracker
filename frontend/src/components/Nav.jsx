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
