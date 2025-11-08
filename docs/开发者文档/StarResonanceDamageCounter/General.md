# 初版DPS项目全局分析

## 项目结构概览

- 核心入口：server.js
  - 网络包解析：PacketProcessor 与抓包辅助 findDefaultNetworkDevice
  - 数据模型：StatisticData(通用统计类，用于处理伤害或治疗数据)、UserData、UserDataManager 负责实时统计、技能归集与缓存。
  - Web/Socket 服务：Express 接口(`/api/data`, `/api/skill/:uid`, `/api/history/...` 等)与 Socket.IO 推送；日志与历史归档写入 logs，用户缓存落地 users.json
- 前端界面：``public/index.html`实时面板，集成 WebSocket/轮询、图表、技能分析、设置同步；`public/history.html`浏览历史分段；`public/hp_window.html` 提供血条监控子窗口；样式位于 `style.css`
- 配置与资源：技能/怪物映射表存放于 tables/，格式化规则在 `.prettierrc.js`，包管理经由 `package.json`与 `pnpm` 工作空间文件。

---

## 主体运行逻辑

1. 启动流程：`server.js/main()`解析命令行→选择网卡→初始化 `winston` 日志→实例化 `UserDataManager` 并加载缓存→设定周期任务与 API。
2. 抓包解码：CAP 持续监听 TCP/IP；重组分片、按序缓存，交由 `PacketProcessor.processPacket` 解压/解析 pb 数据；根据消息类型更新玩家属性、伤害/治疗、敌方信息。
3. 数据维护：`UserDataManager` 在每次事件中更新统计窗口、技能明细、同步到内存缓存；按需触发自动清空、历史归档与日志写入。
4. 对外服务：HTTP 接口返回实时/历史数据，前端通过 Socket.IO 每 100 ms100ms 接收广播；暂停、设置、清空等命令均通过 REST 调用；Web 页面渲染表格、图表与控制面板。

---

## 潜在性能问题

## 关键发现

- **抓包队列无限增长风险**：`server.js` 中的全局 `eth_queue` 每次网卡事件都会 `push`，而消费者循环 `processEthPacket(pkt)` 并未 `await`，若解析速度低于抓包速度，队列会持续膨胀，触发实际的内存泄漏并放大 GC 压力。
- **用户态缓存无淘汰策略**：`UserDataManager.users`、`user.skillUsage`、`enemyCache`、`hpCache` 等 `Map` 仅在手动 `/api/clear` 或触发自动清空时才重置。长时间运行、跨服或大量路人 UID 进入时会把内存锁死在历史数据上。
- **高频广播与深拷贝开销大**：100 ms 的定时任务会完整调用 `getAllUsersData()`，每位玩家都复制一次 `StatisticData` 的多个对象并序列化，通过 Socket.IO 广播。人数或技能条目一旦上涨，GC 频次和 CPU 占比会显著飙升。
- **日志写入吞吐瓶颈**：`PacketProcessor` 对每条伤害/治疗事件都 `logger.info` 并 `addLog()` 落地；虽然 `Lock` 保证串行，但在高频战斗中会形成 I/O 阻塞，进而拖慢整个事件处理链路。
- **忙等待循环浪费 CPU**：处理线程通过 `setTimeout(r, 1)` 轮询 `eth_queue`，即使空闲也保持 1 ms 唤醒一次，导致后台 CPU 空耗。
- **IP 分片缓存尚可**：`fragmentIpCache` 具备 30 s TTL 并定期清理，暂未发现明显泄漏，但若面对海量不同 `ipId` 的碎片也可能瞬间膨胀，需关注监控告警。

## 优化建议

1. **为抓包通道加背压**
   - 直接在 `c.on('packet')` 内同步调用 `processEthPacket`，或将 `eth_queue` 改成有限长度（设置高水位触发丢包/速率告警）。
   - 若仍需队列，可使用 `Promise` 链或 `async` 阻塞，确保生产速度不会长期领先消费速度。
2. **引入数据 TTL 与分段归档**
   - `UserDataManager` 为玩家记录添加 `lastSeen`（事件时间戳），定时清理超过设定时长（如 5–10 分钟）的 UID/技能。
   - 对敌人缓存同理，战斗结束自动释放；`hpCache` 也应限制容量，或在血量低频更新后转储到磁盘避免长期驻留。
3. **降低广播负载**
   - 将 Socket 推送频率调降至 250–500 ms，可配合前端插值保证体验。
   - 为 `getAllUsersData()` 增加轻量模式：仅发送变更字段或通过预序列化缓存（按需更新）。这能显著减少对象分配与 JSON 序列化开销。
4. **优化日志策略**
   - 默认降级到 `debug` 级别或添加采样（如按技能/玩家节流）。

- 将 `addLog` 替换为批量缓冲写：收集 1–2 秒日志一次 `appendFile`，或使用流式写入 (`fs.createWriteStream`) 避免频繁打开文件。

1. **替换忙等待**
   - 使用 `setImmediate`/`process.nextTick` + 自调度模式：`if (eth_queue.length) { await processEthPacket(...) } else { await once(c, 'packet') }`；或改用 `async` 迭代器，空闲时完全休眠。
2. **完善监控与压测**
   - 在启动参数中支持 `--inspect` 并暴露 `/api/metrics`，便于采集堆快照与事件循环延迟。
   - 跑一次高频战斗重放（可用存档日志回放）验证改动后内存和 CPU 的曲线，确保优化有效。

## 质量门禁

- 构建/测试：未执行（分析类任务，无代码改动）。

## Requirements coverage

- 内存/性能问题调查与建议：Done。

如需具体实现参考或压测脚本，我可以继续补充。

---
