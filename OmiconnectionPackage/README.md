# Omi React Native SDK

A reusable React Native BLE SDK for Omi devices. It supports discovery, connection lifecycle events, audio streaming, codec detection, and battery level reads.

## Install

```sh
npm install @omiai/omi-react-native react-native-ble-plx
```

For iOS, run `npx pod-install` after installing dependencies. Add `NSBluetoothAlwaysUsageDescription` to your iOS `Info.plist`. On Android, the SDK requests the required Bluetooth runtime permissions; declare the matching Bluetooth permissions in the app manifest.

## Connect an Omi device

```tsx
import { OmiConnection, requestBluetoothPermissions } from "@omiai/omi-react-native";

const omi = new OmiConnection();
await requestBluetoothPermissions();

const stopScan = omi.scan((device) => {
  console.log("Found", device.name, device.id);
  stopScan();
  void omi.connect(device.id);
}, { requireOmiService: true, timeoutMs: 10_000 });

omi.onConnectionChange((device, connected, error) => {
  if (error) console.warn("Omi connection error", error);
  console.log(connected ? `Connected to ${device?.name}` : "Disconnected");
});
```

## Read device data and stream audio

```ts
const codec = await omi.getAudioCodec();       // pcm8, pcm16, opus, or unknown
const battery = await omi.getBatteryLevel();   // 0–100, or null when unavailable

const stopAudio = await omi.startAudioStream((payload) => {
  // payload is Uint8Array audio data; Omi's 3-byte BLE header is removed.
  uploadToSpeechToText(payload, codec);
});

stopAudio();
await omi.disconnect();
omi.destroy();
```

## Verify a real Omi device

Run this on a physical Android/iOS phone after selecting a scanned device. It logs scan, connection, service discovery, codec, battery, streaming, and error events to Metro/Xcode/Logcat. A resolved report means the phone connected to the Omi and its core audio service was successfully read.

```ts
const report = await omi.diagnose(device.id);
console.log("Omi verified", report);
```

When `startAudioStream` or `useOmiAudioStream` is active, each incoming audio packet is printed as its byte length and byte payload. Audio data may contain sensitive speech; provide a custom `logger` to `new OmiConnection(manager, { logger })` to suppress or redirect these logs in production.

## React audio-stream hook

```tsx
const { start, stop, isStreaming, error } = useOmiAudioStream(omi, (audio) => {
  // send audio to your transcription service
});

// Use start() for the UI's Start button and stop() for its Stop button.
```

## API

- `OmiConnection`: recommended low-level BLE API with device selection.
- `OmiClient`, `BleOmiTransport`, `OmiProvider`, and `useOmi`: React-friendly compatibility API.
- `requestBluetoothPermissions()`: Android runtime-permission helper.
- `OMI_SERVICE_UUID` and related protocol constants: Omi BLE identifiers.

Run checks with `npm test` and `npm run typecheck`. A physical Android or iOS device with an Omi device is required to validate Bluetooth hardware behavior.
