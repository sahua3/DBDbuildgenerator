"""
AI explanation service.

When ANTHROPIC_API_KEY is set: calls Claude to generate a strategic build explanation.
When not set: returns a detailed hardcoded placeholder explanation.
"""
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


PLACEHOLDER_EXPLANATIONS = [
    """**Build Strategy Overview**

This build is designed around maximizing your efficiency while keeping pressure off your team. Each perk in this loadout has been selected because of its strong synergy with the others — they reward consistent, disciplined play rather than gambling on risky plays.

**How to Play This Build**

Start generators immediately. Your first priority every match should be to identify the 3-gen situation the killer is defending and work around it, not into it. Use your information perks to track the killer's patrol route and coordinate with teammates.

When chased, don't panic — your chase perks extend your survival time significantly. The key is to stay calm, make the killer work for every hit, and buy your teammates enough time to push generators. Every second you spend in chase is a second your team gets on gens.

**Key Interactions to Remember**

Your second-chance perk is not a crutch — treat it as insurance. The moment you start relying on it to survive basic chases, you've already lost. Use it as a clutch escape when the killer outplays you, not as your primary survival tool.

**End Game Advice**

When gates are powered, don't rush the exit. Use your escape perk timing carefully, watch for the killer's position on your aura-reading perk, and exit cleanly. A safe escape is worth more than a flashy play that gets you killed at the gates.""",

    """**Build Strategy Overview**

This is a team-first loadout built for survivors who want to be the backbone of their group. While your individual escape odds are slightly lower than a selfish build, your presence on the team dramatically increases everyone else's survival rate — and that's reflected in your overall escape rate over time.

**How to Play This Build**

Position yourself as the "second responder" — not the first into danger, but always nearby to assist. Keep track of your teammates' hook states. When someone goes down, assess whether you can safely attempt a rescue before committing. A dead rescuer helps no one.

Your healing perks shine most in the mid-game, when the first set of generators are done and the killer is applying hook pressure. This is when your team's health states matter most — get injured survivors back to full before the final push.

**Perk Synergies**

The synergy between your altruism and anti-hook perks is the core of this build. When you unhook a survivor, your anti-hook perk immediately gives them a window to create distance, and your altruism perk rewards you for the rescue. Chain these correctly and you can turn a 2-hook pressure situation into a full team alive pushing final generators.

**Adapting Mid-Match**

If you realize early that your team is struggling and getting hooked repeatedly, shift into pure support mode — forget generators, focus on unhooks and heals. A team that stays alive longer than the killer expects can pull off comebacks that seem impossible on paper.""",

    """**Build Strategy Overview**

This stealth-forward build rewards patience and map awareness above all else. You won't win chases against a skilled killer — and that's fine, because this build is designed to avoid chases entirely. Your goal is to be a ghost: always productive, never spotted.

**Core Philosophy**

Every perk in this build serves one purpose: making you invisible to the killer while you complete objectives. This isn't cowardly play — it's strategic. The killer cannot apply pressure to survivors they cannot find.

**Movement Tips**

Crouch more than you think you need to. Cut scratch marks between generators by crouching over grass and avoiding the killer's patrol path. Learn each map's jungle gym layouts so you can plan your generator rotation before the match even starts.

**When You Get Caught**

If spotted, don't immediately try to loop. Break line of sight and use your stealth perks to reset the chase before it fully begins. An experienced stealth player can turn a "I see you" moment into a confused killer standing alone within 20 seconds.

**Late Game**

Your escape perk is your ace card. Hold it until the gates are powered. In end-game collapse scenarios, this build outperforms almost everything else — you're already hidden, already healthy, and just need to reach the gate.""",
]

_placeholder_index = 0


def get_placeholder_explanation(perks: list[dict], theme: Optional[str] = None) -> str:
    """
    Returns a rotating hardcoded explanation. Replace with real AI when API key is set.
    """
    global _placeholder_index
    perk_names = [p.get("name", "Unknown") for p in perks]
    perk_list = ", ".join(perk_names)

    base = PLACEHOLDER_EXPLANATIONS[_placeholder_index % len(PLACEHOLDER_EXPLANATIONS)]
    _placeholder_index += 1

    header = f"## Build: {perk_list}\n"
    if theme:
        header += f"*Theme: {theme}*\n\n"
    else:
        header += "\n"

    return header + base


async def generate_explanation(
    perks: list[dict],
    theme: Optional[str] = None,
    generation_mode: str = "theme",
) -> str:
    """
    Generate a strategic explanation for a build.
    Uses Claude API if configured, otherwise returns placeholder.
    """
    if not settings.use_real_ai:
        logger.info("No API key — returning placeholder explanation")
        return get_placeholder_explanation(perks, theme)

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        perk_details = "\n".join(
            f"- **{p['name']}** ({', '.join(p.get('categories', []))}): {p['description']}"
            for p in perks
        )

        theme_context = f"The player requested a **{theme}** themed build.\n" if theme else ""

        prompt = f"""You are an expert Dead by Daylight coach helping a survivor player understand their build.

{theme_context}
Here are the 4 perks in this build:

{perk_details}

Write a strategic build guide with these sections:
1. **Build Strategy Overview** — What is the core identity/goal of this build?
2. **How to Play This Build** — Step-by-step gameplay advice for early, mid, and late game
3. **Key Perk Synergies** — Explain exactly how these perks work together (be specific about the mechanics)
4. **Common Mistakes to Avoid** — What misplays negate this build's strengths?
5. **Adapting to Different Killers** — Brief tips on adjusting playstyle vs. different killer types

Use markdown formatting. Be specific, tactical, and helpful. Write for an intermediate player who knows the game but wants to optimize."""

        msg = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    except Exception as e:
        logger.error(f"AI explanation failed: {e}")
        return get_placeholder_explanation(perks, theme)
