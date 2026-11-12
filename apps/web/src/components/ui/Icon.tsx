const PATHS = {
  overview: "M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z",
  forecast: "M3 17l5-5 4 4 8-8M15 8h5v5",
  planner: "M4 7h16M4 12h10M4 17h6M17 14v6M14 17h6",
  scenarios: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  research: "M6 3h9l5 5v13H6zM14 3v6h6M9 13h8M9 17h6",
  info: "M12 8h.01M11 12h1v5h1M12 3a9 9 0 100 18 9 9 0 000-18z",
  flask: "M9 3h6M10 3v6L4.5 19A1.5 1.5 0 005.8 21h12.4a1.5 1.5 0 001.3-2L14 9V3M7 15h10",
  alert: "M12 9v4M12 17h.01M10.3 3.9L2.4 18a2 2 0 001.7 3h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z",
  check: "M5 12l5 5L20 7",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "M6 6l12 12M18 6L6 18",
  search: "M11 4a7 7 0 100 14 7 7 0 000-14zM20 20l-3.5-3.5",
  download: "M12 4v11M7 10l5 5 5-5M5 20h14",
  refresh: "M20 11a8 8 0 10-2.3 5.7M20 4v7h-7",
  arrow: "M5 12h14M13 6l6 6-6 6",
  database: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
  shield: "M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z",
  reset: "M4 4v6h6M4.5 15a8 8 0 101.9-8.3L4 10",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" className={className}>
      <path d={PATHS[name]} />
    </svg>
  );
}
