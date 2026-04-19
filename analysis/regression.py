"""
analysis/regression.py — Regression + statistics on fleet records
"""
from __future__ import annotations
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score, mean_squared_error
from scipy import stats


def filter_by_matching_inputs(
    df: pd.DataFrame,
    anchor: Dict[str, Any],
    match_cols: List[str],
    n: int = 5,
) -> pd.DataFrame:
    """
    Priority filter: among all rows, prefer those where the values in
    `match_cols` equal the anchor. Fall back to most recent `n` if not enough.
    """
    if df.empty:
        return df

    # Build mask for matching rows
    mask = pd.Series([True] * len(df), index=df.index)
    for col in match_cols:
        if col in df.columns and col in anchor:
            mask &= df[col] == anchor[col]

    matched = df[mask].copy()
    if len(matched) >= n:
        return matched.tail(n)

    # Fall back: pad with most recent non-matching rows
    unmatched = df[~mask].copy()
    need = n - len(matched)
    return pd.concat([matched, unmatched.tail(need)]).reset_index(drop=True)


def run_regression(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    degree: int = 1,
) -> Dict[str, Any]:
    """
    Run polynomial regression of degree `degree` of y on x.
    Returns a dict with model, predictions, stats, and display-ready data.
    """
    sub = df[[x_col, y_col]].dropna()
    if len(sub) < 2:
        return {"error": "Not enough data points (need >= 2)"}

    X = sub[[x_col]].values
    y = sub[y_col].values

    poly = PolynomialFeatures(degree=degree, include_bias=True)
    X_poly = poly.fit_transform(X)

    model = LinearRegression(fit_intercept=False)
    model.fit(X_poly, y)

    y_pred = model.predict(X_poly)
    r2 = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    n = len(y)
    p = degree + 1  # number of params

    # Adjusted R²
    adj_r2 = 1 - (1 - r2) * (n - 1) / max(n - p, 1)

    # Pearson correlation (linear)
    if n >= 3:
        corr, p_val = stats.pearsonr(X.ravel(), y)
    else:
        corr, p_val = float("nan"), float("nan")

    # Equation string
    coeffs = model.coef_
    terms = []
    feature_names = poly.get_feature_names_out([x_col])
    for name, c in zip(feature_names, coeffs):
        name = name.replace("1", "").replace("^", "^").strip()
        if not name:
            name = "const"
        terms.append(f"{c:+.4g}·{name}")
    equation = " ".join(terms)

    # Smooth curve for plotting
    x_range = np.linspace(X.min(), X.max(), 200).reshape(-1, 1)
    x_range_poly = poly.transform(x_range)
    y_range = model.predict(x_range_poly)

    return {
        "x_col": x_col,
        "y_col": y_col,
        "degree": degree,
        "n": n,
        "r2": r2,
        "adj_r2": adj_r2,
        "rmse": rmse,
        "pearson_r": corr,
        "p_value": p_val,
        "equation": equation,
        "x_data": X.ravel().tolist(),
        "y_data": y.tolist(),
        "y_pred": y_pred.tolist(),
        "x_curve": x_range.ravel().tolist(),
        "y_curve": y_range.tolist(),
        "model": model,
        "poly": poly,
    }


def multi_regression_report(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: List[str],
) -> Dict[str, Any]:
    """
    Multiple linear regression: target ~ feature_cols.
    """
    sub = df[feature_cols + [target_col]].dropna()
    if len(sub) < len(feature_cols) + 1:
        return {"error": "Not enough data"}

    X = sub[feature_cols].values
    y = sub[target_col].values

    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    r2 = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))

    coef_dict = dict(zip(feature_cols, model.coef_))
    return {
        "target": target_col,
        "features": feature_cols,
        "intercept": model.intercept_,
        "coefficients": coef_dict,
        "r2": r2,
        "rmse": rmse,
        "n": len(y),
        "model": model,
    }
