import hashlib, time, json
from app.config import RULE_VERSION
def make(text, parameters=None):
    parameters=parameters or {}
    digest=hashlib.sha256(text.encode('utf-8')).hexdigest()
    identity=RULE_VERSION+':'+digest+':'+json.dumps(parameters,sort_keys=True,ensure_ascii=False)
    return {'run_id':hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16], 'sha256':digest, 'rule_version':RULE_VERSION, 'parameters':parameters, 'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
