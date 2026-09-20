import java.net.URI

plugins {
    alias(libs.plugins.android.application)
}

fun normalizeApiBaseUrl(rawValue: String, requireHttps: Boolean): String {
    val value = rawValue.trim()
    require(value.isNotEmpty()) { "SENTINEL_API_BASE_URL must not be blank" }
    require(value.none { it.isISOControl() }) { "SENTINEL_API_BASE_URL contains invalid characters" }

    val uri = URI(value)
    require(uri.host != null && uri.userInfo == null && uri.query == null && uri.fragment == null) {
        "SENTINEL_API_BASE_URL must be an HTTP(S) API origin without credentials, a query, or a fragment"
    }
    val scheme = uri.scheme?.lowercase()
    require(scheme == "https" || (!requireHttps && scheme == "http")) {
        if (requireHttps) "Release SENTINEL_API_BASE_URL must use HTTPS" else "SENTINEL_API_BASE_URL must use HTTP or HTTPS"
    }
    return if (value.endsWith('/')) value else "$value/"
}

fun quoteBuildConfigValue(value: String): String = buildString {
    append('"')
    value.forEach { character ->
        when (character) {
            '\\' -> append("\\\\")
            '"' -> append("\\\"")
            '\n' -> append("\\n")
            '\r' -> append("\\r")
            '\t' -> append("\\t")
            else -> append(character)
        }
    }
    append('"')
}

val configuredApiBaseUrl = providers.gradleProperty("SENTINEL_API_BASE_URL")
    .orElse(providers.environmentVariable("SENTINEL_API_BASE_URL"))
    .orNull
val debugApiBaseUrl = normalizeApiBaseUrl(
    configuredApiBaseUrl ?: "http://10.0.2.2:8000/",
    requireHttps = false
)
val releaseApiBaseUrl = configuredApiBaseUrl
    ?.let { runCatching { normalizeApiBaseUrl(it, requireHttps = true) }.getOrNull() }

android {
    namespace = "com.example.myapplication"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.myapplication"
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    androidResources {
        localeFilters += listOf("en")
    }

    buildTypes {
        getByName("debug") {
            buildConfigField("String", "SENTINEL_API_BASE_URL", quoteBuildConfigValue(debugApiBaseUrl))
            manifestPlaceholders["usesCleartextTraffic"] = true
        }
        getByName("release") {
            buildConfigField(
                "String",
                "SENTINEL_API_BASE_URL",
                quoteBuildConfigValue(releaseApiBaseUrl ?: "https://sentinel-api.invalid/")
            )
            manifestPlaceholders["usesCleartextTraffic"] = false
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    packaging {
        resources.excludes += setOf(
            "META-INF/AL2.0",
            "META-INF/LGPL2.1",
            "META-INF/LICENSE*",
            "META-INF/NOTICE*"
        )
    }
}

// Keep IDE sync/debug builds usable without production configuration, but never
// produce a release artifact with a placeholder, cleartext, or credentialed URL.
tasks.matching { it.name == "preReleaseBuild" }.configureEach {
    doFirst {
        if (releaseApiBaseUrl == null) {
            throw GradleException(
                "Set SENTINEL_API_BASE_URL to a credential-free HTTPS URL via a Gradle property or environment variable before building release"
            )
        }
    }
}

dependencies {
    implementation(libs.appcompat)
    implementation(libs.constraintlayout)
    implementation(libs.material)

    implementation(libs.retrofit)
    implementation(libs.retrofit.converter.gson)
    implementation(libs.okhttp.logging)

    implementation(libs.lifecycle.viewmodel)
    implementation(libs.lifecycle.livedata)
    implementation(libs.work.runtime)
    implementation(libs.security.crypto)

    testImplementation(libs.junit)
    androidTestImplementation(libs.espresso.core)
    androidTestImplementation(libs.ext.junit)
}
