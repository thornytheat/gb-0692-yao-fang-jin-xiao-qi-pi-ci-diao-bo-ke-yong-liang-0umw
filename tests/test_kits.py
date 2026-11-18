from copy import deepcopy
from app.domain import allocate_plan, orders_of
from app.pipeline import calculate

KITS = """record,kind,sku,lot,qty,frozen,pack,expiry,store,min_days,arrival,version,status
S1,stock,0001,L1,10,0,5,2026-12-10,中央仓,0,2026-11-20,1,normal
S2,stock,0003,L2,10,0,5,2026-12-10,中央仓,0,2026-11-20,1,normal
U1,demand,0001,,10,0,1,,门店A,10,2026-11-20,1,urgent
K1,demand,0001,,5,0,1,,门店B,10,2026-11-20,1,normal
K1,demand,0003,,5,0,1,,门店B,10,2026-11-20,1,normal
K2,demand,0001,,5,0,1,,门店C,10,2026-11-20,1,normal
K2,demand,0003,,5,0,1,,门店C,10,2026-11-20,1,normal
"""

def _stocks():
    return [{'sku':'0001','lot':'L1','expiry':'2026-12-10','arrival':'2026-11-20','status':'normal','available':10,'pack_n':5,'stock_key':'0001:L1'},
            {'sku':'0003','lot':'L2','expiry':'2026-12-10','arrival':'2026-11-20','status':'normal','available':10,'pack_n':5,'stock_key':'0003:L2'}]

def _demands():
    return [{'record':'U1','store':'门店A','sku':'0001','arrival':'2026-11-20','min_days_n':10,'net_need':10,'status':'urgent'},
            {'record':'K1','store':'门店B','sku':'0001','arrival':'2026-11-20','min_days_n':10,'net_need':5,'status':'normal'},
            {'record':'K1','store':'门店B','sku':'0003','arrival':'2026-11-20','min_days_n':10,'net_need':5,'status':'normal'},
            {'record':'K2','store':'门店C','sku':'0001','arrival':'2026-11-20','min_days_n':10,'net_need':5,'status':'normal'},
            {'record':'K2','store':'门店C','sku':'0003','arrival':'2026-11-20','min_days_n':10,'net_need':5,'status':'normal'}]

def test_multi_line_record_is_kit():
    orders={o['record']:o for o in orders_of(_demands())}
    assert orders['K1']['type']=='成套' and orders['U1']['type']=='散单'

def test_urgent_first_serves_urgent_and_starves_kits():
    plan=allocate_plan(_stocks(),_demands(),'urgent_first')
    assert plan['remaining']=={'0001:L1':0,'0003:L2':10}
    orders={o['订单']:o for o in plan['orders']}
    assert orders['U1']['缺口']==0 and orders['K1']['缺口']>0 and orders['K2']['缺口']>0

def test_kit_first_serves_kits_and_leaves_urgent_waiting():
    plan=allocate_plan(_stocks(),_demands(),'set_first')
    assert plan['remaining']=={'0001:L1':0,'0003:L2':0}
    orders={o['订单']:o for o in plan['orders']}
    assert orders['K1']['缺口']==0 and orders['K2']['缺口']==0 and orders['U1']['缺口']>0

def test_missing_kit_reserves_nothing():
    plan=allocate_plan(_stocks(),_demands(),'urgent_first')
    assert all(r['调拨数量']==0 for r in plan['trials'])
    assert plan['remaining']['0003:L2']==10
    trial=next(r for r in plan['trials'] if r['订单']=='K1')
    assert trial['拟调拨数量']==5 and trial['状态']=='缺套预演'

def test_single_line_order_still_partially_supplied():
    stocks=[{'sku':'0001','lot':'L1','expiry':'2026-12-10','arrival':'2026-11-20','status':'normal','available':10,'pack_n':5,'stock_key':'0001:L1'}]
    demands=[{'record':'P1','store':'门店P','sku':'0001','arrival':'2026-11-20','min_days_n':10,'net_need':13,'status':'normal'}]
    plan=allocate_plan(stocks,demands,'urgent_first')
    order=plan['orders'][0]
    assert order['已分配']==10 and order['缺口']==3 and order['可出库']=='部分可出库'

def test_kit_shortage_does_not_consume_stock_for_later_smaller_kit():
    demands=_demands()+[{'record':'K3','store':'门店D','sku':'0001','arrival':'2026-11-20','min_days_n':10,'net_need':5,'status':'normal'},
                        {'record':'K3','store':'门店D','sku':'0003','arrival':'2026-11-20','min_days_n':10,'net_need':5,'status':'normal'}]
    stocks=[{'sku':'0001','lot':'L1','expiry':'2026-12-10','arrival':'2026-11-20','status':'normal','available':5,'pack_n':5,'stock_key':'0001:L1'},
            {'sku':'0003','lot':'L2','expiry':'2026-12-10','arrival':'2026-11-20','status':'normal','available':5,'pack_n':5,'stock_key':'0003:L2'}]
    plan=allocate_plan(stocks,demands,'set_first')
    orders={o['订单']:o for o in plan['orders']}
    assert orders['K1']['缺口']==0 and orders['K2']['缺口']>0

def test_policy_choice_changes_batch_identity(client):
    first=client.post('/api/run',json={'csv':KITS,'policy':'urgent_first'}).get_json()
    second=client.post('/api/run',json={'csv':KITS,'policy':'set_first'}).get_json()
    assert first['manifest']['run_id']!=second['manifest']['run_id']
    assert first['manifest']['parameters']['policy']=='urgent_first'

def test_retry_same_orders_does_not_double_deduct(client):
    first=client.post('/api/run',json={'csv':KITS}).get_json()
    again=client.post('/api/run',json={'csv':KITS}).get_json()
    assert again['reused'] is True
    assert first['stages']['5']['metrics'][0][1]==again['stages']['5']['metrics'][0][1]==10
    assert again['remaining']==first['remaining']

def test_duplicate_demand_line_not_counted_twice():
    text=KITS+'K1,demand,0003,,5,0,1,,门店B,10,2026-11-20,1,normal\n'
    result=calculate(text)
    assert result['duplicates']==1
    assert sum(d['net_need'] for d in result['net_demands'] if d['record']=='K1')==10

def test_reconcile_clears_each_order_and_kit_no_reserve():
    result=calculate(KITS)
    orders={r['项目']:r for r in result['stages']['6']['rows']}
    assert orders['订单 K1']['差额']==0
    assert result['stages']['6']['metrics'][2][1]==2
    assert sum(r['拟调拨数量'] for r in result['trials'])==10
    assert result['balanced'] is True

def test_review_page_marks_shippable_orders():
    result=calculate(KITS)
    rows={r['订单']:r for r in result['stages']['7']['rows']}
    assert rows['U1']['可出库']=='可出库'
    assert rows['K1']['可出库']=='缺套待补'
    assert rows['K1']['复核']=='缺口待补'

def test_compare_reports_both_policies():
    result=calculate(KITS)
    compare={c['策略']:c for c in result['compare']}
    assert compare['urgent_first']['缺口']==20 and compare['set_first']['缺口']==10
    assert compare['urgent_first']['采用']=='是' and compare['set_first']['采用']=='否'

def test_invalid_policy_isolated():
    import pytest
    from app.errors import DomainError
    with pytest.raises(DomainError):
        calculate(KITS,policy='unknown')
