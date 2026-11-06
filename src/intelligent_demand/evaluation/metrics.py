"""Forecast metric definitions only; Phase 2 never generates model predictions."""

import numpy as np


def scaling_denominators(
    training: np.ndarray, season: int = 7
) -> tuple[float | None, float | None]:
    """Compute absolute/squared seasonal-difference scales on origin-available training."""
    values = np.asarray(training, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or type(season) is not int or season < 1:
        raise ValueError("Finite one-dimensional training values and positive season required")
    if len(values) <= season:
        return None, None
    differences = values[season:] - values[:-season]
    absolute, squared = float(np.abs(differences).mean()), float(np.square(differences).mean())
    return (absolute if absolute > 0 else None, squared if squared > 0 else None)


def forecast_metrics(
    actual: np.ndarray, predicted: np.ndarray, training: np.ndarray | None = None, season: int = 7
) -> dict:
    """Bias is prediction-minus-actual; zero percentage/scaled denominators are undefined."""
    y, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if y.ndim != 1 or y.shape != p.shape or not y.size or not np.isfinite([y, p]).all():
        raise ValueError("Matched nonempty finite one-dimensional observations required")
    error = p - y
    mae, mse = float(np.abs(error).mean()), float(np.square(error).mean())
    denominator = float(np.abs(y).sum())
    result = {
        "mae": mae,
        "rmse": float(np.sqrt(mse)),
        "bias_units": float(error.mean()),
        "wape_percent": 100 * float(np.abs(error).sum()) / denominator if denominator else None,
        "bias_percent": 100 * float(error.sum()) / denominator if denominator else None,
    }
    if training is not None:
        absolute, squared = scaling_denominators(training, season)
        result.update(
            mase=mae / absolute if absolute else None,
            rmsse=float(np.sqrt(mse / squared)) if squared else None,
        )
    return result
