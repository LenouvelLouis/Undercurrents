import { MotionConfig } from "motion/react";
import { useEffect, useState } from "react";
import CommandPalette from "./app/CommandPalette";
import Header from "./app/Header";
import LiquidField from "./app/LiquidField";
import Menu from "./app/Menu";
import MeltFilter from "./app/MeltFilter";
import { findRoute } from "./app/routes";
import Shell from "./app/Shell";
import { useHashRoute } from "./app/useHashRoute";
import { api } from "./lib/api";
import type { Overview } from "./lib/types";
import Landing from "./pages/Landing";

export default function App() {
  const { parts, navigate } = useHashRoute();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [palette, setPalette] = useState(false);
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    api.overview().then(setOverview).catch(() => {});
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setMenu(false);
        setPalette((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const route = findRoute(parts[0], parts[1]);

  useEffect(() => {
    document.title = route ? `${route.code} ${route.title} · Undercurrents` : "Undercurrents";
    if (!route && parts.length > 0) navigate("/");
    setMenu(false);
  }, [route, parts.length, navigate]);

  return (
    <MotionConfig reducedMotion="user">
      <MeltFilter />
      <LiquidField mood={menu ? "menu" : route ? route.side : "home"} />
      <Header
        current={route}
        menuOpen={menu}
        onMenu={() => setMenu((m) => !m)}
        onSearch={() => setPalette(true)}
        onHome={() => navigate("/")}
      />
      {route ? <Shell route={route} navigate={navigate} /> : <Landing overview={overview} navigate={navigate} />}
      <Menu open={menu} current={route} onClose={() => setMenu(false)} onSearch={() => setPalette(true)} />
      <CommandPalette open={palette} onClose={() => setPalette(false)} navigate={navigate} />
    </MotionConfig>
  );
}
