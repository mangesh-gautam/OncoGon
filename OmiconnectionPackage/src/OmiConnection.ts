import { BleManager, Device, Subscription } from "react-native-ble-plx";
import { decodeBase64 } from "./base64";
import {
  BATTERY_LEVEL_CHARACTERISTIC_UUID,
  BATTERY_SERVICE_UUID,
  OMI_AUDIO_CODEC_CHARACTERISTIC_UUID,
  OMI_AUDIO_DATA_CHARACTERISTIC_UUID,
  OMI_AUDIO_PACKET_HEADER_BYTES,
  OMI_SERVICE_UUID,
} from "./protocol";
import { BleAudioCodec } from "./types";
import type { OmiDevice, ScanOptions } from "./types";

type CharacteristicLike = {
  uuid: string;
  value: string | null;
  read(): Promise<CharacteristicLike>;
  monitor(callback: (error: Error | null, characteristic: CharacteristicLike | null) => void): Subscription;
};
type ServiceLike = { uuid: string; characteristics(): Promise<CharacteristicLike[]> };
type OmiBleDevice = Device & {
  services(): Promise<ServiceLike[]>;
  onDisconnected(listener: (error: Error | null, device: Device | null) => void): Subscription;
};

export type ConnectionListener = (device: OmiDevice | null, connected: boolean, error?: Error) => void;
export type OmiLogger = Pick<Console, "debug" | "info" | "warn" | "error">;
export type OmiConnectionOptions = {
  logger?: OmiLogger;
  /** Reconnect after an unexpected device-side disconnect. Defaults to true. */
  autoReconnect?: boolean;
  reconnectDelayMs?: number;
};
export type OmiDiagnosticReport = {
  device: OmiDevice;
  bluetoothState: string;
  audioCodec: BleAudioCodec;
  batteryLevel: number | null;
};

/** Low-level Omi BLE client. Scan first, then connect using a selected device id. */
export class OmiConnection {
  private readonly manager: BleManager;
  private device: OmiBleDevice | null = null;
  private scanTimer: ReturnType<typeof setTimeout> | null = null;
  private audioSubscription: Subscription | null = null;
  private disconnectSubscription: Subscription | null = null;
  private readonly connectionListeners = new Set<ConnectionListener>();
  private readonly logger: OmiLogger;
  private readonly autoReconnect: boolean;
  private readonly reconnectDelayMs: number;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private lastDeviceId: string | null = null;
  private explicitDisconnect = false;

  constructor(manager = new BleManager(), options: OmiConnectionOptions = {}) {
    this.manager = manager;
    this.logger = options.logger ?? console;
    this.autoReconnect = options.autoReconnect ?? true;
    this.reconnectDelayMs = options.reconnectDelayMs ?? 1_500;
  }

  get connectedDevice(): OmiDevice | null {
    return this.device ? toOmiDevice(this.device) : null;
  }

  async getBluetoothState(): Promise<string> {
    const state = await this.manager.state();
    this.logger.info("[Omi] Bluetooth state:", state);
    return state;
  }

  async enableBluetooth(): Promise<boolean> {
    try {
      await this.manager.enable();
      return true;
    } catch {
      return false;
    }
  }

