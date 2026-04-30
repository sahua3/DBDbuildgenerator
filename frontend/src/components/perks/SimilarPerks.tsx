import { useQuery } from "@tanstack/react-query";
import { Users, TrendingUp } from "lucide-react";
import clsx from "clsx";
import axios from "axios";
import type { Perk } from "../../types";

const api = axios.create({ baseURL: "/api" });

interface SimilarPerksProps {
  perk: Perk;
  onSelectPerk?: (perk: Perk) => void;
}

export default function SimilarPerks({ perk }: SimilarPerksProps) {
  const { data: similar = [], isLoading } = useQuery({
    queryKey: ["similar-perks", perk.id],
    queryFn: async () => {
      const { data } = await api.get(`/analytics/similar/${perk.id}?top_n=6`);
      return data;
    },
    staleTime: 1000 * 60 * 5,
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-10 bg-ash-900 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!similar.length) {
    return (
      <div className="text-center py-6">
        <Users size={20} className="text-ash-700 mx-auto mb-2" />
        <p className="text-ash-600 text-xs font-mono">
          No data yet — save builds to train recommendations
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <Users size={13} className="text-ash-500" />
        <span className="text-ash-500 text-xs font-mono uppercase tracking-widest">
          Users who save <span className="text-white">{perk.name}</span> also use
        </span>
      </div>
      {similar.map((item: any) => (
        <div
          key={item.perk_id}
          className="flex items-center justify-between p-2.5 bg-ash-950 border border-ash-800 hover:border-ash-600 transition-colors"
        >
          <div className="flex-1 min-w-0">
            <p className="text-ash-200 text-sm font-body truncate">{item.perk_name}</p>
            {item.owner && (
              <p className="text-ash-600 text-xs font-mono truncate">{item.owner}</p>
            )}
          </div>
          <div className="flex items-center gap-2 ml-3 flex-shrink-0">
            <div className="flex items-center gap-1">
              <TrendingUp size={10} className="text-emerald-500" />
              <span className="text-emerald-400 text-xs font-mono">
                {(item.affinity_score * 100).toFixed(0)}%
              </span>
            </div>
            <span className="text-ash-600 text-xs font-mono">
              {item.save_count}×
            </span>
          </div>
        </div>
      ))}
      <p className="text-ash-700 text-xs font-mono pt-1">
        Based on {similar[0]?.save_count ?? 0} saved builds containing this perk
      </p>
    </div>
  );
}
