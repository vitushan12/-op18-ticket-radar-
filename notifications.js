(async()=>{
 const status=document.getElementById('push-status'), enable=document.getElementById('enable-push'), disable=document.getElementById('disable-push');
 const say=t=>status.textContent=t;
 try {
  const config=await fetch('./push-config.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();});
  if(!config.appId){say('Notifications are not active yet: the owner must connect the push service. The tracker still updates normally.');return;}
  const ios=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  if(ios&&!navigator.standalone&&!matchMedia('(display-mode: standalone)').matches){say('Open OP18 Radar from its Home Screen icon to enable iPhone notifications.');return;}
  if(!('PushManager' in window)&&!('serviceWorker' in navigator)){say('This browser does not support Web Push.');return;}
  window.OneSignalDeferred=window.OneSignalDeferred||[];
  window.OneSignalDeferred.push(async os=>{
   try{
    const scope=new URL('./push/',location.href).pathname;
    await os.init({appId:config.appId,serviceWorkerPath:scope.slice(1)+'OneSignalSDKWorker.js',serviceWorkerParam:{scope},notifyButton:{enable:false},welcomeNotification:{disable:false,title:'OP18 Radar alerts enabled',message:'You will receive alerts for newly available tickets.',url:new URL('./',location.href).href}});
    if(!os.Notifications.isPushSupported()){say('Push is unavailable here. On iPhone, use the installed Home Screen app.');return;}
    function sync(){const on=os.User.PushSubscription.optedIn;enable.disabled=!!on;disable.hidden=!on;say(on?'Notifications enabled on this device.':Notification.permission==='denied'?'Notifications are blocked. Allow them in your device notification settings, then reopen the app.':'Ready: tap Enable notifications, then Allow.');}
    os.User.PushSubscription.addEventListener('change',sync);os.Notifications.addEventListener('permissionChange',sync);
    enable.onclick=async()=>{try{await os.User.PushSubscription.optIn();sync();}catch(e){say('Could not enable notifications. Please reopen the app and try again.');}};
    disable.onclick=async()=>{try{await os.User.PushSubscription.optOut();sync();}catch(e){say('Could not turn off notifications. Try again.');}};
    sync();
   }catch(e){say('Push service setup could not be loaded. Please try again later.');}
  });
  const sdk=document.createElement('script');sdk.src='https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js';sdk.defer=true;sdk.onerror=()=>say('Could not reach the notification service. Check your connection and try again.');document.head.append(sdk);
 }catch(e){say('Could not check notification setup. Please refresh when online.');}
})();
