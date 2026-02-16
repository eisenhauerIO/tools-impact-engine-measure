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


def plot_model_comparison(
    model_names: List[str],
    estimates: List[float],
    true_effect: float,
    *,
    ylabel: str = "Treatment Effect",
    title: str = "Model Comparison: Treatment Effect Estimates",
) -> None:
    """Plot treatment effect estimates from multiple models as a bar chart with a truth line."""
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    bars = ax.bar(model_names, estimates, color=colors[: len(model_names)], alpha=0.8)
    ax.axhline(y=true_effect, color="red", linestyle="--", linewidth=2, label=f"True effect ({true_effect:.4f})")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    for bar, est in zip(bars, estimates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{est:.4f}", ha="center", va="bottom")
    plt.tight_layout()
    plt.show()


def plot_parameter_sensitivity(
    param_values: List[float],
    estimates: List[float],
    true_effect: float,
    *,
    xlabel: str = "Parameter Value",
    ylabel: str = "Treatment Effect",
    title: str = "Parameter Sensitivity",
) -> None:
    """Plot model estimate vs true effect as a tuning parameter varies."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(param_values, estimates, "o-", label="Model estimate", color="#1f77b4")
    ax.axhline(y=true_effect, color="red", linestyle="--", linewidth=2, label=f"True effect ({true_effect:.4f})")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()
