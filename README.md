
# 1. Planning & Requirements

## 1.1 Project Objective

Develop an automated algorithmic trading bot for **XAUUSD (Gold)** that identifies intraday trading opportunities, executes trades automatically, and manages risk through predefined rules.

The primary objective is to achieve consistent, risk-adjusted returns while maintaining strict drawdown control and complying with The5ers trading rules.

## 1.2 Trading Specifications

| Parameter | Specification |
|---|---|
| Asset Class | Forex / Precious Metals |
| Trading Instrument | XAUUSD |
| Trading Style | Intraday Algorithmic Trading |
| Initial Account Capital | $5,000 |
| Profit Target | To be determined through strategy research and backtesting |
| Trading Platform (Research) | MetaTrader 5 |
| Backtesting Environment | MT5 Historical Data |
| Paper Trading | MT5 Demo Account |
| Live Trading | The5ers |
| Holding Period | Intraday; no intentional overnight positions |
| Execution | Automated |
| Strategy Timeframe | To be determined during research |

## 1.3 Risk Management Requirements

The bot must incorporate an independent risk-management module that validates every trade before execution.

| Risk Parameter | Internal Limit |
|---|---:|
| Standard Risk per Trade | 0.25% ($12.50) |
| Maximum Risk per Trade | 0.50% ($25) |
| Daily Loss Limit | 1% ($50) |
| Weekly Loss Limit | 2% ($100) |
| Internal Maximum Drawdown | 4% ($200) |
| Maximum Simultaneous Open Risk | 0.50% ($25) |

### Risk Management Rules

- Calculate position size dynamically based on account equity and stop-loss distance.
- Every trade must have a predefined Stop Loss and Take Profit.
- Prevent new entries when daily or weekly loss limits are reached.
- Stop trading when the internal drawdown threshold is breached.
- Account for spreads, commissions and slippage when calculating actual risk.
- Prevent duplicate orders and excessive position exposure.
- Never allow strategy logic to override risk-management restrictions.
- Implement an emergency trading shutdown mechanism.

> **Note:** These are internal safety limits, not The5ers' official account limits.

## 1.4 Broker & Execution Requirements

### Research and Development: MetaTrader 5

- Historical market data for backtesting.
- MT5 Strategy Tester for strategy evaluation.
- Demo account for forward testing.
- MQL5/Python integration where required.

### Live Deployment: The5ers

- Use the permitted trading platform and execution method for the selected program.
- Verify symbol specifications, contract size, leverage and trading conditions.
- Respect the selected program's daily loss, maximum loss and prohibited trading practices.
- Implement account-level risk monitoring.

## 1.5 Performance Metrics

The strategy will be evaluated using the following metrics:

- Net Profit / Return on Capital
- Profit Factor
- Win Rate
- Average Risk-to-Reward Ratio
- Expectancy per Trade
- Maximum Drawdown
- Recovery Factor
- Sharpe Ratio
- Average Trades per Day
- Transaction Costs
- Monthly Return Consistency

The strategy must demonstrate positive expectancy after transaction costs and acceptable drawdown across out-of-sample testing.


# 2. Strategy Research & Market Regime Classification

## 2.1 Research Objective

Develop a data-driven trading framework for XAUUSD using Machine Learning and statistical analysis.

Rather than applying a single trading strategy across all market conditions, the objective is to classify the market into distinct regimes and identify trading opportunities that demonstrate a measurable statistical edge within each regime.

The research process will focus on:

1. Identifying different market conditions.
2. Extracting relevant market features.
3. Applying Machine Learning algorithms for market regime classification.
4. Testing multiple trading hypotheses within each identified regime.
5. Evaluating strategy performance and identifying statistically significant edges.
6. Developing a regime-aware strategy selection framework.

## 2.2 Market Regime Classification

The market will initially be divided into the following categories:

| Market Regime | Characteristics | Potential Strategy |
|---|---|---|
| Trending Bullish | Higher highs, higher lows, positive directional momentum | Trend Following / Momentum |
| Trending Bearish | Lower highs, lower lows, negative directional momentum | Trend Following / Momentum |
| Range-Bound | Price oscillates within defined support and resistance levels | Mean Reversion |
| High-Volatility | Large price movements and expanding ATR | Volatility Breakout |
| Low-Volatility | Price compression and declining ATR | Range Expansion / Breakout |
| Uncertain / Choppy | Weak directional movement and frequent reversals | No Trade |

