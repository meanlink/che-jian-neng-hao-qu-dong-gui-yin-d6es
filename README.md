# 车间能耗驱动归因

特征选择与回归的真实业务分析小型项目。完整模拟客户、痛点、上下游、算法公式与一天工作剧本见 [BUSINESS.md](BUSINESS.md)。

## 模块与业务流程
数据接入（JSON/CSV、字段验证、批次指纹）→ 参数化分析（异步 Python worker）→ 结果复核（指标、图形、明细、解释、批准）→ 定时分发（本地收件箱、CSV/JSON、SHA256）；另有业务总览和审计轨迹。
版本发布（已批准试验封存为不可变预测版本，灰度比例可调，推广/回滚一次性切换）→ 日电耗预测（排产单号稳定分流、整单一版、重试幂等、同号异内容拒绝）。
贯穿实体：Dataset 数据批次、Job 分析任务、Report 分发计划、ModelVersion 预测版本、ReleaseConfig 发布配置、PredictionOrder/Item 排产预测单与明细；辅助 User、Audit、Delivery。

## 快速启动
```bash
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```
访问 http://localhost:18215；后端文档 http://localhost:19215/docs；数据库宿主端口 17715。
`SEED_DEMO=true` 自动幂等 seed；不覆盖用户修改。手动 seed 命令可重复执行。

## 演示账号与权限
|账号|密码|真实权限|
|---|---|---|
|admin@demo.local|Demo123!|接入、执行、批准、分发、暂停、封存、发布、调比、推广、回滚、读取与下载|
|analyst@demo.local|Demo123!|接入、执行、提交排产预测、读取与下载；不能批准、安排分发或管理版本|
|viewer@demo.local|Demo123!|只读与下载|

## 预测版本与日电耗预测
- 封存：`POST /versions` 把已批准试验固化为预测版本，版本文件写入 `ARTIFACT_DIR/versions/`，保存特征、标准化参数、系数、训练窗口与留出验证误差，DB 存 SHA256；此后重训不影响该版本，同一试验只能封存一次。
- 发布：`POST /versions/{id}/publish`（待校验→灰度中）、`POST /releases/ratio`（调灰度比例 0–100%）、`POST /versions/{id}/promote`（→正式，旧正式退役）、`POST /versions/{id}/rollback`（退役版回滚）。上线前重新读取版本文件并双重校验（DB 校验和 + 文件内嵌校验和），缺失或失败即拒绝，现行配置不变；配置单行单事务提交，实现一次性切换。
- 预测：`POST /predictions` 按排产单号 SHA256 稳定分流到正式版或灰度版，整单固定一版；单号唯一约束保证幂等——重试同号同内容返回原结果（`replayed:true`），同号异内容 409；并发下同号竞争由唯一索引兜底，失败方重放已接纳单。明细落库版本、输入与日电耗，`GET /predictions/{id}` 可追溯。
- 页面：版本发布（06）管理封存、发布、调比、推广、回滚并查看计算依据；日电耗预测（07）提交排产单（CSV 行：日期,日产量,运行小时,温度,待机小时）并钻取每单明细。

## 技术与本地开发
Python 3.12 / FastAPI / SQLAlchemy / NumPy / SciPy / scikit-learn；MySQL 8.0；Redis 7；Nginx；原生 HTML CSS JavaScript ES modules（用户指定）。后端所有校验、持久化和算法在服务端。无前端打包步骤。
后端：安装 backend/requirements.txt，设置 DATABASE_URL、REDIS_URL、JWT_SECRET、ARTIFACT_DIR 后在 backend/ 执行 `python -m migrations.initial`、`python -m scripts.seed_demo`、`uvicorn src.main:app`，另开 `python -m src.worker`。前端使用带 /api 反向代理的 Nginx，直接打开 index.html 不支持 API。

## 目录与工程约定
backend/src/{models,schemas,services,routes,controllers,middlewares,constants,config,utils}；backend/scripts/seed_demo.py；backend/migrations/initial.py。
frontend/src/{api,stores,types,components/common,hooks,pages,router,utils,constants}。
Role 枚举：admin/analyst/viewer；JobStatus：queued/running/completed/failed；VersionStatus：pending（待校验）/canary（灰度中）/active（正式）/retired（退役）。后端 backend/src/constants/enums.py，前端 frontend/src/constants/enums.js；路由权限在 middlewares/auth.py；页面按相同角色控制操作入口。

## 环境变量与 Docker
COMPOSE_PROJECT_NAME=energy-ridge；FRONTEND_PORT=18215；BACKEND_PORT=19215；DB_PORT=17715；DB_PASSWORD、JWT_SECRET 见 .env.example；SEED_DEMO 默认 true。共享命名产物卷供后端下载与 worker 写入，数据库/Redis 各持久卷。
恰好五服务均有健康检查。Redis 队列加 SQL 排队状态兜底；worker 按 next_run 生成本地收件箱文件。周期 60 秒至 30 天。分发结果为批准分析的固定快照；若需新数据重新计算并建立新计划。当前不连接邮件或企业聊天。
错误响应、请求编号、Redis 每 IP 每分钟 240 次限流、JWT 和数据库操作审计。演示密钥与密码仅供本机模拟；生产部署前配置独立密钥与账号。

## 数据与验收
所有数据为固定随机种子生成的模拟业务数据，不能作为实际生产决策证据。项目独立算法、输入边界及业务局限详见 BUSINESS.md。测试与截图统一存放 ../../test-artifacts/gb-1016/，源码不含日志/截图/测试报告。
清理本项目演示数据：`docker compose down -v --remove-orphans`（会删除本项目命名卷）。

## License
MIT，见 LICENSE。
