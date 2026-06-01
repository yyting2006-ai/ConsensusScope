from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Set, Tuple

import pandas as pd
import requests

from src.llm.clients import format_http_error, parse_json_from_text


DEFAULT_LITERARY_ESSAY = """Mary Shelley write Frankenstein in 1847, and Jane Austen wrote Jane Eyre. Both novels shows how women are trapped by society, but Frankenstein is only about science and Jane Eyre is only about love. The monster is Victor Frankenstein, so the novel proves that people should never study knowledge. In comparison, the two books are same because both main characters want freedom."""


EXAMPLE_ESSAYS = {
    "Frankenstein vs Jane Eyre · error-rich demo": DEFAULT_LITERARY_ESSAY,
    "Frankenstein vs Jane Eyre · argument-risk demo": """In Frankenstein and Jane Eyre, the protagonists search for freedom, but the essay should not treat both novels as the same story. Mary Shelley write about ambition and responsibility, while Jane Eyre focuses on moral independence. The monster is Victor Frankenstein, so the comparison shows that freedom always destroys society.""",
    "Blank workspace": "",
}


ISSUE_ORDER = {
    "grammar": 0,
    "word_choice": 1,
    "academic_style": 2,
    "literary_fact": 3,
    "argument": 4,
}

KG_RELATION_PRIORITY = {
    "author": 0,
    "publication_year": 1,
    "form": 2,
    "genre": 3,
    "central_character": 4,
    "theme": 5,
    "language": 6,
    "literary_movement": 7,
    "alias": 8,
}

KG_RELATION_CAP = {
    "author": 2,
    "publication_year": 2,
    "form": 2,
    "genre": 4,
    "central_character": 5,
    "theme": 3,
    "language": 1,
    "literary_movement": 2,
    "alias": 2,
}

KG_WORK_CAP = 8


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", _safe_text(value).lower()).strip(" .,:;!?")


def _safe_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, parsed))


def load_literary_kg(path: str) -> pd.DataFrame:
    try:
        kg = pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=["entity", "relation", "value", "work", "evidence", "source"])
    expected = ["entity", "relation", "value", "work", "evidence", "source"]
    for col in expected:
        if col not in kg.columns:
            kg[col] = ""
    return kg[expected].fillna("")


def retrieve_literary_knowledge(essay: str, kg: pd.DataFrame, limit: int = 12) -> List[Dict[str, str]]:
    text = _norm(essay)
    candidates_out: List[Dict[str, str]] = []
    if kg.empty:
        return candidates_out
    for _, row in kg.iterrows():
        entity = _safe_text(row.get("entity"))
        work = _safe_text(row.get("work"))
        value = _safe_text(row.get("value"))
        candidates = [entity, work, value]
        matched = [candidate for candidate in candidates if candidate and _norm(candidate) in text]
        if matched:
            out = {key: _safe_text(row.get(key)) for key in kg.columns}
            out["match"] = matched[0]
            out["match_score"] = str(round(min(1.0, 0.55 + 0.15 * len(matched)), 3))
            candidates_out.append(out)

    candidates_out.sort(
        key=lambda item: (
            text.find(_norm(item.get("work"))) if _norm(item.get("work")) in text else 9999,
            KG_RELATION_PRIORITY.get(item.get("relation", ""), 99),
            item.get("value", ""),
        )
    )
    selected: List[Dict[str, str]] = []
    relation_counts: Dict[tuple[str, str], int] = defaultdict(int)
    work_counts: Dict[str, int] = defaultdict(int)
    seen = set()
    for item in candidates_out:
        key = (item.get("work", ""), item.get("relation", ""), item.get("value", ""))
        if key in seen:
            continue
        work = item.get("work", "")
        if work_counts[work] >= KG_WORK_CAP:
            continue
        relation_key = (item.get("work", ""), item.get("relation", ""))
        cap = KG_RELATION_CAP.get(item.get("relation", ""), 2)
        if relation_counts[relation_key] >= cap:
            continue
        selected.append(item)
        seen.add(key)
        work_counts[work] += 1
        relation_counts[relation_key] += 1
        if len(selected) >= limit:
            break
    return selected


