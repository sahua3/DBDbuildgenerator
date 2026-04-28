import { Outlet, NavLink } from "react-router-dom";
import { Swords, BookMarked, Users, FlameKindling, Skull } from "lucide-react";
import clsx from "clsx";

const navItems = [
  { to: "/builder", label: "Builder", icon: Swords },
  { to: "/shrine", label: "Shrine", icon: FlameKindling },
  { to: "/roster", label: "Roster", icon: Users },
  { to: "/saved", label: "Saved", icon: BookMarked },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Atmospheric top glow */}
      <div className="fixed top-0 left-0 right-0 h-64 pointer-events-none z-0"
        style={{ background: "radial-gradient(ellipse at 50% -20%, rgba(196,20,20,0.08) 0%, transparent 70%)" }}
      />

      {/* Header */}
      <header className="relative z-10 border-b border-[var(--color-border)]"
        style={{ background: "rgba(13,15,20,0.95)", backdropFilter: "blur(12px)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <Skull size={22} className="text-blood-500" />
              <div className="absolute inset-0 blur-md bg-blood-600 opacity-40 rounded-full" />
            </div>
            <div>
              <span className="font-display text-2xl tracking-widest text-white">
                DEAD BUILD
              </span>
              <span className="font-display text-2xl tracking-widest text-blood-500">
                .GG
              </span>
            </div>
          </div>

          {/* Nav */}
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-2 px-4 py-2 text-sm font-body font-medium transition-all duration-200 nav-link",
                    isActive
                      ? "text-white active"
                      : "text-ash-400 hover:text-white"
                  )
                }
              >
                <Icon size={15} />
                <span className="hidden sm:block">{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="relative z-10 flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[var(--color-border)] py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-ash-600 text-xs font-mono">
            Not affiliated with Behaviour Interactive.
          </p>
          <p className="text-ash-600 text-xs font-mono">
            Perk data via Nightlight.gg · Shrine via dbd.tricky.lol
          </p>
        </div>
      </footer>
    </div>
  );
}
