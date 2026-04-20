export interface Perk {
  id: string;
  name: string;
  description: string;
  owner: string | null;
  categories: string[];
  pick_rate: number;
  category_weight: number;
  in_shrine: boolean;
  icon_url: string | null;
  nightlight_rank: number | null;
}

export interface Survivor {
  id: string;
  name: string;
  is_base: boolean;
  icon_url: string | null;
  owned: boolean;
}

export interface BuildResponse {
  perks: Perk[];
  explanation: string;
  theme: string | null;
  generation_mode: "theme" | "category";
}

export interface SavedBuild {
  id: string;
  name: string;
  perks: Perk[];
  theme: string | null;
  ai_explanation: string | null;
  generation_mode: string;
  created_at: string;
}

export interface ShrineResponse {
  perk_names: string[];
  perks: Perk[];
  scraped_at: string | null;
  valid_until: string | null;
}

export interface Category {
  id: string;
  label: string;
}

export interface PerkStats {
  total_perks: number;
  categorized_perks: number;
  categories: Record<string, number>;
  last_nightlight_sync: string | null;
  shrine_perks: string[];
}

export type BuildMode = "theme" | "category";
