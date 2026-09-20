import { useEffect, useState } from "react";
import { api } from "../api/client";
type Call = { id: number; floor: number; direction: string; passengers: number; needs_accessible: boolean; status: string; score: string; assigned_car_id: number | null };
type DispatchOut = { call: Call; detail: string };
export default function DispatchPage() {
  const [rows, setRows] = useState<Call[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const reload = () => api<Call[]>("/calls").then(setRows);
  useEffect(() => { reload(); }, []);
  async function run(id: number) {
    setMsg(""); setErr("");
    try {
      const r = await api<DispatchOut>("/dispatch", { method: "POST", body: JSON.stringify({ call_id: id }) });
      setMsg(`呼梯 #${r.call.id} → 轿厢 ${r.call.assigned_car_id}，评分 ${r.call.score}｜${r.detail}`);
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); reload(); }
  }
  const waiting = rows.filter(r => r.status === "waiting");
  return (<>
    <h2>派工</h2>
    <p className="hint">无障碍呼梯仅派无障碍轿厢；普通呼梯派无障碍车时会为已等待的无障碍人数预留容量。</p>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>呼梯</th><th>楼层</th><th>方向</th><th>人数</th><th>无障碍</th><th></th></tr></thead>
    <tbody>{waiting.map(c => <tr key={c.id}><td>#{c.id}</td><td>{c.floor}</td><td>{c.direction}</td><td>{c.passengers}</td>
      <td>{c.needs_accessible ? <span className="a11y-badge" title="需要无障碍轿厢">♿</span> : "—"}</td>
      <td><button onClick={() => run(c.id)}>评分派轿厢</button></td></tr>)}
      {!waiting.length && <tr><td colSpan={6}>暂无待派呼梯</td></tr>}
    </tbody></table>
  </>);
}
