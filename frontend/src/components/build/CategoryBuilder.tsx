import { useQuery } from "@tanstack/react-query";
import { Minus, Plus, Zap, AlertCircle } from "lucide-react";
import clsx from "clsx";
import { fetchCategories } from "../../lib/api";
import { useBuildStore } from "../../store/buildStore";

interface CategoryBuilderProps {
  onGenerate: () => void;
}

const CATEGORY_ICONS: Record<string, string> = {
  healing: "💉",
  stealth: "👁️",
  chase: "🏃",
  gen_speed: "⚡",
  information: "📡",
  altruism: "🤝",
  escape: "🚪",
  anti_hook: "🪝",
  aura_reading: "🔮",
  exhaustion: "💨",
  endurance: "🛡️",
  second_chance: "🎲",
};

export default function CategoryBuilder({ onGenerate }: CategoryBuilderProps) {
  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
  });

  const {
    categorySelections,
    setCategoryCount,
    resetCategories,
    totalCategoryPerks,
    isGenerating,
  } = useBuildStore();

  const total = totalCategoryPerks();
  const isValid = total === 4;

  return (
    <div className="space-y-5">
      {/* Counter bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-ash-400 text-xs font-mono uppercase tracking-widest">
            Perk slots
          </span>
          <div className="flex gap-1">
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className={clsx(
                  "w-6 h-2 transition-all duration-200",
                  n <= total ? "bg-blood-600" : "bg-ash-800"
                )}
              />
            ))}
          </div>
          <span
            className={clsx(
              "text-sm font-mono font-semibold",
              total === 4
                ? "text-emerald-400"
                : total > 4
                ? "text-blood-400"
                : "text-ash-400"
            )}
          >
            {total}/4
          </span>
        </div>
        {total > 0 && (
          <button
            onClick={resetCategories}
            className="text-xs font-mono text-ash-600 hover:text-ash-300 transition-colors"
          >
            Reset
          </button>
        )}
      </div>

      {/* Validation message */}
      {total > 4 && (
        <div className="flex items-center gap-2 p-3 bg-blood-900/30 border border-blood-800/50">
          <AlertCircle size={14} className="text-blood-400 flex-shrink-0" />
          <p className="text-blood-300 text-xs font-mono">
            Too many perks selected. Reduce to exactly 4 total.
          </p>
        </div>
      )}

      {/* Category grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {categories.map((cat) => {
          const count = categorySelections[cat.id] || 0;
          const icon = CATEGORY_ICONS[cat.id] || "◆";

          return (
            <div
              key={cat.id}
              className={clsx(
                "card p-3 flex flex-col gap-2 transition-all duration-200",
                count > 0 && "border-blood-800/60 bg-blood-950/20"
              )}
            >
              <div className="flex items-center gap-2">
                <span className="text-base leading-none">{icon}</span>
                <span className="text-xs font-mono text-ash-300 flex-1 leading-tight">
                  {cat.label}
                </span>
                {count > 0 && (
                  <span className="text-blood-400 text-xs font-mono font-bold">
                    ×{count}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1">
                <button
                  onClick={() => setCategoryCount(cat.id, count - 1)}
                  disabled={count === 0}
                  className={clsx(
                    "w-7 h-7 flex items-center justify-center border transition-all",
                    count === 0
                      ? "border-ash-800 text-ash-700 cursor-not-allowed"
                      : "border-ash-700 text-ash-300 hover:border-blood-600 hover:text-white"
                  )}
                >
                  <Minus size={12} />
                </button>

                <div className="flex-1 h-7 bg-ash-950 border border-ash-800 flex items-center justify-center">
                  <span className="text-sm font-mono font-semibold text-white">
                    {count}
                  </span>
                </div>

                <button
                  onClick={() => setCategoryCount(cat.id, count + 1)}
                  disabled={total >= 4}
                  className={clsx(
                    "w-7 h-7 flex items-center justify-center border transition-all",
                    total >= 4
                      ? "border-ash-800 text-ash-700 cursor-not-allowed"
                      : "border-ash-700 text-ash-300 hover:border-blood-600 hover:text-white"
                  )}
                >
                  <Plus size={12} />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Generate button */}
      <button
        onClick={onGenerate}
        disabled={isGenerating || !isValid}
        className="btn-primary w-full flex items-center justify-center gap-2 py-4 text-base tracking-widest font-display"
      >
        {isGenerating ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            GENERATING BUILD...
          </>
        ) : (
          <>
            <Zap size={16} />
            {isValid ? "GENERATE BUILD" : `SELECT ${4 - total} MORE PERK${4 - total !== 1 ? "S" : ""}`}
          </>
        )}
      </button>
    </div>
  );
}
