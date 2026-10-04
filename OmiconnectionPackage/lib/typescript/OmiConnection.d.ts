import { BleManager } from "react-native-ble-plx";
import { BleAudioCodec } from "./types";
import type { OmiDevice, ScanOptions } from "./types";
export type ConnectionListener = (device: OmiDevice | null, connected: boolean, error?: Error) => void;
export type OmiLogger = Pick<Console, "debug" | "info" | "warn" | "error">;
export type OmiConnectionOptions = {
    logger?: OmiLogger;
};
export type OmiDiagnosticReport = {
    device: OmiDevice;
    bluetoothState: string;
    audioCodec: BleAudioCodec;
    batteryLevel: number | null;
};
/** Low-level Omi BLE client. Scan first, then connect using a selected device id. */
export declare class OmiConnection {
    private readonly manager;
    private device;
    private scanTimer;
    private audioSubscription;
    private disconnectSubscription;
    private readonly connectionListeners;
    private readonly logger;
    constructor(manager?: BleManager, options?: OmiConnectionOptions);
    get connectedDevice(): OmiDevice | null;
    getBluetoothState(): Promise<string>;
    enableBluetooth(): Promise<boolean>;
    scan(onDevice: (device: OmiDevice) => void, options?: ScanOptions): () => void;
    stopScan(): void;
    connect(deviceId: string): Promise<OmiDevice>;
    disconnect(): Promise<void>;
    isConnected(): boolean;
    onConnectionChange(listener: ConnectionListener): () => void;
    getAudioCodec(): Promise<BleAudioCodec>;
    getBatteryLevel(): Promise<number | null>;
    startAudioStream(onAudio: (data: Uint8Array) => void, includePacketHeader?: boolean): Promise<() => void>;
    stopAudioStream(): void;
    /** Connects and validates the core Omi BLE services. Run this on a real phone with an Omi device. */
    diagnose(deviceId: string): Promise<OmiDiagnosticReport>;
    destroy(): void;
    private findCharacteristic;
    private clearDevice;
    private emitConnection;
}
//# sourceMappingURL=OmiConnection.d.ts.map