**Note:** These are initial research hypotheses. Market regimes may overlap, and the final classification will be determined through statistical analysis and model evaluation.

## 2.3 Historical Market Data Collection

Collect historical XAUUSD data for exploratory analysis, feature engineering, model training and strategy evaluation.

### Data Requirements

- Instrument: XAUUSD
- Primary Data Source: MetaTrader 5
- Historical Timeframe: M1
- Derived Timeframes: M5, M15, H1 and H4
- Data Fields:
  - Timestamp
  - Open
  - High
  - Low
  - Close
  - Tick Volume
  - Spread (where available)

### Data Preprocessing

- Handle missing timestamps and incomplete candles.
- Remove duplicate observations.
- Check for invalid OHLC values.
- Identify abnormal price movements and data anomalies.
- Normalize features where required.
- Align data across different timeframes.
- Account for trading sessions and market closures.
- Prevent look-ahead bias and data leakage.

## 2.4 Exploratory Data Analysis (EDA)

Perform exploratory analysis to understand the statistical properties of XAUUSD and identify potential market patterns.

### Areas of Investigation

1. Return Distribution:
   - Log returns
   - Percentage returns
   - Return volatility
   - Skewness and kurtosis

2. Volatility Analysis:
   - Average True Range (ATR)
   - Rolling standard deviation
   - Volatility clustering
   - Volatility expansion and contraction

3. Trend Analysis:
   - Moving averages
   - ADX
   - Directional movement
   - Trend persistence

4. Market Structure:
   - Higher highs and higher lows
   - Lower highs and lower lows
   - Support and resistance
   - Price consolidation
   - Breakouts and false breakouts

5. Volume Analysis:
   - Tick volume
   - Volume spikes
   - Price-volume relationships

6. Session Analysis:
   - Asian session
   - London session
   - New York session
   - London-New York overlap

## 2.5 Feature Engineering

Develop features that describe the current market environment and its statistical behaviour.

### Initial Feature Set

| Category | Features |
|---|---|
| Trend | EMA 20, EMA 50, EMA 200, ADX |
| Momentum | RSI, MACD, ROC |
| Volatility | ATR, Rolling Standard Deviation, Bollinger Band Width |
| Price Structure | Distance from Swing High/Low, Higher Highs, Lower Lows |
| Volume | Tick Volume, Relative Volume |
| Market Structure | Range Width, Breakout Strength, Price Compression |
| Temporal | Hour, Trading Session, Day of Week |

Feature selection and dimensionality reduction will be investigated to eliminate redundant and noisy variables.

## 2.6 Machine Learning for Market Classification

Investigate different Machine Learning algorithms to identify recurring market regimes.

### Unsupervised Learning

Used to discover market regimes without predefined labels.

| Algorithm | Research Purpose |
|---|---|
| K-Means | Identify clusters of similar market conditions |
| Gaussian Mixture Models (GMM) | Identify probabilistic market regimes |
| Hierarchical Clustering | Explore relationships between market states |
| DBSCAN | Identify dense market clusters and anomalous conditions |

### Time-Series / Probabilistic Models

| Algorithm | Research Purpose |
|---|---|
| Hidden Markov Models (HMM) | Model hidden market states and regime transitions |
| Markov Switching Models | Identify changes in underlying market behaviour |

### Supervised Learning

Used to predict future market conditions after defining reliable regime labels.

| Algorithm | Research Purpose |
|---|---|
| Random Forest | Nonlinear regime classification |
| XGBoost | Identify complex relationships between market features |
| LightGBM | Efficient gradient-boosted classification |
| Support Vector Machine | Explore nonlinear classification boundaries |

### Model Evaluation

- Silhouette Score for clustering quality.
- Davies-Bouldin Index.
- Calinski-Harabasz Score.
- Regime stability over time.
- Transition frequency between regimes.
- Classification accuracy where reliable labels exist.
- Out-of-sample classification performance.

