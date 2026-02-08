"""Shared utilities for demo notebooks."""

from typing import List

import matplotlib.pyplot as plt


def plot_convergence(
    sample_sizes: List[int],
    estimates: List[float],
    truth: List[float],
    *,
    xlabel: str = "Number of Products",
    ylabel: str = "Effect Estimate",
    title: str = "Convergence of Estimate to True Effect",
) -> None:
    """Plot model estimates vs true effect across increasing sample sizes."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(sample_sizes, estimates, "o-", label="Model estimate")
    ax.plot(sample_sizes, truth, "s--", label="True effect")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()
