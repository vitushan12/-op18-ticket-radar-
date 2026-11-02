from monitor import variant_result, discover

def mk(date):
    return {"date":date}

assert variant_result(mk("2026-11-21"),{"variants":[{"title":"Saturday November 21 1 PM","available":False},{"title":"Thursday Nov 26 6 PM","available":True}]})[0]=="sold_out"
assert variant_result(mk("2026-11-26"),{"variants":[{"title":"Saturday November 21","available":False},{"title":"Thursday Nov 26","available":True}]})[0]=="available"
assert variant_result(mk("2026-11-26"),{"variants":[{"title":"Saturday","available":False},{"title":"Thursday","available":True}]})[0] is None
assert variant_result(mk("2026-11-21"),{"variants":[{"title":"Default Title","available":True}]})[0]=="available"
html='<a href="/products/op-18-release-event">OP-18 Release Event</a><a href="/products/op18-booster-box">OP18 Booster Box</a>'
result=discover(html,'https://cards.example/events')
assert len(result)==1 and result[0]['url']=='https://cards.example/products/op-18-release-event'
print('Monitor classification tests: OK')
