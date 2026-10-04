export declare function useOmi(): {
    client: import("./OmiClient").OmiClient;
    state: import("./types").OmiConnectionState;
    device: import("./types").OmiDevice | null;
    transcripts: import("./types").Transcript[];
    connect: () => Promise<import("./types").OmiDevice>;
    disconnect: () => Promise<void>;
    startAudio: () => Promise<void>;
    stopAudio: () => Promise<void>;
};
//# sourceMappingURL=useOmi.d.ts.map