**Important:** A model with good clustering metrics does not necessarily identify economically useful regimes. Each regime must also demonstrate meaningful differences in market behaviour and trading outcomes.

## 2.7 Strategy Hypothesis Development

Once market regimes are identified, investigate different trading hypotheses within each regime.

| Market Regime | Strategy Hypothesis | Potential Indicators |
|---|---|---|
| Trending Bullish | Buy pullbacks in an established uptrend | EMA, ADX, RSI |
| Trending Bearish | Sell pullbacks in an established downtrend | EMA, ADX, RSI |
| Range-Bound | Buy near range support and sell near resistance | Bollinger Bands, RSI |
| High-Volatility | Trade volatility expansion and breakouts | ATR, Volume, Donchian Channels |
| Low-Volatility | Identify price compression before expansion | Bollinger Band Width, ATR |
| Uncertain / Choppy | Avoid trading | Regime confidence and volatility filters |

Each hypothesis must be independently backtested before integration into the trading framework.

## 2.8 Statistical Edge Identification

The objective is to determine whether a trading hypothesis produces a repeatable statistical advantage under specific market conditions.

### Evaluation Metrics

- Win Rate
- Average Win / Average Loss
- Risk-to-Reward Ratio
- Expectancy per Trade
- Profit Factor
- Maximum Drawdown
- Sharpe Ratio
- Sortino Ratio
- Trade Frequency
- Return Distribution

### Statistical Validation

- Compare strategy performance across different market regimes.
- Evaluate whether observed performance is statistically significant.
- Test sensitivity to indicator parameters.
- Perform out-of-sample testing.
- Use walk-forward validation.
- Apply bootstrap analysis and Monte Carlo simulations.
- Account for transaction costs, spread and slippage.
- Check for overfitting and data snooping.

A strategy will only be considered viable if its edge persists across unseen data and different market conditions.

## 2.9 Regime-Aware Strategy Selection

Develop a framework that connects market classification with strategy execution.

### Proposed Workflow

1. Collect incoming XAUUSD market data.
2. Calculate market features.
3. Classify the current market regime.
4. Estimate regime confidence.
5. Select the strategy associated with that regime.
6. Generate trading signals.
7. Validate signals through the risk-management module.
8. Execute trades if all conditions are satisfied.
9. Monitor performance and regime transitions.

If the market regime is uncertain or the classification confidence is below a predefined threshold, the system should avoid opening new positions.

## 2.10 Research Deliverables

1. Clean historical XAUUSD dataset.
2. Exploratory Data Analysis report.
3. Feature engineering pipeline.
4. Market regime classification models.
5. Model evaluation and comparison report.
6. Strategy hypotheses for each market regime.
7. Backtesting results for individual strategies.
8. Statistical edge evaluation report.
9. Final strategy specification containing:
   - Entry conditions
   - Exit conditions
   - Position-sizing rules
   - Stop-loss methodology
   - Take-profit methodology
   - Trading session restrictions
   - Regime-specific execution rules

## 2.11 Completion Criteria

The research phase will be considered complete when:

- Market regimes have been identified and validated.
- Classification models demonstrate stable out-of-sample behaviour.
- Each proposed strategy has been independently tested.
- Statistically meaningful trading edges have been identified.
- Transaction costs and execution assumptions have been incorporated.
- A complete strategy specification is documented.

**Final Research Objective:** Develop a regime-aware algorithmic trading system that adapts its trading approach to changing XAUUSD market conditions instead of relying on a single static trading strategy.

# 5. Backtesting & Strategy Validation

## 5.1 Objective

Evaluate the performance, robustness and statistical reliability of the developed XAUUSD algorithmic trading strategies using historical market data.

The backtesting phase will validate two major components:

1. **Market Regime Classification:** Evaluate whether the ML models can consistently identify different market conditions without using future information.
2. **Trading Strategy Performance:** Evaluate whether the strategies generate a measurable and repeatable trading edge within their respective market regimes.

The primary objective is to identify strategies that demonstrate positive expectancy, controlled drawdown and consistent out-of-sample performance after accounting for transaction costs.

