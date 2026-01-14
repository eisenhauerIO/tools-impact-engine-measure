"""Library of response functions for metrics-based impact approximation.

Response functions define how metric changes translate to expected outcome changes.
Each function takes a metric change (delta) and baseline outcome, returning the
approximated impact.
"""


def linear_response(delta_metric: float, baseline_outcome: float, **kwargs) -> float:
    """Linear response function: impact scales linearly with metric change.

    Formula: impact = coefficient * delta_metric * baseline_outcome

    Args:
        delta_metric: Change in metric (metric_after - metric_before)
        baseline_outcome: Baseline sales/revenue before intervention
        **kwargs: Additional parameters:
            - coefficient (float): Scaling factor (default: 1.0)
                A coefficient of 0.5 means a 1-unit metric increase
                results in a 50% increase in baseline outcome.

    Returns:
        float: Approximated impact on outcome

    Example:
        >>> linear_response(0.4, 100, coefficient=0.5)
        20.0  # 0.4 * 100 * 0.5 = 20
    """
    coefficient = kwargs.get("coefficient", 1.0)
    return coefficient * delta_metric * baseline_outcome