def _kg_evidence(kg_rows: Iterable[Dict[str, str]], entity: str, relation: str = "") -> List[str]:
    evidence: List[str] = []
    entity_norm = _norm(entity)
    relation_norm = _norm(relation)
    for row in kg_rows:
        if entity_norm and entity_norm not in {_norm(row.get("entity")), _norm(row.get("work"))}:
            continue
        if relation_norm and relation_norm != _norm(row.get("relation")):
            continue
        text = _safe_text(row.get("evidence"))
        if text:
            evidence.append(text)
    return evidence


def _suggestion(
    reviewer: str,
    span: str,
    issue_type: str,
    suggestion: str,
    rationale: str,
    confidence: float,
    risk: str,
    evidence: Iterable[str] = (),
) -> Dict[str, Any]:
    return {
        "reviewer": reviewer,
        "span": span,
        "issue_type": issue_type,
        "suggestion": suggestion,
        "rationale": rationale,
        "confidence": round(float(confidence), 3),
        "knowledge_evidence": list(evidence),
        "meaning_change_risk": risk,
    }


def build_literary_feedback_prompt(essay: str, kg_rows: List[Dict[str, str]], reviewer_role: str) -> str:
    kg_text = "\n".join(
        f"- {row.get('entity')} | {row.get('relation')} | {row.get('value')}: {row.get('evidence')}"
        for row in kg_rows[:12]
    )
    return f"""You are an ESL writing feedback reviewer for comparative literature essays.

Reviewer role: {reviewer_role}

Student essay excerpt:
{essay}

Retrieved literary knowledge:
{kg_text or "No retrieved knowledge."}

Return exactly one JSON object with a key named "feedback".
"feedback" must be a list of 1 to 5 objects. Each object must use this schema:
span, issue_type, suggestion, rationale, confidence, knowledge_evidence, meaning_change_risk

Allowed issue_type values:
grammar, word_choice, academic_style, literary_fact, argument

Allowed meaning_change_risk values:
low, medium, high

Rules:
- Focus on concrete, inspectable feedback.
- Do not rewrite the whole essay.
- Mark grammar-only local edits as low risk.
- Mark literary facts and interpretation-changing suggestions as medium or high risk.
- Use knowledge_evidence only when the retrieved knowledge supports the suggestion.
- confidence must be a number from 0 to 1.
- Do not include Markdown.
"""


