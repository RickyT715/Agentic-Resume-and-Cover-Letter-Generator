"""Hybrid Multi-Method ATS (Applicant Tracking System) scoring v2.

Combines 6 scoring approaches based on research into real ATS systems
(Workday, iCIMS, Taleo) and open-source implementations:

1. BM25 Keyword Relevance (20%) — superior to TF-IDF with term saturation + length normalization
2. Semantic Embedding Similarity (20%) — meaning beyond exact words (synonyms, paraphrases)
3. Skill Coverage via PhraseMatcher (30%) — explicit skill overlap from 550+ skill taxonomy
4. Fuzzy Keyword Matching (10%) — abbreviations, typos, variations (K8s→Kubernetes)
5. Resume Quality Heuristics (10%) — action verbs, metrics, sections, format
6. Section-Aware Bonus (10%) — rewards keyword placement in Skills/Summary sections

Key improvements over v1:
- BM25 replaces TF-IDF (handles term frequency saturation, document length normalization)
- Synonym/acronym normalization as pre-processing (AWS↔Amazon Web Services)
- Section-aware scoring (skills section weighted higher than body text)
- Sigmoid calibration instead of linear (better for score clustering)
- Research-backed weight distribution (hard skills 30% highest weight)

Heavy models (spaCy, sentence-transformers) are lazy-loaded as singletons.
"""

import logging
import math
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────

ACTION_VERBS = [
    "achieved",
    "built",
    "created",
    "delivered",
    "designed",
    "developed",
    "engineered",
    "established",
    "implemented",
    "improved",
    "increased",
    "launched",
    "led",
    "managed",
    "optimized",
    "orchestrated",
    "pioneered",
    "reduced",
    "refactored",
    "scaled",
    "spearheaded",
    "streamlined",
    "transformed",
    "architected",
    "automated",
    "collaborated",
    "contributed",
    "deployed",
    "drove",
    "executed",
    "facilitated",
    "generated",
    "initiated",
    "integrated",
    "maintained",
    "mentored",
    "migrated",
    "modernized",
    "resolved",
    "restructured",
    "secured",
    "shipped",
    "standardized",
]

EXPECTED_SECTIONS = ["experience", "education", "skill", "project", "summary", "objective"]

# Section weights for section-aware scoring
SECTION_WEIGHTS = {
    "skills": 0.35,
    "summary": 0.15,
    "objective": 0.15,
    "experience": 0.30,
    "projects": 0.10,
    "education": 0.05,
    "other": 0.05,
}

# BM25 English stop words — removed during tokenization to improve signal-to-noise
_BM25_STOP_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "shall",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "we",
        "you",
        "they",
        "i",
        "he",
        "she",
        "who",
        "which",
        "what",
        "where",
        "when",
        "how",
        "not",
        "no",
        "as",
        "if",
        "so",
        "up",
        "out",
        "about",
        "into",
        "over",
        "after",
    }
)

# Generic words that LLMs commonly extract as "skills" from JDs but aren't actual skills.
# Filtering these prevents inflated denominators and false "missing keywords" in scoring.
JD_SKILL_NOISE = frozenset(
    {
        # Generic verbs/actions
        "build",
        "create",
        "design",
        "develop",
        "implement",
        "manage",
        "maintain",
        "support",
        "work",
        "working",
        "looking",
        "seeking",
        "join",
        "lead",
        "drive",
        "ensure",
        "deliver",
        "contribute",
        # Generic nouns
        "ability",
        "experience",
        "knowledge",
        "understanding",
        "familiarity",
        "proficiency",
        "skills",
        "team",
        "teams",
        "company",
        "role",
        "position",
        "opportunity",
        "environment",
        "solutions",
        "tools",
        "projects",
        "systems",
        "requirements",
        "responsibilities",
        # Filler adjectives
        "strong",
        "excellent",
        "good",
        "proven",
        "relevant",
        "various",
        "complex",
        "multiple",
        "new",
        "key",
        "high",
        "best",
        "flexible",
        "remote",
        "hybrid",
        "onsite",
        # Location/logistics fragments
        "san",
        "york",
        "salary",
        "compensation",
        "budget",
        "schedule",
        "benefits",
        "equity",
        "bonus",
        # Degree/level words
        "degree",
        "bachelor",
        "master",
        "phd",
        "senior",
        "junior",
        "mid",
        "level",
        "years",
        "year",
    }
)


