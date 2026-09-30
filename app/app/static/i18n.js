const I18N = {
  en: {
    brand: "Canadian Political Leak",
    tag: "Public-source watchdog · follow the money · promises vs. record",
    disclaimer:
      "Tracks public officials, parties, lobbyists, contracts, and published reporting. Private addresses, phones, SINs, and people-search dumps are blocked.",
    sandbox: "sandbox",
    no_dox: "no doxing",
    lang_label: "Language",
    country_label: "Country",
    board_ca_only: "The scored mandate board is Canada-only. Run a scan for this country to collect public sources.",
    tab_findings: "Findings",
    tab_money: "Money",
    tab_promises: "Promises",
    tab_entities: "Entities",
    tab_sources: "Sources tray",
    tab_scans: "Scans",
    cat_all: "All",
    cat_finance: "Finance",
    cat_promise: "Promises",
    cat_contradiction: "Contradictions",
    cat_lobbying: "Lobbying",
    cat_contract: "Contracts",
    cat_ethics: "Ethics",
    cat_other: "Other",
    search: "Filter or search the web…",
    search_btn: "Search",
    web_search: "Web search",
    searching_web: "Searching the web in English and French…",
    also_searched: "Also searched",
    no_web: "No allowlisted web hits for this query.",
    hide_low: "Hide low confidence",
    hide_unverified: "Hide unverified",
    sort_date: "Source date",
    sort_money: "Money",
    sort_conf: "Confidence",
    scan: "Run scan now",
    scan_starting: "Starting scan…",
    scan_started: "Scan started — extracted tables land first, then model stories",
    scan_busy: "A scan is already running",
    scan_error: "Scan error",
    scan_failed: "Scan failed",
    scan_progress: "Scan in progress…",
    idle: "idle",
    running: "running",
    stat_findings: "findings",
    stat_sources: "sources",
    stat_money: "money rows",
    stat_claims: "promises",
    empty: "Nothing in this view. Turn off the hide toggles or run a scan.",
    board_title: "2025 promise scoreboard",
    board_missions: "Carney mandate letter (21 May 2025)",
    board_platform: "2025 platform tracker (independent)",
    board_evidence: "Evidence",
    board_none: "No bill, vote, or contract matched yet.",
    board_scored: "Last scored",
    board_kept: "kept",
    board_partial: "partial",
    board_broken: "broken",
    board_unverified: "unverified",
    board_archive: "Older PCO letters",
    col_date: "Date",
    col_role: "Role",
    col_actor: "Actor",
    col_counterpart: "Counterpart",
    col_amount: "Amount",
    col_fx: "FX",
    col_status: "Status",
    col_minister: "Minister",
    col_commitment: "Commitment",
    col_name: "Name",
    col_kind: "Kind",
    col_findings: "Findings",
    col_title: "Title",
    col_engine: "Engine",
    col_seen: "Seen",
    col_reason: "Reason",
    col_queries: "Queries",
    col_hits: "Hits",
    col_started: "Started",
    col_error: "Error",
    money: "Money",
    review: "review",
    origin_extracted: "extracted",
    origin_model: "model",
    origin_official: "official",
    sev_low: "low",
    sev_medium: "medium",
    sev_high: "high",
    status_kept: "kept",
    status_broken: "broken",
    status_partial: "partial",
    status_unverified: "unverified",
    status_na: "n/a",
    review_pending: "pending",
    review_confirmed: "confirmed",
    review_rejected: "rejected",
    finding: "Finding",
    claim: "Claim / promise",
    evidence: "What the sources show",
    entities: "Public entities",
    matched: "Matched promises",
    sources: "Sources",
    source_date: "Source date",
    captured: "captured",
    unknown: "unknown",
    confirm: "Confirm",
    reject: "Reject",
    reset: "Reset",
    back: "← Back to list",
    timeline: "Timeline",
    entity_empty: "No linked findings yet.",
    footer:
      "Local Docker sandbox · SearXNG :8888 · UI :8088 · GPU 1 / Qwen3 8B · extracted tables ≠ model prose",
  },
  fr: {
    brand: "Fuite politique canadienne",
    tag: "Chien de garde public · suivre l’argent · promesses vs. bilan",
    disclaimer:
      "Suit les élus, partis, lobbyistes, contrats et reportages publics. Adresses privées, téléphones, NAS et sites de recherche de personnes sont bloqués.",
    sandbox: "bac à sable",
    no_dox: "pas de doxing",
    lang_label: "Langue",
    country_label: "Pays",
    board_ca_only: "Le tableau des promesses coté ne couvre que le Canada. Lancez un balayage pour ce pays afin de collecter des sources publiques.",
    tab_findings: "Constatations",
    tab_money: "Argent",
    tab_promises: "Promesses",
    tab_entities: "Entités",
    tab_sources: "Sources",
    tab_scans: "Balayages",
    cat_all: "Tout",
    cat_finance: "Finances",
    cat_promise: "Promesses",
    cat_contradiction: "Contradictions",
    cat_lobbying: "Lobbyisme",
    cat_contract: "Contrats",
    cat_ethics: "Éthique",
    cat_other: "Autre",
    search: "Filtrer ou chercher le web…",
    search_btn: "Chercher",
    web_search: "Recherche web",
    searching_web: "Recherche web en français et en anglais…",
    also_searched: "Aussi cherché",
    no_web: "Aucun résultat web sur la liste autorisée pour cette requête.",
    hide_low: "Masquer faible confiance",
    hide_unverified: "Masquer non vérifié",
    sort_date: "Date de source",
    sort_money: "Argent",
    sort_conf: "Confiance",
    scan: "Lancer un balayage",
    scan_starting: "Démarrage du balayage…",
    scan_started: "Balayage lancé — les tableaux extraits arrivent d’abord, puis les textes du modèle",
    scan_busy: "Un balayage est déjà en cours",
    scan_error: "Erreur de balayage",
    scan_failed: "Échec du balayage",
    scan_progress: "Balayage en cours…",
    idle: "inactif",
    running: "en cours",
    stat_findings: "constatations",
    stat_sources: "sources",
    stat_money: "lignes d’argent",
    stat_claims: "promesses",
    empty: "Rien ici. Désactivez les filtres ou lancez un balayage.",
    board_title: "Tableau des promesses 2025",
    board_missions: "Lettre de mandat Carney (21 mai 2025)",
    board_platform: "Suivi de la plateforme 2025 (indépendant)",
    board_evidence: "Preuve",
    board_none: "Aucun projet de loi, vote ou contrat associé pour l’instant.",
    board_scored: "Dernière évaluation",
    board_kept: "tenue",
    board_partial: "partielle",
    board_broken: "rompue",
    board_unverified: "non vérifiée",
    board_archive: "Lettres du BCP plus anciennes",
    col_date: "Date",
    col_role: "Rôle",
    col_actor: "Acteur",
    col_counterpart: "Contrepartie",
    col_amount: "Montant",
    col_fx: "Devise",
    col_status: "Statut",
    col_minister: "Ministre",
    col_commitment: "Engagement",
    col_name: "Nom",
    col_kind: "Type",
    col_findings: "Constatations",
    col_title: "Titre",
    col_engine: "Moteur",
    col_seen: "Vu",
    col_reason: "Motif",
    col_queries: "Requêtes",
    col_hits: "Résultats",
    col_started: "Début",
    col_error: "Erreur",
    money: "Argent",
    review: "revue",
    origin_extracted: "extrait",
    origin_model: "modèle",
    origin_official: "officiel",
    sev_low: "faible",
    sev_medium: "moyen",
    sev_high: "élevé",
    status_kept: "tenue",
    status_broken: "rompue",
    status_partial: "partielle",
    status_unverified: "non vérifiée",
    status_na: "s. o.",
    review_pending: "en attente",
    review_confirmed: "confirmée",
    review_rejected: "rejetée",
    finding: "Constatation",
    claim: "Affirmation / promesse",
    evidence: "Ce que montrent les sources",
    entities: "Entités publiques",
    matched: "Promesses associées",
    sources: "Sources",
    source_date: "Date de source",
    captured: "saisie",
    unknown: "inconnue",
    confirm: "Confirmer",
    reject: "Rejeter",
    reset: "Réinitialiser",
    back: "← Retour à la liste",
    timeline: "Chronologie",
    entity_empty: "Aucune constatation liée pour l’instant.",
    footer:
      "Bac à sable Docker local · SearXNG :8888 · interface :8088 · GPU 1 / Qwen3 8B · tableaux extraits ≠ prose du modèle",
  },
};

