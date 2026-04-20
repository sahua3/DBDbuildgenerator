import axios from "axios";
import type {
  Perk,
  Survivor,
  BuildResponse,
  SavedBuild,
  ShrineResponse,
  Category,
  PerkStats,
} from "../types";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// ── Perks ─────────────────────────────────────────────────────────────────────

export const fetchPerks = async (params?: {
  category?: string;
  owner?: string;
  in_shrine?: boolean;
  search?: string;
}): Promise<Perk[]> => {
  const { data } = await api.get("/perks/", { params });
  return data;
};

export const fetchCategories = async (): Promise<Category[]> => {
  const { data } = await api.get("/perks/categories");
  return data;
};

export const fetchPerkStats = async (): Promise<PerkStats> => {
  const { data } = await api.get("/perks/stats");
  return data;
};

// ── Survivors ─────────────────────────────────────────────────────────────────

export const fetchSurvivors = async (): Promise<Survivor[]> => {
  const { data } = await api.get("/survivors/");
  return data;
};

export const fetchOwnedSurvivorNames = async (): Promise<string[]> => {
  const { data } = await api.get("/survivors/owned");
  return data;
};

export const updateSurvivorOwnership = async (
  id: string,
  owned: boolean
): Promise<Survivor> => {
  const { data } = await api.patch(`/survivors/${id}/owned`, { owned });
  return data;
};

// ── Builds ────────────────────────────────────────────────────────────────────

export const generateThemeBuild = async (payload: {
  theme: string;
  owned_only: boolean;
  owned_survivors: string[];
}): Promise<BuildResponse> => {
  const { data } = await api.post("/builds/theme", payload);
  return data;
};

export const generateCategoryBuild = async (payload: {
  category_selections: Record<string, number>;
  owned_only: boolean;
  owned_survivors: string[];
}): Promise<BuildResponse> => {
  const { data } = await api.post("/builds/category", payload);
  return data;
};

export const saveBuild = async (payload: {
  name: string;
  perk_ids: string[];
  theme?: string;
  ai_explanation?: string;
  generation_mode: string;
}): Promise<SavedBuild> => {
  const { data } = await api.post("/builds/save", payload);
  return data;
};

export const fetchSavedBuilds = async (): Promise<SavedBuild[]> => {
  const { data } = await api.get("/builds/saved");
  return data;
};

export const deleteSavedBuild = async (id: string): Promise<void> => {
  await api.delete(`/builds/saved/${id}`);
};

// ── Shrine ────────────────────────────────────────────────────────────────────

export const fetchShrine = async (): Promise<ShrineResponse> => {
  const { data } = await api.get("/shrine");
  return data;
};

// ── Admin ─────────────────────────────────────────────────────────────────────

export const triggerNightlightSync = async () => {
  const { data } = await api.post("/admin/sync/nightlight");
  return data;
};

export const triggerShrineSync = async () => {
  const { data } = await api.post("/admin/sync/shrine");
  return data;
};
