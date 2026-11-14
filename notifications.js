/* Delivery is deliberately inactive until a notification service is configured. */
'use strict';
document.getElementById('push-status').textContent =
  'Push and email alerts are not configured for this watchlist. Scheduled checks update the dashboard, but no automatic notification is sent to your phone or email.';