def normalize_feedback_items(raw_items: Any, reviewer: str) -> List[Dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    normalized: List[Dict[str, Any]] = []
    allowed_types = set(ISSUE_ORDER)
    allowed_risks = {"low", "medium", "high"}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        issue_type = _norm(item.get("issue_type"))
        risk = _norm(item.get("meaning_change_risk"))
        evidence = item.get("knowledge_evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence] if evidence.strip() else []
        if not isinstance(evidence, list):
            evidence = []
        normalized.append(
            _suggestion(
                reviewer=_safe_text(item.get("reviewer")) or reviewer,
                span=_safe_text(item.get("span")),
                issue_type=issue_type if issue_type in allowed_types else "academic_style",
                suggestion=_safe_text(item.get("suggestion")),
                rationale=_safe_text(item.get("rationale")),
                confidence=_safe_confidence(item.get("confidence", 0.0)),
                risk=risk if risk in allowed_risks else "medium",
                evidence=[_safe_text(value) for value in evidence if _safe_text(value)],
            )
        )
    return [item for item in normalized if item["span"] and item["suggestion"]]


def call_literary_reviewer(
    config: Any,
    essay: str,
    kg_rows: List[Dict[str, str]],
    reviewer_role: str,
    temperature: float = 0.1,
    max_tokens: int = 1200,
    timeout: int = 60,
) -> Dict[str, Any]:
    started = time.time()
    base = {
        "provider": getattr(config, "provider", ""),
        "model": getattr(config, "model", ""),
        "reviewer_role": reviewer_role,
        "feedback": [],
        "raw_output": "",
        "request_error": "",
        "parse_error": "",
        "latency_sec": 0.0,
    }
    if not getattr(config, "enabled", True):
        return {**base, "request_error": "Model is disabled"}
    if not getattr(config, "api_key", ""):
        return {**base, "request_error": "Missing API key"}

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "You must output valid JSON only."},
            {"role": "user", "content": build_literary_feedback_prompt(essay, kg_rows, reviewer_role)},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            f"{config.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        if not response.ok:
            raise RuntimeError(format_http_error(response))
        raw = str(response.json()["choices"][0]["message"]["content"])
        parsed = parse_json_from_text(raw)
        parse_error = _safe_text(parsed.get("parse_error"))
        feedback = normalize_feedback_items(parsed.get("feedback", []), f"{config.provider}_{reviewer_role}")
        return {
            **base,
            "feedback": feedback,
            "raw_output": raw,
            "parse_error": parse_error,
            "latency_sec": round(time.time() - started, 3),
        }
    except Exception as exc:
        return {
            **base,
            "request_error": str(exc),
            "latency_sec": round(time.time() - started, 3),
        }


def run_live_literary_reviewers(
    configs: Iterable[Any],
    essay: str,
    kg_rows: List[Dict[str, str]],
    max_workers: int = 4,
) -> Dict[str, Any]:
    roles = ["grammar", "literary_fact", "argument"]
    tasks = []
    for idx, config in enumerate([cfg for cfg in configs if getattr(cfg, "enabled", True)]):
        role = roles[idx % len(roles)]
        tasks.append((config, role))
    if not tasks:
        return {"feedback": [], "reviewer_results": []}

    results: List[Dict[str, Any]] = []
    workers = max(1, min(max_workers, len(tasks)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(call_literary_reviewer, config, essay, kg_rows, role)
            for config, role in tasks
        ]
        for future in as_completed(futures):
            results.append(future.result())

    feedback = [item for result in results for item in result.get("feedback", [])]
    return {
        "feedback": feedback,
        "reviewer_results": sorted(results, key=lambda item: str(item.get("provider", ""))),
    }


def _term_source(term: str) -> str:
    return re.escape(term).replace(r"\ ", r"\s+")


def _term_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){_term_source(term)}(?!\w)", flags=re.I)


def _contains_term(text: str, term: str) -> bool:
    return bool(term and _term_pattern(term).search(text))


def _profiles_from_kg(kg: pd.DataFrame) -> Dict[str, Dict[str, Set[str]]]:
    profiles: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    if kg.empty:
        return profiles
    for _, row in kg.iterrows():
        work = _safe_text(row.get("work")) or _safe_text(row.get("entity"))
        relation = _safe_text(row.get("relation"))
        value = _safe_text(row.get("value"))
        if not work or not relation or not value:
            continue
        profiles[work][relation].add(value)
    return profiles


def _all_kg_rows(kg: pd.DataFrame) -> List[Dict[str, str]]:
    if kg.empty:
        return []
    return [
        {key: _safe_text(row.get(key)) for key in kg.columns}
        for _, row in kg.iterrows()
    ]


def _work_aliases(work: str, profile: Dict[str, Set[str]]) -> List[str]:
    aliases = [work, *sorted(profile.get("alias", set()), key=len, reverse=True)]
    return list(dict.fromkeys([alias for alias in aliases if alias]))


def _evidence_for_work(
    kg_rows: Iterable[Dict[str, str]],
    work: str,
    relations: Iterable[str],
    limit: int = 3,
) -> List[str]:
    relation_set = set(relations)
    evidence: List[str] = []
    for row in kg_rows:
        if _safe_text(row.get("work")) != work:
            continue
        if relation_set and _safe_text(row.get("relation")) not in relation_set:
            continue
        text = _safe_text(row.get("evidence"))
        if text:
            evidence.append(text)
    return list(dict.fromkeys(evidence))[:limit]


def _author_alias_map(profiles: Dict[str, Dict[str, Set[str]]]) -> Dict[str, str]:
    candidates: Dict[str, Set[str]] = defaultdict(set)
    for profile in profiles.values():
        for author in profile.get("author", set()):
            candidates[author].add(author)
            parts = author.replace(".", "").split()
            if parts:
                candidates[parts[-1]].add(author)
            if len(parts) >= 2:
                candidates[" ".join(parts[-2:])].add(author)
    return {
        alias: next(iter(authors))
        for alias, authors in candidates.items()
        if len(authors) == 1 and len(alias) >= 4
    }


def _character_alias_map(profiles: Dict[str, Dict[str, Set[str]]]) -> Dict[str, Set[str]]:
    skip_first_names = {"the", "john", "jim", "mr", "mrs", "miss", "captain", "doctor", "dr"}
    candidates: Dict[str, Set[str]] = defaultdict(set)
    for work, profile in profiles.items():
        for character in profile.get("central_character", set()):
            candidates[character].add(work)
            parts = re.sub(r"[^A-Za-z' -]", " ", character).split()
            if parts:
                first = parts[0].lower()
                if len(first) >= 4 and first not in skip_first_names:
                    candidates[parts[0]].add(work)
    return {alias: works for alias, works in candidates.items() if alias}


def _detected_work_mentions(
    essay: str,
    profiles: Dict[str, Dict[str, Set[str]]],
) -> List[Tuple[str, str, int, int]]:
    mentions: List[Tuple[str, str, int, int]] = []
    for work, profile in profiles.items():
        for alias in _work_aliases(work, profile):
            for match in _term_pattern(alias).finditer(essay):
                mentions.append((work, alias, match.start(), match.end()))
    mentions.sort(key=lambda item: (item[2], -(item[3] - item[2])))
    return mentions


def _window(text: str, start: int, end: int, radius: int = 110) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)]


