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
  useEffect(() => {
    api<Car[]>("/cars").then(setCars);
    api<Call[]>("/calls").then(setCalls);
    api<B[]>("/buildings").then(bs => { if (bs[0]) setFloors(bs[0].floors); });
  }, []);
  const callFloors = useMemo(() => new Set(calls.filter(c => c.status === "waiting").map(c => c.floor)), [calls]);
  const levels = useMemo(() => Array.from({ length: floors }, (_, i) => i + 1), [floors]);
  async function toggleA11y(car: Car) {
    setErr("");
    try {
      const updated = await api<Car>(`/cars/${car.id}`, { method: "PATCH", body: JSON.stringify({ accessible: !car.accessible }) });
      setCars(cs => cs.map(c => (c.id === updated.id ? updated : c)));
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>轿厢井道</h2>
    {err && <div className="err">{err}</div>}
    <div className="shaft-wrap">
      {cars.map(car => (
        <div className="shaft" key={car.id}>
          <h3>{car.label} · {car.load}/{car.capacity}</h3>
          <label className="check-a11y car-a11y" title="无障碍呼梯只会派给标记了无障碍的轿厢">
            <input type="checkbox" checked={car.accessible} onChange={() => toggleA11y(car)} />
            ♿ 无障碍
          </label>
          {levels.map(f => (
            <div key={f} className={`floor-slot ${car.floor === f ? "has-car" : ""} ${callFloors.has(f) ? "has-call" : ""}`}>
              {car.floor === f ? car.direction : f}
            </div>
          ))}
        </div>
      ))}
    </div>
  </>);
}
