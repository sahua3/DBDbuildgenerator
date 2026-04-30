import { useQuery, useMutation } from "@tanstack/react-query";
import { FlameKindling, RefreshCw } from "lucide-react";
import { fetchShrine, triggerShrineSync } from "../lib/api";
import PerkCard from "../components/perks/PerkCard";

export default function ShrinePage() {
  const { data: shrine, isLoading, refetch } = useQuery({
    queryKey: ["shrine"],
    queryFn: fetchShrine,
    staleTime: 1000 * 60 * 30,
  });

  const syncMutation = useMutation({
    mutationFn: triggerShrineSync,
    onSuccess: () => setTimeout(() => refetch(), 3000),
  });

  const formatDate = (s: string | null) => {
    if (!s) return "—";
    return new Date(s).toLocaleString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex items-end justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <FlameKindling size={28} className="text-amber-500 animate-flicker" />
            <h1 className="font-display text-5xl tracking-widest text-white uppercase">
              Shrine of <span className="text-amber-500">Secrets</span>
            </h1>
          </div>
          <p className="text-ash-400 font-body">
            Weekly rotating perks available for Iridescent Shards — no DLC required
          </p>
        </div>

        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
          className="btn-ghost flex items-center gap-2 text-sm"
        >
          <RefreshCw
            size={14}
            className={syncMutation.isPending ? "animate-spin" : ""}
          />
          Force Sync
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-40 bg-ash-900 animate-pulse" />
          ))}
        </div>
      ) : shrine && shrine.perks.length > 0 ? (
        <>
          {/* Shrine timing */}
          <div className="card p-4 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-6">
              <div>
                <p className="text-ash-600 text-xs font-mono uppercase tracking-widest">Last Updated</p>
                <p className="text-ash-200 text-sm font-mono mt-0.5">
                  {formatDate(shrine.scraped_at)}
                </p>
              </div>
              <div>
                <p className="text-ash-600 text-xs font-mono uppercase tracking-widest">Resets</p>
                <p className="text-amber-400 text-sm font-mono mt-0.5">
                  {formatDate(shrine.valid_until)}
                </p>
              </div>
            </div>
            <div className="shrine-badge self-start sm:self-auto px-3 py-1.5">
              <FlameKindling size={12} />
              <span>Active Shrine</span>
            </div>
          </div>

          {/* Shrine perks */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {shrine.perks.map((perk, i) => (
              <PerkCard key={perk.id} perk={perk} index={i} size="lg" />
            ))}
          </div>

          {/* Names-only fallback for perks not in DB */}
          {shrine.perk_names.length > shrine.perks.length && (
            <div className="mt-4">
              <p className="text-ash-500 text-xs font-mono mb-2">
                Additional shrine perks (not yet in database):
              </p>
              <div className="flex flex-wrap gap-2">
                {shrine.perk_names
                  .filter(
                    (name) =>
                      !shrine.perks.some((p) =>
                        p.name.toLowerCase().includes(name.toLowerCase())
                      )
                  )
                  .map((name) => (
                    <span key={name} className="shrine-badge">
                      {name}
                    </span>
                  ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-20">
          <div className="inline-flex items-center justify-center w-20 h-20 border border-amber-900/50 bg-amber-950/20 mb-6">
            <FlameKindling size={32} className="text-amber-700" />
          </div>
          <p className="font-display text-2xl text-ash-600 tracking-widest">
            SHRINE NOT LOADED
          </p>
          <p className="text-ash-600 text-sm font-mono mt-2 max-w-md mx-auto">
            The shrine syncs automatically every Tuesday at noon EST. Click "Force
            Sync" to fetch it now.
          </p>
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="btn-primary mt-6 flex items-center gap-2 mx-auto"
          >
            <RefreshCw size={14} className={syncMutation.isPending ? "animate-spin" : ""} />
            {syncMutation.isPending ? "Syncing..." : "Sync Shrine Now"}
          </button>
        </div>
      )}
    </div>
  );
}