function getLang() {
  const saved = localStorage.getItem("cpl-lang");
  return saved === "fr" ? "fr" : "en";
}

function setLang(next) {
  localStorage.setItem("cpl-lang", next === "fr" ? "fr" : "en");
}

function t(key) {
  const lang = getLang();
  return (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
}

function labelCat(cat) {
  return t("cat_" + (cat || "other")) || cat;
}

function labelOrigin(origin) {
  return t("origin_" + (origin || "model")) || origin;
}

function labelSev(sev) {
  return t("sev_" + (sev || "medium")) || sev;
}

function labelStatus(status) {
  const key = status === "n/a" ? "status_na" : "status_" + (status || "unverified");
  return t(key) || status;
}

function labelReview(status) {
  return t("review_" + (status || "pending")) || status;
}

function applyI18n() {
  const lang = getLang();
  document.documentElement.lang = lang === "fr" ? "fr-CA" : "en-CA";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nAria));
  });
  document.querySelectorAll(".lang-switch [data-lang]").forEach((btn) => {
    btn.classList.toggle("on", btn.dataset.lang === lang);
  });
}

function bindLangSwitch(onChange) {
  document.querySelectorAll(".lang-switch [data-lang]").forEach((btn) => {
    btn.addEventListener("click", () => {
      setLang(btn.dataset.lang);
      applyI18n();
      if (typeof onChange === "function") onChange();
    });
  });
}
