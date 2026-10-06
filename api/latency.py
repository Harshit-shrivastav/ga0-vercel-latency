import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

TELEMETRY_PATH = os.path.join(os.path.dirname(__file__), "telemetry.json")


def percentile(data, q):
    # Exact port of the exam's ns(): linear-interpolation percentile
    e = sorted(data)
    r = (len(e) - 1) * q
    n = int(r // 1)
    frac = r - n
    if n + 1 < len(e):
        return e[n] + frac * (e[n + 1] - e[n])
    return e[n]


def compute_regions(records, regions, threshold):
    out = []
    for region in regions:
        rows = [r for r in records if r["region"] == region]
        if not rows:
            continue
        lats = [r["latency_ms"] for r in rows]
        ups = [r["uptime_pct"] for r in rows]
        out.append({
            "region": region,
            "avg_latency": round(sum(lats) / len(lats), 2),
            "p95_latency": round(percentile(lats, 0.95), 2),
            "avg_uptime": round(sum(ups) / len(ups), 3),
            "breaches": sum(1 for v in lats if v > threshold),
        })
    return out


class handler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            body = {}
        regions = body.get("regions", [])
        threshold = body.get("threshold_ms", 180)
        try:
            with open(TELEMETRY_PATH) as f:
                records = json.load(f)
        except Exception as e:
            records = []
        result = {"regions": compute_regions(records, regions, threshold)}
        payload = json.dumps(result).encode()
        self.send_response(200)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass
