import { BleManager } from "react-native-ble-plx";
import { decodeBase64 } from "./base64";
import { BATTERY_LEVEL_CHARACTERISTIC_UUID, BATTERY_SERVICE_UUID, OMI_AUDIO_CODEC_CHARACTERISTIC_UUID, OMI_AUDIO_DATA_CHARACTERISTIC_UUID, OMI_AUDIO_PACKET_HEADER_BYTES, OMI_SERVICE_UUID } from "./protocol";
import { BleAudioCodec } from "./types";
/** Low-level Omi BLE client. Scan first, then connect using a selected device id. */
export class OmiConnection {
  device = null;
  scanTimer = null;
  audioSubscription = null;
  disconnectSubscription = null;
  connectionListeners = new Set();
  constructor(manager = new BleManager(), options = {}) {
    this.manager = manager;
    this.logger = options.logger ?? console;
  }
  get connectedDevice() {
    return this.device ? toOmiDevice(this.device) : null;
  }
  async getBluetoothState() {
    const state = await this.manager.state();
    this.logger.info("[Omi] Bluetooth state:", state);
    return state;
  }
  async enableBluetooth() {
    try {
      await this.manager.enable();
      return true;
    } catch {
      return false;
    }
  }
  scan(onDevice, options = {}) {
    const {
      timeoutMs = 10_000,
      requireOmiService = false
    } = options;
    const seen = new Set();
    this.stopScan();
    this.logger.info("[Omi] Starting BLE scan", {
      timeoutMs,
      requireOmiService
    });
    this.manager.startDeviceScan(requireOmiService ? [OMI_SERVICE_UUID] : null, null, (error, device) => {
      if (error) {
        this.logger.error("[Omi] BLE scan error:", error);
        return;
      }
      if (!device || seen.has(device.id)) return;
      seen.add(device.id);
      const found = toOmiDevice(device);
      this.logger.info("[Omi] Found device:", found);
      onDevice(found);
    });
    this.scanTimer = setTimeout(() => this.stopScan(), timeoutMs);
    return () => this.stopScan();
  }
  stopScan() {
    if (this.scanTimer) clearTimeout(this.scanTimer);
    this.scanTimer = null;
    this.manager.stopDeviceScan();
    this.logger.debug("[Omi] BLE scan stopped");
  }
  async connect(deviceId) {
    var _this$device;
    if (((_this$device = this.device) === null || _this$device === void 0 ? void 0 : _this$device.id) === deviceId) return toOmiDevice(this.device);
    await this.disconnect();
    this.stopScan();
    this.logger.info("[Omi] Connecting to device:", deviceId);
    try {
      const device = await this.manager.connectToDevice(deviceId, {
        requestMTU: 512
      });
      await device.discoverAllServicesAndCharacteristics();
      this.device = device;
      this.logger.info("[Omi] Connected; services and characteristics discovered:", toOmiDevice(device));
      this.disconnectSubscription = device.onDisconnected(error => {
        this.clearDevice();
        this.logger.warn("[Omi] Device disconnected:", error ?? "remote disconnect");
        this.emitConnection(null, false, error ?? undefined);
      });
      const result = toOmiDevice(device);
      this.emitConnection(result, true);
      return result;
    } catch (cause) {
      const error = asError(cause);
      this.logger.error("[Omi] Connection failed:", error);
      this.clearDevice();
      this.emitConnection(null, false, error);
      throw error;
    }
  }
  async disconnect() {
    const device = this.device;
    this.clearDevice();
    if (device) await device.cancelConnection();
    this.logger.info("[Omi] Disconnected");
    this.emitConnection(null, false);
  }
  isConnected() {
    return this.device !== null;
  }
  onConnectionChange(listener) {
    this.connectionListeners.add(listener);
    return () => this.connectionListeners.delete(listener);
  }
  async getAudioCodec() {
    const characteristic = await this.findCharacteristic(OMI_SERVICE_UUID, OMI_AUDIO_CODEC_CHARACTERISTIC_UUID);
    const bytes = decodeBase64((await characteristic.read()).value ?? "");
    const codec = bytes[0] === 0 ? BleAudioCodec.PCM16 : bytes[0] === 1 ? BleAudioCodec.PCM8 : bytes[0] === 20 || bytes[0] === 21 ? BleAudioCodec.OPUS : BleAudioCodec.UNKNOWN;
    this.logger.info("[Omi] Audio codec:", codec);
    return codec;
  }
  async getBatteryLevel() {
    const characteristic = await this.findCharacteristic(BATTERY_SERVICE_UUID, BATTERY_LEVEL_CHARACTERISTIC_UUID);
    const level = decodeBase64((await characteristic.read()).value ?? "")[0];
    const batteryLevel = level === undefined ? null : level;
    this.logger.info("[Omi] Battery level:", batteryLevel);
    return batteryLevel;
  }
  async startAudioStream(onAudio, includePacketHeader = false) {
    this.stopAudioStream();
    const characteristic = await this.findCharacteristic(OMI_SERVICE_UUID, OMI_AUDIO_DATA_CHARACTERISTIC_UUID);
    this.logger.info("[Omi] Starting audio stream", {
      includePacketHeader
    });
    this.audioSubscription = characteristic.monitor((error, update) => {
      if (error) {
        this.logger.error("[Omi] Audio stream error:", error);
        return;
      }
      if (!(update !== null && update !== void 0 && update.value)) return;
      const packet = decodeBase64(update.value);
      const audio = includePacketHeader ? packet : packet.slice(OMI_AUDIO_PACKET_HEADER_BYTES);
      this.logger.debug("[Omi] Audio packet received:", {
        bytes: audio.length
      });
      onAudio(audio);
    });
    return () => this.stopAudioStream();
  }
  stopAudioStream() {
    var _this$audioSubscripti;
    (_this$audioSubscripti = this.audioSubscription) === null || _this$audioSubscripti === void 0 || _this$audioSubscripti.remove();
    this.audioSubscription = null;
    this.logger.info("[Omi] Audio stream stopped");
  }

