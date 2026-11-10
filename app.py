from flask import Flask, render_template, jsonify
import pandas as pd
import numpy as np
import random, os
from datetime import datetime, timedelta

app = Flask(__name__)

DATASET = "taxi_trips.csv"
ZONES = ["Downtown", "Airport", "Midtown", "Uptown",
         "Station", "Mall", "University"]

# ---------- Generate dataset ----------
if not os.path.exists(DATASET):
    np.random.seed(42)
    random.seed(42)
    base = datetime(2024, 1, 1)
    rows = []
    for i in range(5000):
        ts = base + timedelta(minutes=random.randint(0, 60 * 24 * 30))
        h = ts.hour
        zone = random.choice(["Downtown", "Midtown", "Station", "Airport"]) \
            if (8 <= h <= 10 or 17 <= h <= 20) else random.choice(ZONES)
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

# ---------- Load data ----------
DF = pd.read_csv(DATASET)
DF["pickup_datetime"] = pd.to_datetime(DF["pickup_datetime"])
DF["hour"] = DF["pickup_datetime"].dt.hour
DF["day"] = DF["pickup_datetime"].dt.day_name()

# ---------- Global stats (for sidebar) ----------
STATS = {
    "total_trips": len(DF),
    "revenue": round(DF["fare_amount"].sum(), 2),
    "avg_fare": round(DF["fare_amount"].mean(), 2),
    "avg_dist": round(DF["trip_distance_km"].mean(), 2),
}

# ---------- Page routes ----------
@app.route("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard", **STATS)

@app.route("/analytics")
def analytics():
    return render_template("analytics.html", active="analytics", **STATS)

@app.route("/live")
def live():
    return render_template("live.html", active="live", **STATS)

# ---------- APIs ----------
@app.route("/api/hourly")
def api_hourly():
    c = DF.groupby("hour").size().reindex(range(24), fill_value=0)
    return jsonify({"labels": [f"{h:02d}:00" for h in c.index], "values": c.tolist()})

@app.route("/api/zones")
def api_zones():
    c = DF["pickup_zone"].value_counts()
    return jsonify({"labels": c.index.tolist(), "values": c.tolist()})

@app.route("/api/payment")
def api_payment():
    c = DF["payment_type"].value_counts()
    return jsonify({"labels": c.index.tolist(), "values": c.tolist()})

@app.route("/api/daily")
def api_daily():
    order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    c = DF.groupby("day").size().reindex(order, fill_value=0)
    return jsonify({"labels": c.index.tolist(), "values": c.tolist()})

@app.route("/api/revenue-zone")
def api_revenue_zone():
    r = DF.groupby("pickup_zone")["fare_amount"].sum().sort_values(ascending=False)
    return jsonify({"labels": r.index.tolist(), "values": [round(v, 2) for v in r.values]})

@app.route("/api/peak-zones")
def api_peak_zones():
    g = DF.groupby("pickup_zone").agg(
        avg_fare=("fare_amount", "mean"),
        trips=("trip_id", "count")
    ).sort_values("avg_fare", ascending=False).head(5)
    return jsonify([
        {"zone": z, "avg_fare": round(r.avg_fare, 2), "trips": int(r.trips)}
        for z, r in g.iterrows()
    ])

@app.route("/api/live")
def api_live():
    demand = {z: int(np.random.poisson(3)) for z in ZONES}
    return jsonify({
        "time": datetime.now().strftime("%H:%M:%S"),
        "demand": demand,
        "total": sum(demand.values())
    })

@app.route("/api/recent")
def api_recent():
    r = DF.sort_values("pickup_datetime", ascending=False).head(10)
    return jsonify(r[["trip_id","pickup_datetime","pickup_zone",
                     "dropoff_zone","fare_amount","payment_type"]]
                   .astype(str).to_dict(orient="records"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
