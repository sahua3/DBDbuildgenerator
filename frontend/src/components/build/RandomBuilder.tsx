import { Shuffle } from "lucide-react";
import { useBuildStore } from "../../store/buildStore";

const FLAVOR_TEXTS = [
  "The Entity decides your fate.",
  "Trust the fog.",
  "No plan. No meta. Pure chaos.",
  "Let RNGesus take the wheel.",
  "Behaviour-approved loadout.",
  "What could possibly go wrong?",
  "A surprise tool that will help us later.",
];

interface RandomBuilderProps {
  onGenerate: () => void;
}

export default function RandomBuilder({ onGenerate }: RandomBuilderProps) {
  const { isGenerating } = useBuildStore();
  const flavor = FLAVOR_TEXTS[Math.floor(Math.random() * FLAVOR_TEXTS.length)];

  return (
    <div className="space-y-6 text-center py-4">
      {/* Big shuffle icon */}
      <div className="flex flex-col items-center gap-3">
        <div className="relative w-20 h-20 flex items-center justify-center border border-ash-700 bg-ash-950">
          <Shuffle size={36} className="text-ash-400" />
          <div
            className="absolute inset-0 opacity-10"
            style={{
              background:
                "radial-gradient(ellipse at center, var(--color-blood) 0%, transparent 70%)",
            }}
          />
        </div>
        <p className="text-ash-500 text-sm font-mono italic">"{flavor}"</p>
      </div>

      <div>
        <p className="text-ash-300 text-sm font-body leading-relaxed max-w-xs mx-auto">
          4 perks chosen at random from your available pool. No categories, no
          synergies, no mercy.
        </p>
      </div>

      <button
        onClick={onGenerate}
        disabled={isGenerating}
        className="btn-primary w-full flex items-center justify-center gap-2 py-4 text-base tracking-widest font-display"
      >
        {isGenerating ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ROLLING THE DICE...
          </>
        ) : (
          <>
            <Shuffle size={16} />
            RANDOMIZE BUILD
          </>
        )}
      </button>

      <p className="text-ash-700 text-xs font-mono">
        Respects your "owned perks only" filter
      </p>
    </div>
  );
}
