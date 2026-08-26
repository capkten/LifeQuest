package com.lifequest.app;

import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.Settings;

import androidx.core.content.FileProvider;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.File;

@CapacitorPlugin(name = "AppUpdater")
public class AppUpdaterPlugin extends Plugin {
    private static final String APK_MIME_TYPE = "application/vnd.android.package-archive";
    private static AppUpdaterPlugin instance;
    private BroadcastReceiver downloadReceiver;
    private File pendingInstall;

    @Override
    public void load() {
        super.load();
        instance = this;
    }

    @PluginMethod
    public void startDownload(PluginCall call) {
        String url = call.getString("url");
        if (url == null || url.trim().isEmpty()) {
            call.reject("更新地址为空");
            return;
        }

        Context context = getContext();
        File downloadDir = context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
        if (downloadDir == null) {
            call.reject("无法访问应用下载目录");
            return;
        }
        if (!downloadDir.exists() && !downloadDir.mkdirs()) {
            call.reject("无法创建应用下载目录");
            return;
        }

        File apkFile = new File(downloadDir, "lifequest-update.apk");
        if (apkFile.exists() && !apkFile.delete()) {
            call.reject("无法清理上一次更新文件");
            return;
        }

        DownloadManager downloadManager = (DownloadManager) context.getSystemService(Context.DOWNLOAD_SERVICE);
        if (downloadManager == null) {
            call.reject("系统下载服务不可用");
            return;
        }

        final long[] downloadId = {-1L};
        downloadReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context receiverContext, Intent intent) {
                if (!DownloadManager.ACTION_DOWNLOAD_COMPLETE.equals(intent.getAction())) return;
                long completedId = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L);
                if (completedId != downloadId[0]) return;
                unregisterDownloadReceiver(receiverContext);

                DownloadManager.Query query = new DownloadManager.Query().setFilterById(completedId);
                try (android.database.Cursor cursor = downloadManager.query(query)) {
                    if (cursor != null && cursor.moveToFirst()
                            && cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS))
                            == DownloadManager.STATUS_SUCCESSFUL) {
                        installApk(apkFile);
                    }
                }
            }
        };

        IntentFilter filter = new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            // DownloadManager is a system service; its completion broadcast must reach
            // this dynamically registered receiver on Android 13+.
            context.registerReceiver(downloadReceiver, filter, Context.RECEIVER_EXPORTED);
        } else {
            context.registerReceiver(downloadReceiver, filter);
        }

        try {
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url))
                    .setTitle("LifeQuest 更新")
                    .setDescription("正在下载最新版本")
                    .setMimeType(APK_MIME_TYPE)
                    .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    .setAllowedOverMetered(true)
                    .setAllowedOverRoaming(true)
                    .setDestinationInExternalFilesDir(context, Environment.DIRECTORY_DOWNLOADS, apkFile.getName());
            downloadId[0] = downloadManager.enqueue(request);

            JSObject result = new JSObject();
            result.put("downloadId", downloadId[0]);
            call.resolve(result);
        } catch (Exception error) {
            unregisterDownloadReceiver(context);
            call.reject("无法开始下载更新", error);
        }
    }

    private void installApk(File apkFile) {
        Context context = getContext();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                && !context.getPackageManager().canRequestPackageInstalls()) {
            pendingInstall = apkFile;
            Intent settingsIntent = new Intent(
                    Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:" + context.getPackageName())
            );
            settingsIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(settingsIntent);
            return;
        }

        pendingInstall = null;

        Uri apkUri = FileProvider.getUriForFile(
                context,
                context.getPackageName() + ".fileprovider",
                apkFile
        );
        Intent installIntent = new Intent(Intent.ACTION_VIEW);
        installIntent.setDataAndType(apkUri, APK_MIME_TYPE);
        installIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
        context.startActivity(installIntent);
    }

    public static void resumePendingInstall() {
        if (instance == null || instance.pendingInstall == null) return;
        File apkFile = instance.pendingInstall;
        if (apkFile.exists()) instance.installApk(apkFile);
    }

    private void unregisterDownloadReceiver(Context context) {
        if (downloadReceiver == null) return;
        try {
            context.unregisterReceiver(downloadReceiver);
        } catch (IllegalArgumentException ignored) {
            // Receiver was already unregistered.
        }
        downloadReceiver = null;
    }
}
