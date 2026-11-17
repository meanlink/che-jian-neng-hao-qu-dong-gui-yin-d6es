from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.config.database import get_db
from src.models import Job, ModelVersion
from src.schemas.release import SealInput, RatioInput, PublishInput
from src.middlewares.auth import current_user, admin_only
from src.services import releases
from src.services.audit import record
from src.utils.serialization import version_dict, config_dict
router = APIRouter()


def _state(db):
    c = releases.get_config(db)
    versions = [version_dict(v) for v in db.scalars(select(ModelVersion).order_by(ModelVersion.id.desc()))]
    return {'config': config_dict(c), 'versions': versions}


@router.get('/releases')
def state(db=Depends(get_db), u=Depends(current_user)):
    return _state(db)


@router.post('/versions', status_code=201)
def seal(data: SealInput, db=Depends(get_db), u=Depends(admin_only)):
    try:
        v = releases.seal(db, data.name, data.job_id, data.note, u)
        record(db, u.email, 'version.seal', {'id': v.id, 'job_id': v.job_id, 'checksum': v.checksum})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '该试验已封存为预测版本；版本不随重训变化，如需更新请训练新试验')
    return version_dict(v)


@router.post('/versions/{id}/publish')
def publish(id: int, data: PublishInput, db=Depends(get_db), u=Depends(admin_only)):
    v = releases.publish(db, id, data.ratio, u.email)
    record(db, u.email, 'version.publish', {'id': v.id, 'ratio': data.ratio})
    db.commit()
    return _state(db)


@router.post('/versions/{id}/promote')
def promote(id: int, db=Depends(get_db), u=Depends(admin_only)):
    v = releases.promote(db, id, u.email)
    record(db, u.email, 'version.promote', {'id': v.id})
    db.commit()
    return _state(db)


@router.post('/versions/{id}/rollback')
def rollback(id: int, db=Depends(get_db), u=Depends(admin_only)):
    v = releases.rollback(db, id, u.email)
    record(db, u.email, 'version.rollback', {'id': v.id})
    db.commit()
    return _state(db)


@router.post('/releases/ratio')
def ratio(data: RatioInput, db=Depends(get_db), u=Depends(admin_only)):
    releases.set_ratio(db, data.ratio, u.email)
    record(db, u.email, 'version.ratio', {'ratio': data.ratio})
    db.commit()
    return _state(db)


@router.get('/versions/{id}/artifact')
def artifact(id: int, db=Depends(get_db), u=Depends(current_user)):
    v = db.get(ModelVersion, id)
    if not v:
        raise HTTPException(404, '预测版本不存在')
    model = releases.load_artifact(v, http_status=422)
    return {'version': version_dict(v), 'model': model}


@router.get('/versions/sealable/jobs')
def sealable(db=Depends(get_db), u=Depends(current_user)):
    sealed = set(db.scalars(select(ModelVersion.job_id)))
    jobs = db.scalars(select(Job).where(Job.status == 'completed', Job.approved == True).order_by(Job.id.desc()))
    return [{'id': j.id, 'name': j.name, 'sealed': j.id in sealed} for j in jobs]
