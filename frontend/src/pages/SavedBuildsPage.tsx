import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, ChevronDown, ChevronUp, BookMarked } from "lucide-react";
import ReactMarkdown from "react-markdown";
import clsx from "clsx";
import { fetchSavedBuilds, deleteSavedBuild } from "../lib/api";
import PerkCard from "../components/perks/PerkCard";
import type { SavedBuild } from "../types";

export default function SavedBuildsPage() {
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: builds = [], isLoading } = useQuery({
    queryKey: ["saved-builds"],
    queryFn: fetchSavedBuilds,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSavedBuild,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-builds"] }),
  });

  const formatDate = (s: string) =>
    new Date(s).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-24 bg-ash-900 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-8">
        <h1 className="font-display text-5xl tracking-widest text-white uppercase">
          Saved <span className="text-blood-500">Builds</span>
        </h1>
        <p className="text-ash-400 mt-2 font-body">
          {builds.length} build{builds.length !== 1 ? "s" : ""} saved
        </p>
      </div>

      {builds.length === 0 ? (
        <div className="text-center py-20">
          <div className="inline-flex items-center justify-center w-20 h-20 border border-[var(--color-border)] mb-6">
            <BookMarked size={32} className="text-ash-700" />
          </div>
          <p className="font-display text-2xl text-ash-600 tracking-widest">NO SAVED BUILDS</p>
          <p className="text-ash-600 text-sm font-mono mt-2">
            Generate a build and save it to see it here
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {builds.map((build) => (
            <BuildCard
              key={build.id}
              build={build}
              expanded={expandedId === build.id}
              onToggle={() => setExpandedId(expandedId === build.id ? null : build.id)}
              onDelete={() => deleteMutation.mutate(build.id)}
              isDeleting={deleteMutation.isPending}
              formatDate={formatDate}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function BuildCard({
  build,
  expanded,
  onToggle,
  onDelete,
  isDeleting,
  formatDate,
}: {
  build: SavedBuild;
  expanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
  isDeleting: boolean;
  formatDate: (s: string) => string;
}) {
  return (
    <div className={clsx("card overflow-hidden transition-all duration-300", expanded && "border-blood-800/50")}>
      {/* Header row */}
      <div
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-ash-900/20 transition-colors"
        onClick={onToggle}
      >
        {/* Perk icon strip */}
        <div className="flex gap-1 flex-shrink-0">
          {build.perks.slice(0, 4).map((perk) => (
            <div
              key={perk.id}
              className="w-8 h-8 bg-ash-900 border border-ash-800 flex items-center justify-center text-xs font-display text-ash-400"
              title={perk.name}
            >
              {perk.icon_url ? (
                <img src={perk.icon_url} alt={perk.name} className="w-full h-full object-cover" />
              ) : (
                perk.name.slice(0, 2).toUpperCase()
              )}
            </div>
          ))}
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-body font-semibold text-white truncate">{build.name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {build.theme && (
              <span className="text-blood-400 text-xs font-mono">{build.theme}</span>
            )}
            <span className="text-ash-600 text-xs font-mono">{formatDate(build.created_at)}</span>
            <span className="text-ash-700 text-xs font-mono capitalize">
              {build.generation_mode}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            disabled={isDeleting}
            className="w-8 h-8 flex items-center justify-center text-ash-600 hover:text-blood-400 transition-colors"
          >
            <Trash2 size={14} />
          </button>
          {expanded ? (
            <ChevronUp size={16} className="text-ash-500" />
          ) : (
            <ChevronDown size={16} className="text-ash-500" />
          )}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <>
          <div className="fog-line" />
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {build.perks.map((perk, i) => (
                <PerkCard key={perk.id} perk={perk} index={i} size="md" />
              ))}
            </div>
            {build.ai_explanation && (
              <div className="pt-2">
                <p className="text-ash-600 text-xs font-mono uppercase tracking-widest mb-3">
                  Strategy Notes
                </p>
                <ReactMarkdown
                  components={{
                    h2: ({ children }) => (
                      <h2 className="font-display text-lg tracking-wider text-white mt-4 mb-1 first:mt-0">
                        {children}
                      </h2>
                    ),
                    p: ({ children }) => (
                      <p className="text-ash-300 text-sm leading-relaxed mb-2">{children}</p>
                    ),
                    strong: ({ children }) => (
                      <strong className="text-white font-semibold">{children}</strong>
                    ),
                  }}
                >
                  {build.ai_explanation}
                </ReactMarkdown>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
