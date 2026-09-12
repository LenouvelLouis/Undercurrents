from datetime import date

from undercurrents.clustering import calendar_features


def test_is_holiday_true_on_a_known_holiday():
    assert calendar_features.is_holiday("United States", date(2020, 7, 4)) is True


def test_is_holiday_false_on_a_non_holiday():
    assert calendar_features.is_holiday("United States", date(2020, 7, 5)) is False


def test_is_holiday_uses_country_name_override_for_united_states():
    # "United States" isn't accepted directly by the `holidays` package (needs "US"); this
    # confirms the override mapping is actually wired in, not just coincidentally correct.
    assert calendar_features.is_holiday("United States", date(2020, 1, 1)) is True


def test_is_holiday_works_for_a_country_accepted_by_full_name():
    assert calendar_features.is_holiday("Germany", date(2020, 1, 1)) is True


def test_is_holiday_returns_none_for_unsupported_country():
    assert calendar_features.is_holiday("Atlantis", date(2020, 1, 1)) is None


def test_nearest_holiday_distance_days_is_zero_on_a_holiday():
    assert calendar_features.nearest_holiday_distance_days("United States", date(2020, 7, 4)) == 0


def test_nearest_holiday_distance_days_counts_forward_and_backward():
    # The US observes Independence Day on both 2020-07-03 ("observed", since 07-04 fell on a
    # Saturday) and 2020-07-04 (actual) — verified directly against the `holidays` package.
    assert calendar_features.nearest_holiday_distance_days("United States", date(2020, 7, 1)) == 2
    assert calendar_features.nearest_holiday_distance_days("United States", date(2020, 7, 7)) == 3


def test_nearest_holiday_distance_days_returns_none_for_unsupported_country():
    assert calendar_features.nearest_holiday_distance_days("Atlantis", date(2020, 1, 1)) is None
