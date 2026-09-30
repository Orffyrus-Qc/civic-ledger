"""Country profiles for official-domain political search. Public records only."""

from __future__ import annotations

from typing import Any

WORLD_NEWS = {
    "www.reuters.com",
    "apnews.com",
    "www.bbc.com",
    "www.bbc.co.uk",
    "www.theguardian.com",
    "www.politico.com",
    "www.politico.eu",
    "www.aljazeera.com",
    "www.france24.com",
    "www.dw.com",
    "theconversation.com",
    "www.nytimes.com",
    "www.washingtonpost.com",
    "www.ft.com",
    "www.economist.com",
    "www.lemonde.fr",
    "www.lefigaro.fr",
    "www.spiegel.de",
    "www.abc.net.au",
    "www.theglobeandmail.com",
    "www.cbc.ca",
}

# ISO code, English name, French name, official host suffixes, extra hosts, extra news, searx lang
_RAW: list[tuple] = [
    ("CA", "Canada", "Canada", (".gc.ca", ".canada.ca", ".parl.ca", ".elections.ca"),
     ("openparliament.ca", "open.canada.ca", "lobbycanada.gc.ca"),
     ("www.cbc.ca", "ici.radio-canada.ca", "www.lapresse.ca", "www.ledevoir.com"), "en-CA"),
    ("US", "United States", "États-Unis", (".gov", ".mil", ".senate.gov", ".house.gov"),
     ("www.congress.gov", "www.whitehouse.gov", "www.fec.gov", "www.gao.gov"),
     ("www.politico.com", "www.npr.org", "www.propublica.org"), "en-US"),
    ("GB", "United Kingdom", "Royaume-Uni", (".gov.uk", ".parliament.uk", ".nhs.uk"),
     ("www.parliament.uk", "www.gov.uk", "ico.org.uk"),
     ("www.bbc.co.uk", "www.theguardian.com", "news.sky.com"), "en-GB"),
    ("FR", "France", "France", (".gouv.fr", ".assemblee-nationale.fr", ".senat.fr"),
     ("www.vie-publique.fr", "www.elysee.fr", "www.hatvp.fr"),
     ("www.lemonde.fr", "www.liberation.fr", "www.francetvinfo.fr"), "fr-FR"),
    ("DE", "Germany", "Allemagne", (".bund.de", ".bundestag.de", ".bundesrat.de"),
     ("www.bundesregierung.de", "www.bundeswahlleiter.de"),
     ("www.spiegel.de", "www.zeit.de", "www.tagesschau.de"), "de-DE"),
    ("AU", "Australia", "Australie", (".gov.au", ".aph.gov.au", ".aec.gov.au"),
     ("www.aph.gov.au", "www.transparency.gov.au"),
     ("www.abc.net.au", "www.smh.com.au", "www.theage.com.au"), "en-AU"),
    ("NZ", "New Zealand", "Nouvelle-Zélande", (".govt.nz", ".parliament.nz"),
     ("www.elections.nz",), ("www.rnz.co.nz", "www.stuff.co.nz"), "en-NZ"),
    ("IE", "Ireland", "Irlande", (".gov.ie", ".oireachtas.ie"),
     ("www.sipo.ie",), ("www.rte.ie", "www.irishtimes.com"), "en-IE"),
    ("IN", "India", "Inde", (".gov.in", ".nic.in", ".india.gov.in"),
     ("sansad.in", "eci.gov.in"), ("www.thehindu.com", "indianexpress.com"), "en-IN"),
    ("JP", "Japan", "Japon", (".go.jp", ".mod.go.jp"),
     ("www.shugiin.go.jp", "www.sangiin.go.jp"), ("www.nhk.or.jp", "www.asahi.com"), "ja-JP"),
    ("MX", "Mexico", "Mexique", (".gob.mx",),
     ("www.diputados.gob.mx", "www.ine.mx"), ("www.eluniversal.com.mx", "www.jornada.com.mx"), "es-MX"),
    ("BR", "Brazil", "Brésil", (".gov.br",),
     ("www.camara.leg.br", "www.senado.leg.br", "www.tse.jus.br"),
     ("www.folha.uol.com.br", "g1.globo.com"), "pt-BR"),
    ("IT", "Italy", "Italie", (".gov.it", ".camera.it", ".senato.it"),
     ("www.governo.it",), ("www.repubblica.it", "www.corriere.it"), "it-IT"),
    ("ES", "Spain", "Espagne", (".gob.es", ".congreso.es", ".senado.es"),
     ("www.lamoncloa.gob.es",), ("elpais.com", "www.elmundo.es"), "es-ES"),
    ("NL", "Netherlands", "Pays-Bas", (".overheid.nl", ".tweedekamer.nl", ".rijksoverheid.nl"),
     ("www.kiesraad.nl",), ("nos.nl", "www.nrc.nl"), "nl-NL"),
    ("BE", "Belgium", "Belgique", (".belgium.be", ".fgov.be", ".dekamer.be"),
     ("www.senate.be",), ("www.lesoir.be", "www.vrt.be"), "fr-BE"),
    ("CH", "Switzerland", "Suisse", (".admin.ch", ".parlament.ch"),
     ("www.bk.admin.ch",), ("www.srf.ch", "www.letemps.ch"), "de-CH"),
    ("AT", "Austria", "Autriche", (".gv.at", ".parlament.gv.at"),
     ("www.bmi.gv.at",), ("orf.at", "www.derstandard.at"), "de-AT"),
    ("SE", "Sweden", "Suède", (".regeringen.se", ".riksdagen.se", ".val.se"),
     ("www.government.se",), ("www.svt.se", "www.dn.se"), "sv-SE"),
    ("NO", "Norway", "Norvège", (".regjeringen.no", ".stortinget.no"),
     ("www.valg.no",), ("www.nrk.no", "www.aftenposten.no"), "nb-NO"),
    ("DK", "Denmark", "Danemark", (".gov.dk", ".ft.dk", ".borger.dk"),
     ("www.stm.dk",), ("www.dr.dk", "www.politiken.dk"), "da-DK"),
    ("FI", "Finland", "Finlande", (".gov.fi", ".eduskunta.fi", ".valtioneuvosto.fi"),
     ("vaalit.fi",), ("yle.fi", "www.hs.fi"), "fi-FI"),
    ("PL", "Poland", "Pologne", (".gov.pl", ".sejm.gov.pl", ".senat.gov.pl"),
     ("www.prezydent.pl",), ("www.tvn24.pl", "wyborcza.pl"), "pl-PL"),
    ("PT", "Portugal", "Portugal", (".gov.pt", ".parlamento.pt"),
     ("www.portugal.gov.pt",), ("www.publico.pt", "observador.pt"), "pt-PT"),
    ("IE2", "skip", "skip", (), (), (), "en"),
    ("ZA", "South Africa", "Afrique du Sud", (".gov.za", ".parliament.gov.za"),
     ("www.gov.za",), ("www.news24.com", "mg.co.za"), "en-ZA"),
    ("KR", "South Korea", "Corée du Sud", (".go.kr", ".assembly.go.kr"),
     ("www.korea.kr",), ("www.koreaherald.com", "www.chosun.com"), "ko-KR"),
    ("SG", "Singapore", "Singapour", (".gov.sg", ".parliament.gov.sg"),
     ("www.eld.gov.sg",), ("www.straitstimes.com", "www.channelnewsasia.com"), "en-SG"),
    ("PH", "Philippines", "Philippines", (".gov.ph",),
     ("www.congress.gov.ph", "www.comelec.gov.ph"), ("www.rappler.com", "newsinfo.inquirer.net"), "en-PH"),
    ("NG", "Nigeria", "Nigeria", (".gov.ng",),
     ("www.nass.gov.ng", "www.inecnigeria.org"), ("www.premiumtimesng.com", "punchng.com"), "en-NG"),
    ("KE", "Kenya", "Kenya", (".go.ke", ".gov.ke"),
     ("www.parliament.go.ke",), ("www.nation.africa", "www.standardmedia.co.ke"), "en-KE"),
    ("AR", "Argentina", "Argentine", (".gob.ar", ".gov.ar"),
     ("www.argentina.gob.ar", "www.electoral.gob.ar"), ("www.lanacion.com.ar", "www.clarin.com"), "es-AR"),
    ("CL", "Chile", "Chili", (".gob.cl", ".gov.cl"),
     ("www.bcn.cl", "www.servel.cl"), ("www.latercera.com", "www.emol.com"), "es-CL"),
    ("CO", "Colombia", "Colombie", (".gov.co",),
     ("www.senado.gov.co", "www.registraduria.gov.co"), ("www.eltiempo.com", "www.elespectador.com"), "es-CO"),
    ("IL", "Israel", "Israël", (".gov.il", ".knesset.gov.il"),
     ("www.gov.il",), ("www.timesofisrael.com", "www.haaretz.com"), "he-IL"),
    ("UA", "Ukraine", "Ukraine", (".gov.ua",),
     ("www.rada.gov.ua", "www.president.gov.ua"), ("www.pravda.com.ua", "www.kyivindependent.com"), "uk-UA"),
    ("EU", "European Union", "Union européenne",
     (".europa.eu", ".europarl.europa.eu"),
     ("commission.europa.eu", "www.consilium.europa.eu"),
     ("www.euronews.com", "www.politico.eu"), "en"),
    ("MX2", "skip", "skip", (), (), (), "en"),
]

