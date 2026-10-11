"""Local test script for AWS Lambda Mangum Handler.

Executes an API Gateway HTTP API v2 event locally through workwise_engine.lambda_handler.handler
to verify serverless payload processing and response serialization without requiring live AWS credentials.
"""

import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workwise_engine.lambda_handler import handler



def main():
    print("=" * 70)
    print("WORKWISE AWS LAMBDA LOCAL INTEGRATION RUNNER")
    print("=" * 70)

    # 1. Test Health Check Event
    print("\n1. Testing GET /api/health through Lambda Handler...")
    health_event = {
        "version": "2.0",
        "routeKey": "GET /api/health",
        "rawPath": "/api/health",
        "rawQueryString": "",
        "headers": {"accept": "application/json"},
        "requestContext": {"http": {"method": "GET", "path": "/api/health"}},
        "isBase64Encoded": False,
    }
    resp = handler(health_event, None)
    print(f"Status Code: {resp['statusCode']}")
    print(f"Response Body: {resp['body']}")
    assert resp["statusCode"] == 200, "Health check failed"

    # 2. Test AI Assistant Status Event
    print("\n2. Testing GET /api/ai/status through Lambda Handler...")
    ai_status_event = {
        "version": "2.0",
        "routeKey": "GET /api/ai/status",
        "rawPath": "/api/ai/status",
        "rawQueryString": "",
        "headers": {"accept": "application/json"},
        "requestContext": {"http": {"method": "GET", "path": "/api/ai/status"}},
        "isBase64Encoded": False,
    }
    resp = handler(ai_status_event, None)
    print(f"Status Code: {resp['statusCode']}")
    body = json.loads(resp["body"])
    print(f"AI Assistant Mode: {body.get('mode')} | Safeguards: {body.get('safeguards_active')}")
    assert resp["statusCode"] == 200, "AI status check failed"

    # 3. Test Scenario Plan Generation Event
    print("\n3. Testing POST /api/scenarios/normal/plan through Lambda Handler...")
    plan_payload = {
        "new_crew": False,
        "tasks": [
            {"id": "concrete", "duration_h": 3},
            {"id": "material_prep", "duration_h": 2},
        ],
    }
    plan_event = {
        "version": "2.0",
        "routeKey": "POST /api/scenarios/normal/plan",
        "rawPath": "/api/scenarios/normal/plan",
        "rawQueryString": "",
        "headers": {"content-type": "application/json", "accept": "application/json"},
        "requestContext": {"http": {"method": "POST", "path": "/api/scenarios/normal/plan"}},
        "body": json.dumps(plan_payload),
        "isBase64Encoded": False,
    }
    resp = handler(plan_event, None)
    print(f"Status Code: {resp['statusCode']}")
    body = json.loads(resp["body"])
    print(f"Scenario: {body.get('scenario_id')}")
    print(f"Top Recommendation: {body.get('top_recommendation')}")
    print(f"Scheduled Tasks Count: {len(body.get('schedule', []))}")
    print(f"Heatmap Rows: {len(body.get('workability_heatmap', []))}")
    assert resp["statusCode"] == 200, "Plan generation failed"
    assert "top_recommendation" in body, "Missing top recommendation"

    print("\n" + "=" * 70)
    print("ALL AWS LAMBDA LOCAL INVOCATION TESTS PASSED (100% OK)")
    print("=" * 70)


if __name__ == "__main__":
    main()
