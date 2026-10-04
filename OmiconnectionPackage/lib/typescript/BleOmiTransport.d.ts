import type { AudioChunk, OmiConnectionState, OmiDevice, OmiTransport } from "./types";
export declare class BleOmiTransport implements OmiTransport {
    private manager;
    private device;
    private audioSubscription;
    private audioListeners;
    private stateListeners;
    private sequence;
    scanAndConnect(): Promise<OmiDevice>;
    startAudioStream(): Promise<void>;
    stopAudioStream(): Promise<void>;
    disconnect(): Promise<void>;
    onAudio(listener: (chunk: AudioChunk) => void): () => boolean;
    onConnectionChange(listener: (state: OmiConnectionState) => void): () => boolean;
    destroy(): void;
    private emitState;
}
//# sourceMappingURL=BleOmiTransport.d.ts.map