def _local_clause(text: str, start: int, end: int) -> str:
    left = max(text.rfind(mark, 0, start) for mark in [".", ";", "\n", ","])
    right_candidates = [idx for idx in [text.find(mark, end) for mark in [".", ";", "\n", ","]] if idx != -1]
    right = min(right_candidates) if right_candidates else len(text)
    return text[left + 1 : right]


GRAMMAR_RULES = [
    (r"\bMary Shelley write\b", "Mary Shelley wrote", "Use past-tense subject-verb agreement when discussing publication history."),
    (r"\b(Both novels) shows\b", r"\1 show", "Plural subject 'novels' takes the base verb 'show'."),
    (r"\b(was) wrote by\b", r"\1 written by", "Use the past participle in passive voice."),
    (r"\b(Moby-Dick) are\b", r"\1 is", "A single work title takes a singular verb."),
    (r"\b(The Yellow Wallpaper) are\b", r"\1 is", "A single work title takes a singular verb."),
    (r"\b(Pride and Prejudice) are\b", r"\1 is", "A single work title takes a singular verb."),
    (r"\b(To the Lighthouse and Mrs Dalloway) is both\b", r"\1 are both", "A compound subject takes a plural verb."),
    (r"\b(Oliver Twist and Great Expectations) shows\b", r"\1 show", "A compound subject takes a plural verb."),
    (r"\b(Macbeth and Lady Macbeth) is\b", r"\1 are", "A compound subject takes a plural verb."),
    (r"\b(the essay) need\b", r"\1 needs", "A singular subject takes a third-person singular verb."),
    (r"\bit are\b", "it is", "A singular pronoun takes a singular verb."),
]


def _grammar_feedback(essay: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for pattern, replacement, rationale in GRAMMAR_RULES:
        for match in re.finditer(pattern, essay, flags=re.I):
            span = match.group(0)
            suggestion = match.expand(replacement)
            key = _norm(span)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                _suggestion(
                    "grammar_reviewer",
                    span,
                    "grammar",
                    suggestion,
                    rationale,
                    0.91,
                    "low",
                )
            )
    return items


def _authorship_feedback(
    essay: str,
    profiles: Dict[str, Dict[str, Set[str]]],
    kg_rows: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    author_aliases = _author_alias_map(profiles)
    items: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str, str]] = set()
    for work, profile in profiles.items():
        expected_author = next(iter(profile.get("author", set())), "")
        if not expected_author:
            continue
        work_sources = [_term_source(alias) for alias in _work_aliases(work, profile)]
        for author_alias, observed_author in sorted(author_aliases.items(), key=lambda row: len(row[0]), reverse=True):
            if observed_author == expected_author:
                continue
            author_source = _term_source(author_alias)
            for work_source in work_sources:
                regexes = [
                    rf"(?<!\w){author_source}(?!\w)\s+(?:write|writes|wrote)\s+(?<!\w){work_source}(?!\w)",
                    rf"(?<!\w){work_source}(?!\w).{{0,90}}\b(?:by|written by|wrote by|is by|was by|is written by|was written by|was wrote by)\s+(?<!\w){author_source}(?!\w)",
                    rf"(?<!\w){work_source}(?!\w).{{0,90}}\b(?<!\w){author_source}(?!\w)\s+(?:tragedy|comedy|novel|play|poem|romance)",
                ]
                for regex in regexes:
                    match = re.search(regex, essay, flags=re.I)
                    if not match:
                        continue
                    key = (work, observed_author, "")
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append(
                        _suggestion(
                            "kg_reviewer",
                            match.group(0),
                            "literary_fact",
                            f"Attribute {work} to {expected_author}",
                            f"The local knowledge graph attributes {work} to {expected_author}, not {observed_author}.",
                            0.88,
                            "medium",
                            _evidence_for_work(kg_rows, work, ["author"]),
                        )
                    )
    return items


