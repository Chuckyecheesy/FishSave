"""
Generate a spoken-friendly explanation of why and how specific policy
implementations can reduce overfishing, and by how much, using Cohere.

Intended use:
- Run this script to produce a short, coherent explanation text.
- Pipe the text into ElevenLabs (or another TTS service) to generate audio
  for policymakers or the general public.

Requires:
    pip install cohere python-dotenv

Environment:
    COHERE_API_KEY must be set in .env or the environment.

Usage examples:
    python explain_policy_impact_for_elevenlabs.py "Brazil" 5 0.49 \
        "Implement temporary seasonal fishing closures" \
        "Tighten gear restrictions to reduce bycatch" \
        "Strengthen local enforcement of maritime boundaries"

    # Use a 10-year horizon:
    python explain_policy_impact_for_elevenlabs.py "Japan" 10 0.62 \
        "Phase out harmful fuel subsidies for industrial fleets" \
        "Expand marine protected areas in key spawning grounds" \
        "Increase at-sea inspections and electronic monitoring coverage"
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None


def _load_cohere_client():
    """Return an initialised Cohere client or exit with a clear message."""
    load_dotenv()
    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        raise SystemExit("COHERE_API_KEY not set in environment or .env")

    try:
        import cohere
    except ImportError:
        raise SystemExit("cohere package not installed. Run: pip install cohere")

    return cohere.Client(api_key=api_key)


def build_agent_prompt(
    country: str,
    horizon_years: int,
    risk_score: float,
    policies: list[str],
) -> str:
    """
    Build the agent-style prompt that explains why and how the policies
    reduce overfishing and by how much, using the agreed quantitative model.
    """
    risk_score = float(risk_score)
    horizon_years = int(horizon_years)
    num_policies = len(policies)

    # Quantitative model logic:
    # Full set of 3 reduces 1/3 of headroom. Single reduces 1/9.
    headroom_factor = 3.0 if num_policies >= 3 else (9.0 if num_policies == 1 else 3.0 * (3.0/num_policies))
    
    risk_reduction_percent = ((1.0 - risk_score) / headroom_factor) * 100.0
    risk_reduction_str = f"{risk_reduction_percent:.1f}"

    policies_text = ""
    if num_policies == 1:
        policies_text = f"The specific policy implementation is: {policies[0]}"
        recommendation_label = "this recommendation"
        count_label = "one measure"
    else:
        policies_text = "The policy implementation recommendations are:\n" + "\n".join(f"- {p}" for p in policies)
        recommendation_label = f"these {num_policies} recommendations"
        count_label = f"{num_policies} measures"

    prompt = f"""You are an expert in fisheries science and fisheries policy communication. Your job is to explain to decision‑makers and the general public why and how specific policy implementations can reduce overfishing, and by how much they can reduce overfishing risk, based on a simple quantitative model.

Context

- Country: {country}
- Time horizon: {horizon_years} years
- Current overfishing risk score (between 0 and 1, higher = more risk): {risk_score:.3f}
- Policy Implementation:
{policies_text}

We use a simple interpretability model for the potential risk reduction if {recommendation_label} is implemented effectively:

- The estimated potential reduction in fish inflation risk due to overfishing under this model is approximately {risk_reduction_str}%.
- This represents the idea that {count_label} can, in expectation, reduce a proportional part of the remaining “headroom” between the current risk level and zero risk.

Your tasks

1. Explain why the policy helps
   - In 2–4 short paragraphs or 3–5 concise bullet points, explain mechanistically how {count_label} can reduce overfishing in {country}.
   - Focus on mechanisms such as:
     * Limiting fishing effort or capacity
     * Changing economic incentives (subsidies, costs, prices)
     * Protecting key habitats or spawning seasons
     * Improving monitoring, control, and enforcement
   - Tailor the explanation to the given country and {horizon_years}-year horizon where relevant.

2. State the expected reduction clearly
   - Include a sentence that explicitly states something like:
     "Under our simple model, implementing {recommendation_label} in {country} over the next {horizon_years} years could reduce the inflation risk of fish associated with overfishing by approximately {risk_reduction_str}%."
   - Make it clear that this is a model‑based, illustrative estimate, not a guaranteed outcome.

Tone and constraints

- Use clear, non‑technical language suitable for policymakers and informed citizens.
- Be honest about uncertainty.
- Do not output formulas or equations; only output the final explanation text with the computed percentage embedded.
- EXTREMELY IMPORTANT: Only explain the policy provided. Do not mention other policies.

Output format

Return a short, coherent explanation in natural language with:
- A brief opening sentence summarising how the policy reduces overfishing in {country}.
- A short explanation (paragraphs or bullet list) of the key mechanisms.
- A closing sentence that states the estimated risk reduction as:
  "Due to lower overfishing activity, this corresponds to an estimated reduction in the inflation change correlated with overfishing of about {risk_reduction_str}%"
"""
    return prompt


def run(country: str, horizon_years: int, risk_score: float, policies: list[str]) -> str:
    """Call Cohere with the constructed prompt and return the explanation text."""
    co = _load_cohere_client()
    prompt = build_agent_prompt(country, horizon_years, risk_score, policies)

    # Use chat so the output is a single coherent explanation suitable for TTS.
    try:
        # Prefer more powerful models first
        response = co.chat(message=prompt, model="command-r-plus")
        text = (response.text or "").strip()
        if text: return text
    except Exception:
        try:
            response = co.chat(message=prompt, model="command-a-03-2025")
            text = (response.text or "").strip()
            if text: return text
        except Exception:
            response = co.chat(message=prompt, model="command")
            return (response.text or "").strip()

    return ""


from typing import List, Optional

def main(argv: Optional[List[str]] = None) -> None:
    """
    CLI entry point.

    Arguments:
        country        (str)  - country name
        horizon_years  (int)  - 5 or 10
        risk_score     (float) - current risk score in [0, 1]
        policy_1       (str)  - first policy recommendation
        policy_2       (str)  - second policy recommendation
        policy_3       (str)  - third policy recommendation
    """
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) < 6:
        prog = Path(sys.argv[0]).name
        msg = (
            f"Usage: python {prog} <country> <horizon_years> <risk_score> "
            "<policy_1> <policy_2> <policy_3>\n"
            "Example:\n"
            f"  python {prog} \"Brazil\" 5 0.49 "
            "\"Implement temporary seasonal fishing closures\" "
            "\"Tighten gear restrictions to reduce bycatch\" "
            "\"Strengthen local enforcement of maritime boundaries\""
        )
        raise SystemExit(msg)

    country = argv[0]
    horizon_years = int(argv[1])
    risk_score = float(argv[2])
    policies = argv[3:6]

    explanation = run(country, horizon_years, risk_score, policies)
    if not explanation:
        raise SystemExit("No explanation text generated from Cohere.")

    # Print plain text so ElevenLabs (or any TTS) can read from stdout.
    print(explanation)


if __name__ == "__main__":
    main()

