from app.services.dispatch_engine import (
    REASON_NOT_ACCESSIBLE,
    REASON_RESERVED,
    CallRequest,
    CarState,
    pick_car,
    score_car,
)


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


def test_accessible_call_rejects_non_accessible_car():
    car = CarState(1, 1, "idle", load=0, capacity=10, accessible=False)
    call = CallRequest(1, 1, "up", 1, needs_accessible=True)
    r = score_car(car, call)
    assert r.accepted is False
    assert r.reason == REASON_NOT_ACCESSIBLE


def test_accessible_call_picks_accessible_car_even_if_farther():
    cars = [
        CarState(1, 1, "idle", load=0, capacity=10, accessible=False),
        CarState(2, 9, "down", load=0, capacity=10, accessible=True),
    ]
    call = CallRequest(5, 2, "up", 1, needs_accessible=True)
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 2


def test_normal_call_cannot_eat_reserved_accessible_seats():
    # 无障碍车剩余 3 席，全部为 waiting 无障碍人数预留；普通 3 人单不得抢光
    cars = [
        CarState(1, 1, "idle", load=5, capacity=8, accessible=True, reserved=3),
        CarState(2, 3, "up", load=2, capacity=10),
    ]
    call = CallRequest(7, 1, "up", 3)
    r = score_car(cars[0], call)
    assert r.accepted is False
    assert r.reason == REASON_RESERVED
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 2


def test_normal_call_fits_exactly_up_to_reservation_boundary():
    # 普通 3 人上后剩余恰好等于预留 3 席：允许
    car = CarState(1, 1, "idle", load=2, capacity=8, accessible=True, reserved=3)
    call = CallRequest(1, 1, "up", 3)
    r = score_car(car, call)
    assert r.accepted is True


def test_normal_call_uses_accessible_car_when_spare_beyond_reserve():
    cars = [
        CarState(1, 1, "idle", load=0, capacity=10, accessible=True, reserved=2),
        CarState(2, 9, "down", load=0, capacity=10),
    ]
    call = CallRequest(3, 1, "up", 2)
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 1


def test_accessible_call_may_use_its_own_reserved_seats():
    # 无障碍单可以使用为其预留的容量（坐满整台车）
    car = CarState(1, 1, "idle", load=5, capacity=8, accessible=True, reserved=3)
    call = CallRequest(1, 2, "up", 3, needs_accessible=True)
    r = score_car(car, call)
    assert r.accepted is True