## 5.2 Backtesting Environment

| Parameter | Specification |
|---|---|
| Instrument | XAUUSD |
| Platform | MetaTrader 5 |
| Historical Data | MT5 Historical Data |
| Primary Timeframe | M1 |
| Derived Timeframes | M5, M15, H1, H4 |
| Testing Framework | Python / MT5 Strategy Tester |
| ML Framework | Scikit-learn / XGBoost / PyTorch (where required) |
| Initial Capital | $5,000 |
| Execution Model | Simulated market execution |
| Transaction Costs | Spread, Commission and Slippage |
| Validation Method | Out-of-Sample / Walk-Forward Testing |

## 5.3 Historical Backtesting

Run the developed trading strategies against historical XAUUSD data.

### Testing Requirements

- Execute trades using historical market prices.
- Simulate realistic entry and exit conditions.
- Account for bid-ask spreads.
- Include broker commissions and applicable fees.
- Model slippage during order execution.
- Account for variable spreads during volatile periods.
- Simulate Stop Loss and Take Profit execution.
- Prevent duplicate trades and invalid order execution.
- Respect trading session restrictions.
- Prevent look-ahead bias in signal generation.

### Execution Assumptions

The backtesting engine should simulate realistic market execution rather than assuming every order is filled at the candle closing price.

Where M1 data is used, lower-level price information should be used to determine whether Stop Loss or Take Profit was reached first whenever possible.

## 5.4 Market Regime Classification Validation

Evaluate the performance of the ML-based market classification system independently of the trading strategies.

### Validation Objectives

- Determine whether identified market regimes represent distinct market behaviours.
- Evaluate regime stability across different periods.
- Measure how frequently the model switches between regimes.
- Identify false classifications and unstable transitions.
- Evaluate classification confidence.
- Check whether regime identification is available using information known at that time.
- Measure classification performance on unseen data.

### Classification Metrics

| Metric | Purpose |
|---|---|
| Silhouette Score | Measure clustering separation |
| Davies-Bouldin Index | Evaluate cluster compactness |
| Calinski-Harabasz Score | Evaluate cluster separation |
| Regime Stability | Measure consistency over time |
| Transition Frequency | Measure regime switching |
| Classification Accuracy | Evaluate supervised models where ground-truth labels exist |

**Important:** Good clustering scores alone do not establish a profitable trading edge. The identified regimes must also demonstrate economically meaningful differences in trading outcomes.

## 5.5 Strategy Performance Evaluation

Test each trading hypothesis independently within its corresponding market regime.

### Strategies to Evaluate

| Market Regime | Strategy |
|---|---|
| Trending Bullish | Long Momentum / Trend Following |
| Trending Bearish | Short Momentum / Trend Following |
| Range-Bound | Mean Reversion |
| High-Volatility | Volatility Breakout |
| Low-Volatility | Range Expansion / Breakout |
| Uncertain / Choppy | No Trade |

### Evaluation Metrics

| Metric | Description |
|---|---|
| Net Profit | Total profit after transaction costs |
| Return on Capital | Percentage return on initial capital |
| Sharpe Ratio | Risk-adjusted return |
| Sortino Ratio | Return relative to downside volatility |
| Maximum Drawdown | Largest peak-to-trough decline |
| Win Rate | Percentage of profitable trades |
| Profit Factor | Gross Profit / Gross Loss |
| Expectancy | Expected profit or loss per trade |
| Recovery Factor | Net Profit / Maximum Drawdown |
| Average Risk-to-Reward | Average winning trade relative to average losing trade |
| Trade Frequency | Number of trades per day/week/month |

## 5.6 Risk Management Validation

Verify that all strategies operate within predefined account-level risk constraints.

### Internal Risk Limits

| Risk Parameter | Limit |
|---|---:|
| Standard Risk per Trade | 0.25% |
| Maximum Risk per Trade | 0.50% |
| Daily Loss Limit | 1% |
| Weekly Loss Limit | 2% |
| Internal Maximum Drawdown | 4% |
| Maximum Simultaneous Open Risk | 0.50% |

### Risk Testing Requirements

