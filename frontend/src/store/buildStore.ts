import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { BuildResponse, BuildMode, Survivor } from "../types";

interface BuildStore {
  // Current build result
  currentBuild: BuildResponse | null;
  setCurrentBuild: (build: BuildResponse | null) => void;

  // Build mode
  buildMode: BuildMode;
  setBuildMode: (mode: BuildMode) => void;

  // Theme input
  themeInput: string;
  setThemeInput: (t: string) => void;

  // Category selections (category -> count)
  categorySelections: Record<string, number>;
  setCategoryCount: (cat: string, count: number) => void;
  resetCategories: () => void;
  totalCategoryPerks: () => number;

  // Owned-only filter
  ownedOnly: boolean;
  setOwnedOnly: (v: boolean) => void;

  // Owned survivors (cached locally)
  ownedSurvivors: string[];
  setOwnedSurvivors: (names: string[]) => void;

  // Loading state
  isGenerating: boolean;
  setIsGenerating: (v: boolean) => void;

  // Error
  error: string | null;
  setError: (e: string | null) => void;
}

export const useBuildStore = create<BuildStore>()(
  persist(
    (set, get) => ({
      currentBuild: null,
      setCurrentBuild: (build) => set({ currentBuild: build }),

      buildMode: "theme",
      setBuildMode: (mode) => set({ buildMode: mode }),

      themeInput: "",
      setThemeInput: (t) => set({ themeInput: t }),

      categorySelections: {},
      setCategoryCount: (cat, count) =>
        set((state) => ({
          categorySelections: {
            ...state.categorySelections,
            [cat]: Math.max(0, count),
          },
        })),
      resetCategories: () => set({ categorySelections: {} }),
      totalCategoryPerks: () =>
        Object.values(get().categorySelections).reduce((a, b) => a + b, 0),

      ownedOnly: false,
      setOwnedOnly: (v) => set({ ownedOnly: v }),

      ownedSurvivors: [],
      setOwnedSurvivors: (names) => set({ ownedSurvivors: names }),

      isGenerating: false,
      setIsGenerating: (v) => set({ isGenerating: v }),

      error: null,
      setError: (e) => set({ error: e }),
    }),
    {
      name: "dbd-build-store",
      partialize: (state) => ({
        ownedOnly: state.ownedOnly,
        ownedSurvivors: state.ownedSurvivors,
        themeInput: state.themeInput,
        categorySelections: state.categorySelections,
        buildMode: state.buildMode,
      }),
    }
  )
);
