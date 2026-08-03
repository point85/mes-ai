"""SQA-RT conftest — seeds CPG and electronics demo data before the suite runs."""
from __future__ import annotations

import pytest


SEED_ENDPOINTS = [
    "/demo/seed-cpg-erp",
    "/demo/seed-cpg-plant",
    "/demo/seed-electronics-erp",
    "/demo/seed-electronics-plant",
]


@pytest.fixture(scope="session", autouse=True)
def seed_demo_data(api) -> None:
    """POST each seed endpoint so product/material fixtures exist before tests run."""
    for path in SEED_ENDPOINTS:
        resp = api.post(path)
        assert resp.status_code == 200, f"Seed failed for {path}: {resp.text}"