- Verify dynamic position sizing.
- Test Stop Loss execution under different volatility conditions.
- Evaluate consecutive losing trades.
- Simulate daily and weekly loss-limit breaches.
- Verify automatic trading shutdown.
- Test equity-based and balance-based drawdown calculations.
- Verify that open positions and floating losses are included where required.
- Ensure that the system cannot exceed internal risk limits through multiple simultaneous orders.

The internal limits must remain separate from The5ers' official account restrictions.

## 5.7 Overfitting & Data Leakage Prevention

Ensure that model and strategy performance is not artificially inflated by information from the future or excessive parameter optimization.

### Prevention Techniques

- Use chronological train-validation-test splits.
- Avoid random shuffling of time-series observations.
- Apply walk-forward validation.
- Use out-of-sample testing.
- Use purging and embargo periods where overlapping labels or holding periods could cause leakage.
- Fit scalers and preprocessing transformations only on training data.
- Avoid using future candles for regime classification.
- Avoid repeatedly optimizing against the final test dataset.
- Test parameter sensitivity.
- Limit unnecessary feature selection and hyperparameter tuning.

### Proposed Data Split

| Dataset | Allocation | Purpose |
|---|---:|---|
| Training | 60% | Model and strategy development |
| Validation | 20% | Parameter selection and tuning |
| Testing | 20% | Final out-of-sample evaluation |

The split must be chronological, not randomly assigned.

The final test dataset must remain untouched until model and strategy development are complete.

## 5.8 Walk-Forward Testing

Use walk-forward analysis to evaluate how the strategy performs when periodically retrained or recalibrated using only past data.

### Proposed Workflow

1. Train the model using historical data.
2. Validate the model on the next chronological period.
3. Freeze the model and test it on unseen future data.
4. Move the testing window forward.
5. Retrain using the expanded historical dataset.
6. Repeat the process across multiple market conditions.
7. Aggregate the results across all testing windows.

The objective is to determine whether the trading edge persists over time rather than existing only within a particular historical period.

## 5.9 Robustness & Stress Testing

Evaluate the sensitivity of the strategy to different market conditions and execution assumptions.

### Testing Scenarios

- Increased spread and commission.
- Higher slippage.
- Different trading sessions.
- High-volatility market conditions.
- Low-volatility market conditions.
- Economic news periods.
- Consecutive losing trades.
- Different Stop Loss and Take Profit configurations.
- Different market regimes.
- Different historical periods.

### Additional Validation

- Monte Carlo simulation of trade sequences.
- Bootstrap analysis of strategy returns.
- Parameter sensitivity analysis.
- Comparison against simple benchmark strategies.
- Performance comparison between individual strategies and the combined regime-aware system.

## 5.10 Strategy Acceptance Criteria

A strategy must satisfy predefined performance and risk requirements before proceeding to paper trading.

### Initial Research Thresholds

| Metric | Proposed Threshold |
|---|---:|
| Out-of-Sample Profit Factor | > 1.20 |
| Out-of-Sample Expectancy | Positive |
| Minimum Trade Count | 200 |
| Maximum Drawdown | < 4% |
| Risk per Trade | <= 0.50% |
| Sharpe Ratio | > 1.0 |
| Transaction Costs | Fully Incorporated |
| Walk-Forward Performance | Positive aggregate expectancy |

These are initial research filters, not guarantees of future profitability. Performance must also be evaluated across individual test windows, not just the aggregate.

A strategy that fails the acceptance criteria must return to **Phase 2: Strategy Research** for further investigation.

A strategy must not be accepted solely because it produces high historical returns.

## 5.11 Final Backtest Report

Generate a comprehensive backtesting report containing:

### A. Strategy Overview
- Strategy name and version.
- Market regime.
- Entry and exit rules.
- Indicators and features.
- Position-sizing methodology.
- Stop Loss and Take Profit rules.

### B. Performance Summary
- Initial capital.
- Final equity.
- Net profit.
- Total return.
- Profit factor.
- Win rate.
- Sharpe and Sortino ratios.
- Maximum drawdown.
- Expectancy.
- Total trades.

