"""Send newly available ticket activity through OneSignal; never expose credentials."""
import json, os, uuid
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'data/push-state.json'
URL='https://vitushan12.github.io/-op18-ticket-radar-/'
def candidates(data,seen):
 return [a for a in reversed(data.get('activity',[])) if a.get('type')=='available' and a['id'] not in seen]
def main():
 app=os.environ.get('ONESIGNAL_APP_ID');key=os.environ.get('ONESIGNAL_REST_API_KEY')
 if not app or not key:
  print('Push inactive: configure OneSignal App ID and API key.');return
 data=json.loads((ROOT/'data/status.json').read_text())
 state=json.loads(STATE.read_text()) if STATE.exists() else None
 if state is None:
  STATE.write_text(json.dumps({'seen':[a['id'] for a in data.get('activity',[])]}))
  print('Push baseline saved; historical alerts will not be sent.');return
 seen=set(state['seen']); failures=0
 for a in candidates(data,seen):
  payload={'app_id':app,'target_channel':'push','included_segments':['All'],'headings':{'en':'OP-18 tickets available'},'contents':{'en':a['message'][:900]},'url':URL,'idempotency_key':str(uuid.uuid5(uuid.NAMESPACE_URL,app+':'+a['id']))}
  try:
   r=requests.post('https://api.onesignal.com/notifications',headers={'Authorization':'Key '+key},json=payload,timeout=30)
   if not r.ok or not r.json().get('id'):
    failures+=1;continue
   seen.add(a['id'])
  except (requests.RequestException,ValueError): failures+=1
 STATE.write_text(json.dumps({'seen':sorted(seen)}))
 print('Push processing complete; unsuccessful sends:',failures)
 if failures:print('::warning::Some push sends failed or had no subscribers; inspect OneSignal setup. They will be retried while present in the activity feed.')
if __name__=='__main__':main()
