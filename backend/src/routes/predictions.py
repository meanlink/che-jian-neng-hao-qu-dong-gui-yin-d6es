from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.config.database import get_db
from src.models import ModelVersion, PredictionOrder, PredictionItem
from src.schemas.release import PredictInput
from src.middlewares.auth import current_user, can_write
from src.services import predictions
from src.services.audit import record
from src.utils.serialization import order_dict, item_dict
router = APIRouter(prefix='/predictions')


def _detail(db, order, replayed):
    version = db.get(ModelVersion, order.version_id)
    items = db.scalars(select(PredictionItem).where(PredictionItem.order_id == order.id).order_by(PredictionItem.id))
    return {**order_dict(order), 'replayed': replayed,
            'version': {'id': version.id, 'name': version.name, 'status': version.status, 'checksum': version.checksum} if version else None,
            'items': [item_dict(i) for i in items]}


@router.get('')
def listing(db=Depends(get_db), u=Depends(current_user)):
    orders = list(db.scalars(select(PredictionOrder).order_by(PredictionOrder.id.desc()).limit(100)))
    names = {v.id: v.name for v in db.scalars(select(ModelVersion))}
    return [{**order_dict(o), 'version_name': names.get(o.version_id, '—')} for o in orders]


@router.post('')
def create(data: PredictInput, db=Depends(get_db), u=Depends(can_write)):
    try:
        order, fresh = predictions.create(db, data, u)
        if fresh:
            record(db, u.email, 'prediction.create', {'id': order.id, 'order_no': order.order_no, 'version_id': order.version_id, 'lane': order.lane, 'items': order.item_count})
        db.commit()
    except IntegrityError:
        db.rollback()  # 并发下同号单已被接纳：按已接纳单重放，内容不一致则拒绝
        order = predictions.find_replay(db, data)
        if not order:
            raise HTTPException(409, '排产单号冲突，请重试')
        fresh = False
    return _detail(db, order, replayed=not fresh)


@router.get('/{id}')
def detail(id: int, db=Depends(get_db), u=Depends(current_user)):
    order = db.get(PredictionOrder, id)
    if not order:
        raise HTTPException(404, '预测单不存在')
    return _detail(db, order, replayed=False)
