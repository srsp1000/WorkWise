"""AWS Lambda Handler for WorkWise Safety Engine.

Uses Mangum ASGI adapter to bridge AWS API Gateway (v1 REST or v2 HTTP API)
and Application Load Balancer (ALB) events to the FastAPI application.

Includes:
- Warm-up ping detection to eliminate cold starts.
- Request tracing and structured CloudWatch logging.
- Graceful exception translation for AWS Lambda runtime.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from mangum import Mangum

from workwise_engine.api import app

# Configure structured logging for AWS CloudWatch
logger = logging.getLogger("workwise.lambda")
logger.setLevel(logging.INFO)

# Initialize Mangum ASGI adapter with API Gateway v2 & v1 support
asgi_handler = Mangum(
    app,
    lifespan="off",  # Lifespan events are disabled for serverless execution speed
    api_gateway_base_path=None,
)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Main AWS Lambda entry point."""
    start_time = time.perf_counter()

    # 1. Handle Lambda warm-up pings (e.g. from CloudWatch Event rules or warm-up plugins)
    if event.get("source") in ("serverless-plugin-warmup", "aws.events", "workwise-warmer"):
        logger.info("Lambda warm-up ping received. Preserving warm container.")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "warm", "message": "WorkWise Lambda container is warm"}),
        }

    # Extract request metadata for CloudWatch observability
    request_id = getattr(context, "aws_request_id", "local-request")
    path = event.get("rawPath") or event.get("path") or "/"
    http_method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "UNKNOWN"
    )

    # Defensively ensure required fields for Mangum API Gateway v2 adapter
    if event.get("version") == "2.0" and "requestContext" in event:
        http_ctx = event["requestContext"].setdefault("http", {})
        http_ctx.setdefault("sourceIp", "127.0.0.1")
        http_ctx.setdefault("userAgent", "aws-client")

    logger.info(

        "Lambda Invocation Started | RequestId=%s | Method=%s | Path=%s",
        request_id,
        http_method,
        path,
    )

    try:
        response = asgi_handler(event, context)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        status_code = response.get("statusCode", 200)
        logger.info(
            "Lambda Invocation Finished | RequestId=%s | Status=%d | Duration=%.2fms",
            request_id,
            status_code,
            duration_ms,
        )
        return response

    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.exception(
            "Unhandled Lambda Exception | RequestId=%s | Duration=%.2fms | Error=%s",
            request_id,
            duration_ms,
            str(exc),
        )
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "detail": "Internal Server Error in WorkWise Lambda runtime.",
                "error": str(exc),
                "request_id": request_id,
            }),
        }
