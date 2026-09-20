from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Building, CallTicket, DispatchLog, ElevatorCar
from app.schemas.schemas import (
    BuildingOut,
    CallCreate,
    CallOut,
    CarOut,
    CarUpdate,
    CongestionFloor,
    DispatchRequest,
    DispatchResult,
    LogOut,
)
from app.services.dispatch_engine import (
    REASON_RESERVED,
    CallRequest,
    CarState,
    congestion_by_floor,
    evaluate_cars,
)

api_router = APIRouter()


@api_router.get("/health")
def health():
    return {"status": "ok"}


@api_router.get("/buildings", response_model=list[BuildingOut])
def buildings(db: Session = Depends(get_db)):
    return db.scalars(select(Building).order_by(Building.id)).all()


@api_router.get("/cars", response_model=list[CarOut])
def cars(db: Session = Depends(get_db)):
    return db.scalars(select(ElevatorCar).order_by(ElevatorCar.id)).all()


@api_router.patch("/cars/{car_id}", response_model=CarOut)
def update_car(car_id: int, body: CarUpdate, db: Session = Depends(get_db)):
    car = db.get(ElevatorCar, car_id)
    if not car:
        raise HTTPException(404, "轿厢不存在")
    car.accessible = body.accessible
    db.commit()
    db.refresh(car)
    return car


@api_router.get("/calls", response_model=list[CallOut])
def calls(db: Session = Depends(get_db)):
    return db.scalars(select(CallTicket).order_by(CallTicket.id.desc())).all()


@api_router.post("/calls", response_model=CallOut)
def create_call(body: CallCreate, db: Session = Depends(get_db)):
    b = db.get(Building, body.building_id)
    if not b:
        raise HTTPException(404, "楼栋不存在")
    if body.floor > b.floors:
        raise HTTPException(400, "楼层超出")
    if body.direction not in ("up", "down"):
        raise HTTPException(400, "方向无效")
    ticket = CallTicket(
        building_id=body.building_id,
        floor=body.floor,
        direction=body.direction,
        passengers=body.passengers,
        needs_accessible=body.needs_accessible,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def _reserved_accessible_seats(db: Session, building_id: int) -> int:
    """Seats to hold on each accessible car for already-waiting accessible calls."""
    return db.scalar(
        select(func.coalesce(func.sum(CallTicket.passengers), 0)).where(
            CallTicket.building_id == building_id,
            CallTicket.status == "waiting",
            CallTicket.needs_accessible.is_(True),
        )
    ) or 0


@api_router.post("/dispatch", response_model=DispatchResult)
def dispatch(body: DispatchRequest, db: Session = Depends(get_db)):
    ticket = db.get(CallTicket, body.call_id)
    if not ticket:
        raise HTTPException(404, "呼梯不存在")
    if ticket.status != "waiting":
        raise HTTPException(400, "呼梯已处理")
    car_rows = db.scalars(
        select(ElevatorCar).where(ElevatorCar.building_id == ticket.building_id)
    ).all()
    reserved = _reserved_accessible_seats(db, ticket.building_id)
    cars = [
        CarState(
            c.id,
            c.floor,
            c.direction,
            c.load,
            c.capacity,
            c.accessible,
            reserved if c.accessible else 0,
        )
        for c in car_rows
    ]
    call = CallRequest(
        ticket.id,
        ticket.floor,
        ticket.direction,
        ticket.passengers,
        ticket.needs_accessible,
    )
    results = evaluate_cars(cars, call)
    accepted = [r for r in results if r.accepted]
    if not accepted:
        reasons = "；".join(sorted({r.reason for r in results}))
        detail = f"拒绝派工：{reasons}"
        db.add(DispatchLog(call_id=ticket.id, car_id=None, detail=detail))
        ticket.status = "rejected"
        db.commit()
        raise HTTPException(409, detail)
    best = max(accepted, key=lambda r: r.score)
    car = db.get(ElevatorCar, best.car_id)
    assert car
    label_by_id = {c.id: c.label for c in car_rows}
    blocked = [
        label_by_id[r.car_id]
        for r in results
        if not r.accepted and r.reason == REASON_RESERVED
    ]
    parts = [f"派予 {car.label}，评分 {best.score:.1f}"]
    if ticket.needs_accessible:
        parts.append("无障碍呼梯")
    if blocked:
        parts.append(f"{'、'.join(blocked)} 因无障碍容量预留跳过")
    detail = "；".join(parts)
    ticket.status = "assigned"
    ticket.assigned_car_id = car.id
    ticket.score = f"{best.score:.1f}"
    car.load += ticket.passengers
    car.floor = ticket.floor
    car.direction = ticket.direction
    db.add(DispatchLog(call_id=ticket.id, car_id=car.id, detail=detail))
    db.commit()
    db.refresh(ticket)
    out = CallOut.model_validate(ticket)
    return DispatchResult(**out.model_dump(), detail=detail)


@api_router.get("/replay", response_model=list[LogOut])
def replay(db: Session = Depends(get_db)):
    return db.scalars(select(DispatchLog).order_by(DispatchLog.id.desc())).all()


@api_router.get("/congestion", response_model=list[CongestionFloor])
def congestion(db: Session = Depends(get_db)):
    waiting = db.scalars(select(CallTicket).where(CallTicket.status == "waiting")).all()
    counts = congestion_by_floor(
        [
            CallRequest(c.id, c.floor, c.direction, c.passengers, c.needs_accessible)
            for c in waiting
        ]
    )
    return [
        CongestionFloor(floor=f, passengers=p)
        for f, p in sorted(counts.items(), key=lambda x: -x[1])
    ]
