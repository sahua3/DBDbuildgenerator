import { useQuery } from "@tanstack/react-query";
import { Filter, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import clsx from "clsx";
import { fetchSurvivors, fetchShrine } from "../../lib/api";
import { useBuildStore } from "../../store/buildStore";

export default function OwnedFilter() {
  const [expanded, setExpanded] = useState(false);
  const { ownedOnly, setOwnedOnly } = useBuildStore();

  const { data: shrine } = useQuery({
    queryKey: ["shrine"],
    queryFn: fetchShrine,
    staleTime: 1000 * 60 * 30,
  });

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-ash-500" />
          <span className="text-ash-300 text-sm font-mono uppercase tracking-widest">
            Filters
          </span>
        </div>
      </div>

      {/* Owned-only toggle */}
      <label className="flex items-center justify-between cursor-pointer group">
        <div>
          <p className="text-sm font-body text-ash-200 group-hover:text-white transition-colors">
            Owned perks only
          </p>
          <p className="text-xs text-ash-600 font-mono">
            Filter by your survivor roster
          </p>
        </div>
        <div
          onClick={() => setOwnedOnly(!ownedOnly)}
          className={clsx(
            "relative w-10 h-5 rounded-full border transition-all duration-200 cursor-pointer",
            ownedOnly
              ? "bg-blood-700 border-blood-600"
              : "bg-ash-900 border-ash-700"
          )}
        >
          <div
            className={clsx(
              "absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all duration-200",
              ownedOnly ? "left-5" : "left-0.5"
            )}
          />
        </div>
      </label>

      {/* Shrine info */}
      {shrine && shrine.perk_names.length > 0 && (
        <div className="pt-2 border-t border-[var(--color-border)]">
          <p className="text-xs font-mono text-ash-500 uppercase tracking-widest mb-2 flex items-center gap-1.5">
            <span className="text-amber-400">🕯</span> This week's shrine
          </p>
          <div className="flex flex-wrap gap-1.5">
            {shrine.perk_names.map((name) => (
              <span
                key={name}
                className="shrine-badge text-xs"
              >
                {name}
              </span>
            ))}
          </div>
          {shrine.valid_until && (
            <p className="text-ash-700 text-xs font-mono mt-1.5">
              Resets{" "}
              {new Date(shrine.valid_until).toLocaleDateString("en-US", {
                weekday: "short",
                month: "short",
                day: "numeric",
              })}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