# ── Sigmoid calibration ──────────────────────────────────────────────
# Research shows sigmoid calibration handles score clustering better than
# linear. Most raw scores cluster around 0.1-0.4, and linear mapping
# fails to discriminate well in that range.


def _sigmoid_calibrate(raw: float, center: float = 0.45, steepness: float = 10.0) -> float:
    """Map raw score through a sigmoid curve centered at `center`.

    This provides better discrimination in the typical score range (0.1-0.5)
    and naturally clamps to [0, 1].
    """
    try:
        return 1.0 / (1.0 + math.exp(-steepness * (raw - center)))
    except OverflowError:
        return 0.0 if raw < center else 1.0


def _calibrate_linear(raw: float, low: float, high: float) -> float:
    """Linear calibration fallback: map [low, high] → [0, 1], clamped."""
    if high <= low:
        return raw
    scaled = (raw - low) / (high - low)
    return max(0.0, min(1.0, scaled))


# ── Lazy-loaded singletons ────────────────────────────────────────────

_spacy_nlp = None
_spacy_nlp_zh = None
_sentence_model = None
_sentence_model_zh = None
_jieba_initialized = False


def _get_spacy_nlp():
    """Lazy-load spaCy English model (singleton)."""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy

            _spacy_nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy en_core_web_sm model loaded")
        except Exception as e:
            logger.warning(f"spaCy not available: {e}")
            _spacy_nlp = False  # Sentinel: tried and failed
    return _spacy_nlp if _spacy_nlp is not False else None


def _get_sentence_model():
    """Lazy-load sentence-transformers model (singleton)."""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer all-MiniLM-L6-v2 loaded")
        except Exception as e:
            logger.warning(f"sentence-transformers not available: {e}")
            _sentence_model = False  # Sentinel
    return _sentence_model if _sentence_model is not False else None


def _get_spacy_nlp_zh():
    """Lazy-load spaCy Chinese model (singleton). Falls back to None."""
    global _spacy_nlp_zh
    if _spacy_nlp_zh is None:
        try:
            import spacy

            _spacy_nlp_zh = spacy.load("zh_core_web_sm")
            logger.info("spaCy zh_core_web_sm model loaded")
        except Exception as e:
            logger.warning(f"spaCy Chinese model not available: {e}")
            _spacy_nlp_zh = False
    return _spacy_nlp_zh if _spacy_nlp_zh is not False else None


def _get_sentence_model_zh():
    """Lazy-load Chinese sentence-transformers model (singleton)."""
    global _sentence_model_zh
    if _sentence_model_zh is None:
        try:
            from sentence_transformers import SentenceTransformer

            _sentence_model_zh = SentenceTransformer("BAAI/bge-large-zh-v1.5")
            logger.info("SentenceTransformer BAAI/bge-large-zh-v1.5 loaded")
        except Exception as e:
            logger.warning(f"Chinese sentence-transformers model not available: {e}")
            _sentence_model_zh = False
    return _sentence_model_zh if _sentence_model_zh is not False else None


def _init_jieba():
    """Initialize jieba tokenizer (singleton)."""
    global _jieba_initialized
    if not _jieba_initialized:
        try:
            import jieba

            jieba.initialize()
            _jieba_initialized = True
            logger.info("jieba tokenizer initialized")
        except ImportError:
            logger.warning("jieba not installed, Chinese tokenization unavailable")
    return _jieba_initialized


def _jieba_tokenize(text: str) -> list[str]:
    """Tokenize Chinese text using jieba. Returns list of tokens."""
    try:
        import jieba

        _init_jieba()
        return [w for w in jieba.cut(text) if w.strip()]
    except ImportError:
        # Fallback: character-level splitting for CJK, whitespace for non-CJK
        return text.split()


# ── Data classes ──────────────────────────────────────────────────────


