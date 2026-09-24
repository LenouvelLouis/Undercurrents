"""What kind of place each venue is, from Wikidata.

Capacity, which `venue_capacity_bulk` already fetches, turns out to be the weaker of the two
facts Wikidata holds about a venue. It resolves for only a quarter of them, and a number on
its own says little about the night: a 5,000-capacity theatre and a 5,000-capacity festival
field are different rooms to play.

The type (P31, "instance of") is better covered and more useful, and it carries the one
distinction that makes the weather data worth anything: indoor or outdoor. Inception (P571)
comes along for free in the same query.

The same conservative disambiguation as the capacity module applies. A venue name is matched
against label and aliases within its own country, and a name that resolves to several
different kinds of place is left unset rather than guessed.
"""

import logging
import ssl
import time

import httpx
import truststore

from undercurrents.clustering.venue_capacity import COUNTRY_QIDS
from undercurrents.clustering.venue_capacity_bulk import (
    BATCH_INTERVAL,
    BATCH_SIZE,
    MAX_RETRIES,
    SPARQL_ENDPOINT,
    TIMEOUT,
    _escape,
)
from undercurrents.clustering.wikidata_client import USER_AGENT

logger = logging.getLogger(__name__)

# Wikidata entity ids for the kinds of place a band plays, mapped to the handful of
# categories worth distinguishing here. The `outdoor` flag is the one that earns its keep:
# it is what makes a rain measurement mean anything.
VENUE_KINDS: dict[str, tuple[str, bool]] = {
    "Q641226": ("arena", False),
    "Q1076486": ("stadium", True),
    "Q483110": ("stadium", True),
    "Q24354": ("theatre", False),
    "Q153562": ("opera house", False),
    "Q1060829": ("concert hall", False),
    "Q18674739": ("event venue", False),
    "Q17350442": ("performing arts venue", False),
    "Q187456": ("club", False),
    "Q1329623": ("cultural centre", False),
    "Q57660343": ("music venue", False),
    "Q52177407": ("festival site", True),
    "Q132241": ("festival", True),
    "Q22698": ("park", True),
    "Q174782": ("public square", True),
    "Q860861": ("amphitheatre", True),
    "Q1195942": ("fairground", True),
    "Q41253": ("cinema", False),
    "Q16917": ("hospital", False),
}


def _build_query(pairs: list[tuple[str, str]]) -> str:
    values = " ".join(f'("{_escape(name)}"@en wd:{qid})' for name, qid in pairs)
    return f"""SELECT ?label ?country ?kind ?inception WHERE {{
  VALUES (?label ?country) {{ {values} }}
  {{
    ?venue rdfs:label ?label ;
           wdt:P31 ?kind ;
           wdt:P17 ?country .
  }} UNION {{
    ?venue skos:altLabel ?label ;
           wdt:P31 ?kind ;
           wdt:P17 ?country .
  }}
  OPTIONAL {{ ?venue wdt:P571 ?inception . }}
}}"""


def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))


def ensure_columns(conn) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(venues)")}
    for column, kind in (("venue_kind", "TEXT"), ("is_outdoor", "INTEGER"), ("opened_year", "INTEGER")):
        if column not in existing:
            conn.execute(f"ALTER TABLE venues ADD COLUMN {column} {kind}")
    conn.commit()


def fetch_profiles(pairs: list[tuple[str, str]], client: httpx.Client | None = None) -> dict:
    """Returns {(label, country_qid): {kind, outdoor, opened_year}} for names that resolve
    to a single recognised kind of place."""
    owns_client = client is None
    client = client or _client()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    kinds: dict[tuple[str, str], set[str]] = {}
    years: dict[tuple[str, str], set[int]] = {}

    try:
        for index, start in enumerate(range(0, len(pairs), BATCH_SIZE)):
            batch = pairs[start:start + BATCH_SIZE]
            if index > 0:
                time.sleep(BATCH_INTERVAL)

            response = None
            for attempt in range(MAX_RETRIES):
                response = client.get(
                    SPARQL_ENDPOINT,
                    params={"query": _build_query(batch), "format": "json"},
                    headers=headers,
                )
                if response.status_code != 429:
                    break
                time.sleep(2 ** (attempt + 1))

            if response is None or response.status_code != 200:
                logger.warning("SPARQL batch at %d failed; those venues stay unset", start)
                continue

            for binding in response.json()["results"]["bindings"]:
                key = (
                    binding["label"]["value"],
                    binding["country"]["value"].rsplit("/", 1)[-1],
                )
                qid = binding["kind"]["value"].rsplit("/", 1)[-1]
                if qid in VENUE_KINDS:
                    kinds.setdefault(key, set()).add(qid)
                inception = binding.get("inception", {}).get("value")
                if inception and len(inception) >= 4 and inception[:4].isdigit():
                    years.setdefault(key, set()).add(int(inception[:4]))
    finally:
        if owns_client:
            client.close()

    profiles = {}
    for key, qids in kinds.items():
        labels = {VENUE_KINDS[q] for q in qids}
        if len(labels) != 1:
            continue  # ambiguous kind, left unset rather than guessed
        kind, outdoor = next(iter(labels))
        year_set = years.get(key, set())
        profiles[key] = {
            "kind": kind,
            "outdoor": outdoor,
            # several inception dates means the name matches more than one building
            "opened_year": next(iter(year_set)) if len(year_set) == 1 else None,
        }
    return profiles


def enrich(conn, client: httpx.Client | None = None) -> dict:
    ensure_columns(conn)
    venues = conn.execute(
        "SELECT id, name, country FROM venues WHERE venue_kind IS NULL AND name IS NOT NULL"
    ).fetchall()

    pairs: list[tuple[str, str]] = []
    by_pair: dict[tuple[str, str], list[str]] = {}
    skipped_country = 0
    for venue in venues:
        qid = COUNTRY_QIDS.get(venue["country"] or "")
        if not qid:
            skipped_country += 1
            continue
        key = (venue["name"], qid)
        if key not in by_pair:
            pairs.append(key)
        by_pair.setdefault(key, []).append(venue["id"])

    profiles = fetch_profiles(pairs, client=client)
    updated = 0
    for key, profile in profiles.items():
        for venue_id in by_pair.get(key, []):
            conn.execute(
                "UPDATE venues SET venue_kind = ?, is_outdoor = ?, opened_year = ? WHERE id = ?",
                (profile["kind"], int(profile["outdoor"]), profile["opened_year"], venue_id),
            )
            updated += 1
    conn.commit()

    return {
        "venues_considered": len(venues),
        "names_queried": len(pairs),
        "names_resolved": len(profiles),
        "venues_updated": updated,
        "skipped_unknown_country": skipped_country,
    }
