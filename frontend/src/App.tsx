import { Link, NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ApplicationDetail from "./pages/ApplicationDetail";
import ProfilePage from "./pages/Profile";
import Analytics from "./pages/Analytics";
import Paused from "./pages/Paused";
import PausedDetail from "./pages/PausedDetail";
import Postings from "./pages/Postings";
import Settings from "./pages/Settings";

const linkClass =
  "px-3 py-1.5 rounded text-sm hover:bg-zinc-800 transition-colors";
const activeClass = "bg-zinc-800 text-white";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-6 sticky top-0 bg-ink/95 backdrop-blur z-10">
        <Link to="/" className="font-semibold">job-tracker</Link>
        <nav className="flex items-center gap-1 text-zinc-300">
          <NavLink to="/" end className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ""}`}>
            Dashboard
          </NavLink>
          <NavLink to="/postings" className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ""}`}>
            Postings
          </NavLink>
          <NavLink to="/paused" className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ""}`}>
            Paused
          </NavLink>
          <NavLink to="/analytics" className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ""}`}>
            Analytics
          </NavLink>
          <NavLink to="/profile" className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ""}`}>
            Profile
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => `${linkClass} ${isActive ? activeClass : ""}`}>
            Settings
          </NavLink>
        </nav>
      </header>
      <main className="flex-1 px-6 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/applications/:id" element={<ApplicationDetail />} />
          <Route path="/postings" element={<Postings />} />
          <Route path="/paused" element={<Paused />} />
          <Route path="/paused/:id" element={<PausedDetail />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
