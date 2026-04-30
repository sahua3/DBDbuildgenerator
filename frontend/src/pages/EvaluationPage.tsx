import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart2, RefreshCw, Info, TrendingUp, Users, Zap, Shuffle } from "lucide-react";
import clsx from "clsx";
import axios from "axios";

const api = axios.create({ baseURL: "/api" });

const fetchEvaluation = async (n: number) => {
  const { data } = await api.get(`/analytics/evaluation?n_builds=${n}`);
  return data;
};

const fetchFeedbackStats = async () => {
  const { data } = await api.get("/analytics/stats");
  return data;
};

const STRATEGY_ICONS: Record<string, React.ReactNode> = {
  random_baseline: <Shuffle size={16} className="text-ash-400" />,
  weighted_rules: <Zap size={16} className="text-yellow-400" />,
  graph_enhanced: <TrendingUp size={16} className="text-blue-400" />,
  user_feedback: <Users size={16} className="text-emerald-400" />,
};

const STRATEGY_COLORS: Record<string, string> = {
  random_baseline: "bg-ash-600",
  weighted_rules: "bg-yellow-600",
  graph_enhanced: "bg-blue-600",
  user_feedback: "bg-emerald-600",
};

export default function EvaluationPage() {
  const [nBuilds, setNBuilds] = useState(100);

  const { data: eval_data, isLoading: evalLoading, refetch, isFetching } = useQuery({
    queryKey: ["evaluation", nBuilds],
    queryFn: () => fetchEvaluation(nBuilds),
    staleTime: 1000 * 60 * 5,
  });

  const { data: stats } = useQuery({
    queryKey: ["feedback-stats"],
    queryFn: fetchFeedbackStats,
    refetchInterval: 30000,
  });

  const strategies = eval_data?.strategies
    ? Object.entries(eval_data.strategies as Record<string, any>)
    : [];

  const maxCombined = strategies.length
    ? Math.max(...strategies.map(([, s]) => s.combined_score))
    : 1;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <BarChart2 size={28} className="text-blood-400" />
          <h1 className="font-display text-5xl tracking-widest text-white uppercase">
            System <span className="text-blood-500">Evaluation</span>
          </h1>
        </div>
        <p className="text-ash-400 font-body">
          Measures how much better graph-enhanced and user-feedback recommendations
          are vs. a random baseline
        </p>
      </div>

      {/* Feedback stats row */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {[
            { label: "Builds Generated", value: stats.by_type?.generated ?? 0 },
            { label: "Builds Saved", value: stats.by_type?.saved ?? 0 },
            { label: "Builds Rerolled", value: stats.by_type?.rerolled ?? 0 },
            { label: "Affinity Pairs", value: stats.affinity_pairs_computed ?? 0 },
          ].map(({ label, value }) => (
            <div key={label} className="card p-4 text-center">
              <p className="font-display text-3xl text-white">{value.toLocaleString()}</p>
              <p className="text-ash-500 text-xs font-mono mt-1 uppercase tracking-widest leading-tight">
                {label}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* How it works */}
      <div className="card p-5 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Info size={14} className="text-ash-500" />
          <span className="text-ash-400 text-xs font-mono uppercase tracking-widest">
            How scores are calculated
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {eval_data?.metrics_explained &&
            Object.entries(eval_data.metrics_explained as Record<string, string>).map(
              ([key, desc]) => (
                <div key={key}>
                  <p className="text-white text-xs font-mono font-semibold mb-1">
                    {key.replace(/_/g, " ").toUpperCase()}
                  </p>
                  <p className="text-ash-400 text-xs font-body leading-relaxed">{desc}</p>
                </div>
              )
            )}
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-ash-400 text-xs font-mono">Sample size:</span>
          {[50, 100, 200].map((n) => (
            <button
              key={n}
              onClick={() => setNBuilds(n)}
              className={clsx(
                "px-3 py-1 text-xs font-mono border transition-all",
                nBuilds === n
                  ? "bg-blood-900/50 border-blood-700 text-blood-300"
                  : "bg-ash-950 border-ash-800 text-ash-500 hover:border-ash-600 hover:text-ash-300"
              )}
            >
              {n}
            </button>
          ))}
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="btn-ghost flex items-center gap-2 text-xs py-1.5 px-3 ml-auto"
        >
          <RefreshCw size={12} className={clsx(isFetching && "animate-spin")} />
          Rerun
        </button>
      </div>

      {/* Strategy comparison */}
      {evalLoading || isFetching ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-ash-900 animate-pulse rounded" />
          ))}
        </div>
      ) : strategies.length > 0 ? (
        <div className="space-y-3">
          {strategies.map(([key, strategy]) => (
            <StrategyCard
              key={key}
              stratKey={key}
              strategy={strategy}
              maxCombined={maxCombined}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 card">
          <p className="font-display text-2xl text-ash-600 tracking-widest">NO DATA YET</p>
          <p className="text-ash-600 text-sm font-mono mt-2">
            Load perks and run a Nightlight sync first, then come back here.
          </p>
        </div>
      )}

      {/* Top saved combos */}
      {stats?.top_saved_combos?.length > 0 && (
        <div className="mt-8">
          <h2 className="font-display text-2xl tracking-widest text-white mb-4 uppercase">
            Most Saved Combinations
          </h2>
          <div className="space-y-2">
            {stats.top_saved_combos.map((combo: any, i: number) => (
              <div key={i} className="card p-3 flex items-center justify-between">
                <p className="text-ash-300 text-xs font-mono truncate flex-1 mr-4">
                  {combo.key.split(",").join(" + ")}
                </p>
                <span className="text-blood-400 text-sm font-mono font-semibold whitespace-nowrap">
                  {combo.count}× saved
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StrategyCard({
  stratKey,
  strategy,
  maxCombined,
}: {
  stratKey: string;
  strategy: any;
  maxCombined: number;
}) {
  const barWidth = maxCombined > 0 ? (strategy.combined_score / maxCombined) * 100 : 0;
  const isBaseline = stratKey === "random_baseline";
  const improvement = strategy.improvement_vs_random;

  return (
    <div className={clsx("card p-5", !isBaseline && strategy.combined_score > 0 && "border-ash-700/80")}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {STRATEGY_ICONS[stratKey]}
          <span className="font-body font-semibold text-white">{strategy.label}</span>
          {stratKey === "user_feedback" && strategy.sample_size !== undefined && (
            <span className="text-ash-600 text-xs font-mono">
              ({strategy.sample_size} saved builds)
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {!isBaseline && improvement !== undefined && (
            <span className={clsx(
              "text-sm font-mono font-semibold",
              improvement > 0 ? "text-emerald-400" : improvement < 0 ? "text-blood-400" : "text-ash-500"
            )}>
              {improvement > 0 ? "+" : ""}{improvement}% vs baseline
            </span>
          )}
          <span className="font-display text-2xl text-white">
            {(strategy.combined_score * 100).toFixed(1)}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-ash-900 w-full mb-3">
        <div
          className={clsx("h-full transition-all duration-500", STRATEGY_COLORS[stratKey] || "bg-ash-600")}
          style={{ width: `${barWidth}%` }}
        />
      </div>

      {/* Sub-metrics */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Pick Rate", value: strategy.pick_rate_score },
          { label: "Synergy", value: strategy.synergy_score },
          { label: "Combined", value: strategy.combined_score },
        ].map(({ label, value }) => (
          <div key={label}>
            <p className="text-ash-600 text-xs font-mono uppercase tracking-widest">{label}</p>
            <p className="text-ash-200 text-sm font-mono mt-0.5">
              {value !== undefined ? (value * 100).toFixed(2) : "—"}
            </p>
          </div>
        ))}
      </div>

      {strategy.n > 0 && (
        <p className="text-ash-700 text-xs font-mono mt-2">n={strategy.n} builds sampled</p>
      )}
    </div>
  );
}
