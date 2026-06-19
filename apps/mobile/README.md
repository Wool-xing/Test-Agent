# Test-Agent Mobile

PWA + Capacitor mobile app for iOS and Android. Connects to a Test-Agent backend server.

## Architecture

```
Mobile App (Capacitor)
  └── Web UI (React PWA — runtime/web/)
        └── HTTP → Test-Agent Backend (FastAPI :8800)
```

## Quick Start (Browser PWA)

1. Start backend: `uvicorn runtime.api.main:app --host 0.0.0.0 --port 8800`
2. Open `http://<server-ip>:5173` on your phone (same WiFi)
3. "Add to Home Screen" from browser menu → installs as PWA

## Build for App Stores

```bash
# 1. Install Capacitor
cd mobile && npm install

# 2. Build web UI
npm run build

# 3. Add platforms
npx cap add ios
npx cap add android

# 4. Open in Xcode / Android Studio
npx cap open ios      # → Xcode → Archive → App Store
npx cap open android  # → Android Studio → Build → Play Store
```

## App Store Requirements

- **iOS**: Apple Developer account ($99/yr), Xcode 16+, macOS
- **Android**: Google Play Console ($25 one-time), Android Studio

## Compatibility

| Platform | Min Version | Status |
| ---------- | ------------- | -------- |
| iOS | 14.0+ | Full PWA + Capacitor |
| Android | 8.0+ (API 26) | Full PWA + Capacitor |
| iPadOS | 14.0+ | PWA adaptive layout |
| Android Tablet | 8.0+ | PWA adaptive layout |

## Backend Connection

The mobile app connects to a Test-Agent backend server. Set the server address in Settings → Backend URL. Default: `http://localhost:8800`.

For remote use, deploy the backend to a cloud server and configure the URL.
