import os, json, hashlib, time
from fastapi import HTTPException
from sqlalchemy import select
from src.config.settings import ARTIFACT_DIR
from src.models import Dataset, Job, ModelVersion, ReleaseConfig
from src.services.business import FEATURES, model_artifact

REQUIRED_KEYS = ('feature_keys', 'alpha', 'scaler_mean', 'scaler_scale', 'coefficients', 'intercept', 'train_window', 'train_ranges', 'validation')


def get_config(db):
    c = db.get(ReleaseConfig, 1)
    if not c:
        c = ReleaseConfig(id=1, canary_ratio=0, updated_by='system', updated_at=time.time())
        db.add(c)
        db.flush()
    return c


def _artifact_file(version_id):
    return os.path.join(ARTIFACT_DIR, 'versions', f'version-{version_id}.json')


def _content_digest(artifact):
    content = {key: value for key, value in artifact.items() if key != 'seal'}
    payload = json.dumps(content, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def _verify(artifact):
    missing = [key for key in REQUIRED_KEYS if key not in artifact.get('model', {})]
    if missing:
        raise ValueError('版本文件缺少必要字段')
    model = artifact['model']
    selected = model['feature_keys']
    if not selected or not set(selected) <= set(FEATURES):
        raise ValueError('版本文件特征清单无效')
    n = len(selected)
    if not (len(model['scaler_mean']) == len(model['scaler_scale']) == len(model['coefficients']) == n):
        raise ValueError('版本文件模型参数长度不一致')
    if not all(isinstance(v, (int, float)) for v in model['scaler_mean'] + model['scaler_scale'] + model['coefficients'] + [model['intercept'], model['alpha']]):
        raise ValueError('版本文件模型参数必须为数值')
    if any(scale <= 0 for scale in model['scaler_scale']):
        raise ValueError('版本文件标准化尺度必须为正')
    if _content_digest(artifact) != artifact.get('seal', {}).get('checksum'):
        raise ValueError('版本文件内嵌校验和不匹配')


def load_artifact(version, http_status=409):
    """Read the sealed artifact file and verify it against both the DB checksum and the embedded one.

    Always reads from disk: lifecycle transitions and predictions must refuse a
    version whose file is missing or fails checksum validation.
    """
    try:
        path = os.path.join(ARTIFACT_DIR, version.artifact_path) if version.artifact_path else ''
        if not path or not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, 'rb') as f:
            artifact = json.loads(f.read().decode('utf-8'))
        if _content_digest(artifact) != version.checksum:
            raise ValueError('版本文件与封存校验和不一致')
        _verify(artifact)
        return artifact['model']
    except FileNotFoundError:
        raise HTTPException(http_status, '版本文件缺失，拒绝上线' if http_status == 409 else '版本文件缺失，无法预测') from None
    except (ValueError, json.JSONDecodeError) as e:
        message = str(e) if isinstance(e, ValueError) else '版本文件不是有效JSON'
        raise HTTPException(http_status, f'版本文件校验失败：{message}' if http_status == 409 else f'版本文件校验失败，无法预测：{message}') from None


def seal(db, name, job_id, note, user):
    j = db.get(Job, job_id)
    if not j or j.status != 'completed' or not j.approved:
        raise HTTPException(409, '仅已完成且获批准的试验可以封存为预测版本')
    if db.scalar(select(ModelVersion).where(ModelVersion.job_id == j.id)):
        raise HTTPException(409, '该试验已封存为预测版本；版本不随重训变化，如需更新请训练新试验')
    d = db.get(Dataset, j.dataset_id)
    try:
        artifact = model_artifact(d.records, j.params)
    except ValueError as e:
        raise HTTPException(422, f'封存前重算失败：{e}') from None
    approved = {m['label']: m.get('value') for m in j.result.get('metrics', [])}
    if isinstance(approved.get('验证RMSE'), (int, float)) and abs(artifact['validation']['rmse'] - approved['验证RMSE']) > 0.05:
        raise HTTPException(409, '封存校验失败：重算验证误差与已批准试验不一致，拒绝封存')
    v = ModelVersion(name=name.strip(), job_id=j.id, status='pending', note=(note or '').strip(), created_by=user.id, created_at=time.time())
    db.add(v)
    db.flush()
    body = {'format': 'energy-ridge-model/1', 'version_id': v.id, 'name': v.name, 'source_job_id': j.id,
            'dataset_checksum': d.checksum, 'sealed_at': time.time(), 'model': artifact}
    digest = _content_digest(body)
    body['seal'] = {'checksum': digest}
    payload = json.dumps(body, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')
    path = _artifact_file(v.id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f'{path}.{os.getpid()}.tmp'
    with open(tmp, 'wb') as f:
        f.write(payload)
    os.replace(tmp, path)
    v.artifact_path = os.path.relpath(path, ARTIFACT_DIR)
    v.checksum = digest
    v.summary = {'features': artifact['feature_keys'], 'alpha': artifact['alpha'], 'validation': artifact['validation'],
                 'train_window': artifact['train_window'], 'dataset_checksum': d.checksum, 'source_job': j.name}
    return v


def _get_version(db, version_id):
    v = db.get(ModelVersion, version_id)
    if not v:
        raise HTTPException(404, '预测版本不存在')
    return v


def publish(db, version_id, ratio, actor):
    v = _get_version(db, version_id)
    if v.status != 'pending':
        raise HTTPException(409, '仅待校验版本可发布为灰度版')
    load_artifact(v)  # 文件缺失或校验失败时拒绝上线，现行配置不变
    c = get_config(db)
    if c.canary_version_id and c.canary_version_id != v.id:
        old = db.get(ModelVersion, c.canary_version_id)
        if old and old.status == 'canary':
            old.status = 'retired'
    v.status = 'canary'
    v.published_at = time.time()
    c.canary_version_id = v.id
    c.canary_ratio = ratio
    c.updated_by = actor
    c.updated_at = time.time()
    return v


def set_ratio(db, ratio, actor):
    c = get_config(db)
    if not c.canary_version_id:
        raise HTTPException(409, '当前没有灰度中的版本，无法调整比例')
    c.canary_ratio = ratio
    c.updated_by = actor
    c.updated_at = time.time()
    return c


def promote(db, version_id, actor):
    v = _get_version(db, version_id)
    if v.status not in ('pending', 'canary'):
        raise HTTPException(409, '仅待校验或灰度中版本可推广为正式版')
    load_artifact(v)  # 校验失败拒绝上线，保留旧版服务
    c = get_config(db)
    if c.active_version_id and c.active_version_id != v.id:
        old = db.get(ModelVersion, c.active_version_id)
        if old and old.status == 'active':
            old.status = 'retired'
    if c.canary_version_id == v.id:
        c.canary_version_id = None
        c.canary_ratio = 0
    v.status = 'active'
    v.published_at = time.time()
    c.active_version_id = v.id
    c.updated_by = actor
    c.updated_at = time.time()
    return v


def rollback(db, version_id, actor):
    v = _get_version(db, version_id)
    if v.status != 'retired':
        raise HTTPException(409, '仅退役版本可用于回滚')
    load_artifact(v)  # 校验失败拒绝回滚，保留现行正式版
    c = get_config(db)
    if c.active_version_id and c.active_version_id != v.id:
        cur = db.get(ModelVersion, c.active_version_id)
        if cur and cur.status == 'active':
            cur.status = 'retired'
    v.status = 'active'
    c.active_version_id = v.id
    c.updated_by = actor
    c.updated_at = time.time()
    return v
