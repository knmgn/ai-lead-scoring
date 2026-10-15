import sys
import json
import argparse
from pathlib import Path
import httpx

PAYLOADS_FILE = Path(__file__).parent / "sample_payloads.json"
BASE_URL = "http://localhost:8000"


def print_banner(text: str, char="="):
    print("\n" + char * 70)
    print(f" {text}")
    print(char * 70)


def send_lead(key: str, payload: dict):
    print_banner(f"TESTING LEAD: {payload['name']} ({payload['company_domain']}) - Key: {key}")
    print(f"Inbound Message: \"{payload['message'][:100]}...\"")

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{BASE_URL}/webhook/lead", json=payload)
            if resp.status_code != 200:
                print(f"[!] Error: Status {resp.status_code}\n{resp.text}")
                return

            data = resp.json()
            scoring = data["scoring"]
            enrichment = data["enrichment"]
            integrations = data["integrations"]

            # Visual presentation
            tier_badge = {
                "S": "[TIER S 🔥 ULTRA-HIGH PRIORITY]",
                "A": "[TIER A 🚀 HIGH PRIORITY]",
                "B": "[TIER B ℹ️ NURTURE]",
                "C": "[TIER C 💤 DISQUALIFIED]"
            }.get(scoring["score_tier"], scoring["score_tier"])

            print(f"\n>> QUALIFICATION RESULT: {tier_badge}")
            print(f"   Total Score : {scoring['total_score']}/100")
            print(f"   Breakdown   : ICP Fit: {scoring['icp_fit_score']} | Intent: {scoring['intent_urgency_score']} | Budget: {scoring['budget_authority_score']}")
            print(f"   Action      : {scoring['suggested_action']} (Priority: {scoring['routing_priority']})")
            
            print(f"\n>> FIRMOGRAPHIC ENRICHMENT:")
            print(f"   Company     : {enrichment['company_name']} ({enrichment['domain']})")
            print(f"   Industry    : {enrichment['industry']}")
            print(f"   Headcount   : {enrichment['employee_range']} | Revenue: {enrichment['estimated_revenue']}")
            print(f"   Source      : {enrichment['source']}")

            print(f"\n>> AI GENERATED SALES PITCH:")
            print(f"   Subject     : {scoring['recommended_sales_pitch']['subject_line']}")
            print(f"   Value Prop  : {scoring['recommended_sales_pitch']['value_proposition']}")
            print(f"   CTA         : {scoring['recommended_sales_pitch']['recommended_cta']}")

            print(f"\n>> INTEGRATIONS STATUS:")
            print(f"   HubSpot CRM : Synced={integrations['hubspot_synced']} (Contact ID: {integrations['hubspot_contact_id']})")
            print(f"   Slack Alert : Sent={integrations['slack_notified']} (Target: {integrations['slack_channel']})")

    except httpx.ConnectError:
        print("[X] Connection Failed: Could not connect to FastAPI server at http://localhost:8000.")
        print("    Please run the server in another terminal first: uvicorn app.main:app --reload")


def main():
    parser = argparse.ArgumentParser(description="Test Inbound Lead Webhook Pipeline")
    parser.add_argument("--tier", choices=["s", "a", "b", "c", "all"], default="s", help="Lead tier to test")
    args = parser.parse_args()

    if not PAYLOADS_FILE.exists():
        print(f"Payload file not found: {PAYLOADS_FILE}")
        sys.exit(1)

    with open(PAYLOADS_FILE, "r", encoding="utf-8") as f:
        payloads = json.load(f)

    tier_mapping = {
        "s": "enterprise_tier_s",
        "a": "midmarket_tier_a",
        "b": "nurture_tier_b",
        "c": "disqualified_tier_c"
    }

    if args.tier == "all":
        for k, p in payloads.items():
            send_lead(k, p)
    else:
        target_key = tier_mapping[args.tier]
        send_lead(target_key, payloads[target_key])


if __name__ == "__main__":
    main()
