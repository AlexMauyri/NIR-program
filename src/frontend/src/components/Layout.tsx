import { NavLink, Outlet } from "react-router-dom";
import "./Layout.css";

export default function Layout() {
  return (
    <>
      <nav className="top-nav">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Главная
        </NavLink>
        <NavLink to="/metrics" className={({ isActive }) => (isActive ? "active" : "")}>
          Метрики
        </NavLink>
      </nav>
      <main className="page-content">
        <Outlet />
      </main>
    </>
  );
}
