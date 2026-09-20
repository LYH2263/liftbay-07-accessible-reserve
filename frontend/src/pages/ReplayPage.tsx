import { useEffect, useState } from "react";
import { api } from "../api/client";
type Log = { id: number; call_id: number; car_id: number | null; detail: string; created_at: string };
export default function ReplayPage() {
  const [rows, setRows] = useState<Log[]>([]);
  useEffect(() => { api<Log[]>("/replay").then(setRows); }, []);
  return (<>
    <h2>回放</h2>
    <table className="table"><thead><tr><th>时间</th><th>呼梯</th><th>轿厢</th><th>详情</th></tr></thead>
    <tbody>{rows.map(l => {
      const reserved = l.detail.includes("预留");
      const accessible = l.detail.includes("无障碍");
      return <tr key={l.id}><td className="mono">{new Date(l.created_at).toLocaleString()}</td><td>#{l.call_id}</td><td>{l.car_id ?? "—"}</td>
        <td>{reserved && <span className="tag tag--amber">预留</span>}{" "}{accessible && !reserved && <span className="tag">无障碍</span>}{" "}{l.detail}</td></tr>;
    })}</tbody></table>
  </>);
}
