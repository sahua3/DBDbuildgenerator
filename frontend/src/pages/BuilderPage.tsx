import { useCallback } from "react";
import clsx from "clsx";
import { useBuildStore } from "../store/buildStore";
import ThemeBuilder from "../components/build/ThemeBuilder";
import CategoryBuilder from "../components/build/CategoryBuilder";
import RandomBuilder from "../components/build/RandomBuilder";
import BuildResult from "../components/build/BuildResult";
import OwnedFilter from "../components/build/OwnedFilter";
import { generateThemeBuild, generateCategoryBuild, generateRandomBuild, fetchOwnedSurvivorNames } from "../lib/api";
import type { BuildMode } from "../types";

const TABS: { id: BuildMode; label: string; desc: string }[] = [
  {
    id: "theme",
    label: "Theme Build",
    desc: "Describe a playstyle and get the optimal meta build",
  },
  {
    id: "category",
    label: "Category Build",
    desc: "Choose how many perks from each category",
  },
  {
    id: "random",
    label: "Random",
    desc: "Spin the wheel — 4 completely random perks, no rules",
  },
];

export default function BuilderPage() {
  const {
    buildMode,
    setBuildMode,
    currentBuild,
    setCurrentBuild,
    themeInput,
    categorySelections,
    ownedOnly,
    ownedSurvivors,
    setOwnedSurvivors,
    isGenerating,
    setIsGenerating,
    error,
    setError,
  } = useBuildStore();

  const getOwnedSurvivors = useCallback(async (): Promise<string[]> => {
    if (!ownedOnly) return [];
    try {
      const names = await fetchOwnedSurvivorNames();
      setOwnedSurvivors(names);
      return names;
    } catch {
      return ownedSurvivors;
    }
  }, [ownedOnly, ownedSurvivors, setOwnedSurvivors]);

  const handleGenerateTheme = useCallback(async () => {
    if (!themeInput.trim()) return;
    setIsGenerating(true);
    setError(null);
    try {
      const owned = await getOwnedSurvivors();
      const build = await generateThemeBuild({
        theme: themeInput.trim(),
        owned_only: ownedOnly,
        owned_survivors: owned,
      });
      setCurrentBuild(build);
      // Scroll to result on mobile
      setTimeout(() => {
        document.getElementById("build-result")?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to generate build. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  }, [themeInput, ownedOnly, getOwnedSurvivors, setIsGenerating, setError, setCurrentBuild]);

  const handleGenerateCategory = useCallback(async () => {
    const total = Object.values(categorySelections).reduce((a, b) => a + b, 0);
    if (total !== 4) return;
    setIsGenerating(true);
    setError(null);
    try {
      const owned = await getOwnedSurvivors();
      const filtered = Object.fromEntries(
        Object.entries(categorySelections).filter(([, v]) => v > 0)
      );
      const build = await generateCategoryBuild({
        category_selections: filtered,
        owned_only: ownedOnly,
        owned_survivors: owned,
      });
      setCurrentBuild(build);
      setTimeout(() => {
        document.getElementById("build-result")?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to generate build. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  }, [categorySelections, ownedOnly, getOwnedSurvivors, setIsGenerating, setError, setCurrentBuild]);

  const handleGenerateRandom = useCallback(async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const owned = await getOwnedSurvivors();
      const build = await generateRandomBuild({
        owned_only: ownedOnly,
        owned_survivors: owned.join(","),
      });
      setCurrentBuild(build);
      setTimeout(() => {
        document.getElementById("build-result")?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to generate random build.");
    } finally {
      setIsGenerating(false);
    }
  }, [ownedOnly, getOwnedSurvivors, setIsGenerating, setError, setCurrentBuild]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="font-display text-5xl tracking-widest text-white uppercase">
          Build<span className="text-blood-500"> Creator</span>
        </h1>
        <p className="text-ash-400 mt-2 font-body">
          Synergy-optimized builds powered by Nightlight.gg perk data
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
        {/* Left panel — builder controls */}
        <div className="space-y-4">
          {/* Mode tabs */}
          <div className="card p-1 flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setBuildMode(tab.id)}
                className={clsx(
                  "flex-1 px-3 py-2.5 text-sm font-body font-medium transition-all duration-200",
                  buildMode === tab.id
                    ? "bg-blood-800 text-white border border-blood-700"
                    : "text-ash-400 hover:text-white"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab description */}
          <p className="text-ash-500 text-xs font-mono px-1">
            {TABS.find((t) => t.id === buildMode)?.desc}
          </p>

          {/* Builder form */}
          <div className="card p-5">
            {buildMode === "theme" ? (
              <ThemeBuilder onGenerate={handleGenerateTheme} />
            ) : buildMode === "category" ? (
              <CategoryBuilder onGenerate={handleGenerateCategory} />
            ) : (
              <RandomBuilder onGenerate={handleGenerateRandom} />
            )}
          </div>

          {/* Filter panel */}
          <OwnedFilter />
        </div>

        {/* Right panel — results */}
        <div id="build-result">
          {error && (
            <div className="card p-4 border-blood-800/60 bg-blood-950/20 mb-4">
              <p className="text-blood-300 text-sm font-mono">{error}</p>
            </div>
          )}

          {currentBuild ? (
            <BuildResult
              build={currentBuild}
              onRegenerate={
                buildMode === "theme"
                  ? handleGenerateTheme
                  : buildMode === "category"
                  ? handleGenerateCategory
                  : handleGenerateRandom
              }
              isRegenerating={isGenerating}
            />
          ) : (
            <EmptyState isGenerating={isGenerating} />
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ isGenerating }: { isGenerating: boolean }) {
  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center min-h-80 gap-4">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-2 border-blood-900" />
          <div className="absolute inset-0 rounded-full border-2 border-t-blood-500 animate-spin" />
        </div>
        <div className="text-center">
          <p className="font-display text-2xl tracking-widest text-white">CONSULTING THE FOG</p>
          <p className="text-ash-500 text-sm font-mono mt-1">Analyzing perk synergies...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-80 gap-4 text-center">
      <div className="w-20 h-20 border border-[var(--color-border)] flex items-center justify-center">
        <span className="font-display text-4xl text-ash-700">?</span>
      </div>
      <div>
        <p className="font-display text-2xl tracking-widest text-ash-600">NO BUILD YET</p>
        <p className="text-ash-600 text-sm font-mono mt-1">
          Enter a theme or pick categories to generate a build
        </p>
      </div>
    </div>
  );
}
