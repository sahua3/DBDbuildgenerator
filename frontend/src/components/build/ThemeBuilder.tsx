import { useState, KeyboardEvent } from "react";
import { Zap } from "lucide-react";
import clsx from "clsx";
import { useBuildStore } from "../../store/buildStore";

const THEME_SUGGESTIONS = [
  "Gen Rush",
  "Full Stealth",
  "Team Medic",
  "Aggressive Chase",
  "Escape Artist",
  "Clutch Master",
  "Information",
  "Support Carry",
  "Hatch Hunt",
  "End Game",
];

interface ThemeBuilderProps {
  onGenerate: () => void;
}

export default function ThemeBuilder({ onGenerate }: ThemeBuilderProps) {
  const { themeInput, setThemeInput, isGenerating } = useBuildStore();

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && themeInput.trim().length >= 3) {
      onGenerate();
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <label className="block text-ash-400 text-xs font-mono uppercase tracking-widest mb-2">
          Describe your playstyle
        </label>
        <div className="relative">
          <input
            type="text"
            value={themeInput}
            onChange={(e) => setThemeInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. 'stealth gen rush', 'aggressive looping', 'team medic'..."
            className="input-field pr-12"
            maxLength={300}
            disabled={isGenerating}
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-ash-600 text-xs font-mono">
            {themeInput.length}/300
          </div>
        </div>
      </div>

      {/* Quick suggestions */}
      <div>
        <p className="text-ash-600 text-xs font-mono uppercase tracking-widest mb-2">
          Quick picks
        </p>
        <div className="flex flex-wrap gap-2">
          {THEME_SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setThemeInput(s)}
              className={clsx(
                "text-xs font-mono px-3 py-1.5 border transition-all duration-150",
                themeInput.toLowerCase() === s.toLowerCase()
                  ? "bg-blood-900/50 border-blood-700 text-blood-300"
                  : "bg-ash-950 border-ash-800 text-ash-400 hover:border-ash-600 hover:text-ash-200"
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Generate button */}
      <button
        onClick={onGenerate}
        disabled={isGenerating || themeInput.trim().length < 3}
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
            GENERATE BUILD
          </>
        )}
      </button>
    </div>
  );
}
