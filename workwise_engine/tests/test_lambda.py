"""Unit tests for AWS Lambda Mangum handler."""

import json

from workwise_engine.lambda_handler import handler


def test_lambda_warmup_event():
    event = {"source": "workwise-warmer"}
    response = handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "warm"


def test_lambda_http_api_health_check():
    event = {
        "version": "2.0",
        "routeKey": "GET /api/health",
        "rawPath": "/api/health",
        "rawQueryString": "",
        "headers": {
            "accept": "application/json",
            "host": "api.workwise.internal",
        },
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/api/health",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest-client",
            },
        },
        "isBase64Encoded": False,
    }

    response = handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "ok"


def test_lambda_http_api_tasks():
    event = {
        "version": "2.0",
        "routeKey": "GET /api/tasks",
        "rawPath": "/api/tasks",
        "rawQueryString": "",
        "headers": {
            "accept": "application/json",
            "host": "api.workwise.internal",
        },
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/api/tasks",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest-client",
            },
        },
        "isBase64Encoded": False,
    }

    response = handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "tasks" in body
    assert "concrete" in body["tasks"]


def test_lambda_http_api_plan_generation():
    payload = {
        "new_crew": False,
        "tasks": [
            {"id": "concrete", "duration_h": 3},
            {"id": "material_prep", "duration_h": 2},
        ],
    }

    event = {
        "version": "2.0",
        "routeKey": "POST /api/scenarios/normal/plan",
        "rawPath": "/api/scenarios/normal/plan",
        "rawQueryString": "",
        "headers": {
            "accept": "application/json",
            "content-type": "application/json",
            "host": "api.workwise.internal",
        },
        "requestContext": {
            "http": {
                "method": "POST",
                "path": "/api/scenarios/normal/plan",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest-client",
            },
        },
        "body": json.dumps(payload),
        "isBase64Encoded": False,
    }

    response = handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["scenario_id"] == "normal"
    assert len(body["schedule"]) == 2
    assert "workability_heatmap" in body
    assert "top_recommendation" in body