  /** Connects and validates the core Omi BLE services. Run this on a real phone with an Omi device. */
  async diagnose(deviceId) {
    this.logger.info("[Omi] Starting connection diagnostic");
    const bluetoothState = await this.getBluetoothState();
    if (bluetoothState !== "PoweredOn") {
      throw new Error(`Bluetooth must be PoweredOn; current state is ${bluetoothState}.`);
    }
    const device = await this.connect(deviceId);
    const audioCodec = await this.getAudioCodec();
    let batteryLevel = null;
    try {
      batteryLevel = await this.getBatteryLevel();
    } catch (error) {
      this.logger.warn("[Omi] Battery service is unavailable:", error);
    }
    const report = {
      device,
      bluetoothState,
      audioCodec,
      batteryLevel
    };
    this.logger.info("[Omi] Connection diagnostic passed:", report);
    return report;
  }
  destroy() {
    this.stopScan();
    this.clearDevice();
    this.manager.destroy();
  }
  async findCharacteristic(serviceUuid, characteristicUuid) {
    if (!this.device) throw new Error("No Omi device is connected.");
    const service = (await this.device.services()).find(item => sameUuid(item.uuid, serviceUuid));
    if (!service) throw new Error(`Required BLE service ${serviceUuid} was not found on this device.`);
    const characteristic = (await service.characteristics()).find(item => sameUuid(item.uuid, characteristicUuid));
    if (!characteristic) throw new Error(`Required BLE characteristic ${characteristicUuid} was not found on this device.`);
    return characteristic;
  }
  clearDevice() {
    var _this$disconnectSubsc;
    this.stopAudioStream();
    (_this$disconnectSubsc = this.disconnectSubscription) === null || _this$disconnectSubsc === void 0 || _this$disconnectSubsc.remove();
    this.disconnectSubscription = null;
    this.device = null;
  }
  emitConnection(device, connected, error) {
    this.connectionListeners.forEach(listener => listener(device, connected, error));
  }
}
function sameUuid(left, right) {
  return left.toLowerCase() === right.toLowerCase();
}
function toOmiDevice(device) {
  return {
    id: device.id,
    name: device.name,
    rssi: device.rssi
  };
}
function asError(cause) {
  return cause instanceof Error ? cause : new Error(String(cause));
}
//# sourceMappingURL=OmiConnection.js.map