  scan(onDevice: (device: OmiDevice) => void, options: ScanOptions = {}): () => void {
    const { timeoutMs = 10_000, requireOmiService = false } = options;
    const seen = new Set<string>();
    this.stopScan();
    this.logger.info("[Omi] Starting BLE scan", { timeoutMs, requireOmiService });
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

  /**
   * Compatibility alias for the original Omi React Native API. It deliberately
   * scans all BLE peripherals: an Omi may not advertise its local name or
   * Omi service UUID until it has been connected.
   */
  scanForDevices(onDevice: (device: OmiDevice) => void, timeoutMs = 10_000): () => void {
    return this.scan(onDevice, { timeoutMs, requireOmiService: false });
  }

  stopScan(): void {
    if (this.scanTimer) clearTimeout(this.scanTimer);
    this.scanTimer = null;
    this.manager.stopDeviceScan();
    this.logger.debug("[Omi] BLE scan stopped");
  }

  async connect(deviceId: string): Promise<OmiDevice> {
    if (this.device?.id === deviceId) return toOmiDevice(this.device);
    await this.disconnect();
    this.cancelReconnect();
    this.explicitDisconnect = false;
    this.lastDeviceId = deviceId;
    this.stopScan();
    this.logger.info("[Omi] Connecting to device:", deviceId);
    try {
      const device = (await this.manager.connectToDevice(deviceId, { requestMTU: 512 })) as OmiBleDevice;
      await device.discoverAllServicesAndCharacteristics();
      await requestHighConnectionPriority(device);
      this.device = device;
      this.logger.info("[Omi] Connected; services and characteristics discovered:", toOmiDevice(device));
      this.disconnectSubscription = device.onDisconnected((error) => {
        const shouldReconnect = this.autoReconnect && !this.explicitDisconnect && this.lastDeviceId !== null;
        this.clearDevice();
        this.logger.warn("[Omi] Device disconnected:", error ?? "remote disconnect");
        this.emitConnection(null, false, error ?? undefined);
        if (shouldReconnect) this.scheduleReconnect();
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

  async disconnect(): Promise<void> {
    this.explicitDisconnect = true;
    this.lastDeviceId = null;
    this.cancelReconnect();
    const device = this.device;
    this.clearDevice();
    if (device) await device.cancelConnection();
    this.logger.info("[Omi] Disconnected");
    this.emitConnection(null, false);
  }

  isConnected(): boolean {
    return this.device !== null;
  }

  onConnectionChange(listener: ConnectionListener): () => void {
    this.connectionListeners.add(listener);
    return () => this.connectionListeners.delete(listener);
  }

  async getAudioCodec(): Promise<BleAudioCodec> {
    const characteristic = await this.findCharacteristic(OMI_SERVICE_UUID, OMI_AUDIO_CODEC_CHARACTERISTIC_UUID);
    const bytes = decodeBase64((await characteristic.read()).value ?? "");
    const codec = bytes[0] === 0 ? BleAudioCodec.PCM16
      : bytes[0] === 1 ? BleAudioCodec.PCM8
      : bytes[0] === 20 || bytes[0] === 21 ? BleAudioCodec.OPUS
      : BleAudioCodec.UNKNOWN;
    this.logger.info("[Omi] Audio codec:", codec);
    return codec;
  }

  async getBatteryLevel(): Promise<number | null> {
    const characteristic = await this.findCharacteristic(BATTERY_SERVICE_UUID, BATTERY_LEVEL_CHARACTERISTIC_UUID);
    const level = decodeBase64((await characteristic.read()).value ?? "")[0];
    const batteryLevel = level === undefined ? null : level;
    this.logger.info("[Omi] Battery level:", batteryLevel);
    return batteryLevel;
  }

  async startAudioStream(onAudio: (data: Uint8Array) => void, includePacketHeader = false): Promise<() => void> {
    this.stopAudioStream();
    const characteristic = await this.findCharacteristic(OMI_SERVICE_UUID, OMI_AUDIO_DATA_CHARACTERISTIC_UUID);
    this.logger.info("[Omi] Starting audio stream", { includePacketHeader });
    this.audioSubscription = characteristic.monitor((error, update) => {
      if (error) {
        this.logger.error("[Omi] Audio stream error:", error);
        return;
      }
      if (!update?.value) return;
      const packet = decodeBase64(update.value);
      const audio = includePacketHeader ? packet : packet.slice(OMI_AUDIO_PACKET_HEADER_BYTES);
      // Audio is logged as bytes for troubleshooting. Disable the default logger in production
      // if audio content must not be visible in device logs.
      this.logger.debug("[Omi] Audio packet received:", { bytes: audio.length, payload: Array.from(audio) });
      onAudio(audio);
    });
    return () => this.stopAudioStream();
  }

  stopAudioStream(): void {
    this.audioSubscription?.remove();
    this.audioSubscription = null;
    this.logger.info("[Omi] Audio stream stopped");
  }

  /** Connects and validates the core Omi BLE services. Run this on a real phone with an Omi device. */
  async diagnose(deviceId: string): Promise<OmiDiagnosticReport> {
    this.logger.info("[Omi] Starting connection diagnostic");
    const bluetoothState = await this.getBluetoothState();
    if (bluetoothState !== "PoweredOn") {
      throw new Error(`Bluetooth must be PoweredOn; current state is ${bluetoothState}.`);
    }
    const device = await this.connect(deviceId);
    const audioCodec = await this.getAudioCodec();
    let batteryLevel: number | null = null;
    try {
      batteryLevel = await this.getBatteryLevel();
    } catch (error) {
      this.logger.warn("[Omi] Battery service is unavailable:", error);
    }
    const report = { device, bluetoothState, audioCodec, batteryLevel };
    this.logger.info("[Omi] Connection diagnostic passed:", report);
    return report;
  }

  destroy(): void {
    this.stopScan();
    this.cancelReconnect();
    this.clearDevice();
    this.manager.destroy();
  }

  private async findCharacteristic(serviceUuid: string, characteristicUuid: string): Promise<CharacteristicLike> {
    if (!this.device) throw new Error("No Omi device is connected.");
    const service = (await this.device.services()).find((item) => sameUuid(item.uuid, serviceUuid));
    if (!service) throw new Error(`Required BLE service ${serviceUuid} was not found on this device.`);
    const characteristic = (await service.characteristics()).find((item) => sameUuid(item.uuid, characteristicUuid));
    if (!characteristic) throw new Error(`Required BLE characteristic ${characteristicUuid} was not found on this device.`);
    return characteristic;
  }

  private clearDevice(): void {
    this.stopAudioStream();
    this.disconnectSubscription?.remove();
    this.disconnectSubscription = null;
    this.device = null;
  }

  private emitConnection(device: OmiDevice | null, connected: boolean, error?: Error): void {
    this.connectionListeners.forEach((listener) => listener(device, connected, error));
  }

  private scheduleReconnect(): void {
    const deviceId = this.lastDeviceId;
    if (!deviceId || this.reconnectTimer) return;
    this.logger.info("[Omi] Reconnecting after unexpected disconnect…", { delayMs: this.reconnectDelayMs });
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      void this.connect(deviceId).catch((error) => {
        this.logger.error("[Omi] Automatic reconnect failed:", error);
        this.scheduleReconnect();
      });
    }, this.reconnectDelayMs);
  }

  private cancelReconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }
}

function sameUuid(left: string, right: string): boolean {
  return left.toLowerCase() === right.toLowerCase();
}

function toOmiDevice(device: Pick<Device, "id" | "name" | "rssi">): OmiDevice {
  return { id: device.id, name: device.name, rssi: device.rssi };
}

function asError(cause: unknown): Error {
  return cause instanceof Error ? cause : new Error(String(cause));
}

async function requestHighConnectionPriority(device: Device): Promise<void> {
  const prioritizedDevice = device as Device & { requestConnectionPriority?: (priority: "high") => Promise<Device> };
  if (!prioritizedDevice.requestConnectionPriority) return;
  try {
    await prioritizedDevice.requestConnectionPriority("high");
  } catch {
    // Connection priority is an Android optimization; it is not required for compatibility.
  }
}
