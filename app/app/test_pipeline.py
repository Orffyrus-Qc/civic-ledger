import io
import zipfile

from .bilingual import expand_terms, glossary_other, looks_french
from .scoreboard import is_homepage_card, score_claims
from .util import looks_like_junk_title
from .analyzer import cap_confidence, sanitize_finding
from .collectors import rotate_search_jobs
from .dedup import canonical_key, normalize_title
from .lobby_dump import is_zip_bytes, parse_lobby_zip
from .mandate import parse_carney_mandate_html, parse_carney_tracker
from .money import format_cad, parse_amount
from .util import looks_like_junk_title, parse_date, lang_text
from .sources import is_allowed


def test_parliament_vote_title():
    desc = {
        "en": "2nd reading of Bill C-266, An Act to establish a national framework respecting skilled trades",
        "fr": "2e lecture",
    }
    title = lang_text(desc)
    assert "C-266" in title
    assert not looks_like_junk_title(title)
    assert looks_like_junk_title("174")
    assert looks_like_junk_title("Home - Canada.ca")
    assert looks_like_junk_title("TSX Composite Index (TXCX) Quote - The Globe and Mail")
    assert looks_like_junk_title("An Act respecting the Administration of Oaths of Office (pro forma bill)")


def test_money_parse():
    assert parse_amount("120518.57") == 120518.57
    assert parse_amount("$2.6 billion") == 2.6 * 1_000_000_000
    assert "million" in (format_cad(2_500_000) or "")


def test_dates():
    assert parse_date("2026-09-23") == "2026-09-23"
    assert parse_date("11/1/2017") is not None
    assert parse_date("May 21, 2025") == "2025-05-21"


def test_dedup_merges_quarterly():
    a = canonical_key({"title": "Quarterly Financial Returns for 2025 Now Available", "category": "finance", "entities": ["Liberal Party"]})
    b = canonical_key({"title": "Quarterly Financial Returns for 2022 Now Available", "category": "finance", "entities": ["Liberal Party"]})
    assert a == b
    assert "2025" not in normalize_title("Quarterly Financial Returns for 2025")


def test_confidence_cap():
    assert cap_confidence("model", None, None, 0.95) <= 0.55
    assert cap_confidence("extracted", 1000, "2026-01-01", 0.99) <= 0.95


def test_sanitize_drops_wikipedia_and_requires_source():
    bad = sanitize_finding(
        {
            "title": "Canada - Wikipedia",
            "summary": "Canada is a country",
            "category": "other",
            "sources": [{"url": "https://en.wikipedia.org/wiki/Canada", "title": "Canada"}],
        }
    )
    assert bad is None
    ok = sanitize_finding(
        {
            "title": "Federal contract: Acme — $120,000.00",
            "summary": "Acme received a disclosed federal contract on 2026-01-12.",
            "category": "contract",
            "origin": "extracted",
            "money": {"amount": "120000", "currency": "CAD"},
            "source_date": "2026-01-12",
            "confidence": 0.9,
            "sources": [{"url": "https://search.open.canada.ca/contracts/", "title": "contracts"}],
            "entities": ["Acme"],
        }
    )
    assert ok is not None
    assert ok["origin"] == "extracted"
    assert ok["money_amount"] == 120000


def test_allowlist():
    assert is_allowed("https://www.elections.ca/content.aspx")
    assert not is_allowed("https://en.wikipedia.org/wiki/Canada")


def test_scoreboard_housing_vote():
    claims = [
        {
            "id": 1,
            "title": "Carney 2025 mandate priority 4: Making housing more affordable by unleashing public-private cooperation",
            "body": "housing skilled trades",
            "status": "unverified",
        }
    ]
    evidence = [
        {
            "title": "2nd reading of Bill C-266, An Act to establish a national framework respecting skilled trades and labour mobility",
            "snippet": "Result Passed; yea 295 nay 21",
            "url": "https://openparliament.ca/votes/45-1/174/",
            "engine": "openparliament",
        }
    ]
    scored = score_claims(claims, evidence)
    assert scored[0]["status"] == "partial"
    assert "C-266" in (scored[0]["evidence_title"] or "")


def test_scoreboard_kept_on_adoption():
    claims = [
        {
            "id": 2,
            "title": "Carney 2025 mandate priority 5: Protecting Canadian sovereignty and keeping Canadians safe",
            "status": "unverified",
        }
    ]
    evidence = [
        {
            "title": "3rd reading and adoption of Bill C-2, An Act respecting border security and the Canadian Armed Forces",
            "snippet": "Result Passed; yea 200 nay 10",
            "url": "https://openparliament.ca/votes/45-1/1/",
            "engine": "openparliament",
        }
    ]
    scored = score_claims(claims, evidence)
    assert scored[0]["status"] in {"partial", "kept"}


def test_homepage_cards_junk():
    assert is_homepage_card("Lobbying Communication Reports Available")
    assert looks_like_junk_title("Lobbying Communication Reports Available")
    assert looks_like_junk_title("Proactive Disclosure of Contracts Over $10,000")
    assert not looks_like_junk_title("Federal contract: Real Time Networks Inc — $120,518.57")