def _publication_year_feedback(
    essay: str,
    profiles: Dict[str, Dict[str, Set[str]]],
    kg_rows: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    for work, alias, start, end in _detected_work_mentions(essay, profiles):
        expected_year = next(iter(profiles[work].get("publication_year", set())), "")
        if not re.fullmatch(r"\d{4}", expected_year):
            continue
        segment = _local_clause(essay, start, end)
        for year_match in re.finditer(r"\b(1[5-9]\d{2}|20\d{2})\b", segment):
            observed_year = year_match.group(1)
            if observed_year == expected_year:
                continue
            if not any(cue in segment.lower() for cue in ["published", "publication", "dated", "in "]):
                continue
            key = (work, observed_year)
            if key in seen:
                continue
            seen.add(key)
            span = f"{alias} ... {observed_year}"
            items.append(
                _suggestion(
                    "kg_reviewer",
                    span,
                    "literary_fact",
                    f"Use {expected_year} as the date for {work}",
                    f"The local knowledge graph dates {work} to {expected_year}, not {observed_year}.",
                    0.86,
                    "medium",
                    _evidence_for_work(kg_rows, work, ["publication_year"]),
                )
            )
    return items


GENRE_OR_FORM_TERMS = [
    "modernist novel",
    "historical novel",
    "adventure novel",
    "British novel",
    "short story",
    "epic poem",
    "comedy",
    "tragedy",
    "romance",
    "novella",
    "novel",
    "poem",
    "play",
]


def _term_is_expected(term: str, expected_values: Iterable[str]) -> bool:
    expected = " | ".join(_norm(value) for value in expected_values)
    norm_term = _norm(term)
    if norm_term in expected:
        return True
    if norm_term.endswith(" novel") and "novel" in expected:
        return "modernist" not in norm_term or "modernist" in expected
    if norm_term == "poem" and "poetry" in expected:
        return True
    if norm_term == "play" and ("drama" in expected or "tragedy" in expected or "comedy" in expected):
        return True
    return False


def _genre_form_feedback(
    essay: str,
    profiles: Dict[str, Dict[str, Set[str]]],
    kg_rows: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for work, alias, start, end in _detected_work_mentions(essay, profiles):
        if work in seen:
            continue
        segment = _local_clause(essay, start, end)
        expected_values = set(profiles[work].get("form", set())) | set(profiles[work].get("genre", set()))
        if not expected_values:
            continue
        for term in GENRE_OR_FORM_TERMS:
            if not _contains_term(segment, term) or _term_is_expected(term, expected_values):
                continue
            seen.add(work)
            expected_text = ", ".join(sorted(expected_values)[:3])
            items.append(
                _suggestion(
                    "kg_reviewer",
                    f"{alias} ... {term}",
                    "literary_fact",
                    f"Check the genre/form of {work}; expected evidence points to {expected_text}",
                    f"The observed genre or form label '{term}' conflicts with the local literary knowledge graph.",
                    0.78,
                    "medium",
                    _evidence_for_work(kg_rows, work, ["form", "genre"]),
                )
            )
            break
    return items


def _character_feedback(
    essay: str,
    profiles: Dict[str, Dict[str, Set[str]]],
    kg_rows: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    lowered = essay.lower()
    if "monster is victor frankenstein" in lowered:
        items.append(
            _suggestion(
                "kg_reviewer",
                "The monster is Victor Frankenstein",
                "literary_fact",
                "Distinguish Victor Frankenstein from the creature he creates",
                "The statement conflates Victor Frankenstein with the created being.",
                0.84,
                "medium",
                _evidence_for_work(kg_rows, "Frankenstein", ["central_character"]),
            )
        )
    character_map = _character_alias_map(profiles)
    relation_cues = ["marries", "marry", "main character", "character", "narrator", "writes the whole story"]
    for work, alias, start, end in _detected_work_mentions(essay, profiles):
        segment = _local_clause(essay, start, end)
        segment_lower = segment.lower()
        for character_alias, owner_works in sorted(character_map.items(), key=lambda row: len(row[0]), reverse=True):
            if not _contains_term(segment, character_alias):
                continue
            if work not in owner_works and any(cue in segment_lower for cue in relation_cues):
                key = (work, character_alias)
                if key in seen:
                    continue
                seen.add(key)
                owner_text = ", ".join(sorted(owner_works))
                items.append(
                    _suggestion(
                        "kg_reviewer",
                        f"{alias} ... {character_alias}",
                        "literary_fact",
                        f"Check whether {character_alias} belongs to {work}",
                        f"The knowledge graph links {character_alias} to {owner_text}, not to {work}.",
                        0.75,
                        "medium",
                        _evidence_for_work(kg_rows, work, ["central_character"]),
                    )
                )
            if work in owner_works and any(cue in segment_lower for cue in ["minor character", "not important"]):
                key = (work, f"{character_alias}:importance")
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    _suggestion(
                        "kg_reviewer",
                        f"{character_alias} ... minor/not important",
                        "argument",
                        f"Review the claim about {character_alias}'s importance in {work}",
                        "The knowledge graph lists this figure as central, so the claim should be checked by a teacher.",
                        0.72,
                        "high",
                        _evidence_for_work(kg_rows, work, ["central_character"]),
                    )
                )
    if "king lear is the youngest daughter" in lowered:
        items.append(
            _suggestion(
                "kg_reviewer",
                "King Lear is the youngest daughter",
                "literary_fact",
                "Distinguish King Lear from Cordelia, his youngest daughter",
                "The claim confuses a title character with another central character.",
                0.8,
                "medium",
                _evidence_for_work(kg_rows, "King Lear", ["central_character"]),
            )
        )
    return items


ARGUMENT_PATTERNS = [
    ("only about science / only about love", ["only about science", "only about love"], "Use a more qualified claim about dominant themes instead of reducing each work to one topic."),
    ("never study knowledge", ["never study knowledge"], "Avoid turning a literary interpretation into an absolute moral rule."),
    ("always destroys society", ["always destroys society"], "Review the causal interpretation before changing the student's thesis."),
    ("exactly the same", ["exactly the same"], "Replace absolute similarity with a specific comparison and contrast."),
    ("same because", ["are same because", "the same because"], "Clarify the comparative basis instead of treating the works as identical."),
    ("no concern with art", ["no concern with art"], "Check this broad historical claim against textual evidence."),
    ("industrial education", ["industrial education"], "Review whether this theme is supported by the text."),
    ("friendly whale", ["friendly whale"], "Check whether the interpretation accounts for obsession and conflict."),
    ("never thinks about obsession", ["never thinks about obsession"], "Avoid a categorical claim that erases a central interpretive issue."),
    ("cheerful adventure", ["cheerful adventure"], "Review the tone and colonial context before accepting this interpretation."),
    ("without any criticism", ["without any criticism"], "This may overstate the author's position and needs teacher review."),
    ("definitely real", ["definitely real"], "Flag interpretive certainty in an ambiguous text."),
    ("all readers should agree", ["all readers should agree"], "Avoid presenting one interpretation as mandatory for all readers."),
    ("chooses her fate freely", ["chooses her fate freely"], "Review whether the claim ignores social constraint in the novel."),
    ("no humor", ["no humor"], "Check the claim against the comic genre and dramatic irony."),
    ("only moral instruction", ["only moral instruction"], "Avoid reducing authorial purpose to a single intention."),
    ("modern Victorian hero", ["modern Victorian hero"], "Check the historical framing and genre context."),
    ("Cordelia is the villain", ["Cordelia is the villain"], "Review the character interpretation before applying a rewrite."),
    ("writes the whole story in first person", ["writes the whole story in first person"], "Check the narrator claim before applying a factual rewrite."),
    ("exactly identical in motivation", ["exactly identical in motivation"], "Ask for a more precise contrast between motivations."),
    ("does not explain why", ["does not explain why"], "Route thesis-development feedback to the teacher rather than auto-rewriting the student's argument."),
]


def _argument_feedback(essay: str) -> List[Dict[str, Any]]:
    lowered = essay.lower()
    items: List[Dict[str, Any]] = []
    for span, triggers, suggestion in ARGUMENT_PATTERNS:
        if any(trigger.lower() in lowered for trigger in triggers):
            items.append(
                _suggestion(
                    "argument_reviewer",
                    span,
                    "argument",
                    suggestion,
                    "The suggested change may alter interpretation, emphasis, or the student's intended thesis.",
                    0.73,
                    "high",
                )
            )
    return items


def generate_demo_literary_feedback(essay: str, kg: pd.DataFrame) -> List[Dict[str, Any]]:
    """Generate deterministic multi-reviewer feedback for a no-API demo.

    The output mirrors the schema expected from live LLM reviewers. It is a
    rule-based local model: low-risk grammar edits are separated from literary
    facts and interpretation-changing suggestions, which are grounded in the
    curated literary knowledge graph when possible.
    """

    kg_rows = retrieve_literary_knowledge(essay, kg, limit=40)
    all_rows = _all_kg_rows(kg)
    profiles = _profiles_from_kg(kg)

    feedback: List[Dict[str, Any]] = []
    feedback.extend(_grammar_feedback(essay))
    feedback.extend(_authorship_feedback(essay, profiles, all_rows))
    feedback.extend(_publication_year_feedback(essay, profiles, all_rows))
    feedback.extend(_genre_form_feedback(essay, profiles, all_rows))
    feedback.extend(_character_feedback(essay, profiles, all_rows))
    feedback.extend(_argument_feedback(essay))

    if "are same" in essay.lower() or "the same as" in essay.lower():
        feedback.append(
            _suggestion(
                "academic_reviewer",
                "same comparison claim",
                "academic_style",
                "Name the shared concern and then explain the specific contrast between the works",
                "The sentence needs a more precise comparative thesis, but the teacher should preserve the student's intended argument.",
                0.78,
                "medium",
            )
        )

    if not feedback:
        feedback.append(
            _suggestion(
                "academic_reviewer",
                essay[:90] + ("..." if len(essay) > 90 else ""),
                "academic_style",
                "Add a clearer comparative thesis that names the two works, the shared theme, and the key contrast.",
                "The system found no high-confidence local error, so it routes a thesis-level suggestion for review.",
                0.62,
                "medium",
            )
        )

    return feedback


def feedback_issue_key(item: Dict[str, Any]) -> str:
    return f"{_norm(item.get('issue_type'))}::{_norm(item.get('span'))}"


def adjudicate_literary_feedback(feedback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in feedback:
        groups[feedback_issue_key(item)].append(item)

    decisions: List[Dict[str, Any]] = []
    for items in groups.values():
        issue_type = _safe_text(items[0].get("issue_type"))
        span = _safe_text(items[0].get("span"))
        suggestion_counts = Counter(_norm(item.get("suggestion")) for item in items)
        selected_norm, selected_count = suggestion_counts.most_common(1)[0]
        selected = next(item for item in items if _norm(item.get("suggestion")) == selected_norm)
        evidence = [e for item in items for e in item.get("knowledge_evidence", []) if _safe_text(e)]
        avg_conf = sum(float(item.get("confidence", 0.0) or 0.0) for item in items) / len(items)
        max_risk = "high" if any(item.get("meaning_change_risk") == "high" for item in items) else "medium" if any(item.get("meaning_change_risk") == "medium" for item in items) else "low"
        agreement = selected_count / len(items)
        kg_supported = bool(evidence)

        if issue_type in {"grammar", "word_choice"} and agreement >= 0.5 and max_risk == "low":
            risk_level = "low"
            decision = "auto_accept"
            teacher_action = "Optional skim"
            priority = 3
            rationale = "Low-risk local language edit with reviewer agreement."
        elif issue_type == "literary_fact" and kg_supported and agreement >= 0.5:
            risk_level = "medium"
            decision = "teacher_review"
            teacher_action = "Verify factual correction"
            priority = 2
            rationale = "Knowledge-supported factual correction; route to teacher review before changing the essay."
        elif issue_type in {"argument", "academic_style"} or max_risk == "high":
            risk_level = "high" if max_risk == "high" else "medium"
            decision = "teacher_review"
            teacher_action = "Review meaning change"
            priority = 1 if risk_level == "high" else 2
            rationale = "The suggestion may change interpretation, thesis framing, or student intent."
        else:
            risk_level = "medium"
            decision = "teacher_review"
            teacher_action = "Check manually"
            priority = 2
            rationale = "Insufficient agreement or evidence for automatic adoption."

        decisions.append(
            {
                "span": span,
                "issue_type": issue_type,
                "selected_suggestion": _safe_text(selected.get("suggestion")),
                "decision": decision,
                "risk_level": risk_level,
                "teacher_action": teacher_action,
                "priority": priority,
                "agreement": round(agreement, 3),
                "avg_confidence": round(avg_conf, 3),
                "kg_supported": kg_supported,
                "evidence_count": len(evidence),
                "knowledge_evidence": " | ".join(dict.fromkeys(evidence[:3])),
                "rationale": rationale,
            }
        )

    return sorted(decisions, key=lambda row: (row["priority"], ISSUE_ORDER.get(row["issue_type"], 99), row["span"]))


def apply_auto_accepted_edits(essay: str, decisions: List[Dict[str, Any]]) -> str:
    revised = essay
    for item in decisions:
        if item.get("decision") != "auto_accept":
            continue
        span = _safe_text(item.get("span"))
        suggestion = _safe_text(item.get("selected_suggestion"))
        if not span or not suggestion:
            continue
        revised = re.sub(re.escape(span), suggestion, revised, count=1, flags=re.I)
    return revised


def review_queue(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item for item in decisions if item.get("decision") == "teacher_review"]


def decision_summary_by_type(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in decisions:
        grouped[_safe_text(item.get("issue_type"))].append(item)
    rows = []
    for issue_type, items in grouped.items():
        rows.append(
            {
                "issue_type": issue_type,
                "total": len(items),
                "auto_accept": sum(1 for item in items if item.get("decision") == "auto_accept"),
                "teacher_review": sum(1 for item in items if item.get("decision") == "teacher_review"),
                "kg_supported": sum(1 for item in items if item.get("kg_supported")),
            }
        )
    return sorted(rows, key=lambda row: ISSUE_ORDER.get(row["issue_type"], 99))


def literary_routing_summary(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(decisions)
    auto = sum(1 for item in decisions if item.get("decision") == "auto_accept")
    review = total - auto
    return {
        "total_suggestions": total,
        "auto_accept": auto,
        "teacher_review": review,
        "auto_share": round(auto / total, 3) if total else 0.0,
        "review_share": round(review / total, 3) if total else 0.0,
        "high_risk": sum(1 for item in decisions if item.get("risk_level") == "high"),
        "kg_supported": sum(1 for item in decisions if item.get("kg_supported")),
    }


def build_literary_feedback_report(
    essay: str,
    kg_rows: List[Dict[str, str]],
    feedback: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
) -> str:
    summary = literary_routing_summary(decisions)
    revised = apply_auto_accepted_edits(essay, decisions)
    queue = review_queue(decisions)
    lines = [
        "# ConsensusScope ESL Literary Feedback Report",
        "",
        "## Essay",
        "",
        essay,
        "",
        "## Routing Summary",
        "",
        f"- Total suggestions: {summary['total_suggestions']}",
        f"- Auto-accepted low-risk edits: {summary['auto_accept']} ({summary['auto_share']})",
        f"- Teacher-review suggestions: {summary['teacher_review']} ({summary['review_share']})",
        f"- KG-supported suggestions: {summary['kg_supported']}",
        f"- High-risk suggestions: {summary['high_risk']}",
        "",
        "## Auto-Accepted Preview",
        "",
        revised,
        "",
        "## Teacher Review Queue",
        "",
    ]
    for item in queue:
        lines.extend(
            [
                f"- [{item['risk_level']}] {item['span']} -> {item['selected_suggestion']}",
                f"  - Action: {item['teacher_action']}",
                f"  - Rationale: {item['rationale']}",
            ]
        )
    lines.extend(
        [
        "",
        "## Retrieved Literary Knowledge",
        "",
        ]
    )
    for row in kg_rows:
        lines.append(f"- {row.get('entity')} / {row.get('relation')} / {row.get('value')}: {row.get('evidence')}")
    lines.extend(["", "## Adjudicated Feedback", ""])
    for item in decisions:
        lines.extend(
            [
                f"### {item['issue_type']} · {item['risk_level']}",
                "",
                f"- Span: {item['span']}",
                f"- Decision: {item['decision']}",
                f"- Selected suggestion: {item['selected_suggestion']}",
                f"- Agreement: {item['agreement']}",
                f"- Knowledge evidence: {item['knowledge_evidence'] or 'N/A'}",
                f"- Rationale: {item['rationale']}",
                "",
            ]
        )
    lines.extend(["## Raw Reviewer Suggestions", "", "```json", json.dumps(feedback, ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines)
