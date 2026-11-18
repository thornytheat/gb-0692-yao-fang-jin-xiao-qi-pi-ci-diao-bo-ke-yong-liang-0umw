from app.config import DEFAULT_POLICY, POLICIES
from app.domain import allocate_plan, plan_stats
def apply(ctx):
    policy=ctx.get('policy') or DEFAULT_POLICY
    plan=allocate_plan(ctx['usable'],ctx['net_demands'],policy)
    compare=[]
    for key,label in POLICIES.items():
        trial=plan if key==policy else allocate_plan(ctx['usable'],ctx['net_demands'],key)
        stats=plan_stats(trial)
        compare.append({'策略':key,'策略名称':label,'采用':'是' if key==policy else '否','已分配':stats['已分配'],'缺口':stats['缺口'],'可出库单':stats['可出库单'],'缺套单':stats['缺套单'],'急单缺口':stats['急单缺口'],'急单可出库':stats['急单可出库']})
    ctx.update(allocations=plan['rows'],remaining=plan['remaining'],shortages=plan['shortages'],orders=plan['orders'],trials=plan['trials'],policy=policy,compare=compare)
    stats=plan_stats(plan)
    return {'rows':plan['rows']+plan['trials'],'compare':compare,'metrics':[['调拨',stats['已分配'],'件'],['可出库单',stats['可出库单'],'单'],['缺套单',stats['缺套单'],'单']]}
