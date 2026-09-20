"""Elevator dispatch: same-direction preference + floor distance; reject if car full.

无障碍规则：
- 标记 needs_accessible 的呼梯只能派给 accessible 轿厢。
- 普通呼梯仍可派无障碍轿厢，但每台无障碍车会为「已 waiting 的无障碍人数」
  预留容量（reserved_accessible）：普通呼梯若会把剩余空间吃到低于预留量，
  则在该车上被拒绝，避免随后的无障碍单失败。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CarState:
    car_id: int
    floor: int
    direction: str  # "up" | "down" | "idle"
    load: int
    capacity: int
    accessible: bool = False


@dataclass(frozen=True)
class CallRequest:
    call_id: int
    floor: int
    direction: str  # desired travel after boarding
    passengers: int = 1
    needs_accessible: bool = False


@dataclass(frozen=True)
class ScoreResult:
    car_id: int
    score: float
    accepted: bool
    reason: str


SAME_DIR_BONUS = 40.0
IDLE_BONUS = 20.0
DISTANCE_WEIGHT = 5.0

REASON_FULL = "轿厢满员"
REASON_NOT_ACCESSIBLE = "非无障碍轿厢"
REASON_RESERVED = "为无障碍呼梯预留容量"


def score_car(car: CarState, call: CallRequest, reserved_accessible: int = 0) -> ScoreResult:
    if call.needs_accessible and not car.accessible:
        return ScoreResult(car.car_id, -1e9, False, REASON_NOT_ACCESSIBLE)

    if car.load + call.passengers > car.capacity:
        return ScoreResult(car.car_id, -1e9, False, REASON_FULL)

    if (
        not call.needs_accessible
        and car.accessible
        and reserved_accessible > 0
        and car.load + call.passengers + reserved_accessible > car.capacity
    ):
        return ScoreResult(car.car_id, -1e9, False, REASON_RESERVED)

    distance = abs(car.floor - call.floor)
    score = 100.0 - distance * DISTANCE_WEIGHT

    if car.direction == "idle":
        score += IDLE_BONUS
    elif car.direction == call.direction:
        # approaching or already going same way
        if car.direction == "up" and car.floor <= call.floor:
            score += SAME_DIR_BONUS
        elif car.direction == "down" and car.floor >= call.floor:
            score += SAME_DIR_BONUS
        else:
            score -= 15.0  # same dir but already passed
    else:
        score -= 25.0

    return ScoreResult(car.car_id, score, True, "ok")


def evaluate(
    cars: list[CarState], call: CallRequest, reserved_accessible: int = 0
) -> list[ScoreResult]:
    return [score_car(c, call, reserved_accessible) for c in cars]


def pick_car(
    cars: list[CarState], call: CallRequest, reserved_accessible: int = 0
) -> ScoreResult | None:
    accepted = [r for r in evaluate(cars, call, reserved_accessible) if r.accepted]
    if not accepted:
        return None
    return max(accepted, key=lambda r: r.score)


def congestion_by_floor(calls: list[CallRequest]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for c in calls:
        counts[c.floor] = counts.get(c.floor, 0) + c.passengers
    return counts
