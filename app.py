"""
============================================================
 Real-Time Taxi Demand & Mobility Analytics
 Backend Model — Flask + Pandas
============================================================
"""

from flask import Flask, render_template, jsonify
import pandas as pd
import numpy as np
import random
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# ============================================================
# 1. DATASET GENERATION (runs only once)
# ============================================================
DATASET = "taxi_trips.csv"
ZONES = ["Downtown", "Airport", "Midtown", "Uptown",
         "Station", "Mall", "University"]

def generate_dataset(n_rows=5000):
    """Create a realistic taxi trip dataset if not present."""
    np.random.seed(42)
    random.seed(42)
    base = datetime(2024, 1, 1)
    rows = []

    for i in range(n_rows):
        ts = base + timedelta(minutes=random.randint(0, 60 * 24 * 30))
        hour = ts.hour

        # Realistic demand pattern: peaks at 8-10 AM and 5-8 PM
        if 8 <= hour <= 10 or 17 <= hour <= 20:
            zone = random.choice(["Downtown", "Midtown", "Station", "Airport"])
        else:
            zone = random.choice(ZONES)

        rows.append({
            "trip_id": i + 1,
            "pickup_datetime": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "pickup_zone": zone,
            "dropoff_zone": random.choice(ZONES),
            "fare_amount": round(random.uniform(3.0, 60.0), 2),
            "trip_distance_km": round(random.uniform(0.5, 25.0), 2),
            "payment_type": random.choice(["Cash", "Card", "UPI"]),
        })

    pd.DataFrame(rows).to_csv(DATASET, index=False)
    print(f"✅ Generated {DATASET} with {n_rows} rows")


if not os.path.exists(DATASET):
    generate_dataset()


# ============================================================
# 2. LOAD & PREPARE DATA (Pandas model)
# ============================================================
def load_data():
    df = pd.read_csv(DATASET)
    df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"])
    df["hour"] = df["pickup_datetime"].dt.hour
    df["day"] = df["pickup_datetime"].dt.day_name()
    return df

DF = load_data()


# ============================================================
# 3. ROUTES
# ============================================================
@app.route("/")
def home():
    """Render the dashboard with KPI stats."""
    return render_template(
        "index.html",
        total_trips=len(DF),
        revenue=round(DF["fare_amount"].sum(), 2),
        avg_fare=round(DF["fare_amount"].mean(), 2),
        avg_dist=round(DF["trip_distance_km"].mean(), 2),
    )


# ---------- API 1: Demand by hour ----------
@app.route("/api/hourly")
def api_hourly():
    counts = DF.groupby("hour").size().reindex(range(24), fill_value=0)
    return jsonify({
        "labels": [f"{h:02d}:00" for h in counts.index],
        "values": counts.tolist(),
    })


# ---------- API 2: Demand by zone ----------
@app.route("/api/zones")
def api_zones():
    counts = DF["pickup_zone"].value_counts()
    return jsonify({
        "labels": counts.index.tolist(),
        "values": counts.tolist(),
    })


# ---------- API 3: Payment split ----------
@app.route("/api/payment")
def api_payment():
    counts = DF["payment_type"].value_counts()
    return jsonify({
        "labels": counts.index.tolist(),
        "values": counts.tolist(),
    })


# ---------- API 4: Demand by day ----------
@app.route("/api/daily")
def api_daily():
    order = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]
    counts = DF.groupby("day").size().reindex(order, fill_value=0)
    return jsonify({
        "labels": counts.index.tolist(),
        "values": counts.tolist(),
    })


# ---------- API 5: Real-time live demand (simulated) ----------
@app.route("/api/live")
def api_live():
    """
    Simulated real-time demand.
    In production this would be fed by Kafka + PySpark streaming.
    """
    demand = {zone: int(np.random.poisson(3)) for zone in ZONES}
    return jsonify({
        "time": datetime.now().strftime("%H:%M:%S"),
        "demand": demand,
        "total": sum(demand.values()),
    })


# ============================================================
# 4. RUN
# ============================================================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
