import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS

from app.backtest.backtest import get_backtest
from app.data.downloader import get_price_data, get_fundamentals
from app.factors.momentum import generate_signals, generate_momentum_score
from app.mote_carlo.simulation import mc_simulation
from app.prediction.predictor import StockPredictor, scan_top_nasdaq

app = Flask(__name__)
CORS(app)


@app.route("/api/analyze/<ticker>", methods=["GET"])
def analyze(ticker):
    try:
        price_data = get_price_data(ticker)
        fundamentals = get_fundamentals(ticker)
        score = generate_momentum_score(price_data)

        return jsonify(
            {
                "ticker": ticker,
                "momentum_score": float(score) if score else None,
                **fundamentals,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/backtest/<ticker>", methods=["GET"])
def backtest(ticker):
    try:
        price_data = get_price_data(ticker)
        print(f"columns: {price_data.columns}")
        close_prices = price_data[("Close", ticker)]

        signals = generate_signals(close_prices)

        if len(close_prices) != len(signals):
            raise ValueError(
                f"Price data length {len(close_prices)} != signals length {len(signals)}"
            )

        backtest_result = get_backtest(close_prices, signals)

        df = backtest_result.to_frame("portfolio_value")
        df.index = df.index.astype(str)  # ensure JSON serializable

        return jsonify(df["portfolio_value"].to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/monte-carlo-sim/<ticker>", methods=["GET"])
def mc_sim(ticker):
    result = mc_simulation(ticker)
    return jsonify(result)

@app.route("/api/predict/<ticker>", methods=["GET"])
def predict(ticker):
    try:
        predictor = StockPredictor(ticker)
        predictor.train()
        decision = predictor.predict_latest()
        return jsonify({"ticker": ticker, "recommendation": decision})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/nasdaq-buy-recs", methods=["GET"])
def nasdaq():
    try:
        buy_rec: pd.DataFrame = scan_top_nasdaq()
        return jsonify(buy_rec.to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8000)
