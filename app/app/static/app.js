const listEl = document.getElementById("list");
const statusEl = document.getElementById("status");
let category = "all";
let query = "";
let tab = "findings";
let country = localStorage.getItem("cpl-country") || "CA";
let lastWeb = { q: "", lang: "", items: [], q_en: "", q_fr: "" };

function withCountry(params) {
  params.set("country", country);
  return params;
}

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function sourceLinks(sources) {
  if (!Array.isArray(sources) || !sources.length) return "";
  return `<ul class="sources">${sources
    .slice(0, 4)
    .map(
      (s) =>
        `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(
          s.title || s.url
        )}</a>${s.kind ? ` <span class="pill">${esc(s.kind)}</span>` : ""}</li>`
    )
    .join("")}</ul>`;
}

function entityPills(entities) {
  return (entities || [])
    .slice(0, 6)
    .map((e) => {
      const slug = String(e)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      return `<a class="pill" href="/entity/${esc(slug)}">${esc(e)}</a>`;
    })
    .join(" ");
}

function renderWebHits() {
  if (!query || lastWeb.q !== query) return "";
  const pair = [lastWeb.q_en, lastWeb.q_fr].filter(Boolean);
  const also = pair.length > 1 ? `<p class="muted">${t("also_searched")}: <em>${esc(pair.join(" · "))}</em></p>` : "";
  if (!lastWeb.items.length) {
    return `<section class="card"><h2>${t("web_search")}</h2>${also}<p class="muted">${t("no_web")}</p></section>`;
  }
  const rows = lastWeb.items
    .slice(0, 8)
    .map(
      (h) =>
        `<li><span class="pill">${esc(h.kind || "")}</span> <a href="${esc(h.url)}" target="_blank" rel="noopener noreferrer">${esc(
          h.title || h.url
        )}</a> <span class="muted">${esc((h.snippet || "").slice(0, 140))}</span></li>`
    )
    .join("");
  return `<section class="card"><h2>${t("web_search")}</h2>${also}<ul class="sources">${rows}</ul></section>`;
}

function renderFindings(items) {
  const web = renderWebHits();
  if (!items.length) {
    listEl.innerHTML = web + `<div class="empty">${t("empty")}</div>`;
    return;
  }
  listEl.innerHTML =
    web +
    items
    .map((item) => {
      const amt = item.money && item.money.amount;
      const money =
        amt && amt !== "null" && amt !== "None"
          ? `<p class="muted">${t("money")}: ${esc(amt)} ${esc(item.money.currency || "CAD")}</p>`
          : "";
      return `<article class="card">
        <p class="badges">
          <span class="cat ${esc(item.category)}">${esc(labelCat(item.category))}</span>
          <span class="sev ${esc(item.severity)}">${esc(labelSev(item.severity))}</span>
          <span class="pill origin ${esc(item.origin || "model")}">${esc(labelOrigin(item.origin || "model"))}</span>
          <span class="pill">${esc(labelStatus(item.promise_status))}</span>
          <span class="pill">${Math.round((item.confidence || 0) * 100)}%</span>
        </p>
        <h2><a href="/finding/${item.id}">${esc(item.title)}</a></h2>
        <p>${esc(item.summary)}</p>
        ${money}
        <p>${entityPills(item.entities)}</p>
        ${sourceLinks(item.sources)}
        <p class="muted">${esc(item.source_date || item.created_at || "")} · ${t("review")} ${esc(
          labelReview(item.review_status || "pending")
        )}</p>
      </article>`;
    })
    .join("");
}

