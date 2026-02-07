"""Subclassification (stratification) for treatment effect estimation.

This subpackage provides an implementation of subclassification
that stratifies on covariates and aggregates within-stratum treatment
effects to estimate ATT or ATE.
"""

from .adapter import SubclassificationAdapter

__all__ = [
    "SubclassificationAdapter",
]
