package com.emam.emo;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;
import android.content.SharedPreferences;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Explicit opt-in, Gemini-package-only command bridge.
 * It persists only text explicitly addressed with "EMO:"; it does not record
 * general screen contents, passwords, clipboard data, or arbitrary UI trees.
 */
public final class GeminiAccessibilityService extends AccessibilityService {
    private static final String GEMINI_PACKAGE = "com.google.android.apps.bard";
    private static final Pattern COMMAND = Pattern.compile("(?is)(?:^|\\s)EMO\\s*[:：]\\s*(.{1,1000})");
    private static final long DEDUP_WINDOW_MS = 2500L;
    private String lastCommand = "";
    private long lastCommandAt = 0L;

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null || event.getPackageName() == null) return;
        if (!GEMINI_PACKAGE.contentEquals(event.getPackageName())) return;
        if (event.isPassword()) return;

        CharSequence className = event.getClassName();
        if (className != null) {
            String lower = className.toString().toLowerCase(java.util.Locale.ROOT);
            if (lower.contains("login") || lower.contains("signin") ||
                lower.contains("password") || lower.contains("auth") ||
                lower.contains("consent")) return;
        }

        CharSequence eventText = boundedEventText(event);
        if (eventText == null) return;
        Matcher matcher = COMMAND.matcher(eventText);
        if (!matcher.find()) return;

        String command = matcher.group(1).trim();
        if (command.isEmpty() || command.length() > 1000) return;
        long now = System.currentTimeMillis();
        if (command.equals(lastCommand) && now - lastCommandAt < DEDUP_WINDOW_MS) return;
        lastCommand = command;
        lastCommandAt = now;
        writeCommandFile(command, now);
    }

    private CharSequence boundedEventText(AccessibilityEvent event) {
        StringBuilder builder = new StringBuilder();
        for (CharSequence item : event.getText()) {
            if (item == null) continue;
            if (builder.length() > 0) builder.append(' ');
            int remaining = 4000 - builder.length();
            if (remaining <= 0) break;
            String value = item.toString();
            builder.append(value, 0, Math.min(value.length(), remaining));
        }
        return builder.length() == 0 ? null : builder.toString();
    }

    private void writeCommandFile(String command, long timestamp) {
        File inbox = new File(getFilesDir(), "gemo_inbox");
        if (!inbox.exists() && !inbox.mkdirs()) return;
        String id = UUID.randomUUID().toString();
        File temporary = new File(inbox, id + ".tmp");
        File target = new File(inbox, id + ".json");
        String payload = "{\"request_id\":\"" + id + "\",\"source_package\":\"" +
            GEMINI_PACKAGE + "\",\"timestamp_ms\":" + timestamp +
            ",\"command\":\"" + jsonEscape(command) + "\"}";
        try (FileOutputStream stream = new FileOutputStream(temporary)) {
            stream.write(payload.getBytes(StandardCharsets.UTF_8));
            stream.getFD().sync();
            if (!temporary.renameTo(target)) temporary.delete();
        } catch (Exception ignored) {
            // Fail closed. Do not log command text or exception details.
            temporary.delete();
        }
    }

    private String jsonEscape(String value) {
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 0x20) out.append(String.format("\\u%04x", (int)c));
                    else out.append(c);
            }
        }
        return out.toString();
    }

    @Override
    public void onInterrupt() {
        // No queued command is executed from this callback.
    }
}
