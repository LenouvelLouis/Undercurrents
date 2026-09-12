from datetime import date

import holidays as holidays_lib

# Most country names stored in `venues.country` are accepted directly by the `holidays`
# package (verified against every country in the real dataset, 2026-09-12, `holidays==0.104`).
# These four aren't — mapped to their ISO 3166-1 alpha-2 code instead.
COUNTRY_NAME_OVERRIDES: dict[str, str] = {
    "United States": "US",
    "New Zealand": "NZ",
    "United Kingdom": "GB",
    "Hong Kong SAR China": "HK",
}


def _holiday_calendar(country: str, years: set[int]):
    identifier = COUNTRY_NAME_OVERRIDES.get(country, country)
    try:
        return holidays_lib.country_holidays(identifier, years=years)
    except NotImplementedError:
        return None


def is_holiday(country: str, event_date: date) -> bool | None:
    calendar = _holiday_calendar(country, {event_date.year})
    if calendar is None:
        return None
    return event_date in calendar


def nearest_holiday_distance_days(country: str, event_date: date) -> int | None:
    """Absolute number of days from `event_date` to the closest holiday (0 if `event_date`
    itself is one), or `None` if `country` isn't supported by the `holidays` package."""
    calendar = _holiday_calendar(country, {event_date.year - 1, event_date.year, event_date.year + 1})
    if calendar is None:
        return None
    if not calendar:
        return None
    return min(abs((holiday - event_date).days) for holiday in calendar)
