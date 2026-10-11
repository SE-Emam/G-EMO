[app]
title = EMO
package.name = emo
package.domain = com.emam
source.dir = .
source.include_exts = py,json,png,md
version = 1.0.0
requirements = python3,kivy
android.add_src = android/src
android.res_xml = android/res/xml/gemo_accessibility_service.xml
android.extra_manifest_application_arguments = android/extra_manifest_application_arguments.xml
p4a.branch = develop
p4a.commit = d2ee8c5
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,FOREGROUND_SERVICE,POST_NOTIFICATIONS
android.api = 35
android.minapi = 26
android.ndk = 27c
android.archs = arm64-v8a,armeabi-v7a,x86_64
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
