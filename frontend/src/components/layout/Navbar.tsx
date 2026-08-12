import { Link, useLocation } from "react-router-dom";
import { Sparkles, Zap, Menu, X, LogOut, LogIn, UserPlus } from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../../contexts/AuthContext";

export function Navbar() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { isAuthenticated, isAdmin, logout, user } = useAuth();

  const publicLinks = [
    { label: "Product", href: "/" },
    { label: "Workflow", href: "/login" },
    { label: "Templates", href: "/templates" },
    { label: "Docs", href: "/docs" },
  ];

  const userLinks = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Builder", href: "/builder" },
    { label: "My Projects", href: "/projects" },
    { label: "My Generated Apps", href: "/generated-apps" },
    { label: "Templates", href: "/templates" },
    { label: "Docs", href: "/docs" },
    { label: "Profile", href: "/profile" },
  ];

  const adminLinks = [
    { label: "Admin Dashboard", href: "/admin" },
    { label: "Users", href: "/admin/users" },
    { label: "All Projects", href: "/admin/projects" },
    { label: "All Generated Apps", href: "/admin/generated-apps" },
    { label: "System", href: "/admin/system" },
    { label: "Models", href: "/admin/models" },
    { label: "Logs", href: "/admin/logs" },
  ];

  const navLinks = !isAuthenticated ? publicLinks : isAdmin ? adminLinks : userLinks;

  const isActive = (href: string) => location.pathname === href;

  const handleLogout = async () => {
    await logout();
    setMobileMenuOpen(false);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-slate-950/80 backdrop-blur-xl">
      <div className="container mx-auto px-6">
        <div className="flex h-16 items-center justify-between">
          <Link to={isAuthenticated ? (isAdmin ? "/admin" : "/dashboard") : "/"} className="flex items-center gap-2 group">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-lg blur-lg opacity-50 group-hover:opacity-75 transition-opacity" />
              <div className="relative bg-gradient-to-r from-cyan-500 to-purple-500 p-2 rounded-lg">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              AI Builder
            </span>
          </Link>

          <div className="hidden lg:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive(link.href)
                    ? "bg-cyan-500/10 text-cyan-400"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="hidden md:flex items-center gap-3">
            {!isAuthenticated ? (
              <>
                <Link to="/login" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-white/5 text-sm font-medium">
                  <LogIn className="w-4 h-4" />
                  Login
                </Link>
                <Link to="/register" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 text-slate-200 hover:bg-white/5 text-sm font-medium">
                  <UserPlus className="w-4 h-4" />
                  Register
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
                >
                  <Zap className="w-4 h-4" />
                  Start Building
                </Link>
              </>
            ) : (
              <>
                {user && (
                  <span className="text-xs text-slate-500 hidden xl:inline">
                    {user.full_name}
                  </span>
                )}
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-white/5 text-sm font-medium"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </button>
                {!isAdmin && (
                  <Link
                    to="/builder"
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
                  >
                    <Zap className="w-4 h-4" />
                    Start Building
                  </Link>
                )}
              </>
            )}
          </div>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            {mobileMenuOpen ? <X className="w-6 h-6 text-white" /> : <Menu className="w-6 h-6 text-white" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="lg:hidden border-t border-white/10 bg-slate-950/95 backdrop-blur-xl"
          >
            <div className="container mx-auto px-6 py-4 space-y-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  to={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`block px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                    isActive(link.href)
                      ? "bg-cyan-500/10 text-cyan-400"
                      : "text-slate-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
              {!isAuthenticated ? (
                <>
                  <Link to="/login" onClick={() => setMobileMenuOpen(false)} className="block px-4 py-3 rounded-lg text-slate-300">
                    Login
                  </Link>
                  <Link to="/register" onClick={() => setMobileMenuOpen(false)} className="block px-4 py-3 rounded-lg text-slate-300">
                    Register
                  </Link>
                  <Link
                    to="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block mt-4 px-4 py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-center font-semibold"
                  >
                    Start Building
                  </Link>
                </>
              ) : (
                <button onClick={handleLogout} className="block w-full text-left px-4 py-3 rounded-lg text-slate-300">
                  Logout
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
