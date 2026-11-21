"""Integration Tests for FastAPI Endpoints"""
import time
import pytest
from fastapi.testclient import TestClient


def test_full_api_workflow(client: TestClient):
    # 1. Register
    reg_payload = {
        "email": "quant_trader@example.com",
        "password": "StrongPassword123!",
        "workspace_name": "Alpha Research Lab",
    }
    reg_resp = client.post("/auth/register", json=reg_payload)
    assert reg_resp.status_code == 200, reg_resp.text
    data = reg_resp.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Me
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "quant_trader@example.com"
    assert len(me_data["workspaces"]) >= 1
    workspace_id = me_data["workspaces"][0]["id"]

    # 3. Create Strategy
    strat_payload = {
        "name": "XAUUSD Mean Reversion",
        "description": "RSI mean reversion with volatility ATR stops",
        "strategy_type": "rsi",
        "initial_parameters": {
            "rsi_period": 14,
            "oversold": 30.0,
            "overbought": 70.0,
            "risk_per_trade_pct": 0.01,
            "risk_reward_ratio": 2.0,
        },
    }
    strat_resp = client.post("/strategies/", json=strat_payload, headers=headers)
    assert strat_resp.status_code == 200
    strat_data = strat_resp.json()
    strat_id = strat_data["id"]
    version_id = strat_data["latest_version"]["id"]
    code_hash = strat_data["latest_version"]["code_hash"]
    assert code_hash is not None

    # 4. Bump Immutable Version
    v2_payload = {
        "parameters": {
            "rsi_period": 21,
            "oversold": 28.0,
            "overbought": 72.0,
            "risk_per_trade_pct": 0.015,
            "risk_reward_ratio": 2.5,
        }
    }
    v2_resp = client.post(f"/strategies/{strat_id}/versions", json=v2_payload, headers=headers)
    assert v2_resp.status_code == 200
    v2_data = v2_resp.json()
    assert v2_data["version_number"] == 2
    assert v2_data["code_hash"] != code_hash

    # 5. Launch Async Backtest
    bt_payload = {
        "strategy_version_id": version_id,
        "symbol": "XAUUSD",
        "timeframe": "1H",
        "initial_capital": 10000.0,
        "slippage_bps": 1.0,
        "commission_per_trade": 1.0,
        "spread_pips": 0.2,
        "risk_per_trade_pct": 0.01,
    }
    bt_resp = client.post("/backtests/run", json=bt_payload, headers=headers)
    assert bt_resp.status_code == 200
    run_job = bt_resp.json()
    run_id = run_job["job_id"]

    # 6. Poll Status until COMPLETED
    max_wait = 10
    completed = False
    for _ in range(max_wait):
        status_resp = client.get(f"/backtests/{run_id}/status", headers=headers)
        assert status_resp.status_code == 200
        st = status_resp.json()["status"]
        if st == "COMPLETED":
            completed = True
            break
        elif st == "FAILED":
            pytest.fail(f"Backtest failed: {status_resp.json().get('error_message')}")
        time.sleep(0.5)

    assert completed is True

    # 7. Get Tearsheet
    ts_resp = client.get(f"/backtests/{run_id}/tearsheet", headers=headers)
    assert ts_resp.status_code == 200
    ts_data = ts_resp.json()
    assert "metrics" in ts_data
    assert ts_data["metrics"]["total_trades"] > 0
    assert len(ts_data["recent_trades"]) > 0
    assert len(ts_data["equity_curve"]) > 0

    # 8. Test AI Hypothesis-to-Spec Endpoint
    ai_spec_resp = client.post(
        "/ai/hypothesis-to-spec",
        json={"prompt": "Enter long when RSI drops below 25 on 1H gold, stop loss 1.5 ATR and take profit 3 RR"},
        headers=headers,
    )
    assert ai_spec_resp.status_code == 200
    spec_data = ai_spec_resp.json()
    assert spec_data["strategy_type"] == "rsi"
    assert spec_data["parameters"]["oversold"] == 25.0
    assert spec_data["parameters"]["risk_reward_ratio"] == 3.0

    # 9. Test AI Backtest Critique Endpoint
    ai_crit_resp = client.post(f"/ai/critique-backtest/{run_id}", headers=headers)
    assert ai_crit_resp.status_code == 200
    crit_data = ai_crit_resp.json()
    assert crit_data["run_id"] == str(run_id)
    assert "overfitting_analysis" in crit_data
    assert "drawdown_critique" in crit_data

    # 10. Check Billing Usage Recording
    bill_resp = client.get("/billing/usage", headers=headers)
    assert bill_resp.status_code == 200
    bill_data = bill_resp.json()
    assert bill_data["total_records"] >= 2  # backtest + ai calls
