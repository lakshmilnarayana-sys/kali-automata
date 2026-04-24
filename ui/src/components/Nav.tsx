import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/",          label: "Builder",   icon: "⚡" },
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/runs",      label: "History",   icon: "🕑" },
];

export function Nav() {
  return (
    <nav className="flex items-center gap-1 border-b border-gray-800 bg-[#0a0c10] px-4 shrink-0">
      {LINKS.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            `flex items-center gap-1.5 px-3 py-2.5 text-[12px] font-medium border-b-2 transition-colors ${
              isActive
                ? "border-blue-500 text-white"
                : "border-transparent text-gray-500 hover:text-gray-300"
            }`
          }
        >
          <span className="text-sm">{icon}</span>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
