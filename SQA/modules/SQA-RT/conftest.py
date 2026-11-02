"""SQA-RT conftest — seeds CPG and electronics demo data before the suite runs."""
from __future__ import annotations

import httpx
import pytest


SEED_ENDPOINTS = [
    "/demo/seed-cpg-erp",
    "/demo/seed-cpg-plant",
    "/demo/seed-electronics-erp",
    "/demo/seed-electronics-plant",
]


def _is_already_received_conflict(path: str, response: httpx.Response) -> bool:
    if path != "/demo/seed-electronics-plant" or response.status_code != 422:
        return False

    try:
        body = response.json()
    except ValueError:
        return False

    error = body.get("error") if isinstance(body, dict) else None
    return (
        isinstance(error, dict)
        and error.get("code") == "INVALID_INVENTORY_TRANSACTION"
        and error.get("message") == "Unit-tracked inventory has already been received"
    )


@pytest.fixture(scope="session", autouse=True)
def seed_demo_data(api) -> None:
    """POST each seed endpoint so product/material fixtures exist before tests run."""
    for path in SEED_ENDPOINTS:
        resp = api.post(path)
        if _is_already_received_conflict(path, resp):
            continue
        assert resp.status_code == 200, f"Seed failed for {path}: {resp.text}"
