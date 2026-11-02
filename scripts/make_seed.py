import json, pathlib
root=pathlib.Path(__file__).resolve().parents[1]
stores=[
 ('401-vaughan','401 Games Vaughan','Vaughan','https://store.401games.ca/collections/events-by-day-thursday/products/vaughan-events-one-piece-tcg-op-18-the-dominance-of-god-release-event','https://store.401games.ca/collections/one-piece-events','Priority • TCG+ also required'),
 ('401-downtown','401 Games Downtown','Toronto','https://store.401games.ca/products/downtown-events-one-piece-tcg-op-18-the-dominance-of-god-release-event','https://store.401games.ca/collections/one-piece-events','Priority • TCG+ also required'),
 ('dollys','Dolly’s Toys & Games','Scarborough','https://dollys.ca','https://dollys.ca','Priority • check store announcements'),
 ('game-shack','Game Shack','Toronto','https://www.gameshack.ca/pages/event-calendar','https://www.gameshack.ca/pages/event-calendar','Priority • One Piece announcements via Discord'),
 ('mintink','MINTINK Games','Vaughan','https://www.mintink.ca/pages/play-one-piece-card-game','https://www.mintink.ca/pages/play-one-piece-card-game','Priority • One Piece event page'),
 ('banana','Banana Games & Hobby','Toronto','https://bananagames.ca/products/one-piece-op-18-release-event','https://bananagames.ca/collections/events','OP-18 event published'),
 ('hairy','Hairy Tarantula','Toronto','https://hairyt.com','https://hairyt.com','OP-18 events published'),
 ('face','Face to Face Games Toronto','Toronto','https://facetofacegames.com/products/one-piece-op-18-prerelease-saturday-november-21st-1100-am-toronto-2026','https://facetofacegames.com/collections/events-toronto','OP-18 event published'),
 ('anime','Anime Alley','Toronto','https://animealley.ca/products/one-piece-op-18-release-event-sat-november-28th-2026-1-00-pm','https://animealley.ca/pages/events','OP-18 event published'),
 ('derpy','Derpy Cards','Richmond Hill','https://events.derpycards.ca/','https://events.derpycards.ca/','Check featured event announcements'),
 ('sunny','Sunny Hobbies','Scarborough','https://sunnyhobbies.com/collections/frontpage','https://sunnyhobbies.com/collections/frontpage','Weekly One Piece ≠ OP-18 event'),
 ('perfect','Perfect Sphere Games','Scarborough','','','No OP-18 listing verified'),
 ('esper','Esper Cards & Games','Scarborough','','','No OP-18 listing verified'),
 ('mad','Mad Merchant Cards & Games','Scarborough','','','No OP-18 listing verified'),
 ('the6ix','The6ixTCGs Markham','Markham','https://6ixtcgsmarkham.ca','https://6ixtcgsmarkham.ca','OP-18 event tracked by third party'),
 ('newrealm','New Realm Games','Vaughan','','','No OP-18 listing verified'),
]
objstores=[dict(id=i,name=n,city=c,url=u,eventsUrl=e,notes=note,priority=(i in {'401-vaughan','401-downtown','dollys','game-shack','mintink'})) for i,n,c,u,e,note in stores]
events=[]
def add(store,day,time,status='sold_out',price=None,url='',sourceNote='Store page',tcg=False):
 events.append(dict(id=f'{store}-{day}-{time.replace(":","")}',storeId=store,date=f'2026-11-{day}',time=time,status=status,price=price,url=url or next(s['url'] for s in objstores if s['id']==store),statusSource=sourceNote,lastVerified='2026-11-01',tcgPlus=tcg))
add('401-vaughan','21','13:00',price=42.48,tcg=True)
add('401-vaughan','26','18:30',price=42.48,tcg=True)
add('401-downtown','22','13:00',price=42.48,tcg=True)
add('401-downtown','23','18:00',price=42.48,tcg=True)
add('face','21','11:00',price=60)
add('banana','22','13:00',price=49.95)
add('banana','26','18:30',price=49.95)
add('banana','29','13:00',price=49.95)
add('hairy','22','13:00',price=50,url='https://hairyt.com',sourceNote='Event tracker; verify at store')
add('hairy','24','18:00',price=50,url='https://hairyt.com',sourceNote='Event tracker; verify at store')
add('anime','28','13:00',price=44.95)
add('anime','02','18:00',price=44.95,url='https://animealley.ca/products/one-piece-op-18-release-event-december-2nd-2026-6-00pm',sourceNote='Store ticket page; date is December 2')
events[-1]['date']='2026-12-02'
add('the6ix','25','18:00',price=50,sourceNote='Zeltrix tracker; verify at store')
# Put commonly cited 401/Games/Anime events first; never mark unverified stores as sold out.
seed={
 'schemaVersion':1,
 'meta':{'title':'OP-18 Ticket Radar','lastChecked':None,'snapshotDate':'2026-11-01','checker':'Initial research snapshot — no live sync yet','timezone':'America/Toronto','source':'Store pages and published event tracker'},
 'stores':objstores,'events':events,
 'discoveries':[],
 'activity':[{'id':'seed','type':'info','timestamp':'2026-11-01T19:00:00-05:00','message':'Initial OP-18 event list imported. Ticket availability is a November 1 snapshot, not a live reading.'}],
 'checks':[]
}
(root/'data/seed.json').write_text(json.dumps(seed,indent=2,ensure_ascii=False)+'\n')
(root/'data/status.json').write_text(json.dumps(seed,indent=2,ensure_ascii=False)+'\n')
(root/'data/seed.js').write_text('window.OP18_SEED = '+json.dumps(seed,ensure_ascii=False)+';\n')
print(len(objstores),'stores',len(events),'events')
