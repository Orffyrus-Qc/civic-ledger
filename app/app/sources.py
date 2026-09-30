"""Allowlist of public Canadian political / journalistic sources. No people-search."""

from __future__ import annotations

from urllib.parse import urlparse

# Official government, parliament, watchdogs, open data.
OFFICIAL_SUFFIXES = (
    ".gc.ca",
    ".canada.ca",
    ".parl.gc.ca",
    ".parl.ca",
    ".ourcommons.ca",
    ".elections.ca",
    ".pbo-dpb.ca",
    ".ci.gc.ca",
)

OFFICIAL_HOSTS = {
    "open.canada.ca",
    "search.open.canada.ca",
    "openparliament.ca",
    "api.openparliament.ca",
    "www.ourcommons.ca",
    "www.parl.ca",
    "lop.parl.ca",
    "www.canada.ca",
    "www.elections.ca",
    "lobbycanada.gc.ca",
    "www.lobbycanada.gc.ca",
    "search.lobbycanada.gc.ca",
    "ciec-ccie.parl.gc.ca",
    "www.ciec-ccie.parl.gc.ca",
    "laws-lois.justice.gc.ca",
    "www.justice.gc.ca",
    "canadagazette.gc.ca",
    "www.gazette.gc.ca",
    "canadabuyandsell.gc.ca",
    "canadabuys.canada.ca",
    "www.tpsgc-pwgsc.gc.ca",
    "www.pbo-dpb.ca",
    "www.oag-bvg.gc.ca",
    "www.priv.gc.ca",
    "www.cbc.ca",
}

# National / major regional newsrooms that publish political reporting.
NEWS_HOSTS = {
    "www.cbc.ca",
    "cbc.ca",
    "ici.radio-canada.ca",
    "www.radio-canada.ca",
    "www.theglobeandmail.com",
    "www.nationalpost.com",
    "nationalpost.com",
    "www.thestar.com",
    "www.ctvnews.ca",
    "globalnews.ca",
    "www.lapresse.ca",
    "www.ledevoir.com",
    "www.macleans.ca",
    "www.hilltimes.com",
    "www.ipolitics.ca",
    "ipolitics.ca",
    "www.thecanadianpress.com",
    "www.cp24.com",
    "www.nationalobserver.com",
    "thetyee.ca",
    "www.thetyee.ca",
    "www.canadaland.com",
    "theconversation.com",
    "www.reuters.com",
    "apnews.com",
    "www.theguardian.com",
    "www.politico.com",
    "www.bbc.com",
    "www.bbc.co.uk",
}

BLOCKED_HOSTS = {
    "www.whitepages.com",
    "www.whitepages.ca",
    "www.411.ca",
    "www.canada411.ca",
    "www.spokeo.com",
    "www.beenverified.com",
    "www.truepeoplesearch.com",
    "www.fastpeoplesearch.com",
    "www.thatsthem.com",
    "www.intelius.com",
    "www.peoplefinder.com",
    "www.zoominfo.com",
    "www.rocketreach.co",
    "pipl.com",
    "www.pipl.com",
    "www.familytreenow.com",
    "www.ancestry.ca",
    "www.ancestry.com",
    "www.zabasearch.com",
    "radaris.com",
    "www.radaris.com",
}

BLOCKED_KEYWORDS = (
    "people search",
    "find person",
    "background check",
    "home address",
    "residential address",
    "phone number lookup",
    "sin number",
    "social insurance",
    "dox",
    "doxx",
    "personal cell",
)


def _host(url: str) -> str:
    try:
        return urlparse(url).hostname.lower() if urlparse(url).hostname else ""
    except Exception:
        return ""


def is_blocked(url: str) -> bool:
    host = _host(url)
    if not host:
        return True
    if host in BLOCKED_HOSTS:
        return True
    if any(host == b or host.endswith("." + b) for b in BLOCKED_HOSTS):
        return True
    return False


def is_official(url: str, country: str | None = None) -> bool:
    host = _host(url)
    if not host:
        return False
    from .countries import normalize, profile

    code = normalize(country)
    if code == "CA":
        if host in OFFICIAL_HOSTS:
            return True
        return any(host.endswith(suffix) for suffix in OFFICIAL_SUFFIXES)
    p = profile(code)
    if host in p["hosts"]:
        return True
    for suffix in p["suffixes"]:
        s = suffix if suffix.startswith(".") else "." + suffix
        if host.endswith(s) or host == s[1:]:
            return True
    return False


def is_news(url: str, country: str | None = None) -> bool:
    host = _host(url)
    if host in NEWS_HOSTS:
        return True
    from .countries import profile

    return host in profile(country)["news"]


def is_allowed(url: str, country: str | None = None) -> bool:
    if is_blocked(url):
        return False
    return is_official(url, country) or is_news(url, country)


def source_kind(url: str, country: str | None = None) -> str:
    if is_official(url, country):
        return "official"
    if is_news(url, country):
        return "news"
    return "blocked"
