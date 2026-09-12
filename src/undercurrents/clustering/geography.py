from datetime import date, datetime

DATE_FORMAT = "%Y-%m-%d"

# Covers every country observed in the real dataset (39 as of 2026-09-12) plus a handful of
# other common ones. Not exhaustive — `continent_for_country` returns `None` for anything
# missing rather than guessing, so an unmapped country degrades gracefully (see
# `days_since_continent_last_visited`) instead of silently misclassifying it.
COUNTRY_TO_CONTINENT: dict[str, str] = {
    "United States": "North America",
    "Canada": "North America",
    "Mexico": "North America",
    "Australia": "Oceania",
    "New Zealand": "Oceania",
    "United Kingdom": "Europe",
    "Germany": "Europe",
    "France": "Europe",
    "Spain": "Europe",
    "Netherlands": "Europe",
    "Italy": "Europe",
    "Belgium": "Europe",
    "Portugal": "Europe",
    "Denmark": "Europe",
    "Sweden": "Europe",
    "Ireland": "Europe",
    "Switzerland": "Europe",
    "Norway": "Europe",
    "Poland": "Europe",
    "Hungary": "Europe",
    "Finland": "Europe",
    "Czechia": "Europe",
    "Austria": "Europe",
    "Slovenia": "Europe",
    "Slovakia": "Europe",
    "Luxembourg": "Europe",
    "Croatia": "Europe",
    "Brazil": "South America",
    "Argentina": "South America",
    "Chile": "South America",
    "Colombia": "South America",
    "Peru": "South America",
    "Paraguay": "South America",
    "Japan": "Asia",
    "Singapore": "Asia",
    "Indonesia": "Asia",
    "Malaysia": "Asia",
    "Hong Kong SAR China": "Asia",
    "Israel": "Asia",
}


def continent_for_country(country: str) -> str | None:
    return COUNTRY_TO_CONTINENT.get(country)


def country_show_count(conn, country: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS c FROM setlists s
        JOIN venues v ON v.id = s.venue_id
        WHERE v.country = ?
        """,
        (country,),
    ).fetchone()
    return row["c"]


def _parse_event_date(event_date: str) -> date:
    return datetime.strptime(event_date, DATE_FORMAT).date()


def days_since_country_last_visited(conn, country: str, reference_date: date) -> int | None:
    row = conn.execute(
        """
        SELECT MAX(s.event_date) AS d FROM setlists s
        JOIN venues v ON v.id = s.venue_id
        WHERE v.country = ? AND s.event_date < ?
        """,
        (country, reference_date.isoformat()),
    ).fetchone()
    if row["d"] is None:
        return None
    return (reference_date - _parse_event_date(row["d"])).days


def venue_show_count(conn, venue_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM setlists WHERE venue_id = ?", (venue_id,)
    ).fetchone()
    return row["c"]


def days_since_venue_last_visited(conn, venue_id: str, reference_date: date) -> int | None:
    row = conn.execute(
        "SELECT MAX(event_date) AS d FROM setlists WHERE venue_id = ? AND event_date < ?",
        (venue_id, reference_date.isoformat()),
    ).fetchone()
    if row["d"] is None:
        return None
    return (reference_date - _parse_event_date(row["d"])).days


def days_since_continent_last_visited(conn, continent: str, reference_date: date) -> int | None:
    countries = [c for c, cont in COUNTRY_TO_CONTINENT.items() if cont == continent]
    if not countries:
        return None

    placeholders = ",".join("?" * len(countries))
    row = conn.execute(
        f"""
        SELECT MAX(s.event_date) AS d FROM setlists s
        JOIN venues v ON v.id = s.venue_id
        WHERE v.country IN ({placeholders}) AND s.event_date < ?
        """,
        (*countries, reference_date.isoformat()),
    ).fetchone()
    if row["d"] is None:
        return None
    return (reference_date - _parse_event_date(row["d"])).days
