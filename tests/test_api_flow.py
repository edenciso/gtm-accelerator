#!/usr/bin/env python3
"""
Integration test script for GTM Accelerator Value Sprint API.
Usage:
  export API_URL=https://xxxxx.execute-api.us-east-1.amazonaws.com/dev
  export AUTH_TOKEN=<your-cognito-jwt>
  python tests/test_api_flow.py
"""
import os, sys, json, time, urllib.request, urllib.error

API_URL = os.environ.get("API_URL", "http://localhost:3000")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")

def req(method, path, data=None):
    url = f"{API_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            result = json.loads(resp.read().decode())
            print(f"  OK {method} {path} -> {resp.status}")
            return result
    except urllib.error.HTTPError as e:
        print(f"  FAIL {method} {path} -> {e.code}: {e.read().decode()[:200]}")
        return None

def run():
    print("=== GTM Accelerator Sprint - API Flow Test ===\n")
    print("[1] Create engagement...")
    r = req("POST", "/engagements", {"company_name":"TestCo AI","contact_email":"t@t.ai","stage":"series_b"})
    if not r: return
    eid = r["engagement_id"]
    print(f"    ID: {eid}")

    from sample_data.demo_data import SAMPLE_GTM_DATA, SAMPLE_SALES_DATA, SAMPLE_FINANCIALS, SAMPLE_TOOLS
    print("[2] Ingest GTM data...")
    req("POST", f"/engagements/{eid}/data/gtm", SAMPLE_GTM_DATA)
    print("[3] Ingest sales data...")
    req("POST", f"/engagements/{eid}/data/sales", SAMPLE_SALES_DATA)
    print("[4] Ingest financials...")
    req("POST", f"/engagements/{eid}/data/financials", SAMPLE_FINANCIALS)
    print("[5] Ingest tools...")
    req("POST", f"/engagements/{eid}/data/tools", SAMPLE_TOOLS)
    print("[6] Generate report (this takes 2-5 min)...")
    r = req("POST", f"/engagements/{eid}/report/generate")
    if r:
        print(f"    Report ID: {r.get('report_id')}")
        print(f"    Status: {r.get('status')}")
        print(f"    Score: {r.get('report_summary',{}).get('scorecard_overall_score')}")
    print("\n=== Demo endpoint (one-click) ===")
    print("[7] POST /demo/run ...")
    r = req("POST", "/demo/run", {})
    if r:
        print(f"    Score: {r.get('report_summary',{}).get('scorecard_score')}")
    print("\nDone.")

if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    run()
