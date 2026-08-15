"""
Monthly Sales Forecasting (Holt-Winters Exponential Smoothing)
================================================================

Aggregates order-level sales to a monthly time series and forecasts the next
N months. Uses Holt-Winters instead of Prophet/SARIMAX deliberately: with
~4-5 years of monthly data (48-60 points), a triple-exponential-smoothing
model is honestly the right-sized tool -- it has few parameters to overfit,
it's fast, and it's a model you can actually explain end-to-end in an
interview. Swap in SARIMAX or Prophet if you have more history or need
exogenous regressors (promotions calendar, holidays, etc.) -- the
`fit_and_forecast()` function is written so the model object is the only
thing you'd need to swap out.

Usage:
    python forecasting.py --input ../data/processed/orders.csv --periods 6
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_percentage_error
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def build_monthly_series(orders_path: str) -> pd.Series:
    orders = pd.read_csv(orders_path, parse_dates=["order_date"])
    monthly = (
        orders.set_index("order_date")["sales"]
        .resample("MS")  # month start
        .sum()
    )
    # drop the first/last month if they're partial (common with real-world
    # extracts where the data starts or ends mid-month) -- forecasting off a
    # partial month systematically understates the trend
    if len(monthly) > 2:
        monthly = monthly.iloc[1:-1] if monthly.index[0].day == 1 else monthly
    return monthly


def backtest(series: pd.Series, holdout: int = 6) -> dict:
    """Hold out the last `holdout` months, fit on everything before that, and
    report MAPE, MAE, and RMSE on the held-out months -- plus the actual vs.
    predicted values themselves, so the backtest can be plotted, not just
    summarized as a single percentage. A number without the underlying
    train/validation split visible isn't independently checkable."""
    if len(series) <= holdout + 6:
        print(f"Series too short ({len(series)} points) for a {holdout}-month backtest; skipping.")
        return {}
    train, test = series.iloc[:-holdout], series.iloc[-holdout:]
    model = ExponentialSmoothing(
        train, trend="add", seasonal="add" if len(train) >= 24 else None,
        seasonal_periods=12 if len(train) >= 24 else None,
    ).fit()
    preds = pd.Series(model.forecast(holdout).values, index=test.index)

    mape = mean_absolute_percentage_error(test, preds)
    mae = np.mean(np.abs(test.values - preds.values))
    rmse = np.sqrt(np.mean((test.values - preds.values) ** 2))

    return {
        "train": train, "test": test, "preds": preds,
        "mape": mape, "mae": mae, "rmse": rmse,
    }


def fit_and_forecast(series: pd.Series, periods: int = 6):
    use_seasonal = len(series) >= 24
    model = ExponentialSmoothing(
        series,
        trend="add",
        seasonal="add" if use_seasonal else None,
        seasonal_periods=12 if use_seasonal else None,
    ).fit()
    forecast = model.forecast(periods)
    return model, forecast


def plot_forecast(series: pd.Series, forecast: pd.Series, bt: dict, output_path: str):
    """Two panels: (1) the full history with the forward forecast, and (2)
    a zoomed-in actual-vs-predicted view of just the backtest window -- the
    second panel is the one that actually substantiates the MAPE/MAE/RMSE
    numbers, rather than asking the reader to trust a single percentage."""
    _fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

    ax = axes[0]
    ax.plot(series.index, series.values, label="Actual monthly sales", color="#0F6E62")
    ax.plot(forecast.index, forecast.values, label="Forward forecast", color="#D97706", linestyle="--", marker="o")
    ax.set_title("Full history + forward forecast")
    ax.set_ylabel("Sales (INR)")
    ax.legend(fontsize=8)

    ax = axes[1]
    if bt:
        ax.plot(bt["train"].index[-12:], bt["train"].values[-12:], label="Train (last 12mo shown)", color="#94A3B8")
        ax.plot(bt["test"].index, bt["test"].values, label="Actual (held out)", color="#0F6E62", marker="o")
        ax.plot(bt["preds"].index, bt["preds"].values, label="Predicted", color="#D97706", linestyle="--", marker="o")
        ax.set_title(f"Backtest: MAPE {bt['mape']:.1%} | MAE ₹{bt['mae']:,.0f} | RMSE ₹{bt['rmse']:,.0f}")
        ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=110)
    print(f"Saved forecast plot to {output_path}")


def run(orders_path: str, periods: int, output_csv: str, output_plot: str):
    series = build_monthly_series(orders_path)
    print(f"Built monthly series: {len(series)} months, "
          f"{series.index.min().date()} to {series.index.max().date()}")
    print(f"Train period: {series.index[0].date()} to {series.index[-7].date()} ({len(series)-6} months)")
    print(f"Validation (backtest) period: {series.index[-6].date()} to {series.index[-1].date()} (6 months)")

    bt = backtest(series)
    if bt:
        print("\nBacktest results (last 6 months held out):")
        print(f"  MAPE: {bt['mape']:.1%}")
        print(f"  MAE:  ₹{bt['mae']:,.0f}")
        print(f"  RMSE: ₹{bt['rmse']:,.0f}")

    _model, forecast = fit_and_forecast(series, periods)
    print(f"\nForecast period: {forecast.index[0].date()} to {forecast.index[-1].date()} ({periods} months)")
    print(forecast.round(0).to_string())

    forecast.rename("forecast_sales").to_csv(output_csv)
    print(f"\nSaved forecast to {output_csv}")

    plot_forecast(series, forecast, bt, output_plot)
    return forecast, bt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forecast monthly retail sales with Holt-Winters")
    parser.add_argument("--input", default="../data/processed/orders.csv")
    parser.add_argument("--periods", type=int, default=6)
    parser.add_argument("--output-csv", default="../data/processed/sales_forecast.csv")
    parser.add_argument("--output-plot", default="../dashboard/sales_forecast.png")
    args = parser.parse_args()

    run(args.input, args.periods, args.output_csv, args.output_plot)