### C. Risk Analysis
- Daily and weekly drawdown.
- Consecutive losses.
- Average losing trade.
- Largest losing trade.
- Exposure and position sizing.
- Risk-limit violations.

### D. Model Evaluation
- Classification performance.
- Regime distribution.
- Regime transition analysis.
- Classification confidence.
- Out-of-sample model performance.

### E. Robustness Analysis
- Walk-forward results.
- Parameter sensitivity.
- Monte Carlo results.
- Transaction cost sensitivity.
- Performance across different market conditions.

### F. Visualizations
- Equity curve.
- Drawdown curve.
- Monthly returns.
- Trade distribution.
- Regime distribution.
- Performance by market regime.
- Long versus short performance.

## 5.12 Deliverables

1. Historical backtesting engine.
2. Individual strategy backtest reports.
3. Market regime classification evaluation.
4. Combined regime-aware strategy backtest.
5. Transaction cost and slippage analysis.
6. Out-of-sample validation report.
7. Walk-forward testing report.
8. Monte Carlo and robustness analysis.
9. Strategy acceptance/rejection decision.
10. Final backtest report.

## 5.13 Completion Criteria

The backtesting phase will be considered complete when:

- All strategies have been tested on historical XAUUSD data.
- Transaction costs and realistic execution assumptions are incorporated.
- Market regime classification has been independently evaluated.
- Look-ahead bias and data leakage have been addressed.
- Out-of-sample and walk-forward testing have been completed.
- Risk-management rules have been verified.
- Strategies have passed the agreed acceptance criteria.

**Final Objective:** Identify robust, statistically validated trading strategies that demonstrate positive out-of-sample expectancy, acceptable drawdown and resilience across different XAUUSD market regimes.

Strategies that fail the agreed thresholds return to Phase 2: Strategy Research for further development and evaluation.

# System Design: MT5 + Python + PyTorch Trading Bot

Target: live trading on a The5ers account through MetaTrader 5.

---

## 1. Design Goals
- **Safety first:** the bot must never breach the prop firm's drawdown rules. The risk manager has veto power over every order.
- **Same code for backtest, paper and live:** only the data and execution adapters change.
- **Recoverable:** after a crash or restart, the bot rebuilds its state from MT5 and the database.
- **Observable:** every signal, decision and order is logged.

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Broker bridge | `MetaTrader5` Python package | Windows only, requires the MT5 terminal running |
| ML | PyTorch | Training offline on a GPU or Colab; inference on CPU is usually enough |
| Data | pandas, numpy, pyarrow (Parquet) | |
| Features | pandas-ta or TA-Lib | |
| Database | SQLite to start, PostgreSQL later | Trades, signals, logs, model versions |
| Config | YAML + `pydantic` models | Validated on startup |
| Secrets | `.env` file (git-ignored) or OS credential store | Never in code or repo |
| Scheduler | `asyncio` or APScheduler | |
| Alerts | Telegram bot API | |
| Hosting | Windows VPS (24/7) | Needed because the MT5 Python API runs on Windows |
| Testing | pytest | |
| Experiment tracking | MLflow or a simple CSV/JSON log | Optional |

## 3. Architecture

```
                  +--------------------------+
                  |   MT5 Terminal (VPS)     |
                  |  logged in to 5ers acct  |
                  +------------+-------------+
                               |  MetaTrader5 API
        +----------------------+-----------------------+
        |                                              |
+-------v--------+                              +------v--------+
|  Data Handler  |                              | Order Executor|
| ticks / bars   |                              | send / modify |
+-------+--------+                              | close / retry |
        |                                       +------^--------+
+-------v--------+                                     |
| Feature Engine |                              +------+--------+
+-------+--------+                              | Risk Manager  |
        |                                       | (veto power)  |
+-------v--------+     signal      +------------>               |
| Model Inference|---------------->| Strategy   | +------^--------+
| (PyTorch)      |                 | Engine     |      |
+----------------+                 +-------------+      |
                                                 +------+--------+
+-----------------+    +-----------------+       | Account/State |
| Database        |<---| Logger / Audit  |<------| Monitor       |
+-----------------+    +-----------------+       +------+--------+
                                                        |
                                                 +------v--------+
                                                 | Alerts (TG)   |
                                                 +---------------+
```
![alt text](image_565966b9.jpg)