@dataclass
class ATSScoreBreakdown:
    """Detailed ATS score breakdown from the hybrid multi-method scorer."""

    # Primary method scores (weights sum to 1.0)
    keyword_similarity: float = 0.0  # BM25 keyword relevance (was TF-IDF in v1)
    semantic_similarity: float = 0.0  # Sentence embedding similarity
    skill_coverage: float = 0.0  # PhraseMatcher skill overlap
    fuzzy_match: float = 0.0  # Fuzzy keyword matching
    resume_quality: float = 0.0  # Heuristic quality score
    section_bonus: float = 0.0  # Section-aware keyword placement

    # Quality sub-scores (components of resume_quality)
    action_verbs_score: float = 0.0
    quantified_score: float = 0.0
    section_score: float = 0.0
    format_score: float = 0.0

    # Overall weighted score
    overall: float = 0.0

    # Keyword lists
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)

    # Actionable feedback
    feedback: list[str] = field(default_factory=list)

    # ── Backward-compat aliases for old field names ───────────────
    @property
    def keyword_match(self) -> float:
        return self.keyword_similarity

    @property
    def experience_alignment(self) -> float:
        return self.semantic_similarity

    @property
    def action_verbs(self) -> float:
        return self.action_verbs_score

    @property
    def readability(self) -> float:
        return self.quantified_score

    @property
    def section_completeness(self) -> float:
        return self.section_score


# ── Text extraction ───────────────────────────────────────────────────


def _extract_text_from_latex(latex: str) -> str:
    """Strip LaTeX commands to get plain text for analysis."""
    text = latex
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(\[.*?\])?\{([^}]*)\}", r"\2", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}\\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_latex_sections(latex: str) -> dict[str, str]:
    """Extract named sections from LaTeX source.

    Returns a dict mapping section names (lowercase) to their content.
    Used for section-aware scoring.
    """
    sections: dict[str, str] = {}
    # Match \section{Name} or \section*{Name}
    pattern = r"\\section\*?\{([^}]+)\}"
    parts = re.split(pattern, latex, flags=re.IGNORECASE)

    # parts = [preamble, section1_name, section1_content, section2_name, ...]
    for i in range(1, len(parts) - 1, 2):
        name = parts[i].strip().lower()
        content = _extract_text_from_latex(parts[i + 1]) if i + 1 < len(parts) else ""
        sections[name] = content

    return sections


# ── Synonym normalization ─────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Apply synonym expansion to text for better matching."""
    try:
        from evaluation.skills_taxonomy import normalize_text

        return normalize_text(text)
    except ImportError:
        return text


# ── Method 1: BM25 Keyword Relevance (20%) ──────────────────────────


def _is_chinese(text: str) -> bool:
    """Detect if text is primarily Chinese by checking CJK character ratio."""
    cjk_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return cjk_count > len(text) * 0.1


