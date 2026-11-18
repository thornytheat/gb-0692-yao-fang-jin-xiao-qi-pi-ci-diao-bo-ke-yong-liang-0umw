from flask import Blueprint, render_template, request
from app.config import TITLE, MODULES, SHORT, SAMPLE, POLICIES
from app.pipeline import calculate
from app.store import latest, save, get_run, get_source
bp=Blueprint('web',__name__)
@bp.route('/')
@bp.route('/work/<int:stage>')
def work(stage=1):
    if stage<1 or stage>7:
        from flask import abort
        abort(404)
    run=get_run(request.args['run_id']) if request.args.get('run_id') else latest()
    if run is None:
        text=SAMPLE.read_text(encoding='utf-8-sig');run=save(calculate(text),text)
    current=run['stages'][str(stage)]
    policy=run['manifest'].get('parameters',{}).get('policy','urgent_first')
    sample=get_source(run['manifest']['run_id']) or SAMPLE.read_text(encoding='utf-8-sig')
    return render_template('m'+str(stage)+'.html', title=TITLE, modules=MODULES, short=SHORT, run=run, current=current, stage=stage, sample=sample, policy=policy, policies=POLICIES)
