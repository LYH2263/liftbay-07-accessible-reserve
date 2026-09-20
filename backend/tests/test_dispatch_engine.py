from app.services.dispatch_engine import CallRequest, CarState, pick_car, score_car


def test_reject_when_full():
    car = CarState(1, 5, "idle", load=8, capacity=8)
    call = CallRequest(1, 5, "up", passengers=1)
    r = score_car(car, call)
    assert r.accepted is False
    assert "满员" in r.reason


def test_same_direction_beats_far_idle():
    cars = [
        CarState(1, 2, "up", load=1, capacity=10),
        CarState(2, 12, "idle", load=0, capacity=10),
    ]
    call = CallRequest(9, 4, "up", 1)
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 1


def test_closer_idle_wins_when_opposite():
    cars = [
        CarState(1, 10, "down", load=0, capacity=10),
        CarState(2, 3, "idle", load=0, capacity=10),
    ]
    call = CallRequest(3, 2, "up", 1)
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 2


def test_accessible_call_only_accessible_car():
    cars = [
        CarState(1, 1, "idle", load=0, capacity=10),  # 非无障碍，更近
        CarState(2, 6, "idle", load=0, capacity=10, accessible=True),
    ]
    call = CallRequest(1, 2, "up", passengers=1, needs_accessible=True)
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 2


def test_accessible_call_rejected_without_accessible_car():
    car = CarState(1, 1, "idle", load=0, capacity=10)
    call = CallRequest(1, 2, "up", passengers=1, needs_accessible=True)
    r = score_car(car, call)
    assert r.accepted is False
    assert "无障碍" in r.reason
    assert pick_car([car], call) is None


def test_normal_call_cannot_drain_accessible_reservation():
    # 种子场景：无障碍车剩余容量刚好够一笔 waiting 无障碍单，普通呼梯离它更近
    cars = [
        CarState(1, 1, "idle", load=6, capacity=8, accessible=True),  # 剩 2
        CarState(2, 3, "up", load=2, capacity=10),
    ]
    normal = CallRequest(1, 2, "up", passengers=2)  # 距无障碍车 1 层，更近
    # 无预留时普通单会抢走这台更近的无障碍车
    naive = pick_car(cars, normal, reserved_accessible=0)
    assert naive is not None and naive.car_id == 1
    # 有 2 人无障碍 waiting 时，普通单不能把预留吃光，被改派到另一台
    best = pick_car(cars, normal, reserved_accessible=2)
    assert best is not None
    assert best.car_id == 2
    # 无障碍单随后成功派上无障碍车（剩余容量刚好）
    a11y = CallRequest(2, 4, "up", passengers=2, needs_accessible=True)
    best2 = pick_car(cars, a11y)
    assert best2 is not None
    assert best2.car_id == 1


def test_normal_call_rejected_when_only_reserved_car_available():
    cars = [CarState(1, 1, "idle", load=6, capacity=8, accessible=True)]
    normal = CallRequest(1, 2, "up", passengers=2)
    r = score_car(cars[0], normal, reserved_accessible=2)
    assert r.accepted is False
    assert "预留" in r.reason
    assert pick_car(cars, normal, reserved_accessible=2) is None


def test_normal_call_fits_outside_reservation():
    # 剩余容量大于预留量时，普通单仍可使用无障碍车
    car = CarState(1, 1, "idle", load=2, capacity=10, accessible=True)
    normal = CallRequest(1, 2, "up", passengers=2)
    r = score_car(car, normal, reserved_accessible=2)
    assert r.accepted is True
