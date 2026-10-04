import type { AudioChunk, OmiConnectionState, OmiDevice, OmiTransport, Transcript } from "./types";
type Listener<T> = (value: T) => void;
export declare class OmiClient {
    private readonly transport;
    private device;
    private state;
    private stateListeners;
    private audioListeners;
    private transcriptListeners;
    constructor(transport: OmiTransport);
    connect(): Promise<OmiDevice>;
    disconnect(): Promise<void>;
    startAudio(): Promise<void>;
    stopAudio(): Promise<void>;
    receiveTranscript(transcript: Transcript): void;
    getState(): OmiConnectionState;
    getDevice(): OmiDevice | null;
    onState(listener: Listener<OmiConnectionState>): () => boolean;
    onAudio(listener: Listener<AudioChunk>): () => boolean;
    onTranscript(listener: Listener<Transcript>): () => boolean;
    destroy(): void;
}
export {};
//# sourceMappingURL=OmiClient.d.ts.map