function renderScoreboard(board) {
  if (board.note === "scoreboard_ca_only") {
    listEl.innerHTML = `<section class="card"><h2>${t("board_title")}</h2><p>${t("board_ca_only")}</p></section>`;
    return;
  }
  const counts = board.counts || {};
  const summary = `<p class="badges">
    <span class="pill origin extracted">${counts.kept || 0} ${t("board_kept")}</span>
    <span class="pill">${counts.partial || 0} ${t("board_partial")}</span>
    <span class="pill">${counts.broken || 0} ${t("board_broken")}</span>
    <span class="pill">${counts.unverified || 0} ${t("board_unverified")}</span>
  </p>
  <p class="muted">${t("board_scored")}: ${esc(board.scored_at || "")}</p>`;
  const section = (title, rows) => {
    if (!rows || !rows.length) return "";
    const cards = rows
      .map((c) => {
        const ev = c.evidence_url
          ? `<p><a href="${esc(c.evidence_url)}" target="_blank" rel="noopener noreferrer">${t("board_evidence")}: ${esc(
              c.evidence_title || c.evidence_url
            )}</a></p>`
          : `<p class="muted">${t("board_none")}</p>`;
        return `<article class="card">
          <p class="badges"><span class="pill origin extracted">${esc(labelStatus(c.status))}</span></p>
          <h2>${esc(c.title)}</h2>
          <p>${esc(c.score_note || c.body || "")}</p>
          ${ev}
          <p class="muted">${esc(c.source_date || "")} · ${esc(c.minister || "")}</p>
        </article>`;
      })
      .join("");
    return `<h2>${esc(title)}</h2>${cards}`;
  };
  listEl.innerHTML =
    `<section class="card"><h2>${t("board_title")}</h2>${summary}</section>` +
    section(t("board_missions"), board.missions || []) +
    section(t("board_platform"), board.platform || []);
}

