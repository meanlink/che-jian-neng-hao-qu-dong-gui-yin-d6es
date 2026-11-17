import hashlib, json
def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def dataset_dict(d):
    return {'id':d.id, 'name':d.name, 'source':d.source, 'rows':len(d.records), 'checksum':d.checksum, 'created_at':d.created_at}
def job_dict(j):
    return {k:getattr(j,k) for k in ['id','name','dataset_id','params','status','result','error','approved','created_at','finished_at']}
def report_dict(r):
    return {k:getattr(r,k) for k in ['id','name','job_id','destination','interval_seconds','next_run','enabled']}
def delivery_dict(d):
    return {k:getattr(d,k) for k in ['id','report_id','created_at','checksum','filename','destination']}
def version_dict(v):
    return {k:getattr(v,k) for k in ['id','name','job_id','status','checksum','summary','note','created_at','published_at']}
def config_dict(c):
    return {k:getattr(c,k) for k in ['active_version_id','canary_version_id','canary_ratio','updated_by','updated_at']}
def order_dict(o):
    return {k:getattr(o,k) for k in ['id','order_no','version_id','lane','status','item_count','total_kwh','created_at']}
def item_dict(i):
    return {k:getattr(i,k) for k in ['id','day','inputs','kwh','flags']}
