import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookmarkPlus, ChevronDown, ChevronUp, RefreshCw, Sparkles } from "lucide-react";
import clsx from "clsx";
import type { BuildResponse } from "../../types";
import PerkCard from "../perks/PerkCard";
import { saveBuild } from "../../lib/api";

interface BuildResultProps {
  build: BuildResponse;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
}

export default function BuildResult({ build, onRegenerate, isRegenerating }: BuildResultProps) {
  const [showExplanation, setShowExplanation] = useState(true);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveName, setSaveName] = useState(
    build.theme
      ? `${build.theme.slice(0, 30)} Build`
      : `Custom Build ${new Date().toLocaleDateString()}`
  );
  const [showSaveForm, setShowSaveForm] = useState(false);

  const handleSave = async () => {
    if (!saveName.trim()) return;
    setSaveState("saving");
    try {
      await saveBuild({
        name: saveName,
        perk_ids: build.perks.map((p) => p.id),
        theme: build.theme ?? undefined,
        ai_explanation: build.explanation,
        generation_mode: build.generation_mode,
      });
      setSaveState("saved");
      setShowSaveForm(false);
      setTimeout(() => setSaveState("idle"), 3000);
    } catch {
      setSaveState("error");
      setTimeout(() => setSaveState("idle"), 3000);
    }
  };

  const isRandom = build.generation_mode === "random";
  const hasExplanation = !isRandom && Boolean(build.explanation);

  const modeLabel =
    build.generation_mode === "theme"
      ? "Theme build"
      : build.generation_mode === "random"
      ? "Random build"
      : "Category build";

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-3xl tracking-widest text-white uppercase">
            {build.theme || (isRandom ? "Random Build" : "Your Build")}
          </h2>
          <p className="text-ash-500 text-sm font-mono mt-1">
            {modeLabel} · {build.perks.length} perks
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              disabled={isRegenerating}
              className="btn-ghost flex items-center gap-2 text-sm"
            >
              <RefreshCw size={14} className={clsx(isRegenerating && "animate-spin")} />
              Reroll
            </button>
          )}
          <button
            onClick={() => setShowSaveForm(!showSaveForm)}
            className="btn-ghost flex items-center gap-2 text-sm"
          >
            <BookmarkPlus size={14} />
            Save
          </button>
        </div>
      </div>

      {/* Save form */}
      {showSaveForm && (
        <div className="card p-4 flex items-center gap-3">
          <input
            type="text"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            placeholder="Build name..."
            className="input-field flex-1"
          />
          <button
            onClick={handleSave}
            disabled={saveState === "saving"}
            className="btn-primary text-sm px-4 py-2 whitespace-nowrap"
          >
            {saveState === "saving"
              ? "Saving..."
              : saveState === "saved"
              ? "Saved!"
              : "Confirm Save"}
          </button>
        </div>
      )}

      {/* Perk grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {build.perks.map((perk, i) => (
          <PerkCard key={perk.id} perk={perk} index={i} size="lg" />
        ))}
      </div>

      {/* Strategy guide — hidden for random builds */}
      {hasExplanation && (
        <div className="card overflow-hidden">
          <button
            onClick={() => setShowExplanation(!showExplanation)}
            className="w-full flex items-center justify-between p-4 hover:bg-ash-900/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-blood-400" />
              <span className="font-display tracking-wider text-white text-lg">
                STRATEGY GUIDE
              </span>
            </div>
            {showExplanation
              ? <ChevronUp size={16} className="text-ash-500" />
              : <ChevronDown size={16} className="text-ash-500" />
            }
          </button>

          {showExplanation && (
            <>
              <div className="fog-line" />
              <div className="p-5">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h2: ({ children }) => (
                      <h2 className="font-display text-xl tracking-wider text-white mt-6 mb-2 first:mt-0">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="font-body font-semibold text-fog-light mt-4 mb-1.5">
                        {children}
                      </h3>
                    ),
                    p: ({ children }) => (
                      <p className="text-ash-300 text-sm leading-relaxed mb-3">
                        {children}
                      </p>
                    ),
                    strong: ({ children }) => (
                      <strong className="text-white font-semibold">{children}</strong>
                    ),
                    li: ({ children }) => (
                      <li className="text-ash-300 text-sm leading-relaxed mb-1 ml-4 list-disc">
                        {children}
                      </li>
                    ),
                    ul: ({ children }) => (
                      <ul className="mb-3 space-y-0.5">{children}</ul>
                    ),
                  }}
                >
                  {build.explanation}
                </ReactMarkdown>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
