import time, hashlib
from fastapi import HTTPException
from sqlalchemy import select
from src.models import ModelVersion, PredictionOrder, PredictionItem
from src.services.releases import get_config, load_artifact
from src.services.business import predict_one
from src.utils.serialization import checksum


def route_lane(order_no, config):
    """Stable split by scheduling order number: same order_no always lands on the same lane for a given config."""
    if not config.active_version_id:
        return 'canary' if config.canary_version_id else None
    ratio = config.canary_ratio if config.canary_version_id else 0
    bucket = int(hashlib.sha256(order_no.encode('utf-8')).hexdigest(), 16) % 100
    return 'canary' if bucket < ratio else 'active'


def _payload(data):
    return {'order_no': data.order_no.strip(), 'items': [item.model_dump() for item in data.items]}


def find_replay(db, data):
    """Return the accepted order for this order_no; reject if the same number carries different content."""
    order = db.scalar(select(PredictionOrder).where(PredictionOrder.order_no == data.order_no.strip()))
    if not order:
        return None
    if order.request_hash != checksum(_payload(data)):
        raise HTTPException(409, '同一排产单号已受理且内容不一致，拒绝覆盖；请核对排产单或更换单号')
    return order


def create(db, data, user):
    replay = find_replay(db, data)
    if replay:
        return replay, False  # 中断恢复后的重试：不重复预测、不改换版本
    config = get_config(db)
    lane = route_lane(data.order_no.strip(), config)
    version_id = config.canary_version_id if lane == 'canary' else config.active_version_id
    if not version_id:
        raise HTTPException(409, '尚未发布可用的预测版本，请先在版本发布页上线')
    version = db.get(ModelVersion, version_id)
    artifact = load_artifact(version, http_status=503)
    rows = []
    total = 0.0
    for item in data.items:
        try:
            kwh, flags = predict_one(artifact, item.model_dump())
        except ValueError as e:
            raise HTTPException(422, f'排产明细 {item.day}：{e}') from None
        rows.append((item, kwh, flags))
        total += kwh
    order = PredictionOrder(order_no=data.order_no.strip(), request_hash=checksum(_payload(data)), version_id=version.id,
                            lane=lane, status='completed', item_count=len(rows), total_kwh=round(total, 2),
                            created_by=user.id, created_at=time.time())
    db.add(order)
    db.flush()
    for item, kwh, flags in rows:
        db.add(PredictionItem(order_id=order.id, day=item.day, kwh=kwh, flags=flags,
                              inputs={'units': item.units, 'run_hours': item.run_hours, 'temp_c': item.temp_c, 'idle_hours': item.idle_hours}))
    return order, True