def _score_bm25(resume_text: str, jd_text: str, language: str = "en") -> float:
    """Compute BM25 relevance score between resume and JD.

    BM25 (Okapi BM25) is superior to TF-IDF because:
    - Term frequency saturation: prevents over-weighting repeated terms
    - Document length normalization: fair comparison regardless of resume length
    - IDF weighting: distinguishes rare/important terms from common ones
    """
    try:
        from rank_bm25 import BM25Plus
    except ImportError:
        logger.warning("rank-bm25 not installed, falling back to TF-IDF")
        return _score_tfidf_fallback(resume_text, jd_text)

    try:
        # Normalize both texts for synonym matching
        norm_resume = _normalize(resume_text)
        norm_jd = _normalize(jd_text)

        # Tokenize resume into sentences/chunks as the "corpus"
        if language == "zh":
            resume_sentences = [s.strip() for s in re.split(r"[。；！\n]", norm_resume) if s.strip()]
        else:
            resume_sentences = [s.strip() for s in re.split(r"[.;!\n]", norm_resume) if s.strip()]
        if not resume_sentences:
            resume_sentences = [norm_resume]

        # Tokenize each sentence — use jieba for Chinese, stop word filtering for English
        if language == "zh":
            tokenized_corpus = [_jieba_tokenize(s.lower()) for s in resume_sentences]
            jd_tokens = _jieba_tokenize(norm_jd.lower())
        else:
            tokenized_corpus = [[w for w in s.lower().split() if w not in _BM25_STOP_WORDS] for s in resume_sentences]
            jd_tokens = [w for w in norm_jd.lower().split() if w not in _BM25_STOP_WORDS]

        bm25 = BM25Plus(tokenized_corpus)
        scores = bm25.get_scores(jd_tokens)

        # Aggregate: use mean of top scores (captures best-matching sections)
        if len(scores) == 0:
            return 0.5

        sorted_scores = sorted(scores, reverse=True)
        # Take average of top 30% of sentence scores
        top_n = max(1, len(sorted_scores) // 3)
        raw = sum(sorted_scores[:top_n]) / top_n

        # BM25Plus scores range widely; use sigmoid calibration
        # center=5.0: an adequate match (raw ~5) maps to 50%
        # steepness=0.2: good discrimination in the 5-15 range
        return _sigmoid_calibrate(raw, center=5.0, steepness=0.2)

    except Exception as e:
        logger.warning(f"BM25 scoring failed: {e}")
        return _score_tfidf_fallback(resume_text, jd_text)


def _score_tfidf_fallback(resume_text: str, jd_text: str) -> float:
    """TF-IDF fallback if BM25 is unavailable."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        norm_resume = _normalize(resume_text)
        norm_jd = _normalize(jd_text)

        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            max_features=5000,
        )
        tfidf_matrix = vectorizer.fit_transform([norm_jd, norm_resume])
        raw = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return _sigmoid_calibrate(float(raw), center=0.15, steepness=15.0)
    except Exception as e:
        logger.warning(f"TF-IDF fallback failed: {e}")
        return 0.5


# ── Method 2: Semantic Embedding Similarity (20%) ─────────────────────


def _score_semantic(resume_text: str, jd_text: str, language: str = "en") -> float:
    """Compute semantic similarity using sentence embeddings."""
    model = _get_sentence_model_zh() if language == "zh" else _get_sentence_model()
    if model is None:
        return 0.5  # Neutral fallback if model unavailable

    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        # Chunk long texts into segments for better embedding quality
        def chunk_text(text: str, max_len: int = 512) -> list[str]:
            words = text.split()
            chunks = []
            for i in range(0, len(words), max_len):
                chunks.append(" ".join(words[i : i + max_len]))
            return chunks or [text]

        resume_chunks = chunk_text(resume_text)
        jd_chunks = chunk_text(jd_text)

        resume_embeddings = model.encode(resume_chunks)
        jd_embeddings = model.encode(jd_chunks)

        # Average embeddings for each document
        resume_avg = np.mean(resume_embeddings, axis=0).reshape(1, -1)
        jd_avg = np.mean(jd_embeddings, axis=0).reshape(1, -1)

        raw = cosine_similarity(resume_avg, jd_avg)[0][0]
        # Semantic sim for related docs typically 0.3-0.6
        # center=0.35: spreads the useful range so 0.5 cosine → ~73%
        # steepness=6.0: avoids the "always 60%" flat spot of the old calibration
        return _sigmoid_calibrate(float(raw), center=0.35, steepness=6.0)
    except Exception as e:
        logger.warning(f"Semantic scoring failed: {e}")
        return 0.5


# ── Method 3: Skill Coverage via PhraseMatcher (30%) ──────────────────


def _score_skill_coverage(
    resume_text: str,
    jd_text: str,
    jd_analysis: dict | None,
) -> tuple[float, list[str], list[str]]:
    """Score skill overlap using spaCy PhraseMatcher + taxonomy.

    Returns (score, matched_skills, missing_skills).
    """
    from evaluation.skills_taxonomy import ALL_SKILLS

    # Normalize texts for better matching
    resume_normalized = _normalize(resume_text)
    jd_normalized = _normalize(jd_text)
    resume_lower = resume_normalized.lower()
    jd_lower = jd_normalized.lower()

    # Build skill sets from JD analysis if available, filtering noise words
    jd_required: list[str] = []
    jd_preferred: list[str] = []
    if jd_analysis:
        jd_required = [
            s for s in jd_analysis.get("required_skills", []) if s.lower() not in JD_SKILL_NOISE and len(s) > 1
        ]
        jd_preferred = [
            s for s in jd_analysis.get("preferred_skills", []) if s.lower() not in JD_SKILL_NOISE and len(s) > 1
        ]

    # Combine JD-extracted skills with taxonomy matches found in JD text
    jd_explicit_skills = {s.lower() for s in jd_required + jd_preferred}

    # Find taxonomy skills present in JD text
    jd_taxonomy_skills = set()
    for skill in ALL_SKILLS:
        if len(skill) <= 2:
            if re.search(rf"\b{re.escape(skill)}\b", jd_lower):
                jd_taxonomy_skills.add(skill)
        else:
            if skill in jd_lower:
                jd_taxonomy_skills.add(skill)

    # Union: all skills the JD cares about
    all_jd_skills = jd_explicit_skills | jd_taxonomy_skills
    if not all_jd_skills:
        return 0.5, [], []

    # Try spaCy PhraseMatcher for accurate resume skill extraction
    nlp = _get_spacy_nlp()
    resume_skills_found: set[str] = set()

    if nlp is not None:
        try:
            from spacy.matcher import PhraseMatcher

            matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
            patterns = []
            for skill in all_jd_skills:
                try:
                    patterns.append(nlp.make_doc(skill))
                except Exception:
                    continue
            if patterns:
                matcher.add("SKILLS", patterns)
                doc = nlp(resume_normalized[:100000])
                matches = matcher(doc)
                for _, start, end in matches:
                    resume_skills_found.add(doc[start:end].text.lower())
        except Exception as e:
            logger.warning(f"PhraseMatcher failed, using substring fallback: {e}")
            nlp = None

    # Fallback: substring matching
    if nlp is None:
        for skill in all_jd_skills:
            if len(skill) <= 2:
                if re.search(rf"\b{re.escape(skill)}\b", resume_lower):
                    resume_skills_found.add(skill)
            else:
                if skill in resume_lower:
                    resume_skills_found.add(skill)

    matched = list(resume_skills_found & all_jd_skills)
    missing_required = [s for s in jd_required if s.lower() not in resume_skills_found]

    # Weight required skills more heavily
    if jd_required:
        required_set = {s.lower() for s in jd_required}
        required_matched = len(resume_skills_found & required_set)
        required_coverage = required_matched / len(required_set) if required_set else 0
        total_coverage = len(matched) / len(all_jd_skills) if all_jd_skills else 0
        # 70% weight on required skills, 30% on total
        coverage = required_coverage * 0.7 + total_coverage * 0.3
    else:
        coverage = len(matched) / len(all_jd_skills) if all_jd_skills else 0.5

    return min(coverage, 1.0), sorted(matched), missing_required


# ── Method 4: Fuzzy Keyword Matching (10%) ────────────────────────────


def _score_fuzzy(
    resume_text: str,
    jd_analysis: dict | None,
    jd_text: str,
) -> float:
    """Fuzzy match JD keywords against resume to catch abbreviations/typos."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.warning("rapidfuzz not installed, skipping fuzzy scoring")
        return 0.5

    # Normalize for synonym matching
    resume_normalized = _normalize(resume_text)

    # Collect target keywords from JD, filtering noise words
    keywords: list[str] = []
    if jd_analysis:
        keywords.extend(
            s for s in jd_analysis.get("required_skills", []) if s.lower() not in JD_SKILL_NOISE and len(s) > 1
        )
        keywords.extend(
            s for s in jd_analysis.get("preferred_skills", []) if s.lower() not in JD_SKILL_NOISE and len(s) > 1
        )
    if not keywords:
        words = set(re.findall(r"\b[a-zA-Z][\w.#+/-]{2,}\b", jd_text))
        stop = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "was",
            "one",
            "our",
            "has",
            "had",
            "how",
            "its",
            "may",
            "new",
            "now",
            "see",
            "way",
            "who",
            "did",
            "get",
            "use",
            "this",
            "that",
            "with",
            "will",
            "have",
            "been",
            "from",
            "just",
            "also",
            "more",
            "than",
            "them",
            "when",
            "what",
            "where",
            "which",
            "while",
            "about",
            "their",
            "would",
            "could",
            "should",
            "through",
            "using",
            "based",
            "including",
            "experience",
            "team",
            "ability",
            "work",
            "working",
            "strong",
            "excellent",
            "good",
            "must",
            "year",
            "years",
            "role",
            "position",
            "company",
            "opportunity",
        }
        keywords = [w for w in words if w.lower() not in stop]

    if not keywords:
        return 0.5

    resume_lower = resume_normalized.lower()
    resume_tokens = set(re.findall(r"\b[a-zA-Z][\w.#+/-]{1,}\b", resume_lower))

    matched_count = 0
    for kw in keywords:
        kw_lower = kw.lower()
        # Exact substring first
        if kw_lower in resume_lower:
            matched_count += 1
            continue
        # Fuzzy match against resume tokens
        best_score = 0
        for token in resume_tokens:
            score = fuzz.token_set_ratio(kw_lower, token)
            if score > best_score:
                best_score = score
        # Also try partial_ratio for multi-word keywords
        partial = fuzz.partial_ratio(kw_lower, resume_lower)
        best_score = max(best_score, partial)

        if best_score >= 85:
            matched_count += 1

    raw = matched_count / len(keywords) if keywords else 0.5
    if jd_analysis and (jd_analysis.get("required_skills") or jd_analysis.get("preferred_skills")):
        return raw
    return _calibrate_linear(raw, 0.2, 0.8)


