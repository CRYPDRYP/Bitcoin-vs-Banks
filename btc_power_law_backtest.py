"""
BTC Power Law Band-Position Backtest
------------------------------------
Tests the claim: "buying at the power law support band produces strong
forward returns."

Two fits are compared:
  1. STATIC fit  — regression on ALL history (what the chart websites show).
     This has lookahead bias: the line already "knows" every recovery.
  2. WALK-FORWARD fit — at each date, refit using only data available
     up to that date. This is what you could have actually traded.

Same principle as .shift(1), applied at model scale.

Run:  python btc_power_law_backtest.py
Deps: pandas, numpy, yfinance
Note: yfinance BTC-USD history starts Sep 2014, so the 2011 cycle
      is not included. Genesis date is still used as t=0.
"""

import numpy as np
import pandas as pd
import yfinance as yf

GENESIS = pd.Timestamp("2009-01-03")
BAND_THRESHOLD = 0.10   # "at support" = bottom 10% of the band
MIN_FIT_YEARS = 2       # walk-forward needs at least this much data
FWD_WINDOWS = [365, 730]  # forward return horizons (days)


# ---------------------------------------------------------------- data
def load_btc() -> pd.DataFrame:
    """Daily BTC-USD closes with days-since-genesis column."""
    px = yf.download("BTC-USD", start="2014-09-17", auto_adjust=True,
                     progress=False)["Close"]
    if isinstance(px, pd.DataFrame):          # yfinance >= 0.2 returns DF
        px = px.iloc[:, 0]
    df = px.dropna().to_frame("close")
    df["t"] = (df.index - GENESIS).days.astype(float)
    return df


# ---------------------------------------------------------------- fitting
def fit_power_law(df: pd.DataFrame) -> dict:
    """
    OLS on log10(price) vs log10(days since genesis).
    Support/resistance offsets = min/max residual, i.e. the bands are
    shifted until they contain all data — same construction as the chart.
    """
    x = np.log10(df["t"].values)
    y = np.log10(df["close"].values)
    n, a = np.polyfit(x, y, 1)                # slope, intercept
    resid = y - (a + n * x)
    return {"a": a, "n": n,
            "sup_off": resid.min(),           # support = fair + sup_off
            "res_off": resid.max()}           # resistance = fair + res_off


def band_position(df: pd.DataFrame, fit: dict) -> pd.Series:
    """0 = on support line, 1 = on resistance line (log space)."""
    logt = np.log10(df["t"].values)
    logp = np.log10(df["close"].values)
    fair = fit["a"] + fit["n"] * logt
    sup, res = fair + fit["sup_off"], fair + fit["res_off"]
    return pd.Series((logp - sup) / (res - sup), index=df.index)


def walk_forward_position(df: pd.DataFrame,
                          step_days: int = 7) -> pd.Series:
    """
    Band position using only data known at each date.
    Refit every `step_days` for speed; position evaluated on that fit.
    """
    start = df.index[0] + pd.Timedelta(days=365 * MIN_FIT_YEARS)
    out = {}
    dates = df.index[df.index >= start][::step_days]
    for d in dates:
        hist = df.loc[:d]
        fit = fit_power_law(hist)
        out[d] = band_position(hist.tail(1), fit).iloc[0]
    return pd.Series(out)


# ---------------------------------------------------------------- episodes
def support_episodes(pos: pd.Series, px: pd.Series,
                     thresh: float = BAND_THRESHOLD,
                     gap_days: int = 90) -> pd.DataFrame:
    """
    Contiguous stretches where band position < thresh.
    Stretches separated by < gap_days are merged into one episode.
    Returns the lowest-position day of each episode + forward returns.
    """
    below = pos[pos < thresh]
    if below.empty:
        return pd.DataFrame()

    rows, group = [], [below.index[0]]
    for d in below.index[1:]:
        if (d - group[-1]).days <= gap_days:
            group.append(d)
        else:
            rows.append(group)
            group = [d]
    rows.append(group)

    records = []
    for g in rows:
        seg = below.loc[g[0]:g[-1]]
        trough = seg.idxmin()
        rec = {"trough_date": trough.date(),
               "band_pos": round(seg.min(), 3),
               "price": round(float(px.asof(trough)), 2)}
        for w in FWD_WINDOWS:
            fwd_date = trough + pd.Timedelta(days=w)
            fwd_px = px.asof(fwd_date) if fwd_date <= px.index[-1] else np.nan
            rec[f"ret_{w}d"] = (round(float(fwd_px / px.asof(trough) - 1), 3)
                                if not np.isnan(fwd_px) else np.nan)
        records.append(rec)
    return pd.DataFrame(records)


# ---------------------------------------------------------------- main
def main():
    df = load_btc()
    px = df["close"]

    # --- 1. static fit (lookahead-biased, matches the website chart)
    static_fit = fit_power_law(df)
    static_pos = band_position(df, static_fit)
    print(f"Static fit:  price ~ t^{static_fit['n']:.2f}   "
          f"(fit on {len(df)} days, 2014->today)")
    print(f"Today's band position (static): {static_pos.iloc[-1]:.1%}\n")

    print("=== Support episodes — STATIC fit (biased) ===")
    print(support_episodes(static_pos, px).to_string(index=False))

    # --- 2. walk-forward fit (honest)
    wf_pos = walk_forward_position(df)
    print(f"\nToday's band position (walk-forward): {wf_pos.iloc[-1]:.1%}\n")

    print("=== Support episodes — WALK-FORWARD fit (tradeable) ===")
    print(support_episodes(wf_pos, px).to_string(index=False))

    print("\nCompare the two tables. Episodes that only appear under the "
          "static fit\nwere not visible in real time — that gap is the "
          "lookahead bias, quantified.")


if __name__ == "__main__":
    main()
