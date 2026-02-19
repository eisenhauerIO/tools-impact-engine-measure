"""Shared utilities for methodology demo notebooks."""

from typing import Dict, List

import matplotlib.pyplot as plt


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


def plot_monte_carlo_distribution(
    model_names: List[str],
    distributions: Dict[str, List[float]],
    true_effect: float,
    *,
    ylabel: str = "Treatment Effect",
    title: str = "Monte Carlo: Sampling Distributions by Model",
) -> None:
    """Plot sampling distributions of treatment effect estimates as violin plots.

    Parameters
    ----------
    model_names : list of str
        Model names in display order.
    distributions : dict of str to list of float
        Mapping from model name to list of estimates across replications.
    true_effect : float
        True treatment effect, shown as a horizontal reference line.
    ylabel : str, optional
        Y-axis label.
    title : str, optional
        Plot title.
    """
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    data = [distributions[name] for name in model_names]
    positions = list(range(1, len(model_names) + 1))

    fig, ax = plt.subplots(figsize=(8, 5))

    parts = ax.violinplot(data, positions=positions, showextrema=False)
    for i, body in enumerate(parts["bodies"]):
        body.set_facecolor(colors[i % len(colors)])
        body.set_edgecolor(colors[i % len(colors)])
        body.set_alpha(0.7)

    bp = ax.boxplot(data, positions=positions, widths=0.15, patch_artist=True, zorder=3, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor("white")
        patch.set_edgecolor("black")
    for element in ["whiskers", "caps", "medians"]:
        for line in bp[element]:
            line.set_color("black")

    ax.axhline(y=true_effect, color="red", linestyle="--", linewidth=2, label=f"True effect ({true_effect:.4f})")
    ax.set_xticks(positions)
    ax.set_xticklabels(model_names)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()


def plot_parameter_sensitivity_mc(
    param_values: List[float],
    mean_estimates: List[float],
    lower_band: List[float],
    upper_band: List[float],
    true_effect: float,
    *,
    xlabel: str = "Parameter Value",
    ylabel: str = "Treatment Effect",
    title: str = "Parameter Sensitivity (Monte Carlo)",
    band_label: str = "Mean +/- 1 SD",
) -> None:
    """Plot parameter sensitivity with uncertainty bands from Monte Carlo replications.

    Parameters
    ----------
    param_values : list of float
        Parameter values along the x-axis.
    mean_estimates : list of float
        Mean treatment effect at each parameter value across replications.
    lower_band : list of float
        Lower uncertainty bound.
    upper_band : list of float
        Upper uncertainty bound.
    true_effect : float
        True treatment effect, shown as a horizontal reference line.
    xlabel : str, optional
        X-axis label.
    ylabel : str, optional
        Y-axis label.
    title : str, optional
        Plot title.
    band_label : str, optional
        Legend label for the uncertainty band.
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(param_values, mean_estimates, "o-", label="Mean estimate", color="#1f77b4")
    ax.fill_between(param_values, lower_band, upper_band, alpha=0.25, color="#1f77b4", label=band_label)
    ax.axhline(y=true_effect, color="red", linestyle="--", linewidth=2, label=f"True effect ({true_effect:.4f})")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.show()