# ── Method 5: Resume Quality Heuristics (10%) ────────────────────────


def _score_quality(
    resume_text: str,
    resume_latex: str,
    language: str = "en",
) -> tuple[float, float, float, float, float, list[str]]:
    """Score resume quality heuristics.

    Returns (overall_quality, action_verbs, quantified, sections, format, feedback).
    """
    feedback: list[str] = []
    resume_lower = resume_latex.lower()

    if language == "zh":
        return _score_quality_zh(resume_text, resume_latex, feedback)

    # Action Verbs (25% of quality)
    found_verbs = [v for v in ACTION_VERBS if re.search(rf"\b{v}\b", resume_text.lower())]
    verbs_score = min(len(found_verbs) / 8, 1.0)
    if len(found_verbs) < 5:
        feedback.append(
            f"Use more action verbs ({len(found_verbs)} found, aim for 8+). Try: {', '.join(ACTION_VERBS[:5])}"
        )

    # Quantified Achievements (25% of quality)
    quant_patterns = [
        r"\d+%",
        r"\$[\d,]+",
        r"\d+x",
        r"\d+\+?\s*(?:users|clients|customers|projects|team|engineers|people)",
    ]
    quant_count = sum(len(re.findall(p, resume_text.lower())) for p in quant_patterns)
    quant_score = min(quant_count / 5, 1.0)
    if quant_count < 3:
        feedback.append("Add more quantified achievements (numbers, percentages, metrics)")

    # Section Completeness (25% of quality)
    sections_found = sum(1 for s in EXPECTED_SECTIONS if s in resume_lower)
    section_score = min(sections_found / 4, 1.0)
    if sections_found < 3:
        missing_sections = [s for s in EXPECTED_SECTIONS[:4] if s not in resume_lower]
        feedback.append(f"Consider adding sections: {', '.join(missing_sections)}")

    # Format Quality (25% of quality)
    has_itemize = "\\begin{itemize}" in resume_lower or "\\item" in resume_lower
    has_sections = sections_found >= 3
    has_hyperlinks = "\\href{" in resume_lower or "\\url{" in resume_lower
    has_dates = bool(re.findall(r"\b20\d{2}\b", resume_latex))
    format_points = sum([has_itemize, has_sections, has_hyperlinks, has_dates])
    fmt_score = format_points / 4
    if not has_itemize:
        feedback.append("Use bullet points (\\item) for better ATS parsing")

    overall_quality = (verbs_score + quant_score + section_score + fmt_score) / 4
    return overall_quality, verbs_score, quant_score, section_score, fmt_score, feedback