**Flow of one decision:**
1. Data Handler pulls a new bar or tick from MT5.
2. Feature Engine builds the input vector or window.
3. Model returns a prediction (direction, probability).
4. Strategy Engine converts it into a trade proposal (symbol, side, size, SL, TP).
5. Risk Manager checks the proposal against all limits. It can approve, resize or reject.
6. Order Executor sends the order to MT5, confirms the fill and records it.
7. Logger writes everything to the database. Monitor checks account state.

## 4. Module List

```
trading_bot/
├── config/
│   ├── settings.yaml          # symbols, timeframes, risk limits
│   └── .env.example           # variable names only, no real values
├── src/
│   ├── data/
│   │   ├── mt5_client.py      # connect, reconnect, health check
│   │   ├── market_data.py     # bars/ticks fetch, gap detection
│   │   └── storage.py         # Parquet / DB read-write
│   ├── features/
│   │   └── feature_engine.py  # indicators, scaling, windowing
│   ├── models/
│   │   ├── model.py           # PyTorch nn.Module
│   │   ├── train.py           # offline training
│   │   ├── inference.py       # load + predict
│   │   └── registry.py        # versions, metrics, active model
│   ├── strategy/
│   │   └── strategy.py        # signal -> trade proposal
│   ├── risk/
│   │   ├── risk_manager.py    # all limits and veto logic
│   │   └── position_sizer.py
│   ├── execution/
│   │   ├── order_executor.py  # send, modify, close, retry
│   │   └── reconciler.py      # compare local state vs MT5
│   ├── monitor/
│   │   ├── account_monitor.py # equity, drawdown, positions
│   │   └── alerts.py          # Telegram
│   ├── backtest/
│   │   ├── engine.py          # replay with fees and slippage
│   │   └── report.py
│   ├── db/
│   │   ├── models.py
│   │   └── migrations/
│   └── main.py                # entry point, run loop, shutdown
├── tests/
├── notebooks/                 # research only
├── logs/
└── README.md
```

## 5. Risk Manager Rules (Prop Firm Compliance)

The risk manager runs **before every order** and continuously on open positions. Fill in the real values from your The5ers account rules and check them again whenever you change program or account.

| Rule | Config key | Bot behavior |
|---|---|---|
| Max daily loss | `max_daily_loss_pct` | Stop trading for the day when reached; close positions if breached |
| Max overall drawdown | `max_total_drawdown_pct` | Hard stop and alert |
| Internal buffer | `buffer_pct` | Trigger the bot's limits **before** the firm's limits (e.g. stop at 70-80% of the allowed loss) |
| Risk per trade | `risk_per_trade_pct` | Position size from stop distance |
| Max open positions | `max_open_positions` | Reject new proposals above this |
| Stop loss required | always on | Reject any order with no SL |
| News and weekend restrictions | `restricted_windows` | Block entries inside defined windows, if the firm restricts them |
| Allowed instruments and leverage | `allowed_symbols` | Whitelist only |
| Kill switch | file flag or Telegram command | Flatten all positions and halt |

Note the way the firm measures drawdown (balance vs equity, daily reset time and time zone). The bot must measure it the same way, or the buffer may be wrong.

## 6. Data Design

**Market data:** stored as Parquet per symbol and timeframe (`data/EURUSD/M15.parquet`) with columns `time, open, high, low, close, tick_volume, spread`. Time is UTC.

**Database tables (SQLite/PostgreSQL):**

`signals`
| column | type |
|---|---|
| id | int, pk |
| ts | datetime (UTC) |
| symbol | text |
| model_version | text |
| prediction | float |
| direction | text |
| features_hash | text |

`orders`
| column | type |
|---|---|
| id | int, pk |
| client_id | text, unique (idempotency key) |
| signal_id | int, fk |
| symbol, side | text |
| volume, price, sl, tp | float |
| status | text (proposed / approved / rejected / sent / filled / partial / failed / closed) |
| mt5_ticket | int |
| reject_reason | text |
| created_at, updated_at | datetime |

