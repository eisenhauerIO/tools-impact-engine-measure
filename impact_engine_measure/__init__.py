"""Impact Engine - A tool for measuring causal impact of product interventions."""

from .engine import measure_impact
from .results import MeasureJobResult, load_results

__version__ = "0.1.0"
__author__ = "eisenhauer.io"


__all__ = [
    "measure_impact",
    "load_results",
    "MeasureJobResult",
]
