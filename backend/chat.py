"""
AgriMind AI – Chat Module
Calls the Groq API with RAG-retrieved context injected into the
system prompt for grounded, accurate agricultural advice.
"""

from __future__ import annotations
import os
import logging
from typing import List

import asyncio
from groq import Groq

from .rag import rag_engine

logger = logging.getLogger(__name__)

MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # Can be overridden via .env
MAX_TOKENS = 1024

logger.info("Using Groq model: %s", MODEL)


def _model_candidates() -> List[str]:
    """Return ordered model candidates for Groq requests.

    Priority:
    1) GROQ_MODEL
    2) GROQ_MODEL_FALLBACKS (comma-separated)
    3) hardcoded safety fallback list
    """
    configured = [MODEL]

    from_env = os.getenv("GROQ_MODEL_FALLBACKS", "")
    parsed = [m.strip() for m in from_env.split(",") if m.strip()]

    safety = [
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
    ]

    # Preserve order while removing duplicates
    out: List[str] = []
    seen: set[str] = set()
    for m in configured + parsed + safety:
        if m not in seen:
            out.append(m)
            seen.add(m)
    return out

BASE_SYSTEM = """You are AgriMind AI — a professional agricultural advisor with expertise in crop science, soil management, water engineering, pest control, and sustainable farming.

## CRITICAL INSTRUCTIONS

Only answer agriculture-related questions. For non-agriculture topics, say: "I specialize in agriculture. Let's focus on your farming challenge."

## RESPONSE FORMAT

Always use these sections:

### 🔍 Analysis
Summarize the situation and your assessment.

### 📋 Action Plan
Numbered steps for sequences; bullets for parallel tasks.
**Always include specifics:**
- Quantity (kg/ha, L/1000m², cm spacing)
- Timing (DAS, months, growth stages)
- Product names and rates
- Expected outcomes

### ⚠️ Risks to Watch
1–3 specific threats for this situation.

### 💡 Pro Insight
One practical tip farmers often miss.

---

## QUALITY STANDARDS

✓ Professional scientific language, stay accessible
✓ Reference provided weather data
✓ Cite knowledge base figures
✓ Ground in proven practices
✓ Concise and complete
✓ Admit knowledge limits

## KNOWLEDGE BASE
{rag_context}
"""


def _build_system(query: str, weather_ctx: str) -> str:
    """Build the final system prompt with RAG context injected."""
    rag_context = rag_engine.retrieve(query, top_k=5)

    context_block = ""
    if rag_context:
        context_block = rag_context
    else:
        context_block = "(No specific database entries retrieved — use your expert knowledge.)"

    system = BASE_SYSTEM.format(rag_context=context_block)

    if weather_ctx:
        system += f"\n\n## Live Weather Data\n{weather_ctx}\n"

    return system


def _synthesize_from_rag(user_message: str, weather_ctx: str) -> str:
    """Create a safe, structured reply using only RAG context and simple heuristics.

    This fallback runs when the Groq API is unavailable so the frontend still
    receives actionable advice.
    """
    rag_context = rag_engine.retrieve(user_message, top_k=5)
    if not rag_context:
        rag_context = "(No specific database entries retrieved — use practical farming best-practices.)"

    # Build a simple structured response
    analysis = f"Based on your question: '{user_message[:200]}', here is a short assessment."

    recommendations = []
    # Extract some lines from rag_context to form recommendations
    for part in rag_context.split('\n'):
        part = part.strip()
        if not part:
            continue
        # Take up to 4 recommendation-like lines
        if len(recommendations) >= 4:
            break
        if part.lower().startswith("q:"):
            continue
        recommendations.append(part)

    if not recommendations:
        recommendations = [
            "Follow local agronomic guidance: test soil, use balanced fertiliser, and rotate crops.",
            "Use drip irrigation where possible to conserve water and improve yields.",
        ]

    risks = [
        "Monitor for pests and disease regularly — early detection reduces losses.",
        "Avoid overwatering during heavy rain forecasts to prevent root disease.",
    ]

    pro_tip = "Soil testing every 2 years and using cover crops will improve long-term fertility."

    # Compose the markdown reply consistent with system format
    reply_lines = [
        "### 🔍 Analysis",
        analysis,
        "",
        "### 📋 Action Plan",
    ]
    for i, r in enumerate(recommendations, start=1):
        reply_lines.append(f"{i}. {r}")

    reply_lines += ["", "### ⚠️ Risks to Watch"]
    for r in risks[:3]:
        reply_lines.append(f"- {r}")

    reply_lines += ["", "### 💡 Pro Insight", pro_tip]

    # Include RAG context at the end for transparency
    reply_lines += ["", "---", "## RAG Context", rag_context]

    if weather_ctx:
        reply_lines += ["", "## Live Weather Data", weather_ctx]

    return "\n\n".join(reply_lines)


async def chat(
    messages: List[dict],
    weather_context: str = "",
) -> str:
    """
    Send a conversation to Groq and return the assistant reply.

    Args:
        messages: List of {"role": "user"|"assistant", "content": str}
        weather_context: Optional weather string to inject into system prompt.

    Returns:
        The assistant's reply as a string.
    """
    # Use the last user message to retrieve RAG context
    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set — using RAG-only fallback reply.")
        return _synthesize_from_rag(last_user, weather_context)

    client = Groq(api_key=api_key)

    system_prompt = _build_system(last_user, weather_context)

    # Filter to valid roles only and ensure alternation
    clean_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]

    # Groq requires system message as first message in array
    messages_with_system = [
        {"role": "system", "content": system_prompt}
    ] + clean_messages

    # Try the request with model fallback + simple retry logic for transient errors.
    models = _model_candidates()
    logger.info("Trying Groq models in order: %s", ", ".join(models))

    max_attempts = 3
    for model_name in models:
        backoff = 1.0
        for attempt in range(1, max_attempts + 1):
            try:
                # Run blocking client call in a thread to avoid blocking the event loop
                response = await asyncio.to_thread(
                    lambda: client.chat.completions.create(
                        model=model_name,
                        max_tokens=MAX_TOKENS,
                        messages=messages_with_system,
                    )
                )
                # Normalise different response shapes and return text
                try:
                    return response.choices[0].message.content
                except Exception:
                    return str(response)

            except Exception as exc:
                err_text = str(exc)
                logger.warning(
                    "Groq request failed for model '%s' (attempt %s/%s): %s",
                    model_name,
                    attempt,
                    max_attempts,
                    err_text,
                )

                # Decommissioned/unavailable model: switch to next model immediately
                if "model_decommissioned" in err_text or "decommissioned" in err_text or "not found" in err_text:
                    logger.warning("Model '%s' unavailable. Trying next model.", model_name)
                    break

                # Bad request (client input issue): no need to keep retrying models
                if "400" in err_text or "Bad Request" in err_text:
                    logger.error("Groq request invalid. Falling back to RAG-only reply: %s", err_text)
                    return _synthesize_from_rag(last_user, weather_context)

                # For transient failures, retry this model a few times
                if attempt < max_attempts:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

                # Last attempt on this model failed; move to next model
                logger.warning("Model '%s' failed after %s attempts. Trying next model.", model_name, max_attempts)

    logger.error("All Groq models failed. Falling back to RAG-only reply.")
    return _synthesize_from_rag(last_user, weather_context)