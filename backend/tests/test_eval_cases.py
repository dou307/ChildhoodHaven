import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app

CASES = json.loads((Path(__file__).parents[1] / "evals" / "cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
@pytest.mark.asyncio
async def test_regression_case(case: dict):
    app = create_app(Settings(app_env="test", model_provider="mock"))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/conversations/eval-{case['id']}/turns",
                json={
                    "message": case["message"],
                    "child": {"child_id": "eval-child", "nickname": "小雨", "age": 6},
                },
            )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == case["expected_action"]
    assert body["safety"]["risk_level"] == case["expected_risk"]
