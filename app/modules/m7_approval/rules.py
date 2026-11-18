def apply(ctx):
    orders={o['订单']:o for o in ctx.get('orders',[])}
    grouped={}
    for r in ctx['shortages']: grouped.setdefault(r['订单'],[]).append(r)
    rows=[]
    for record,lines in grouped.items():
        o=orders.get(record)
        if o is None:
            o={'订单':record,'门店':lines[0]['门店'],'类型':lines[0].get('订单类型','散单'),'需求':sum(l['净需求'] for l in lines),'已分配':sum(l['已分配'] for l in lines),'缺口':sum(l['缺口'] for l in lines),'缺套原因':'','最短余期_天':0}
        if o['缺口']==0: decision='可出库'
        elif o['类型']=='散单' and o['已分配']>0: decision='部分可出库'
        elif o['类型']=='成套' and o['已分配']==0: decision='缺套待补'
        else: decision='缺口待补'
        rows.append({'订单':record,'门店':o['门店'],'类型':o['类型'],'净需求':o['需求'],'已分配':o['已分配'],'缺口':o['缺口'],'最短余期_天':o['最短余期_天'],'可出库':decision,'缺套原因':o.get('缺套原因',''),'复核':'可下发' if o['缺口']==0 else '缺口待补','计划版本':1})
    return {'rows':rows,'metrics':[['可出库单',sum(r['可出库']=='可出库' for r in rows),'单'],['部分可出库',sum(r['可出库']=='部分可出库' for r in rows),'单'],['待补',sum(r['复核']=='缺口待补' for r in rows),'单'],['版本',1,'']]}
