"""EN↔FR expansion for search queries (Canadian political vocabulary)."""

from __future__ import annotations

import re

PAIRS: tuple[tuple[str, str], ...] = (
    ("political financing", "financement politique"),
    ("quarterly returns", "rapports trimestriels"),
    ("campaign promise", "promesse électorale"),
    ("mandate letter", "lettre de mandat"),
    ("conflict of interest", "conflit d'intérêts"),
    ("public office holder", "titulaire d'une charge publique"),
    ("communication report", "rapport de communication"),
    ("monthly return", "rapport mensuel"),
    ("proactive disclosure", "divulgation proactive"),
    ("government contracts", "contrats gouvernementaux"),
    ("federal contracts", "contrats fédéraux"),
    ("political donations", "dons politiques"),
    ("registered party", "parti enregistré"),
    ("lobbying", "lobbyisme"),
    ("lobbyist", "lobbyiste"),
    ("contracts", "contrats"),
    ("contract", "contrat"),
    ("promise", "promesse"),
    ("promises", "promesses"),
    ("ethics", "éthique"),
    ("finance", "finances"),
    ("donations", "dons"),
    ("donation", "don"),
    ("minister", "ministre"),
    ("cabinet", "conseil des ministres"),
    ("parliament", "parlement"),
    ("elections", "élections"),
    ("election", "élection"),
    ("party", "parti"),
    ("parties", "partis"),
    ("vendor", "fournisseur"),
    ("housing", "logement"),
    ("affordability", "abordabilité"),
    ("carbon", "carbone"),
    ("climate", "climat"),
    ("immigration", "immigration"),
    ("defence", "défense"),
    ("defense", "défense"),
    ("trade", "commerce"),
    ("tariff", "tarif"),
    ("tariffs", "tarifs"),
    ("broken promise", "promesse rompue"),
    ("kept promise", "promesse tenue"),
    ("fact check", "vérification des faits"),
    ("contradiction", "contradiction"),
    ("canada", "canada"),
)

_FR_HINT = re.compile(
    r"[àâäéèêëîïôùûüçœ]|(\b(le|la|les|des|du|un|une|et|ou|pour|dans|sur|avec|promesse|contrat|dons?|financement|ministre|lobbyisme)\b)",
    re.I,
)


def looks_french(text: str) -> bool:
    return bool(_FR_HINT.search(text or ""))


def _sub_pairs(text: str, to_fr: bool) -> str:
    out = text
    directed = [(en, fr) if to_fr else (fr, en) for en, fr in PAIRS]
    directed.sort(key=lambda p: len(p[0]), reverse=True)
    for src, dst in directed:
        out = re.sub(r"\b" + re.escape(src) + r"\b", dst, out, flags=re.I)
    return out


def glossary_other(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    to_fr = not looks_french(text)
    translated = _sub_pairs(text, to_fr)
    if translated.lower() != text.lower():
        return translated
    return ""


def expand_terms(text: str, extra: str | None = None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in (text, extra, glossary_other(text)):
        term = (raw or "").strip()
        if len(term) < 2:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(term)
    return out[:6]
