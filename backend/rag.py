"""
AgriMind AI – RAG Engine
Loads agricultural knowledge from curated built-in knowledge base,
then retrieves the most relevant chunks for each query.
"""

from __future__ import annotations
import logging
import os
from typing import List, Dict
import warnings

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Suppress HuggingFace dataset warnings
warnings.filterwarnings("ignore", message=".*trust_remote_code.*")
warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Built-in curated agriculture knowledge base
# Covers: crops, soil, irrigation, pests, fertiliser, weather, seasons, etc.
# ─────────────────────────────────────────────────────────────────────────────
BUILTIN_KNOWLEDGE: List[Dict[str, str]] = [
    # ── Soil types ──────────────────────────────────────────────────────────
    {"q": "What crops grow best in clay soil?",
     "a": "Clay soil retains water well and suits rice, wheat, cabbage, broccoli, and legumes. "
          "Improve drainage by adding organic compost before planting. Avoid root vegetables like "
          "carrots as they struggle in heavy clay."},
    {"q": "What crops grow best in sandy soil?",
     "a": "Sandy soil drains quickly and warms fast. Best choices: carrots, potatoes, strawberries, "
          "peanuts, watermelon, and sweet potatoes. Add compost or manure every season to build "
          "organic matter. Drip irrigation is essential to offset rapid moisture loss."},
    {"q": "What crops grow best in loamy soil?",
     "a": "Loamy soil is the gold standard—it suits almost every crop. Top performers: maize, "
          "wheat, soybeans, tomatoes, peppers, and most vegetables. Maintain fertility with "
          "balanced NPK (20-10-10) and rotate crops annually."},
    {"q": "What crops suit silty soil?",
     "a": "Silty soil is fertile and moisture-retentive. Great for: grapes, vegetables, fruits, "
          "and moisture-loving crops. Avoid compaction by minimising heavy machinery use. "
          "Add coarse sand or organic matter to improve aeration."},
    {"q": "How do I test my soil pH?",
     "a": "Use a home soil pH kit or digital meter. Most crops prefer pH 6.0–7.0. "
          "To raise pH (acidic soil): add agricultural lime at 1–2 tonnes/ha. "
          "To lower pH (alkaline soil): apply elemental sulphur at 200–500 kg/ha. "
          "Test soil every 2 years."},

    # ── Crop-specific advice ─────────────────────────────────────────────────
    {"q": "How to maximise maize yield?",
     "a": "Plant in rows 75 cm apart, seeds 25 cm apart. Apply nitrogen at 120–150 kg/ha split "
          "across 3 stages: planting, knee-high, and silking. Keep soil moist during tasselling "
          "and silking—this is the critical water window. Target yield: 8–10 tonnes/ha under "
          "good management."},
    {"q": "How to grow wheat successfully?",
     "a": "Sow at 100–120 kg seed/ha in well-prepared loamy soil. Apply 60 kg N/ha at sowing "
          "and 40 kg N/ha at tillering. Irrigate 4–5 times at critical stages: crown root "
          "initiation, tillering, jointing, flowering, and grain filling. Watch for rust diseases; "
          "spray propiconazole 0.1% at first sign."},
    {"q": "Best practices for rice cultivation?",
     "a": "Transplant 25-day-old seedlings at 20×15 cm spacing. Maintain 5 cm standing water "
          "during vegetative stage. Apply 120 kg N/ha (split 3 times), 60 kg P2O5, and 40 kg "
          "K2O/ha. Drain fields 10 days before harvest. Common pests: stem borer (use carbofuran) "
          "and blast fungus (use tricyclazole)."},
    {"q": "How to grow tomatoes for maximum yield?",
     "a": "Use raised beds in well-drained soil. Plant seedlings 45–60 cm apart. Apply drip "
          "irrigation; tomatoes need 400–600 mm/season. Use NPK 12-24-12 at transplanting, "
          "then switch to high-K fertiliser (potassium nitrate) at flowering. Stake plants at "
          "30 cm height. Watch for early blight; spray mancozeb weekly in humid conditions."},
    {"q": "How to grow soybeans?",
     "a": "Inoculate seed with Bradyrhizobium japonicum before planting to boost nitrogen fixation. "
          "Sow at 8–10 cm depth, 5 cm apart in 45 cm rows. Needs 450–700 mm rainfall/season. "
          "Avoid excess nitrogen fertiliser—the bacteria fix 50–200 kg N/ha naturally. "
          "Harvest when 95% of pods turn brown."},
    {"q": "Tips for growing potatoes",
     "a": "Plant certified seed potatoes (60–80 g each) in ridges 75 cm apart, 30 cm between "
          "plants. Earth up twice to prevent greening. Apply 150 kg N/ha in 2 splits. "
          "Potatoes need 500–700 mm water/season. Main threats: late blight (Phytophthora)—"
          "apply chlorothalonil every 7–10 days in wet weather; and aphids carrying viruses."},

    # ── Fertiliser ───────────────────────────────────────────────────────────
    {"q": "What is NPK fertiliser and how do I use it?",
     "a": "NPK stands for Nitrogen (N), Phosphorus (P), Potassium (K). "
          "N drives leaf growth; apply urea (46% N) at 100–150 kg/ha. "
          "P promotes root and flower development; use DAP (18-46-0) at 50–100 kg/ha at sowing. "
          "K improves disease resistance and fruit quality; apply MOP (60% K2O) at 50–100 kg/ha. "
          "Always split N applications to reduce leaching."},
    {"q": "How to use organic fertilisers?",
     "a": "Farmyard manure (FYM): apply 10–15 tonnes/ha 4 weeks before sowing. "
          "Compost: apply 5–8 tonnes/ha; improves soil structure and adds micronutrients. "
          "Vermicompost: 2–3 tonnes/ha; highly bioavailable nutrients. "
          "Green manure (e.g., dhaincha): plough in at 45 days to add 60–80 kg N/ha equivalent. "
          "Organic sources improve soil health long-term better than synthetic fertilisers."},
    {"q": "How to improve nitrogen in soil naturally?",
     "a": "Plant legumes (beans, peas, lentils, clover) in rotation—they fix 50–200 kg N/ha/year. "
          "Apply compost or well-rotted manure. Use green manure crops like sunn hemp or mucuna. "
          "Maintain soil pH 6.0–6.5 to optimise bacterial activity. "
          "Avoid over-tilling which destroys nitrogen-fixing bacteria."},

    # ── Irrigation ───────────────────────────────────────────────────────────
    {"q": "What irrigation method is most water-efficient?",
     "a": "Drip irrigation is most efficient (90–95% efficiency) vs flood (40–60%) and sprinkler "
          "(70–80%). It delivers water directly to the root zone, reduces weed growth, and lowers "
          "disease pressure from leaf wetness. Initial cost is higher but saves 30–50% water. "
          "Suitable for vegetables, orchards, and row crops."},
    {"q": "How often should I irrigate wheat?",
     "a": "Wheat needs 5–6 irrigations: (1) crown root initiation (20–25 DAS), "
          "(2) tillering (40–45 DAS), (3) jointing (60–65 DAS), "
          "(4) flowering (80–85 DAS), (5) grain filling (100–105 DAS), "
          "and optionally one at milky stage. Each irrigation: 50–60 mm. "
          "Skip irrigation if rainfall exceeds 25 mm within 5 days."},
    {"q": "How do I schedule irrigation based on weather?",
     "a": "Use the formula: Net irrigation = ETc – Effective Rainfall. "
          "ETc (crop evapotranspiration) = Kc × ETo. "
          "When rainfall exceeds 20 mm, withhold next irrigation by 5–7 days. "
          "High temperature (>35°C) increases water demand by 20–30%—irrigate more frequently. "
          "Install a rain gauge and soil moisture sensor for precision scheduling."},

    # ── Pest and disease control ─────────────────────────────────────────────
    {"q": "How to control aphids on crops?",
     "a": "Aphids suck sap and spread viruses. Spray neem oil (0.5%) or insecticidal soap as "
          "a first line. For severe infestations use imidacloprid 17.8 SL at 0.3 ml/litre or "
          "dimethoate 30 EC at 1.5 ml/litre. Encourage natural predators: ladybugs and lacewings. "
          "Yellow sticky traps monitor population levels. Avoid excessive nitrogen fertiliser "
          "which produces soft growth that attracts aphids."},
    {"q": "How to prevent and treat fungal diseases in crops?",
     "a": "Prevention: ensure good air circulation with correct plant spacing; avoid overhead "
          "irrigation; use resistant varieties. Treatment: powdery mildew—spray sulphur 80% WP "
          "at 2 g/litre. Early blight—mancozeb 75% WP at 2.5 g/litre every 10 days. "
          "Downy mildew—metalaxyl + mancozeb at 2.5 g/litre. "
          "Spray in the morning; do not apply when temperature exceeds 35°C."},
    {"q": "How to control stem borers in maize and rice?",
     "a": "Apply carbofuran 3G granules at 16–20 kg/ha in the leaf whorl at 20–25 DAS. "
          "Or spray chlorpyrifos 20 EC at 2.5 ml/litre. "
          "Biological control: Trichogramma card (50,000 eggs/ha) at weekly intervals. "
          "Pheromone traps (5/ha) to monitor adult moth populations. "
          "Remove and destroy infested tillers immediately."},
    {"q": "How to control weeds organically?",
     "a": "Mulching with straw (5–10 cm) suppresses 80–90% of weeds and retains moisture. "
          "Inter-row cultivation with a hand hoe at 2–3 week intervals. "
          "Cover crops (e.g., rye, clover) outcompete weeds between cash crop rows. "
          "Flame weeding works for pre-emergence control in vegetable rows. "
          "Proper crop spacing creates canopy cover that shades out weed seedlings."},

    # ── Weather & climate adaptation ─────────────────────────────────────────
    {"q": "What should I do before heavy rainfall?",
     "a": "Do NOT apply fertiliser 48 hours before heavy rain—it will leach. "
          "Do NOT spray pesticides—rain will wash them off. "
          "Check field drainage channels are clear. "
          "If harvesting is near, prioritise cutting before rain arrives. "
          "Stake tall crops (tomatoes, maize) to prevent lodging. "
          "Harvest mature vegetables before waterlogging damages quality."},
    {"q": "How to manage crops during drought?",
     "a": "Prioritise water to crops at critical growth stages (flowering, grain fill). "
          "Apply mulch to reduce evaporation by 30–40%. "
          "Switch to drought-tolerant varieties: sorghum, millet, cowpea. "
          "Reduce plant density to lower water demand. "
          "Apply potassium fertiliser to improve drought tolerance. "
          "Consider rainwater harvesting using check dams and farm ponds."},
    {"q": "How does high humidity affect crops?",
     "a": "High humidity (>80%) dramatically increases fungal disease risk—especially "
          "blight, mildew, and botrytis. Actions: increase plant spacing for airflow; "
          "switch to drip irrigation (keeps foliage dry); apply preventive fungicides; "
          "harvest in the morning when humidity is lower. "
          "Monitor crops daily during humid spells and act quickly at first signs of disease."},
    {"q": "How to protect crops from frost?",
     "a": "Cover sensitive crops with frost cloth or polythene sheets the evening before frost. "
          "Apply irrigation at night—water releases heat as it freezes (latent heat). "
          "Smoke pots or wind machines circulate warmer air. "
          "Plant cold-tolerant varieties: kale, cabbage, spinach, and Brussels sprouts survive "
          "light frosts. Avoid frost-sensitive crops (tomatoes, beans, cucumbers) when frost "
          "is forecast within 2 weeks."},

    # ── Crop rotation & soil health ──────────────────────────────────────────
    {"q": "Why is crop rotation important and how do I plan it?",
     "a": "Rotation breaks pest and disease cycles, reduces fertiliser needs, and improves "
          "soil structure. A good 4-year rotation: "
          "Year 1: Cereal (wheat/maize) → Year 2: Legume (soybean/groundnut) → "
          "Year 3: Root vegetable (potato/carrot) → Year 4: Brassica (cabbage/canola). "
          "Never grow the same family in the same field two years in a row. "
          "Legumes preceding cereals provide 40–60 kg/ha free nitrogen."},
    {"q": "How to improve soil organic matter?",
     "a": "Add compost at 5–10 tonnes/ha annually. Incorporate crop residues instead of burning. "
          "Plant cover crops (rye, vetch, clover) and plough in before flowering. "
          "Reduce tillage—no-till farming increases organic matter 0.1% per year. "
          "Apply biochar at 5–10 tonnes/ha to permanently improve carbon content. "
          "Soil organic matter above 3% dramatically improves water holding capacity and "
          "nutrient availability."},

    # ── Planting calendars ───────────────────────────────────────────────────
    {"q": "When is the best time to plant in tropical climates?",
     "a": "Tropical regions generally have two seasons—wet (main season) and dry (off-season). "
          "Main season: plant 2 weeks after rains begin (April–May or October–November). "
          "Off-season: use irrigation; plant drought-tolerant crops. "
          "Avoid planting just before peak rainfall—fields can waterlog. "
          "Check your local agro-meteorological bulletin for precise onset of rains."},
    {"q": "Best planting time for subtropical climates?",
     "a": "Spring crops (after last frost): tomatoes, maize, soybeans, groundnuts. "
          "Summer: fast-maturing vegetables (okra, cowpea, cucumber). "
          "Autumn: wheat, barley, mustard. "
          "Winter (mild subtropics): leafy vegetables, peas, onions. "
          "Avoid frost-sensitive crops when minimum temperature is below 5°C."},

    # ── Post-harvest & storage ───────────────────────────────────────────────
    {"q": "How to reduce post-harvest losses in grains?",
     "a": "Dry grains to safe moisture levels: rice 14%, wheat 12%, maize 13.5%. "
          "Use hermetic storage bags (e.g., PICS triple-layer bags) to eliminate grain pests "
          "without chemicals. Fumigate stores with aluminium phosphide (3 tablets/tonne) "
          "before sealing. Store in cool, dry conditions; keep off the ground on pallets. "
          "Inspect monthly for signs of mould, insects, or moisture."},
    {"q": "How to store vegetables after harvest?",
     "a": "Cool immediately after harvest—every hour at field temperature reduces shelf life. "
          "Potatoes: 4–7°C in dark; light causes greening (solanine). "
          "Tomatoes: 12–15°C (never refrigerate—damages flavour). "
          "Leafy vegetables: 0–2°C with high humidity (95%). "
          "Onions: dry, ventilated store at 0–4°C or 25–30°C (avoid 5–18°C which causes sprouting). "
          "Simple evaporative coolers (zeir pot/brick-sand structures) extend shelf life by 10–20 days."},

    # ── Sustainable farming ──────────────────────────────────────────────────
    {"q": "How to farm sustainably and profitably?",
     "a": "Adopt integrated pest management (IPM): biological controls first, chemicals as last resort. "
          "Use precision fertilisation based on soil tests—saves 20–30% fertiliser cost. "
          "Water harvesting and drip irrigation reduce water costs by 40%. "
          "Intercropping (e.g., maize + beans) reduces risk and improves total income per hectare. "
          "Join a cooperative to reduce input costs and access better markets. "
          "Keep farm records to identify profitable enterprises and cut losses."},
    {"q": "What is intercropping and what are the benefits?",
     "a": "Intercropping grows two or more crops simultaneously on the same field. "
          "Common systems: maize + beans (beans fix nitrogen for maize); "
          "sorghum + cowpea (cowpea provides ground cover); "
          "banana + coffee (banana provides shade). "
          "Benefits: 20–40% higher land use efficiency, risk diversification, "
          "natural pest suppression, and improved soil health. "
          "Ensure compatible plant heights and maturity dates to avoid competition."},
]


