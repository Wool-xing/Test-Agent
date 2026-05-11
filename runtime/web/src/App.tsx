import { Outlet, NavLink } from "react-router-dom";
import { Beaker, Upload, BookOpen } from "lucide-react";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b" role="banner">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <Beaker className="w-5 h-5" aria-hidden="true" />
            <span>Test-Agent · Runtime</span>
            <span className="text-xs text-slate-500">v1.2.0-alpha</span>
          </h1>
          <nav aria-label="Primary">
            <ul className="flex gap-4 text-sm">
              <li>
                <NavLink to="/" end className={({ isActive }) => (isActive ? "font-semibold" : "")}>
                  <Upload className="inline w-4 h-4 mr-1" aria-hidden="true" />
                  上传
                </NavLink>
              </li>
              <li>
                <NavLink to="/catalog" className={({ isActive }) => (isActive ? "font-semibold" : "")}>
                  <BookOpen className="inline w-4 h-4 mr-1" aria-hidden="true" />
                  目录
                </NavLink>
              </li>
            </ul>
          </nav>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6 flex-1" role="main">
        <Outlet />
      </main>
      <footer className="border-t mt-auto" role="contentinfo">
        <div className="container mx-auto px-4 py-3 text-xs text-slate-500">
          Test-Agent runtime · charter §16 MCP · §21 L2 · MIT License
        </div>
      </footer>
    </div>
  );
}
