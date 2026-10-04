export type OmiConnectionState = "idle" | "scanning" | "connecting" | "connected" | "disconnected" | "error";
export type OmiDevice = {
    id: string;
    name: string | null;
    rssi?: number | null;
};
export declare enum BleAudioCodec {
    PCM16 = "pcm16",
    PCM8 = "pcm8",
    OPUS = "opus",
    UNKNOWN = "unknown"
}
export type AudioChunk = {
    deviceId: string;
    sequence: number;
    timestamp: number;
    base64: string;
    data?: Uint8Array;
};
export type Transcript = {
    id: string;
    text: string;
    timestamp: number;
    isFinal: boolean;
};
export type OmiEvents = {
    state: OmiConnectionState;
    device: OmiDevice | null;
    error: Error | null;
    audioChunk: AudioChunk | null;
    transcript: Transcript | null;
};
export interface OmiTransport {
    scanAndConnect(): Promise<OmiDevice>;
    disconnect(): Promise<void>;
    startAudioStream(): Promise<void>;
    stopAudioStream(): Promise<void>;
    destroy(): void;
    onAudio(listener: (chunk: AudioChunk) => void): () => void;
    onConnectionChange(listener: (state: OmiConnectionState) => void): () => void;
}
export type ScanOptions = {
    timeoutMs?: number;
    requireOmiService?: boolean;
};
//# sourceMappingURL=types.d.ts.map