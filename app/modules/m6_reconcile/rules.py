def apply(ctx):
     opening=sum(s['available'] for s in ctx['usable']);sent=sum(r['调拨数量'] for r in ctx['allocations']);left=sum(ctx['remaining'].values())
     need=sum(d['net_need'] for d in ctx['net_demands']);missing=sum(r['缺口'] for r in ctx['shortages'])
     balanced=opening==sent+left and need==sent+missing;ctx['balanced']=balanced
     rows=[{'项目':'可调拨库存','期初':opening,'发出':sent,'结余或缺口':left,'差额':opening-sent-left},
           {'项目':'净需求','期初':need,'发出':sent,'结余或缺口':missing,'差额':need-sent-missing}]
     orders=[{'订单':o['订单'],'门店':o['门店'],'类型':o['类型'],'需求':o['需求'],'已分配':o['已分配'],'缺口':o['缺口'],'差额':o['需求']-o['已分配']-o['缺口'],'可出库':o['可出库'],'缺套原因':o.get('缺套原因','')} for o in ctx.get('orders',[])]
     for o in orders: rows.append({'项目':'订单 '+o['订单'],'期初':o['需求'],'发出':o['已分配'],'结余或缺口':o['缺口'],'差额':o['差额'],'门店':o['门店'],'类型':o['类型'],'可出库':o['可出库']})
     return {'rows':rows,'orders':orders,'metrics':[['库存差额',opening-sent-left,'件'],['需求差额',need-sent-missing,'件'],['缺套预演',len(ctx.get('trials',[])),'条'],['可出库单',sum(1 for o in orders if o['可出库'] in ('可出库','部分可出库')),'单']]}
