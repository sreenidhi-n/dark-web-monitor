"use client";

import type { ThreatCategory } from "@/lib/types";

const CATEGORIES: { value: ThreatCategory; label: string; color: string }[] = [
  { value: "general",     label: "General",     color: "bg-gray-700 text-gray-300" },
  { value: "narcotics",   label: "Narcotics",   color: "bg-yellow-900 text-yellow-300" },
  { value: "weapons",     label: "Weapons",     color: "bg-orange-900 text-orange-300" },
  { value: "trafficking", label: "Trafficking", color: "bg-red-900 text-red-300" },
  { value: "csam",        label: "CSAM",        color: "bg-red-950 text-red-200 font-bold" },
  { value: "fraud",       label: "Fraud",       color: "bg-blue-900 text-blue-300" },
  { value: "hacking",     label: "Hacking",     color: "bg-purple-900 text-purple-300" },
];

export function CategoryBadge({ category }: { category: ThreatCategory }) {
  const meta = CATEGORIES.find((c) => c.value === category) ?? CATEGORIES[0];
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ${meta.color}`}>
      {meta.label}
    </span>
  );
}
