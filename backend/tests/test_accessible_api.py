"""API 级测试：无障碍派工。

用独立 SQLite 库跑完整应用（含种子），锁住：
- 普通呼梯即使更近，也不得抢光为无障碍 waiting 预留的容量（改派 A1）；
- 无障碍呼梯随后成功派上无障碍车 A3；
- 回放/派工响应可见"预留"原因；
- 轿厢无障碍标记可维护且持久。
"""

import os
import tempfile

os.environ["DATABASE_URL"] = (
    f"sqlite:///{tempfile.mkdtemp(prefix='liftbay-test-')}/test.db"
)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_seed_scenario_normal_call_cannot_steal_reserved_accessible_car():
    with TestClient(app) as client:
        cars = {c["label"]: c for c in client.get("/api/cars").json()}
        assert cars["A3"]["accessible"] is True
        assert all(c["accessible"] is False for l, c in cars.items() if l != "A3")

        calls = client.get("/api/calls").json()
        normal = next(
            c for c in calls
            if c["status"] == "waiting" and not c["needs_accessible"] and c["floor"] == 1
        )
        acc = next(c for c in calls if c["status"] == "waiting" and c["needs_accessible"])
        # 种子：A3 剩余容量刚好够这笔无障碍 waiting
        assert acc["passengers"] == cars["A3"]["capacity"] - cars["A3"]["load"]

        # 普通呼梯距 A3 更近，但不得抢光预留 → 改派 A1
        r = client.post("/api/dispatch", json={"call_id": normal["id"]})
        assert r.status_code == 200
        got = r.json()
        assert got["assigned_car_id"] == cars["A1"]["id"]
        assert "预留" in got["detail"]

        # 无障碍单随后成功派上无障碍车
        r = client.post("/api/dispatch", json={"call_id": acc["id"]})
        assert r.status_code == 200
        got = r.json()
        assert got["status"] == "assigned"
        assert got["assigned_car_id"] == cars["A3"]["id"]

        # 回放可见因预留改派与无障碍派工
        logs = client.get("/api/replay").json()
        assert any("预留" in l["detail"] and l["call_id"] == normal["id"] for l in logs)
        assert any("无障碍" in l["detail"] and l["call_id"] == acc["id"] for l in logs)


def test_car_accessible_toggle_persists_and_call_registration_flag():
    with TestClient(app) as client:
        cars = client.get("/api/cars").json()
        a2 = next(c for c in cars if c["label"] == "A2")

        r = client.patch(f"/api/cars/{a2['id']}", json={"accessible": True})
        assert r.status_code == 200
        assert r.json()["accessible"] is True
        # 再次读取（相当于再次进入轿厢页）标记仍在
        again = client.get("/api/cars").json()
        assert next(c for c in again if c["label"] == "A2")["accessible"] is True

        r = client.patch(f"/api/cars/{a2['id']}", json={"accessible": False})
        assert r.json()["accessible"] is False

        buildings = client.get("/api/buildings").json()
        r = client.post(
            "/api/calls",
            json={
                "building_id": buildings[0]["id"],
                "floor": 3,
                "direction": "up",
                "passengers": 1,
                "needs_accessible": True,
            },
        )
        assert r.status_code == 200
        assert r.json()["needs_accessible"] is True
