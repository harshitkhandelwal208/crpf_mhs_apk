"use client";

import {
  LayoutDashboard, Users, ShieldAlert, BellRing, BarChart3,
  ScrollText, Settings, LogOut, ChevronRight,
  Languages,
} from "lucide-react";
import { Logo } from "@/components/shared/logo";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useApp } from "@/lib/store";
import { ADMIN_NAV, ROLE_LABELS } from "@/lib/constants";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { View } from "@/lib/store";
import { translate } from "@/lib/i18n";
import { motion } from "framer-motion";
import { BackButton } from "@/components/shared/back-button";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard, Users, ShieldAlert, BellRing, BarChart3, ScrollText, Settings,
};

export function AdminShell({ children }: { children: React.ReactNode }) {
  const { user, view, navigate, mobileNavOpen, setMobileNavOpen, language, setLanguage } = useApp();

  const Sidebar = (
    <div className="flex h-full flex-col bg-[#0B192C] text-white">
      <div className="flex h-16 items-center border-b border-white/10 px-5">
        <button onClick={() => navigate("admin")} className="transition-transform hover:scale-105 active:scale-95 duration-200">
            <span className="inline-flex items-center gap-2.5">
            <Logo size={28} />
            <span className="font-semibold tracking-tight text-white">CRPF MHS <span className="text-blue-400">Admin</span></span>
          </span>
        </button>
      </div>
      <nav className="flex-1 space-y-1.5 overflow-y-auto calm-scroll px-3 py-6 relative">
        {ADMIN_NAV.map((item) => {
          const Icon = ICONS[item.icon ?? ""] ?? LayoutDashboard;
          const activeView = view === item.key || (view === "admin-person" && item.key === "admin-personnel");
          return (
            <button
              key={item.key}
              onClick={() => navigate(item.key as View)}
              className={cn(
                "group relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-300",
                activeView ? "text-white" : "text-white/60 hover:text-white hover:bg-white/5"
              )}
            >
              {activeView && (
                <motion.div
                  layoutId="sidebar-active-indicator"
                  className="absolute inset-0 rounded-lg bg-white/10"
                  initial={false}
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
              {activeView && (
                <motion.div
                  layoutId="sidebar-active-pill"
                  className="absolute left-0 top-1/2 -mt-2.5 h-5 w-1 rounded-r-full bg-[#FF9933] shadow-[0_0_8px_rgba(255,153,51,0.6)]"
                  initial={false}
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
              <Icon className={cn("h-4 w-4 shrink-0 relative z-10 transition-transform duration-300", activeView ? "scale-110 text-white" : "group-hover:scale-110")} />
              <span className="relative z-10">{translate(item.label, language)}</span>
            </button>
          );
        })}
      </nav>
      <div className="border-t border-white/10 p-3">
        <button onClick={() => navigate("dashboard")} className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-white/5">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-700 text-white font-semibold shadow-inner">
            {(user?.name?.[0] ?? "A").toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{user?.name}</p>
            <p className="truncate text-xs text-white/60">{user ? ROLE_LABELS[user.role] : ""}</p>
          </div>
          <ChevronRight className="h-4 w-4 text-white/50" />
        </button>
        <Button
          variant="ghost" size="sm" className="mt-1 w-full justify-start text-white/60 hover:text-white hover:bg-white/5"
          onClick={async () => { await api.post("/api/auth/logout"); useApp.getState().setUser(null); useApp.getState().navigate("home"); }}
        >
          <LogOut className="mr-2 h-4 w-4" /> {translate("Sign out", language)}
        </Button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 lg:block">
        {Sidebar}
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/15 bg-[#1d256f] px-4 text-white shadow-sm backdrop-blur sm:px-6">
          <div className="flex items-center gap-3">
            <BackButton />
          </div>
          <div className="flex items-center gap-1">
            <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
              <SheetTrigger asChild>
                <button
                  type="button"
                  aria-label={translate("Open menu", language)}
                  aria-haspopup="dialog"
                  className="flex h-11 w-11 items-center justify-center rounded-lg border border-white/20 bg-transparent transition hover:border-white/40 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80 lg:hidden"
                >
                  <span className="flex flex-col gap-[5px]" aria-hidden="true">
                    <span className="block h-[3px] w-[22px] rounded-full bg-[#FF9933]" />
                    <span className="block h-[3px] w-[22px] rounded-full bg-white/80" />
                    <span className="block h-[3px] w-[22px] rounded-full bg-[#138808]" />
                  </span>
                </button>
              </SheetTrigger>
              <SheetContent side="left" className="w-72 p-0">{Sidebar}</SheetContent>
            </Sheet>
            <Button variant="ghost" size="sm" onClick={() => setLanguage(language === "en" ? "hi" : "en")} aria-label={translate("Toggle script", language)} className="text-white hover:bg-white/10 hover:text-white">
              <Languages className="mr-1.5 h-4 w-4" /> {language === "en" ? "हिंदी" : "English"}
            </Button>
          </div>
        </header>
        <main className="min-h-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