function renderTable(rows, cols) {
  if (!rows.length) {
    listEl.innerHTML = `<div class="empty">${t("empty")}</div>`;
    return;
  }
  const head = cols.map((c) => `<th>${esc(c.label)}</th>`).join("");
  const body = rows
    .map(
      (row) =>
        `<tr>${cols
          .map((c) => {
            const val = row[c.key];
            if (c.href && val) {
              return `<td><a href="${esc(typeof c.href === "function" ? c.href(row) : val)}" ${
                c.external ? 'target="_blank" rel="noopener"' : ""
              }>${esc(c.format ? c.format(row) : val)}</a></td>`;
            }
            return `<td>${esc(c.format ? c.format(row) : val ?? "")}</td>`;
          })
          .join("")}</tr>`
    )
    .join("");
  listEl.innerHTML = `<table class="data"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

async function load() {
  applyI18n();
  const health = await fetch("/api/health?" + withCountry(new URLSearchParams())).then((r) => r.json());
  const st = health.stats || {};
  document.getElementById("stat-findings").textContent = st.findings ?? "0";
  document.getElementById("stat-hits").textContent = st.hits ?? "0";
  document.getElementById("stat-money").textContent = st.money_events ?? "0";
  document.getElementById("stat-claims").textContent = st.claims ?? "0";
  document.getElementById("stat-running").textContent = st.running ? t("running") : t("idle");
  if (!health.model_ready) statusEl.textContent = "Model: " + (health.model_detail || "");
  else if (st.running) statusEl.textContent = t("scan_progress");
  else if (!statusEl.dataset.hold) statusEl.textContent = "";

  if (tab === "findings") {
    const params = new URLSearchParams({
      category,
      limit: "100",
      hide_low: document.getElementById("hide-low").checked,
      hide_unverified: document.getElementById("hide-unverified").checked,
      sort: document.getElementById("sort").value,
    });
    if (query) params.set("q", query);
    const data = await fetch("/api/findings?" + withCountry(params)).then((r) => r.json());
    renderFindings(data.items || []);
    return;
  }
  if (tab === "money") {
    const data = await fetch("/api/money?" + withCountry(new URLSearchParams())).then((r) => r.json());
    renderTable(data.items || [], [
      { key: "event_date", label: t("col_date") },
      { key: "role", label: t("col_role") },
      { key: "actor", label: t("col_actor") },
      { key: "counterpart", label: t("col_counterpart") },
      { key: "amount", label: t("col_amount") },
      { key: "currency", label: t("col_fx") },
    ]);
    return;
  }
  if (tab === "promises") {
    const board = await fetch("/api/scoreboard?" + withCountry(new URLSearchParams())).then((r) => r.json());
    renderScoreboard(board);
    return;
  }
  if (tab === "entities") {
    const data = await fetch("/api/entities?" + withCountry(new URLSearchParams())).then((r) => r.json());
    renderTable(data.items || [], [
      {
        key: "name",
        label: t("col_name"),
        href: (row) => "/entity/" + row.slug,
        format: (row) => row.name,
      },
      { key: "kind", label: t("col_kind") },
      { key: "n", label: t("col_findings") },
    ]);
    return;
  }
  if (tab === "sources") {
    const data = await fetch("/api/hits?" + withCountry(new URLSearchParams())).then((r) => r.json());
    renderTable(data.items || [], [
      { key: "kind", label: t("col_kind") },
      { key: "title", label: t("col_title"), href: (row) => row.url, external: true, format: (row) => row.title },
      { key: "engine", label: t("col_engine") },
      { key: "created_at", label: t("col_seen") },
    ]);
    return;
  }
  if (tab === "scans") {
    const data = await fetch("/api/scans?" + withCountry(new URLSearchParams())).then((r) => r.json());
    renderTable(data.items || [], [
      { key: "id", label: "#" },
      { key: "reason", label: t("col_reason") },
      { key: "status", label: t("col_status") },
      { key: "queries", label: t("col_queries") },
      { key: "hits", label: t("col_hits") },
      { key: "findings", label: t("col_findings") },
      { key: "started_at", label: t("col_started") },
      { key: "error", label: t("col_error") },
    ]);
  }
}

document.getElementById("filters").addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-cat]");
  if (!btn) return;
  category = btn.dataset.cat;
  document.querySelectorAll("#filters button").forEach((b) => b.classList.toggle("on", b === btn));
  load();
});

document.getElementById("tabs").addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-tab]");
  if (!btn) return;
  tab = btn.dataset.tab;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b === btn));
  load();
});

document.getElementById("search-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  query = document.getElementById("q").value.trim();
  tab = "findings";
  document.querySelectorAll("#tabs button").forEach((b) =>
    b.classList.toggle("on", b.dataset.tab === "findings")
  );
  if (query.length >= 2) {
    statusEl.textContent = t("searching_web");
    try {
      const lang = getLang();
      const data = await fetch(
        "/api/websearch?" + withCountry(new URLSearchParams({ q: query, lang }))
      ).then((r) => r.json());
      lastWeb = {
        q: query,
        lang,
        items: data.items || [],
        q_en: data.q_en || "",
        q_fr: data.q_fr || "",
      };
    } catch (err) {
      lastWeb = { q: query, lang: getLang(), items: [], q_en: query, q_fr: "" };
      statusEl.textContent = t("scan_failed") + ": " + err;
    }
  } else {
    lastWeb = { q: "", lang: "", items: [], q_en: "", q_fr: "" };
  }
  load();
});

["hide-low", "hide-unverified", "sort"].forEach((id) => {
  document.getElementById(id).addEventListener("change", load);
});

bindLangSwitch(async () => {
  document.title = t("brand");
  await fillCountries();
  if (query.length >= 2) {
    try {
      const lang = getLang();
      const data = await fetch(
        "/api/websearch?" + withCountry(new URLSearchParams({ q: query, lang }))
      ).then((r) => r.json());
      lastWeb = {
        q: query,
        lang,
        items: data.items || [],
        q_en: data.q_en || "",
        q_fr: data.q_fr || "",
      };
    } catch (_err) {
      /* keep previous web hits */
    }
  }
  load();
});

document.getElementById("scan-btn").addEventListener("click", async () => {
  statusEl.dataset.hold = "1";
  statusEl.textContent = t("scan_starting");
  document.getElementById("scan-btn").disabled = true;
  try {
    const res = await fetch("/api/scan?" + withCountry(new URLSearchParams()), { method: "POST" });
    const data = await res.json();
    statusEl.textContent =
      data.status === "started"
        ? t("scan_started")
        : data.status === "busy"
          ? t("scan_busy")
          : t("scan_error") + ": " + (data.error || data.status);
  } catch (err) {
    statusEl.textContent = t("scan_failed") + ": " + err;
  } finally {
    document.getElementById("scan-btn").disabled = false;
    setTimeout(() => {
      delete statusEl.dataset.hold;
      load();
    }, 2500);
  }
});

async function fillCountries() {
  const sel = document.getElementById("country-sel");
  if (!sel) return;
  const data = await fetch("/api/countries").then((r) => r.json());
  const lang = getLang();
  sel.innerHTML = (data.items || [])
    .map((c) => `<option value="${esc(c.code)}">${esc(lang === "fr" ? c.name_fr : c.name)}</option>`)
    .join("");
  if (![...sel.options].some((o) => o.value === country)) country = "CA";
  sel.value = country;
}

document.getElementById("country-sel").addEventListener("change", () => {
  country = document.getElementById("country-sel").value || "CA";
  localStorage.setItem("cpl-country", country);
  lastWeb = { q: "", lang: "", items: [], q_en: "", q_fr: "" };
  load();
});

applyI18n();
document.title = t("brand");
fillCountries().then(() => {
  load();
  setInterval(load, 15000);
});
