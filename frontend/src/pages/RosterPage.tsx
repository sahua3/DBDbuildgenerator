import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Lock, Unlock } from "lucide-react";
import clsx from "clsx";
import { fetchSurvivors, updateSurvivorOwnership } from "../lib/api";
import type { Survivor } from "../types";

export default function RosterPage() {
  const queryClient = useQueryClient();

  const { data: survivors = [], isLoading } = useQuery({
    queryKey: ["survivors"],
    queryFn: fetchSurvivors,
  });

  const mutation = useMutation({
    mutationFn: ({ id, owned }: { id: string; owned: boolean }) =>
      updateSurvivorOwnership(id, owned),
    onMutate: async ({ id, owned }) => {
      await queryClient.cancelQueries({ queryKey: ["survivors"] });
      const prev = queryClient.getQueryData<Survivor[]>(["survivors"]);
      queryClient.setQueryData<Survivor[]>(["survivors"], (old) =>
        old?.map((s) => (s.id === id ? { ...s, owned } : s)) ?? []
      );
      return { prev };
    },
    onError: (_, __, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(["survivors"], ctx.prev);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["survivors"] }),
  });

  const owned = survivors.filter((s) => s.owned);
  const unowned = survivors.filter((s) => !s.owned);

  const handleToggle = (s: Survivor) => {
    if (s.is_base) return; // Base survivors can't be unowned
    mutation.mutate({ id: s.id, owned: !s.owned });
  };

  const handleSelectAll = () => {
    survivors.forEach((s) => {
      if (!s.owned) mutation.mutate({ id: s.id, owned: true });
    });
  };

  const handleDeselectAll = () => {
    survivors.forEach((s) => {
      if (s.owned && !s.is_base) mutation.mutate({ id: s.id, owned: false });
    });
  };

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="animate-pulse space-y-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-16 bg-ash-900 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="font-display text-5xl tracking-widest text-white uppercase">
            Survivor <span className="text-blood-500">Roster</span>
          </h1>
          <p className="text-ash-400 mt-2 font-body">
            Mark which survivors you own to filter builds by your available perks
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleDeselectAll} className="btn-ghost text-xs py-1.5 px-3">
            Deselect All
          </button>
          <button onClick={handleSelectAll} className="btn-ghost text-xs py-1.5 px-3">
            Select All
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: "Total Survivors", value: survivors.length },
          { label: "Owned", value: owned.length },
          { label: "Locked Perks", value: unowned.length * 3 },
        ].map(({ label, value }) => (
          <div key={label} className="card p-4 text-center">
            <p className="font-display text-3xl text-white">{value}</p>
            <p className="text-ash-500 text-xs font-mono mt-1 uppercase tracking-widest">
              {label}
            </p>
          </div>
        ))}
      </div>

      {/* Survivor grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
        {survivors.map((survivor) => (
          <button
            key={survivor.id}
            onClick={() => handleToggle(survivor)}
            disabled={survivor.is_base}
            className={clsx(
              "card p-4 flex flex-col items-center gap-2 text-center transition-all duration-200",
              "hover:-translate-y-0.5 active:translate-y-0",
              survivor.owned
                ? survivor.is_base
                  ? "border-ash-700/60 bg-ash-900/20"
                  : "border-blood-800/60 bg-blood-950/20 selected-glow"
                : "hover:border-ash-600",
              survivor.is_base && "cursor-default"
            )}
          >
            {/* Avatar */}
            <div
              className={clsx(
                "w-12 h-12 flex items-center justify-center border text-lg font-display",
                survivor.owned ? "border-blood-700 bg-blood-950/40" : "border-ash-700 bg-ash-900"
              )}
            >
              {survivor.icon_url ? (
                <img src={survivor.icon_url} alt={survivor.name} className="w-full h-full object-cover" />
              ) : (
                survivor.name.slice(0, 2).toUpperCase()
              )}
            </div>

            {/* Name */}
            <p className={clsx(
              "text-xs font-body font-medium leading-tight",
              survivor.owned ? "text-white" : "text-ash-400"
            )}>
              {survivor.name}
            </p>

            {/* Status */}
            <div className={clsx(
              "flex items-center gap-1 text-xs font-mono",
              survivor.owned ? "text-blood-400" : "text-ash-600"
            )}>
              {survivor.is_base ? (
                <>
                  <Lock size={10} />
                  <span>Base</span>
                </>
              ) : survivor.owned ? (
                <>
                  <Check size={10} />
                  <span>Owned</span>
                </>
              ) : (
                <>
                  <Unlock size={10} />
                  <span>Locked</span>
                </>
              )}
            </div>
          </button>
        ))}
      </div>

      {survivors.length === 0 && (
        <div className="text-center py-16">
          <p className="font-display text-2xl text-ash-600 tracking-widest">NO SURVIVORS LOADED</p>
          <p className="text-ash-600 text-sm font-mono mt-2">
            Load your perks CSV first using the perk loader script
          </p>
        </div>
      )}
    </div>
  );
}