COUNTRIES: dict[str, dict[str, Any]] = {}
for row in _RAW:
    code, name, name_fr, suffixes, hosts, news, lang = row
    if name == "skip":
        continue
    COUNTRIES[code] = {
        "code": code,
        "name": name,
        "name_fr": name_fr,
        "suffixes": tuple(suffixes),
        "hosts": tuple(hosts),
        "news": set(news) | set(WORLD_NEWS),
        "lang": lang,
        "structured": code == "CA",
    }


def normalize(code: str | None) -> str:
    c = (code or "CA").strip().upper()
    if c in COUNTRIES:
        return c
    if len(c) == 2 and c.isalpha():
        return c
    return "CA"


def profile(code: str | None) -> dict[str, Any]:
    c = normalize(code)
    if c in COUNTRIES:
        return COUNTRIES[c]
    # Unknown ISO code: still searchable by name if the UI sent a label.
    return {
        "code": c,
        "name": c,
        "name_fr": c,
        "suffixes": (f".gov.{c.lower()}", f".gob.{c.lower()}", f".go.{c.lower()}", ".gov"),
        "hosts": (),
        "news": tuple(WORLD_NEWS),
        "lang": "en",
        "structured": False,
    }


def list_countries() -> list[dict[str, str]]:
    items = [
        {"code": p["code"], "name": p["name"], "name_fr": p["name_fr"]}
        for p in COUNTRIES.values()
    ]
    items.sort(key=lambda x: (0 if x["code"] == "CA" else 1, x["name"]))
    return items