`trades`
| column | type |
|---|---|
| id, order_id | int |
| open_time, close_time | datetime |
| open_price, close_price | float |
| profit, commission, swap | float |

`account_snapshots`
| column | type |
|---|---|
| ts | datetime |
| balance, equity, margin, free_margin | float |
| daily_pnl, drawdown_pct | float |

`model_registry`
| column | type |
|---|---|
| version | text, pk |
| trained_at | datetime |
| data_range | text |
| metrics_json | text |
| artifact_path | text |
| is_active | bool |

`events`: free-form log of errors, reconnects and kill-switch triggers.

## 7. ML Design Notes
- Train offline; the live bot only loads a saved model file and runs inference.
- Use time-based splits (train / validation / test), never random splits, to avoid look-ahead leakage.
- Save the scaler/normalizer with the model so live features are processed identically.
- Log the model version with every signal so results can be traced.
- Add a confidence threshold: no trade when the prediction is weak.
- Monitor live feature distributions against training data to detect drift; alert and pause if they diverge badly.
- Promote a new model only after backtest, then paper trading (a demo MT5 account), then small live size.

## 8. Failure Handling

| Failure | Handling |
|---|---|
| MT5 terminal not running / disconnected | Health check each loop; try `initialize()` again with backoff; alert after N failures; no new orders while disconnected |
| Order rejected (requote, off quotes, invalid stops, market closed) | Log retcode, retry limited times with fresh price, else cancel proposal |
| Partial fill | Record actual volume; set SL/TP on the filled volume; do not resend the remainder blindly |
| Duplicate orders | Unique `client_id` per proposal; check existing orders and positions before sending; one in-flight order per symbol |
| Bot crash / restart | On start, **reconcile**: read open positions and orders from MT5, compare to the DB, resolve differences, then resume; run under a supervisor that restarts it |
| Stale or missing data | Check timestamp freshness and bar gaps; skip the decision and alert |
| Model errors (NaN output, load failure) | Fall back to "no trade"; never trade on invalid output |
| Slippage or spread spike | Max spread and max deviation checks before sending |
| VPS reboot or internet loss | Server-side SL on every position so open trades are protected even when the bot is offline |
| Drawdown limit approached | Reduce risk, then halt, then flatten, with alert at each step |

Every position must have a stop loss set on the broker side at the time of entry, not only inside the bot's logic.

## 9. Secrets Management
- Store MT5 login, password and server, plus the Telegram token, in `.env`, loaded at startup.
- Add `.env`, `logs/` and `data/` to `.gitignore`. Commit only `.env.example`.
- Restrict file permissions on the VPS; use a separate Windows user for the bot.
- Use different credentials for demo and live, selected by an `ENV=demo|live` setting, with a startup banner and confirmation guard for live mode.
- Rotate passwords if there is any chance of exposure. Never paste credentials into logs, screenshots or chats.

## 10. Environments

| Environment | Data | Execution | Purpose |
|---|---|---|---|
| Research | historical files | none | explore, train |
| Backtest | historical files | simulated with costs | validate |
| Demo / paper | live MT5 demo feed | MT5 demo account | forward test |
| Live | live MT5 on The5ers | real orders | production |

## 11. Logging and Monitoring
- Structured logs (JSON) with timestamp, module, symbol, order id.
- Heartbeat message every N minutes to Telegram.
- Alerts: disconnect, rejected order, drawdown thresholds, kill switch, model error, unexpected position.
- Daily report: trades, P&L, drawdown, rejected signals.

## 12. Build Order (Suggested)
1. `mt5_client` + data download and storage
2. Feature engine + backtest engine with a simple baseline strategy
3. Risk manager and position sizer, with unit tests
4. Order executor on a **demo** account, with reconciler
5. Model training and inference
6. Monitoring and alerts
7. Demo forward test for several weeks
8. Live with minimum size

## 13. Open Decisions
- Symbols and timeframes to trade
- Prediction target (direction, return, volatility) and model type (LSTM, Transformer, MLP)
- Single instrument or portfolio
- Exact The5ers program and its current rules (check the official rules page and your account terms)
- Whether automated/EA trading is allowed under your specific account terms (confirm with The5ers)