def _score_quality_zh(
    resume_text: str,
    resume_latex: str,
    feedback: list[str],
) -> tuple[float, float, float, float, float, list[str]]:
    """Score resume quality heuristics for Chinese resumes."""
    from evaluation.skills_taxonomy import (
        ACTION_VERBS_ZH_MEDIUM,
        ACTION_VERBS_ZH_STRONG,
        ACTION_VERBS_ZH_WEAK,
        ALL_SECTION_NAMES_ZH,
    )

    resume_lower = resume_latex.lower()

    # Action Verbs (25%) — Chinese verb detection
    found_strong = [v for v in ACTION_VERBS_ZH_STRONG if v in resume_text]
    found_medium = [v for v in ACTION_VERBS_ZH_MEDIUM if v in resume_text]
    found_weak = [v for v in ACTION_VERBS_ZH_WEAK if v in resume_text]
    # Strong verbs count double, weak verbs count half
    verb_score_raw = len(found_strong) * 2 + len(found_medium) + len(found_weak) * 0.5
    verbs_score = min(verb_score_raw / 10, 1.0)
    if verb_score_raw < 5:
        examples = "、".join(list(ACTION_VERBS_ZH_STRONG)[:5])
        feedback.append(f"建议使用更多强动词（已找到{len(found_strong)}个强动词）。例如：{examples}")
    if found_weak and not found_strong:
        feedback.append("避免仅使用弱动词（参与、协助等），改用更有力的表达（主导、设计、架构等）")

    # Quantified Achievements (25%) — Chinese quantification patterns
    zh_quant_patterns = [
        r"\d+%",
        r"\d+倍",
        r"\d+万",
        r"\d+亿",
        r"(?:提升|降低|缩短|增加|减少|优化)[\d.]+",
        r"日活[\d]+",
        r"[\d]+(?:万|亿)(?:用户|条|次|人)",
        r"[\d,]+\+?\s*(?:用户|客户|项目|团队|人)",
        r"\$[\d,]+",
        r"\d+x",
    ]
    quant_count = sum(len(re.findall(p, resume_text)) for p in zh_quant_patterns)
    quant_score = min(quant_count / 5, 1.0)
    if quant_count < 3:
        feedback.append("建议添加更多量化成果（百分比、数字、指标），如'提升30%'、'服务500万用户'")

    # Section Completeness (25%) — Chinese section detection
    sections_found = sum(1 for s in ALL_SECTION_NAMES_ZH if s in resume_text)
    section_score = min(sections_found / 4, 1.0)
    if sections_found < 3:
        feedback.append(f"简历只有{sections_found}个必要板块，建议包含：工作经历、教育背景、专业技能、项目经历")

    # Format Quality (25%)
    has_itemize = "\\begin{itemize}" in resume_lower or "\\item" in resume_lower
    has_sections = sections_found >= 3
    has_hyperlinks = "\\href{" in resume_lower or "\\url{" in resume_lower
    has_dates = bool(re.findall(r"20\d{2}", resume_latex))
    format_points = sum([has_itemize, has_sections, has_hyperlinks, has_dates])
    fmt_score = format_points / 4
    if not has_itemize:
        feedback.append("建议使用项目符号（\\item）使简历结构更清晰")

    overall_quality = (verbs_score + quant_score + section_score + fmt_score) / 4
    return overall_quality, verbs_score, quant_score, section_score, fmt_score, feedback


