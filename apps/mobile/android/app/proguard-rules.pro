# ProGuard/R8 rules for Test-Agent Android App (§1.1.1)
# Code obfuscation + shrinking for release builds

# Keep Flutter engine classes
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }

# Keep API service classes (used via reflection)
-keep class dev.testagent.mobile.** { *; }

# Remove logging in release
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
}

# String encryption (StringFog compatible)
# If using StringFog: uncomment and add StringFog gradle plugin
# -keep class com.github.megatronking.stringfog.** { *; }
