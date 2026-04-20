import clsx from "clsx";
import { Flame } from "lucide-react";
import type { Perk } from "../../types";

const CATEGORY_COLORS: Record<string, string> = {
  healing: "text-emerald-400 bg-emerald-900/30 border-emerald-800/50",
  stealth: "text-violet-400 bg-violet-900/30 border-violet-800/50",
  chase: "text-orange-400 bg-orange-900/30 border-orange-800/50",
  gen_speed: "text-yellow-400 bg-yellow-900/30 border-yellow-800/50",
  information: "text-sky-400 bg-sky-900/30 border-sky-800/50",
  altruism: "text-pink-400 bg-pink-900/30 border-pink-800/50",
  escape: "text-lime-400 bg-lime-900/30 border-lime-800/50",
  anti_hook: "text-red-400 bg-red-900/30 border-red-800/50",
  aura_reading: "text-cyan-400 bg-cyan-900/30 border-cyan-800/50",
  exhaustion: "text-amber-400 bg-amber-900/30 border-amber-800/50",
  endurance: "text-indigo-400 bg-indigo-900/30 border-indigo-800/50",
  second_chance: "text-rose-400 bg-rose-900/30 border-rose-800/50",
};

const CATEGORY_LABELS: Record<string, string> = {
  healing: "Healing",
  stealth: "Stealth",
  chase: "Chase",
  gen_speed: "Gen Speed",
  information: "Info",
  altruism: "Altruism",
  escape: "Escape",
  anti_hook: "Anti-Hook",
  aura_reading: "Aura",
  exhaustion: "Exhaustion",
  endurance: "Endurance",
  second_chance: "2nd Chance",
};

interface PerkCardProps {
  perk: Perk;
  index?: number;
  size?: "sm" | "md" | "lg";
  showDescription?: boolean;
  className?: string;
}

export default function PerkCard({
  perk,
  index,
  size = "md",
  showDescription = true,
  className,
}: PerkCardProps) {
  return (
    <div
      className={clsx(
        "perk-card card group relative overflow-hidden transition-all duration-300",
        "hover:-translate-y-0.5",
        size === "lg" && "p-5",
        size === "md" && "p-4",
        size === "sm" && "p-3",
        className
      )}
      style={{
        animationDelay: index !== undefined ? `${index * 80}ms` : "0ms",
        animation: "fadeUp 0.4s ease forwards",
        opacity: 0,
      }}
    >
      {/* Subtle blood-red corner accent */}
      <div className="absolute top-0 right-0 w-12 h-12 opacity-20 pointer-events-none">
        <div
          className="absolute top-0 right-0 w-full h-full"
          style={{
            background:
              "linear-gradient(225deg, var(--color-blood) 0%, transparent 70%)",
          }}
        />
      </div>

      {/* Shrine badge */}
      {perk.in_shrine && (
        <div className="absolute top-3 right-3">
          <span className="shrine-badge">
            <Flame size={10} className="text-amber-400" />
            Shrine
          </span>
        </div>
      )}

      {/* Header row */}
      <div className={clsx("flex items-start gap-3", perk.in_shrine && "pr-16")}>
        {/* Perk icon or placeholder */}
        <div
          className={clsx(
            "flex-shrink-0 bg-ash-900 border border-[var(--color-border)] flex items-center justify-center font-display text-blood-500",
            size === "lg" && "w-14 h-14 text-lg",
            size === "md" && "w-11 h-11 text-base",
            size === "sm" && "w-9 h-9 text-sm"
          )}
        >
          {perk.icon_url ? (
            <img
              src={perk.icon_url}
              alt={perk.name}
              className="w-full h-full object-cover"
            />
          ) : (
            perk.name.slice(0, 2).toUpperCase()
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h3
            className={clsx(
              "font-display tracking-wider text-white leading-tight",
              size === "lg" && "text-xl",
              size === "md" && "text-base",
              size === "sm" && "text-sm"
            )}
          >
            {perk.name}
          </h3>
          {perk.owner && (
            <p className="text-ash-500 text-xs font-mono mt-0.5 truncate">
              {perk.owner}
            </p>
          )}
        </div>
      </div>

      {/* Description */}
      {showDescription && (
        <p
          className={clsx(
            "text-ash-300 leading-relaxed mt-3",
            size === "sm" ? "text-xs" : "text-sm"
          )}
        >
          {perk.description}
        </p>
      )}

      {/* Footer: categories + pick rate */}
      <div className="flex items-center flex-wrap gap-1.5 mt-3">
        {perk.categories.slice(0, 3).map((cat) => (
          <span
            key={cat}
            className={clsx(
              "tag border",
              CATEGORY_COLORS[cat] || "text-ash-400 bg-ash-800/50 border-ash-700/50"
            )}
          >
            {CATEGORY_LABELS[cat] || cat}
          </span>
        ))}

        {perk.pick_rate > 0 && (
          <span className="ml-auto text-xs font-mono text-ash-500">
            {(perk.pick_rate * 100).toFixed(1)}% pick
          </span>
        )}
      </div>
    </div>
  );
}
