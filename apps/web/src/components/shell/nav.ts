import type { IconName } from "../ui/Icon";

export interface NavItem {
  href: "/" | "/forecasts" | "/planner" | "/scenarios" | "/research";
  label: string;
  description: string;
  icon: IconName;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Executive Overview", description: "Research findings at a glance", icon: "overview" },
  { href: "/forecasts", label: "Forecast Explorer", description: "Saved validation forecasts per series", icon: "forecast" },
  { href: "/planner", label: "Inventory Planner", description: "Run a bounded hypothetical simulation", icon: "planner" },
  { href: "/scenarios", label: "Scenario Comparison", description: "The 17-scenario Phase 5 study", icon: "scenarios" },
  { href: "/research", label: "Research & Methodology", description: "Protocol, audit, limitations", icon: "research" },
];

export function isActive(pathname: string, href: NavItem["href"]): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
