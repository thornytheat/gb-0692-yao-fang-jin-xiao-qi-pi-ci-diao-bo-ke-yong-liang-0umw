from datetime import date
from app.numeric import number
from app.errors import DomainError
from app.config import DEFAULT_POLICY, POLICIES
AS_OF=date(2026,11,18)

def day(value):
    try: return date.fromisoformat(value)
    except ValueError: raise DomainError('DATE','日期格式无效')

def whole(value):
    n=number(value)
    if n<0 or n!=n.to_integral_value(): raise DomainError('QUANTITY','数量须为非负整数')
    return int(n)

def eligible(stock,demand):
    return stock['sku']==demand['sku'] and stock['status']=='normal' and (day(stock['expiry'])-day(demand['arrival'])).days>=demand['min_days_n'] and day(stock['expiry'])>day(demand['arrival'])

# 同一 record 的 demand 行构成一张补货单。多行（多药品）为成套单，单行为散单。
def orders_of(demands):
    groups={}
    for d in demands: groups.setdefault(d['record'],[]).append(d)
    orders=[]
    for record,lines in groups.items():
        lines=sorted(lines,key=lambda r:(r['sku'],r['record']))
        orders.append({'record':record,'store':lines[0]['store'],'arrival':min((r.get('arrival') or '9999-12-31') for r in lines),'lines':lines,'type':'成套' if len(lines)>1 else '散单','urgent':any(str(r.get('status','')).lower() in URGENT for r in lines)})
    return orders

def _take_line(stocks,remaining,demand):
    need=demand['net_need'];takes=[]
    for stock in sorted(stocks,key=lambda s:(s['expiry'],s['lot'])):
        if not eligible(stock,demand): continue
        key=stock.get('stock_key',stock['lot'])
        take=min(remaining[key],need)//stock['pack_n']*stock['pack_n']
        if take<=0: continue
        remaining[key]-=take;need-=take
        takes.append((stock,take))
        if need==0: break
    return takes,need

def _rows_for(demand,stock,take,state,trial,note):
    return {'需求单':demand['record'],'订单':demand['record'],'门店':demand['store'],'药品':demand['sku'],'批号':stock['lot'],'到期日':stock['expiry'],'调拨数量':0 if trial else take,'整包装':stock['pack_n'],'到店余期_天':(day(stock['expiry'])-day(demand['arrival'])).days,'状态':state,'拟调拨数量':take if trial else 0,'说明':note}

URGENT={'urgent','急单','紧急','加急'}

def _by_urgency(orders):
    return sorted(orders,key=lambda o:(0 if o['urgent'] else 1,o['arrival'],o['store'],o['record']))

def _ordered(orders,policy):
    if policy=='set_first':
        return sorted(orders,key=lambda o:(0 if o['type']=='成套' else 1,0 if o['urgent'] else 1,o['arrival'],o['store'],o['record']))
    return _by_urgency(orders)

def allocate_plan(stocks,demands,policy=DEFAULT_POLICY):
    if policy not in POLICIES: raise DomainError('POLICY','优先级策略无效')
    base={s.get('stock_key',s['lot']):s['available'] for s in stocks}
    remaining=dict(base);rows=[];shortages=[];trials=[];orders=[]
    for order in _ordered(orders_of(demands),policy):
        work=dict(remaining);lines=[]
        for d in order['lines']:
            takes,need=_take_line(stocks,work,d);lines.append((d,takes,need))
        complete=all(need==0 for _,_,need in lines)
        shortage_lines=[(d,need) for d,_,need in lines if need]
        if order['type']=='成套' and not complete:
            # 缺套整单回滚：预演出的货一件也不扣，留给后续订单。
            reason='；'.join('%s 缺 %d'%(d['sku'],need) for d,need in shortage_lines)
            for d,takes,need in lines:
                for stock,take in takes: trials.append(_rows_for(d,stock,take,'缺套预演',True,'整单缺套，不占库存'))
                shortages.append({'需求单':d['record'],'订单':d['record'],'门店':d['store'],'药品':d['sku'],'净需求':d['net_need'],'已分配':0,'缺口':d['net_need'],'订单类型':'成套','缺套':True})
            orders.append({'订单':order['record'],'门店':order['store'],'类型':'成套','急单':'是' if order['urgent'] else '否','行数':len(lines),'需求':sum(d['net_need'] for d,_,_ in lines),'已分配':0,'缺口':sum(d['net_need'] for d,_,_ in lines),'可出库':'否','缺套原因':reason,'到货日':order['arrival'],'最短余期_天':None})
            continue
        remaining=work;allocated=0;lifes=[]
        for d,takes,need in lines:
            for stock,take in takes:
                allocated+=take;lifes.append((day(stock['expiry'])-day(d['arrival'])).days)
                rows.append(_rows_for(d,stock,take,'已确认',False,''))
            shortages.append({'需求单':d['record'],'订单':d['record'],'门店':d['store'],'药品':d['sku'],'净需求':d['net_need'],'已分配':d['net_need']-need,'缺口':need,'订单类型':order['type'],'缺套':False})
        gap=sum(need for _,_,need in lines)
        state='可出库' if gap==0 else ('部分可出库' if (allocated>0 and order['type']=='散单') else '否')
        orders.append({'订单':order['record'],'门店':order['store'],'类型':order['type'],'急单':'是' if order['urgent'] else '否','行数':len(lines),'需求':sum(d['net_need'] for d,_,_ in lines),'已分配':allocated,'缺口':gap,'可出库':state,'缺套原因':'','到货日':order['arrival'],'最短余期_天':min(lifes) if lifes else None})
    return {'rows':rows,'remaining':remaining,'shortages':shortages,'orders':orders,'trials':trials,'policy':policy}

def plan_stats(plan):
    return {'已分配':sum(a['调拨数量'] for a in plan['rows']),'缺口':sum(s['缺口'] for s in plan['shortages']),'完整单':sum(1 for o in plan['orders'] if o['缺口']==0),'可出库单':sum(1 for o in plan['orders'] if o['可出库'] in ('可出库','部分可出库')),'缺套单':sum(1 for o in plan['orders'] if o['类型']=='成套' and o['缺口']>0),'急单缺口':sum(o['缺口'] for o in plan['orders'] if o.get('急单')=='是'),'急单可出库':sum(1 for o in plan['orders'] if o.get('急单')=='是' and o['可出库'] in ('可出库','部分可出库'))}

def allocate(stocks,demands,policy=DEFAULT_POLICY):
    plan=allocate_plan(stocks,demands,policy)
    return plan['rows'],plan['remaining'],plan['shortages']