def search_jobs(code: str | None) -> list[dict[str, str]]:
    p = profile(code)
    if p["code"] == "CA":
        from .collectors import SEARCH_POOL

        return list(SEARCH_POOL)
    name = p["name"]
    suffix = p["suffixes"][0] if p["suffixes"] else ""
    site = f"site:{suffix.lstrip('.')}" if suffix else ""
    lang = (p.get("lang") or "en")[:2]
    jobs = [
        {"id": "finance", "category": "finance", "lang": "en",
         "query": f"{name} political donations campaign finance lobbying 2025 2026 {site}"},
        {"id": "contracts", "category": "contract", "lang": "en",
         "query": f"{name} government contracts procurement spending {site}"},
        {"id": "lobby", "category": "lobbying", "lang": "en",
         "query": f"{name} lobbying register transparency {site}"},
        {"id": "promises", "category": "promise", "lang": "en",
         "query": f"{name} campaign promise tracker kept broken 2025 2026"},
        {"id": "ethics", "category": "ethics", "lang": "en",
         "query": f"{name} conflict of interest ethics minister {site}"},
        {"id": "contradiction", "category": "contradiction", "lang": "en",
         "query": f"{name} minister contradicts fact check 2025 2026"},
    ]
    if lang == "fr":
        jobs.append(
            {"id": "finance-fr", "category": "finance", "lang": "fr",
             "query": f"{p['name_fr']} dons politiques lobbying contrats {site}"}
        )
    return jobs