def test_bilingual_search_expansion():
    assert looks_french("dons politiques")
    assert not looks_french("political donations")
    assert "dons politiques" in expand_terms("political donations")
    assert "political donations" in [x.lower() for x in expand_terms("dons politiques")] or glossary_other(
        "dons politiques"
    )
    other = glossary_other("lobbying contracts")
    assert "lobbyisme" in other or "contrats" in other


def test_country_profiles():
    from .countries import profile, search_jobs, list_countries
    from .sources import is_allowed

    assert profile("CA")["structured"] is True
    assert profile("US")["structured"] is False
    assert profile("us")["code"] == "US"
    us_jobs = search_jobs("US")
    assert any("United States" in j["query"] for j in us_jobs)
    assert not any("elections.ca" in j["query"] for j in us_jobs)
    assert is_allowed("https://www.congress.gov/bill", "US")
    assert not is_allowed("https://www.congress.gov/bill", "CA")
    assert is_allowed("https://www.elections.ca/content.aspx", "CA")
    codes = {c["code"] for c in list_countries()}
    assert "CA" in codes and "FR" in codes and "GB" in codes


def test_query_rotation_includes_french():
    jobs = rotate_search_jobs(1, take=16)
    assert any(j.get("lang") == "fr" for j in jobs)


def test_lobby_zip_recent_rows():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "Communication_PrimaryExport.csv",
            "COMLOG_ID,EN_CLIENT_ORG_CORP_NM_AN,COMM_DATE,POSTED_DATE_PUBLICATION\n"
            "1,Old Corp,2009-01-01,2009-01-01\n"
            "99,ThinkOn Inc,2026-09-20,2026-09-22\n",
        )
        zf.writestr(
            "Communication_DpohExport.csv",
            "COMLOG_ID,DPOH_LAST_NM_TCPD,DPOH_FIRST_NM_PRENOM_TCPD,DPOH_TITLE_TITRE_TCPD,INSTITUTION\n"
            "99,Joly,Melanie,Minister of Industry,ISED\n",
        )
        zf.writestr(
            "Communication_SubjectMatterDetailsExport.csv",
            "COMLOG_ID,DESCRIPTION\n99,Procurement software briefing\n",
        )
    rows = parse_lobby_zip(buf.getvalue(), "https://open.canada.ca/data/en/dataset/a34eb330-7136-4f5e-9f5f-3ba41df58b06")
    assert rows
    assert any("ThinkOn" in r["title"] for r in rows)
    assert any("Joly" in r["summary"] for r in rows)
    assert is_zip_bytes(buf.getvalue())
    assert not is_zip_bytes(b"<html>Just a moment</html>")


def test_carney_mandate_letter_priorities():
    html = """
    <html><body><p>May 21, 2025</p>
    <h2>Our Priorities</h2>
    <ol>
      <li>Establishing a new economic and security relationship with the United States.</li>
      <li>Building one Canadian economy by removing barriers to interprovincial trade.</li>
      <li>Bringing down costs for Canadians and helping them to get ahead.</li>
      <li>Making housing more affordable by unleashing public-private cooperation.</li>
      <li>Protecting Canadian sovereignty and keeping Canadians safe.</li>
      <li>Attracting the best talent in the world while returning immigration to sustainable levels.</li>
      <li>Spending less on government operations so Canadians can invest more.</li>
    </ol></body></html>
    """
    claims = parse_carney_mandate_html(html, "https://www.pm.gc.ca/en/mandate-letters/2025/05/21/mandate-letter")
    assert len(claims) == 7
    assert claims[0]["source_date"] == "2025-05-21"
    assert "housing" in claims[3]["title"].lower()


def test_carney_tracker_status_map():
    payload = {
        "meta": {"as_of": "2026-09-28"},
        "pledges": [
            {"title": "Middle-class tax cut", "pledge": "Cut taxes", "status": "kept", "note": "done"},
            {"title": "Housing plan", "pledge": "Build homes", "status": "in progress"},
        ],
    }
    rows = parse_carney_tracker(payload, "https://carneytracker.xyz/data.json")
    assert rows[0]["status"] == "kept"
    assert rows[1]["status"] == "partial"


if __name__ == "__main__":
    test_parliament_vote_title()
    test_money_parse()
    test_dates()
    test_dedup_merges_quarterly()
    test_confidence_cap()
    test_sanitize_drops_wikipedia_and_requires_source()
    test_allowlist()
    test_scoreboard_housing_vote()
    test_scoreboard_kept_on_adoption()
    test_homepage_cards_junk()
    test_bilingual_search_expansion()
    test_country_profiles()
    test_query_rotation_includes_french()
    test_lobby_zip_recent_rows()
    test_carney_mandate_letter_priorities()
    test_carney_tracker_status_map()
    print("pipeline tests ok")