class AgriRAG:
    """Lightweight TF-IDF based retrieval-augmented generation for agriculture."""

    def __init__(self) -> None:
        self.documents: List[str] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.tfidf_matrix = None
        self._loaded = False

    # ── Public API ─────────────────────────────────────────────────────────

    async def load(self) -> None:
        """Load built-in knowledge + attempt HuggingFace datasets."""
        docs = self._load_builtin()
        docs += await self._load_huggingface()

        self.documents = docs
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=20_000,
            stop_words="english",
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)
        self._loaded = True
        logger.info("AgriRAG ready — %d documents indexed.", len(self.documents))

    def retrieve(self, query: str, top_k: int = 5) -> str:
        """Return the top-k most relevant passages as a formatted context string."""
        if not self._loaded or not self.documents:
            return ""

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = scores.argsort()[-top_k:][::-1]

        # Only include passages with a minimum relevance score
        relevant = [
            self.documents[i]
            for i in top_indices
            if scores[i] > 0.05
        ]

        if not relevant:
            return ""

        return "\n\n---\n\n".join(relevant)

    # ── Private helpers ────────────────────────────────────────────────────

    def _load_builtin(self) -> List[str]:
        """Convert built-in Q&A pairs into retrieval documents."""
        docs = []
        for item in BUILTIN_KNOWLEDGE:
            docs.append(f"Q: {item['q']}\nA: {item['a']}")
        logger.info("Built-in knowledge base: %d entries.", len(docs))
        return docs

    async def _load_huggingface(self) -> List[str]:
        """Try to pull additional datasets from HuggingFace Hub."""
        docs: List[str] = []
        # Only attempt to load HuggingFace datasets when a token is available
        hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HF_API_TOKEN")
        if not hf_token:
            logger.info("No HuggingFace token found; skipping external dataset loads.")
            return docs

        candidates = [
            # (dataset_name, config, split, question_col, answer_col)
            ("Malikeh1375/agricultural-texts-for-ner", None, "train", "tokens", None),
            ("nateraw/agriculture", None, "train", "text", None),
            ("MBZUAI/agriculture-llm-instruction-tuning", None, "train", "instruction", "output"),
        ]

        for name, config, split, q_col, a_col in candidates:
            try:
                from datasets import load_dataset  # type: ignore
                # Avoid 'trust_remote_code' to prevent security/deprecation issues
                kwargs: dict = {"split": split}
                if config:
                    kwargs["name"] = config

                ds = load_dataset(name, **kwargs)

                # Determine how to build text from columns
                if q_col and a_col and q_col in ds.column_names and a_col in ds.column_names:
                    for row in ds.select(range(min(500, len(ds)))):
                        q = str(row.get(q_col, "")).strip()
                        a = str(row.get(a_col, "")).strip()
                        if q and a:
                            docs.append(f"Q: {q}\nA: {a}")
                elif q_col and q_col in ds.column_names:
                    for row in ds.select(range(min(500, len(ds)))):
                        text = str(row.get(q_col, "")).strip()
                        if text:
                            docs.append(text)

                logger.info("HuggingFace dataset '%s': %d docs loaded.", name, len(docs))

            except Exception as exc:
                logger.warning("Could not load HuggingFace dataset '%s': %s", name, exc)

        return docs


# Singleton
rag_engine = AgriRAG()