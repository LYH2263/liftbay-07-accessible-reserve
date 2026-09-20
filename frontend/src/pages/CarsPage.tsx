import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
type Car = { id: number; label: string; floor: number; direction: string; load: number; capacity: number; accessible: boolean };
type Call = { id: number; floor: number; status: string };
type B = { floors: number };
export default function CarsPage() {
  const [cars, setCars] = useState<Car[]>([]);
  const [calls, setCalls] = useState<Call[]>([]);
  const [floors, setFloors] = useState(18);
  const [err, setErr] = useState("");
  const reloadCars = () => api<Car[]>("/cars").then(setCars);
  useEffect(() => {
    reloadCars();
    api<Call[]>("/calls").then(setCalls);
    api<B[]>("/buildings").then(bs => { if (bs[0]) setFloors(bs[0].floors); });
  }, []);
  async function toggle(car: Car) {
    setErr("");
    try {
      await api(`/cars/${car.id}`, { method: "PATCH", body: JSON.stringify({ accessible: !car.accessible }) });
      reloadCars();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  const callFloors = useMemo(() => new Set(calls.filter(c => c.status === "waiting").map(c => c.floor)), [calls]);
  const levels = useMemo(() => Array.from({ length: floors }, (_, i) => i + 1), [floors]);
  return (<>
    <h2>轿厢井道</h2>
    {err && <div className="err">{err}</div>}
    <div className="shaft-wrap">
      {cars.map(car => (
        <div className="shaft" key={car.id}>
          <h3>{car.accessible && "♿ "}{car.label} · {car.load}/{car.capacity}</h3>
          {levels.map(f => (
            <div key={f} className={`floor-slot ${car.floor === f ? "has-car" : ""} ${callFloors.has(f) ? "has-call" : ""}`}>
              {car.floor === f ? car.direction : f}
            </div>
          ))}
          <button className="car-acc-toggle" onClick={() => toggle(car)}>
            {car.accessible ? "取消无障碍" : "标记无障碍"}
          </button>
        </div>
      ))}
    </div>
  </>);
}
