import { Link, NavLink } from "react-router-dom";
import { Logo, useLogout } from "./RequireOwner";

export default function TopBar() {
  const logout = useLogout();
  return (
    <header className="topbar">
      <Link to="/" className="logo">
        <Logo /> <span className="logo-text">Papertrail</span>
      </Link>
      <nav className="nav">
        <NavLink to="/" end>
          Ask
        </NavLink>
        <NavLink to="/library">Library</NavLink>
        <NavLink to="/history">History</NavLink>
      </nav>
      <button className="link-btn" onClick={logout}>
        Log out
      </button>
    </header>
  );
}