# ── Method 6: Section-Aware Bonus (10%) ──────────────────────────────


def _score_section_bonus(
    resume_latex: str,
    jd_text: str,
    jd_analysis: dict | None,
) -> float:
    """Score how well keywords are distributed across resume sections.

    Research shows ATS systems weight the Skills section highest (35%),
    followed by Experience (30%) and Summary (15%). This method rewards
    resumes that place keywords in high-impact sections.
    """
    sections = _extract_latex_sections(resume_latex)
    if not sections:
        return 0.5  # Can't determine sections

    # Collect target keywords, filtering noise words
    target_keywords: list[str] = []
    if jd_analysis:
        target_keywords.extend(
            s for s in jd_analysis.get("required_skills", []) if s.lower() not in JD_SKILL_NOISE and len(s) > 1
        )
        target_keywords.extend(
            s for s in jd_analysis.get("preferred_skills", []) if s.lower() not in JD_SKILL_NOISE and len(s) > 1
        )

    if not target_keywords:
        # Extract from JD text
        from evaluation.skills_taxonomy import ALL_SKILLS

        jd_lower = jd_text.lower()
        for skill in ALL_SKILLS:
            if len(skill) <= 2:
                if re.search(rf"\b{re.escape(skill)}\b", jd_lower):
                    target_keywords.append(skill)
            else:
                if skill in jd_lower:
                    target_keywords.append(skill)

    if not target_keywords:
        return 0.5

    target_keywords_lower = [kw.lower() for kw in target_keywords]

    # Score each section based on keyword presence and section weight
    weighted_score = 0.0
    total_weight = 0.0

    for section_name, section_content in sections.items():
        # Determine section weight
        weight = SECTION_WEIGHTS.get("other", 0.05)
        for key, w in SECTION_WEIGHTS.items():
            if key in section_name:
                weight = w
                break

        section_lower = section_content.lower()
        if target_keywords_lower:
            found = sum(1 for kw in target_keywords_lower if kw in section_lower)
            section_coverage = found / len(target_keywords_lower)
        else:
            section_coverage = 0.0

        weighted_score += section_coverage * weight
        total_weight += weight

    raw = weighted_score / total_weight if total_weight > 0 else 0.0

    # Sigmoid calibration — center at 0.3, typical range is 0.1-0.6
    return _sigmoid_calibrate(raw, center=0.25, steepness=8.0)


