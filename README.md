# LiftBay

电梯派梯：同向优先与楼层距离评分，轿厢满员拒绝派工。

无障碍派工：呼梯可标记"需要无障碍轿厢"，此类呼梯只派给已标记无障碍的轿厢；普通呼梯仍可派无障碍轿厢，但不得占用为已等待无障碍人数预留的容量（预留 = 当前 waiting 的无障碍人数之和），因预留被跳过或拒绝会写入派工日志，可在派工页与回放页查看。

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4200 |
| API | http://localhost:9200 |
| API 文档 | http://localhost:9200/docs |
| Postgres | localhost:5443 |

健康检查：`GET http://localhost:9200/api/health`

## 页面

- `/buildings` — 楼栋
- `/cars` — 轿厢
- `/calls` — 呼梯
- `/dispatch` — 派工
- `/replay` — 回放
- `/congestion` — 拥堵

## 使用说明

1. 查看楼栋与轿厢状态。
2. 在呼梯页登记请求，在派工页按评分分配轿厢。
3. 回放页查看派工轨迹，拥堵页查看高峰楼层。

## 开发与测试

```bash
docker compose exec api pytest -q
```
