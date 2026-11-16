package com.lifequest.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;

import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

import com.capacitorjs.plugins.localnotifications.LocalNotificationManager;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONObject;

import java.util.UUID;

@CapacitorPlugin(name = "CaveNotifications")
public class CaveNotificationsPlugin extends Plugin {
    private static final int NOTIFICATION_ID = 190008;
    private static final String CHANNEL = "cave-ongoing";
    private static final String ACTION = "com.lifequest.app.CAVE_NOTIFICATION";
    private static final String EXTRA = "caveNotificationAction";
    private static final String CONSUMED = "caveNotificationConsumed";
    private JSObject pendingAction;

    @Override
    public void load() {
        captureAction(getActivity().getIntent());
    }

    @Override
    protected void handleOnNewIntent(Intent intent) {
        captureAction(intent);
    }

    private void captureAction(Intent intent) {
        if (intent == null || intent.getBooleanExtra(CONSUMED, false)) return;
        try {
            JSObject event = null;
            if (ACTION.equals(intent.getAction()) && intent.hasExtra(EXTRA)) {
                event = new JSObject(intent.getStringExtra(EXTRA));
                intent.removeExtra(EXTRA);
            } else if (intent.getIntExtra(LocalNotificationManager.NOTIFICATION_INTENT_KEY, -1) == NOTIFICATION_ID) {
                String source = intent.getStringExtra(LocalNotificationManager.NOTIFICATION_OBJ_INTENT_KEY);
                if (source == null) return;
                JSONObject extra = new JSONObject(source).optJSONObject("extra");
                if (extra == null || !"completion".equals(extra.optString("type"))) return;
                event = new JSObject(extra.toString());
                event.put("action", "open");
            }
            if (event == null) return;
            intent.putExtra(CONSUMED, true);
            event.put("eventId", UUID.randomUUID().toString());
            if (hasListeners("notificationAction")) {
                notifyListeners("notificationAction", event);
            } else {
                pendingAction = event;
            }
        } catch (Exception ignored) {
            // Malformed notification payloads never navigate or settle a session.
        }
    }

    @PluginMethod
    public void getPendingAction(PluginCall call) {
        JSObject result = new JSObject();
        result.put("action", pendingAction == null ? JSONObject.NULL : pendingAction);
        pendingAction = null;
        call.resolve(result);
    }

    @PluginMethod
    public void showOngoing(PluginCall call) {
        String sessionId = call.getString("sessionId");
        String ownerId = call.getString("ownerId");
        long deadline = call.getData().optLong("deadlineMs", 0);
        long postedAt = call.getData().optLong("postedAt", System.currentTimeMillis());
        if (sessionId == null || ownerId == null || deadline <= System.currentTimeMillis()) {
            call.reject("入定时间或会话无效");
            return;
        }
        NotificationManagerCompat manager = NotificationManagerCompat.from(getContext());
        if (!manager.areNotificationsEnabled()) {
            call.reject("通知未开启");
            return;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(CHANNEL, "入定进行中", NotificationManager.IMPORTANCE_LOW);
            channel.setSound(null, null);
            channel.enableVibration(false);
            manager.createNotificationChannel(channel);
        }
        PendingIntent open = actionIntent(sessionId, ownerId, postedAt, "open", NOTIFICATION_ID + 1);
        PendingIntent finish = actionIntent(sessionId, ownerId, postedAt, "finish", NOTIFICATION_ID + 2);
        NotificationCompat.Builder notification = new NotificationCompat.Builder(getContext(), CHANNEL)
            .setSmallIcon(com.lifequest.app.R.drawable.ic_stat_cave)
            .setContentTitle("入定中")
            .setContentText(call.getString("taskTitle", "安心入定"))
            .setWhen(deadline)
            .setUsesChronometer(true)
            .setChronometerCountDown(true)
            .setOngoing(true)
            .setAutoCancel(false)
            .setOnlyAlertOnce(true)
            .setSilent(true)
            .setContentIntent(open)
            .addAction(0, "回到入定", open)
            .addAction(0, "收功", finish);
        try {
            manager.notify(NOTIFICATION_ID, notification.build());
            call.resolve();
        } catch (SecurityException error) {
            call.reject("通知未开启");
        }
    }

    private PendingIntent actionIntent(String sessionId, String ownerId, long postedAt, String action, int requestCode) {
        JSObject event = new JSObject();
        event.put("sessionId", sessionId);
        event.put("ownerId", ownerId);
        event.put("postedAt", postedAt);
        event.put("action", action);
        event.put("type", "ongoing");
        Intent intent = new Intent(getContext(), MainActivity.class)
            .setAction(ACTION)
            .setData(Uri.parse("lifequest-notification://session/" + sessionId + "/" + action))
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP)
            .putExtra(EXTRA, event.toString());
        return PendingIntent.getActivity(getContext(), requestCode, intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    @PluginMethod
    public void cancel(PluginCall call) {
        NotificationManagerCompat.from(getContext()).cancel(NOTIFICATION_ID);
        pendingAction = null;
        call.resolve();
    }
}
