"""Choosing between candidate methods when their validation scores are close.

Backtesting several methods and shipping whichever scored highest sounds obviously right and
is quietly wrong when the gap between the top two is smaller than the scatter between folds.
On this data both the encore and the comeback task produced exactly that: a trained logistic
regression ahead of a one-line recency rule by 1.6 points and 0.1 points respectively, across
folds that themselves varied by 10 to 14 points. Declaring the model the winner there is not a
measurement, it is a coin landing heads.

So the rule is two-part, and both parts are fixed before any test number is looked at:

1. Rank by the mean across validation folds.
2. Where a simpler method is not *distinguishable* from the best one, take the simpler one.

"Not distinguishable" is the paired comparison: for each fold, the difference between the two
methods; if the mean of those differences is no larger than its own standard error, the folds
do not support an ordering. Preferring simplicity in that case is a standing engineering
preference, not a reading of the data, which is what keeps it out of the test window.
"""

from statistics import mean as _mean
from statistics import stdev


def _standard_error(values: list[float]) -> float:
    if len(values) < 2:
        return float("inf")  # one fold cannot establish a spread, so nothing is distinguishable
    return stdev(values) / (len(values) ** 0.5)


def distinguishable(better: list[float], worse: list[float]) -> bool:
    """Whether the per-fold advantage of one method over another survives its own scatter."""
    if len(better) != len(worse) or not better:
        return False
    differences = [b - w for b, w in zip(better, worse)]
    return _mean(differences) > _standard_error(differences)


def choose(
    fold_precisions: dict[str, list[float]], complexity: dict[str, int]
) -> tuple[str, dict]:
    """Returns the method to ship and a record of how the choice was reached.

    `complexity` ranks methods, lowest is simplest. A simpler method wins a tie, and the
    reasoning is returned rather than being buried, because "the simple rule was kept" and
    "the model genuinely won" are very different things to print on a page.
    """
    means = {name: _mean(values) for name, values in fold_precisions.items()}
    leader = max(means, key=lambda name: means[name])

    simpler = sorted(
        (name for name in means if complexity[name] < complexity[leader]),
        key=lambda name: complexity[name],
    )
    for name in simpler:
        if not distinguishable(fold_precisions[leader], fold_precisions[name]):
            return name, {
                "leader": leader,
                "leader_mean": round(means[leader], 4),
                "chosen_mean": round(means[name], 4),
                "reason": (
                    "kept the simpler method: across the validation folds its gap to the "
                    "highest-scoring one is no bigger than the scatter of that gap"
                ),
            }

    return leader, {
        "leader": leader,
        "leader_mean": round(means[leader], 4),
        "chosen_mean": round(means[leader], 4),
        "reason": "highest mean across the validation folds, by more than the fold-to-fold scatter",
    }