# ── Public API ────────────────────────────────────────────────────────


def score_resume(
    resume_latex: str,
    jd_text: str,
    jd_analysis: dict | None = None,
    language: str = "en",
) -> ATSScoreBreakdown:
    """Score a resume against a job description using hybrid multi-method analysis.

    Weights (research-backed, v2):
        20% BM25 keyword relevance (replaces TF-IDF)
        20% Semantic embedding similarity
        30% Skill coverage (PhraseMatcher + taxonomy) — highest weight per research
        10% Fuzzy keyword matching
        10% Resume quality heuristics
        10% Section-aware keyword placement bonus

    Args:
        resume_latex: LaTeX source of the resume
        jd_text: Raw job description text
        jd_analysis: Optional structured JD analysis from the pipeline
        language: "en" or "zh" — selects language-appropriate scoring

    Returns:
        ATSScoreBreakdown with detailed scores and feedback
    """
    # Auto-detect language if not specified
    if language == "en" and _is_chinese(jd_text):
        language = "zh"

    result = ATSScoreBreakdown()
    resume_text = _extract_text_from_latex(resume_latex)

    # Method 1: BM25 Keyword Relevance (20%)
    result.keyword_similarity = _score_bm25(resume_text, jd_text, language=language)

    # Method 2: Semantic Embedding (20%)
    result.semantic_similarity = _score_semantic(resume_text, jd_text, language=language)

    # Method 3: Skill Coverage (30%)
    result.skill_coverage, result.matched_keywords, result.missing_keywords = _score_skill_coverage(
        resume_text, jd_text, jd_analysis
    )

    # Method 4: Fuzzy Matching (10%)
    result.fuzzy_match = _score_fuzzy(resume_text, jd_analysis, jd_text)

    # Method 5: Resume Quality (10%)
    (
        result.resume_quality,
        result.action_verbs_score,
        result.quantified_score,
        result.section_score,
        result.format_score,
        quality_feedback,
    ) = _score_quality(resume_text, resume_latex, language=language)
    result.feedback.extend(quality_feedback)

    # Method 6: Section-Aware Bonus (10%)
    result.section_bonus = _score_section_bonus(resume_latex, jd_text, jd_analysis)

    # Add skill-gap feedback
    if result.missing_keywords:
        if language == "zh":
            result.feedback.append(
                f"缺少{len(result.missing_keywords)}个关键技能：{', '.join(result.missing_keywords[:5])}"
            )
        else:
            result.feedback.append(
                f"Missing {len(result.missing_keywords)} required skills: {', '.join(result.missing_keywords[:5])}"
            )

    # Weighted overall score (research-backed distribution)
    result.overall = round(
        result.keyword_similarity * 0.20
        + result.semantic_similarity * 0.20
        + result.skill_coverage * 0.30
        + result.fuzzy_match * 0.10
        + result.resume_quality * 0.10
        + result.section_bonus * 0.10,
        3,
    )

    logger.info(
        f"ATS Score: {result.overall:.2f} "
        f"(bm25={result.keyword_similarity:.2f}, "
        f"semantic={result.semantic_similarity:.2f}, "
        f"skills={result.skill_coverage:.2f}, "
        f"fuzzy={result.fuzzy_match:.2f}, "
        f"quality={result.resume_quality:.2f}, "
        f"section={result.section_bonus:.2f})"
    )

    return result
