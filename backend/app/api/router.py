from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
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
    DispatchOut,
    DispatchRequest,
    LogOut,
)
from app.services.dispatch_engine import (
    REASON_RESERVED,
    CallRequest,
    CarState,
    congestion_by_floor,
    evaluate,
    pick_car,
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


@api_router.post("/dispatch", response_model=DispatchOut)
def dispatch(body: DispatchRequest, db: Session = Depends(get_db)):
    ticket = db.get(CallTicket, body.call_id)
    if not ticket:
        raise HTTPException(404, "呼梯不存在")
    if ticket.status != "waiting":
        raise HTTPException(400, "呼梯已处理")
    car_rows = db.scalars(
        select(ElevatorCar).where(ElevatorCar.building_id == ticket.building_id)
    ).all()
    cars = [
        CarState(c.id, c.floor, c.direction, c.load, c.capacity, c.accessible)
        for c in car_rows
    ]
    # 为其他 waiting 无障碍呼梯预留的座位数（本单若是无障碍单则不为自己预留）
    reserved = sum(
        c.passengers
        for c in db.scalars(
            select(CallTicket).where(
                CallTicket.building_id == ticket.building_id,
                CallTicket.status == "waiting",
                CallTicket.needs_accessible.is_(True),
                CallTicket.id != ticket.id,
            )
        ).all()
    )
    call = CallRequest(
        ticket.id,
        ticket.floor,
        ticket.direction,
        ticket.passengers,
        ticket.needs_accessible,
    )
    results = evaluate(cars, call, reserved)
    best = pick_car(cars, call, reserved)
    labels = {c.id: c.label for c in car_rows}
    if best is None:
        reasons = "；".join(
            f"{labels[r.car_id]}：{r.reason}" for r in results if not r.accepted
        ) or "楼内无轿厢"
        detail = f"拒绝派工 — {reasons}"[:240]
        db.add(DispatchLog(call_id=ticket.id, car_id=None, detail=detail))
        ticket.status = "rejected"
        db.commit()
        db.refresh(ticket)
        msg = "无可用无障碍轿厢" if ticket.needs_accessible else "无可用轿厢（满员或无障碍预留）"
        raise HTTPException(409, msg)
    car = db.get(ElevatorCar, best.car_id)
    assert car
    ticket.status = "assigned"
    ticket.assigned_car_id = car.id
    ticket.score = f"{best.score:.1f}"
    car.load += ticket.passengers
    car.floor = ticket.floor
    car.direction = ticket.direction
    detail = f"派予 {car.label}，评分 {best.score:.1f}（同向/距离综合）"
    if ticket.needs_accessible:
        detail += "；无障碍呼梯"
    skipped = [
        labels[r.car_id]
        for r in results
        if not r.accepted and r.reason == REASON_RESERVED
    ]
    if skipped:
        detail += f"；跳过 {'、'.join(skipped)}（无障碍预留）"
    db.add(DispatchLog(call_id=ticket.id, car_id=car.id, detail=detail[:240]))
    db.commit()
    db.refresh(ticket)
    return DispatchOut(call=CallOut.model_validate(ticket), detail=detail)


@api_router.get("/replay", response_model=list[LogOut])
def replay(db: Session = Depends(get_db)):
    return db.scalars(select(DispatchLog).order_by(DispatchLog.id.desc())).all()


@api_router.get("/congestion", response_model=list[CongestionFloor])
def congestion(db: Session = Depends(get_db)):
    waiting = db.scalars(select(CallTicket).where(CallTicket.status == "waiting")).all()
    counts = congestion_by_floor(
        [CallRequest(c.id, c.floor, c.direction, c.passengers) for c in waiting]
    )
    return [
        CongestionFloor(floor=f, passengers=p)
        for f, p in sorted(counts.items(), key=lambda x: -x[1])
    ]
