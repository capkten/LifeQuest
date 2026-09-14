package com.lifequest.app;

import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
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
    private final Handler progressHandler = new Handler(Looper.getMainLooper());
    private Runnable progressPoller;
    private DownloadManager downloadManager;
    private long activeDownloadId = -1L;
    private File activeApkFile;

    @Override
    public void load() {
        super.load();
        instance = this;
    }

    @PluginMethod
    public void startDownload(PluginCall call) {
        if (activeDownloadId != -1L) {
            call.reject("已有更新正在下载");
            return;
        }

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

        downloadManager = (DownloadManager) context.getSystemService(Context.DOWNLOAD_SERVICE);
        if (downloadManager == null) {
            call.reject("系统下载服务不可用");
            return;
        }

        downloadReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context receiverContext, Intent intent) {
                if (!DownloadManager.ACTION_DOWNLOAD_COMPLETE.equals(intent.getAction())) return;
                long completedId = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L);
                if (completedId != activeDownloadId) return;
                pollDownload();
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
            activeApkFile = apkFile;
            activeDownloadId = downloadManager.enqueue(request);
            startProgressPolling();

            JSObject result = new JSObject();
            result.put("downloadId", activeDownloadId);
            call.resolve(result);
        } catch (Exception error) {
            unregisterDownloadReceiver(context);
            stopProgressPolling();
            activeDownloadId = -1L;
            activeApkFile = null;
            call.reject("无法开始下载更新", error);
        }
    }

    private void startProgressPolling() {
        progressPoller = this::pollDownload;
        notifyDownloadProgress("queued", 0, 0L, -1L, null);
        progressHandler.post(progressPoller);
    }

    private void pollDownload() {
        if (downloadManager == null || activeDownloadId == -1L) return;

        DownloadManager.Query query = new DownloadManager.Query().setFilterById(activeDownloadId);
        try (android.database.Cursor cursor = downloadManager.query(query)) {
            if (cursor == null || !cursor.moveToFirst()) {
                finishDownload(false, "找不到更新下载任务，请重试。", 0, 0L, -1L);
                return;
            }

            int status = cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));
            long downloadedBytes = cursor.getLong(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR));
            long totalBytes = cursor.getLong(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES));
            int percent = totalBytes > 0
                    ? (int) Math.min(100, Math.round(downloadedBytes * 100d / totalBytes))
                    : -1;

            if (status == DownloadManager.STATUS_SUCCESSFUL) {
                finishDownload(true, null, 100, downloadedBytes, totalBytes);
                return;
            }
            if (status == DownloadManager.STATUS_FAILED) {
                int reason = cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_REASON));
                finishDownload(false, downloadFailureMessage(reason), percent, downloadedBytes, totalBytes);
                return;
            }

            notifyDownloadProgress("downloading", percent, downloadedBytes, totalBytes, null);
            progressHandler.postDelayed(progressPoller, 500L);
        } catch (Exception error) {
            finishDownload(false, "无法读取更新下载状态，请打开 GitHub 手动下载。", 0, 0L, -1L);
        }
    }

    private String downloadFailureMessage(int reason) {
        switch (reason) {
            case DownloadManager.ERROR_CANNOT_RESUME:
                return "更新下载无法继续，请重试。";
            case DownloadManager.ERROR_DEVICE_NOT_FOUND:
                return "找不到下载存储空间，请检查设备后重试。";
            case DownloadManager.ERROR_FILE_ALREADY_EXISTS:
                return "更新文件已存在，请重试。";
            case DownloadManager.ERROR_FILE_ERROR:
                return "更新文件保存失败，请检查存储空间。";
            case DownloadManager.ERROR_HTTP_DATA_ERROR:
            case DownloadManager.ERROR_UNHANDLED_HTTP_CODE:
                return "更新服务器返回异常，请打开 GitHub 手动下载。";
            case DownloadManager.ERROR_INSUFFICIENT_SPACE:
                return "设备存储空间不足，请清理空间后重试。";
            case DownloadManager.ERROR_TOO_MANY_REDIRECTS:
                return "更新地址跳转次数过多，请打开 GitHub 手动下载。";
            default:
                return "更新下载失败，请打开 GitHub 手动下载。";
        }
    }

    private void finishDownload(boolean successful, String message, int percent, long downloadedBytes, long totalBytes) {
        File apkFile = activeApkFile;
        stopProgressPolling();
        unregisterDownloadReceiver(getContext());
        activeDownloadId = -1L;
        activeApkFile = null;

        if (!successful) {
            notifyDownloadProgress("failed", percent, downloadedBytes, totalBytes, message);
            return;
        }

        notifyDownloadProgress("completed", 100, downloadedBytes, totalBytes, null);
        try {
            installApk(apkFile);
        } catch (Exception error) {
            notifyDownloadProgress("failed", 100, downloadedBytes, totalBytes, "无法打开安装程序，请打开 GitHub 手动下载。");
        }
    }

    private void notifyDownloadProgress(String state, int percent, long downloadedBytes, long totalBytes, String message) {
        JSObject progress = new JSObject();
        progress.put("downloadId", activeDownloadId);
        progress.put("state", state);
        progress.put("percent", percent);
        progress.put("downloadedBytes", downloadedBytes);
        progress.put("totalBytes", totalBytes);
        if (message != null) progress.put("message", message);
        notifyListeners("downloadProgress", progress);
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

    private void stopProgressPolling() {
        if (progressPoller == null) return;
        progressHandler.removeCallbacks(progressPoller);
        progressPoller = null;
    }

    @Override
    protected void handleOnDestroy() {
        stopProgressPolling();
        unregisterDownloadReceiver(getContext());
        super.handleOnDestroy();
    }
}
