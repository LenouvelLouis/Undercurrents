"""The tie-break that decides which method ships when the validation folds cannot."""

import pytest

from undercurrents.prediction import selection

COMPLEXITY = {"simple": 0, "middling": 1, "model": 2}


def test_a_clear_and_consistent_lead_is_kept():
    # Ahead on every fold by a wide, steady margin: a real ordering, so the winner stands.
    chosen, rationale = selection.choose(
        {"model": [0.90, 0.91, 0.89], "simple": [0.50, 0.51, 0.49]}, COMPLEXITY
    )
    assert chosen == "model"
    assert "highest mean" in rationale["reason"]


def test_a_lead_smaller_than_its_own_scatter_hands_the_win_to_the_simpler_method():
    # Mean advantage of 0.001, with the per-fold differences swinging either side of zero.
    # That is noise, and the simpler method takes it.
    chosen, rationale = selection.choose(
        {"model": [0.61, 0.58, 0.50], "simple": [0.57, 0.58, 0.53]}, COMPLEXITY
    )
    assert chosen == "simple"
    assert rationale["leader"] == "model"
    assert "simpler" in rationale["reason"]


def test_the_simplest_indistinguishable_method_wins_not_merely_a_simpler_one():
    scores = {
        "model": [0.61, 0.58, 0.50],
        "middling": [0.60, 0.575, 0.505],
        "simple": [0.57, 0.58, 0.53],
    }
    assert selection.choose(scores, COMPLEXITY)[0] == "simple"


def test_a_simpler_method_that_is_genuinely_worse_does_not_win():
    chosen, _ = selection.choose(
        {"model": [0.80, 0.82, 0.81], "simple": [0.40, 0.42, 0.41]}, COMPLEXITY
    )
    assert chosen == "model"


def test_one_fold_can_never_establish_an_ordering():
    # With a single fold there is no scatter to compare against, so nothing is
    # distinguishable and simplicity has to decide.
    chosen, _ = selection.choose({"model": [0.99], "simple": [0.10]}, COMPLEXITY)
    assert chosen == "simple"
    assert selection.distinguishable([0.99], [0.10]) is False


def test_distinguishable_needs_matching_fold_counts():
    assert selection.distinguishable([0.5, 0.6], [0.1]) is False
    assert selection.distinguishable([], []) is False


def test_the_leader_wins_when_it_is_already_the_simplest():
    chosen, rationale = selection.choose(
        {"simple": [0.61, 0.58, 0.50], "model": [0.57, 0.58, 0.53]}, COMPLEXITY
    )
    assert chosen == "simple"
    assert rationale["leader"] == "simple"
