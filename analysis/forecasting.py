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

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.metrics import mean_absolute_percentage_error


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


def backtest(series: pd.Series, holdout: int = 6) -> float:
    """Hold out the last `holdout` months, fit on everything before that,
    and report MAPE on the held-out months. This is the number you actually
    quote on a resume/interview -- 'forecast accuracy' without a backtest
    number attached isn't a verifiable claim."""
    if len(series) <= holdout + 6:
        print(f"Series too short ({len(series)} points) for a {holdout}-month backtest; skipping.")
        return float("nan")
    train, test = series.iloc[:-holdout], series.iloc[-holdout:]
    model = ExponentialSmoothing(
        train, trend="add", seasonal="add" if len(train) >= 24 else None,
        seasonal_periods=12 if len(train) >= 24 else None,
    ).fit()
    preds = model.forecast(holdout)
    mape = mean_absolute_percentage_error(test, preds)
    return mape


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


def plot_forecast(series: pd.Series, forecast: pd.Series, mape: float, output_path: str):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(series.index, series.values, label="Actual monthly sales", color="#0F6E62")
    ax.plot(forecast.index, forecast.values, label="Forecast", color="#D97706", linestyle="--", marker="o")
    title = "Monthly Sales Forecast"
    if not np.isnan(mape):
        title += f"  (backtest MAPE: {mape:.1%})"
    ax.set_title(title)
    ax.set_ylabel("Sales (INR)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=110)
    print(f"Saved forecast plot to {output_path}")


def run(orders_path: str, periods: int, output_csv: str, output_plot: str):
    series = build_monthly_series(orders_path)
    print(f"Built monthly series: {len(series)} months, "
          f"{series.index.min().date()} to {series.index.max().date()}")

    mape = backtest(series)
    if not np.isnan(mape):
        print(f"Backtest MAPE (last 6 months held out): {mape:.1%}")

    model, forecast = fit_and_forecast(series, periods)
    print(f"\nForecast for next {periods} months:")
    print(forecast.round(0).to_string())

    forecast.rename("forecast_sales").to_csv(output_csv)
    print(f"\nSaved forecast to {output_csv}")

    plot_forecast(series, forecast, mape, output_plot)
    return forecast, mape


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forecast monthly retail sales with Holt-Winters")
    parser.add_argument("--input", default="../data/processed/orders.csv")
    parser.add_argument("--periods", type=int, default=6)
    parser.add_argument("--output-csv", default="../data/processed/sales_forecast.csv")
    parser.add_argument("--output-plot", default="../dashboard/sales_forecast.png")
    args = parser.parse_args()

    run(args.input, args.periods, args.output_csv, args.output_plot)
