# Retrofit inspects generic signatures and method/parameter annotations at runtime.
-keepattributes Signature, InnerClasses, EnclosingMethod
-keepattributes RuntimeVisibleAnnotations, RuntimeVisibleParameterAnnotations, AnnotationDefault

-keep,allowoptimization,allowobfuscation interface com.example.myapplication.api.SentinelApiService
-keepclasseswithmembers,allowshrinking,allowoptimization,allowobfuscation class * {
    @retrofit2.http.* <methods>;
}

# Gson maps these DTO fields reflectively. Preserve field names, including fields
# that use the default JSON name rather than @SerializedName.
-keepclassmembers,allowoptimization class com.example.myapplication.models.** {
    <fields>;
}
-keepclassmembers,allowoptimization class com.example.myapplication.models.** {
    public <init>();
}
