# Model Decision Guide

Impact Engine supports six measurement models, each designed for a different data situation and study design. This guide helps you choose the right one for your analysis. The [decision matrix](#decision-matrix) provides a compact comparison, and the per-model sections below give more detail on when each model applies, what data it requires, and what it assumes.

---

## Decision Matrix

| Criterion | Experiment | Interrupted Time Series | Nearest Neighbour Matching | Subclassification | Synthetic Control | Metrics Approximation |
|-----------|-----------|-------------------------|----------------------------|-------------------|-------------------|-----------------------|
| Data type | Cross-sectional | Time series | Cross-sectional | Cross-sectional | Panel | Cross-sectional |
| Control group needed | Yes | No | Yes | Yes | Yes (donor units) | No |
| Key assumption | Randomization | No structural breaks | Unconfoundedness | Unconfoundedness | Parallel trends | Known response function |
| Estimates | Regression coefficients | Intervention effect | ATT / ATE | ATT / ATE | ATT | Approximate impact |
| Complexity | Low | Low | Medium | Low | High | Low |

---

## Models

### Experiment

Use when treatment is randomly assigned, such as an A/B test. Randomization ensures the control group is a valid counterfactual, making this the simplest and most credible design when feasible.

**Data requirements.** Cross-sectional data with a binary treatment indicator and an outcome variable. Covariates are optional but can improve precision.

**Key assumption.** Treatment assignment is independent of potential outcomes (randomization holds).

**Links.** [Demo notebook](demo_experiment) | [statsmodels `ols()`](https://www.statsmodels.org/stable/generated/statsmodels.formula.api.ols.html)

### Interrupted Time Series

Use when a single unit is observed before and after an intervention and no control group is available. The pre-intervention series serves as its own counterfactual.

**Data requirements.** A time series of the outcome variable with enough pre-intervention observations to fit a time-series model. Data must be aggregated to a regular frequency.

**Key assumption.** No structural breaks or confounding events coincide with the intervention date.

**Links.** [Demo notebook](demo_interrupted_time_series) | [statsmodels `SARIMAX()`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html)

### Nearest Neighbour Matching

Use when treatment is not randomized but you have rich covariates that plausibly capture all confounding. Matching pairs treated and control units on observed characteristics to estimate the treatment effect.

**Data requirements.** Cross-sectional data with a treatment indicator, an outcome variable, and covariates to match on. Sufficient overlap in covariate distributions between groups is essential.

**Key assumption.** All confounders are observed and included in the matching variables (unconfoundedness).

**Links.** [Demo notebook](demo_nearest_neighbour_matching) | [causalml `NearestNeighborMatch`](https://causalml.readthedocs.io/en/latest/methodology.html#matching)

### Subclassification

Use when treatment is observational and you want a transparent, non-parametric approach. Propensity score stratification divides the sample into strata with similar treatment probabilities, then estimates within-stratum effects.

**Data requirements.** Cross-sectional data with a treatment indicator, an outcome variable, and covariates for propensity estimation. Strata must contain both treated and control units.

**Key assumption.** All confounders are captured by the propensity score (unconfoundedness).

**Links.** [Demo notebook](demo_subclassification) | [pandas `qcut()`](https://pandas.pydata.org/docs/reference/api/pandas.qcut.html) + [NumPy `np.average()`](https://numpy.org/doc/stable/reference/generated/numpy.average.html)

### Synthetic Control

Use when a single treated unit (e.g., a region or product line) is observed over time alongside multiple untreated donor units. The method constructs a weighted combination of donors to approximate the treated unit's counterfactual trajectory.

**Data requirements.** Panel data with one treated unit and several donor units observed over the same time periods. A sufficiently long pre-intervention window is needed to fit donor weights.

**Key assumption.** The treated and donor units share parallel trends in the absence of treatment.

**Links.** [Demo notebook](demo_synthetic_control) | [pysyncon `Synth`](https://sdfordham.github.io/pysyncon/synth.html)

### Metrics Approximation

Use when the relationship between an input and a business metric is known or hypothesized but running a controlled experiment is infeasible. The model fits a library of candidate response functions and selects the best approximation.

**Data requirements.** Cross-sectional data with an input variable and an outcome variable. No treatment indicator or control group is needed.

**Key assumption.** The true relationship between input and outcome can be adequately described by one of the candidate response functions.

**Links.** [Demo notebook](demo_metrics_approximation) | Built-in response function registry

---

## Comparing Models on the Same Data

The [Model Selection](demo_model_selection) notebook applies multiple models to a single dataset and compares their estimates side by side. This is useful for understanding how model choice affects conclusions and for building intuition about when different approaches agree or diverge.
