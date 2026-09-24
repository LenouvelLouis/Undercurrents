import { useCallback, useEffect, useState } from "react";

// Hash routing, deliberately tiny: the portal is a static bundle served behind the API,
// so a hash keeps deep links and the back button working without any server rewrite.
function read(): string[] {
  return window.location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
}

export function useHashRoute() {
  const [parts, setParts] = useState<string[]>(read);

  useEffect(() => {
    const onChange = () => setParts(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const navigate = useCallback((path: string) => {
    const next = `#${path.startsWith("/") ? path : `/${path}`}`;
    if (window.location.hash !== next) window.location.hash = next;
  }, []);

  return { parts, navigate };
}
