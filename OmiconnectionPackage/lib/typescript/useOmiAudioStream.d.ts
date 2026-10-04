import type { OmiConnection } from "./OmiConnection";
export type UseOmiAudioStreamResult = {
    isStreaming: boolean;
    error: Error | null;
    start: () => Promise<void>;
    stop: () => void;
};
/** React hook for controlling an Omi audio stream. It always stops on unmount. */
export declare function useOmiAudioStream(connection: OmiConnection | null, onAudio: (payload: Uint8Array) => void, includePacketHeader?: boolean): UseOmiAudioStreamResult;
//# sourceMappingURL=useOmiAudioStream.d.ts.map