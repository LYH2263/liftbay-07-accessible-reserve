"""Elevator dispatch: same-direction preference + floor distance; reject if car full.

Accessibility rules:
- A call marked ``needs_accessible`` may only board an ``accessible`` car.
- A regular call may still use an accessible car, but it must not eat into the
  capacity reserved for already-waiting accessible passengers (``reserved``).
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
    reserved: int = 0  # seats held for waiting accessible passengers


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


def score_car(car: CarState, call: CallRequest) -> ScoreResult:
    if call.needs_accessible and not car.accessible:
        return ScoreResult(car.car_id, -1e9, False, REASON_NOT_ACCESSIBLE)
    if car.load + call.passengers > car.capacity:
        return ScoreResult(car.car_id, -1e9, False, REASON_FULL)
    if car.accessible and not call.needs_accessible:
        # Regular calls may board, but the seats reserved for waiting
        # accessible passengers must still be free after boarding.
        if car.load + call.passengers > car.capacity - car.reserved:
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


def evaluate_cars(cars: list[CarState], call: CallRequest) -> list[ScoreResult]:
    return [score_car(c, call) for c in cars]


def pick_car(cars: list[CarState], call: CallRequest) -> ScoreResult | None:
    accepted = [r for r in evaluate_cars(cars, call) if r.accepted]
    if not accepted:
        return None
    return max(accepted, key=lambda r: r.score)


def congestion_by_floor(calls: list[CallRequest]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for c in calls:
        counts[c.floor] = counts.get(c.floor, 0) + c.passengers
    return counts
