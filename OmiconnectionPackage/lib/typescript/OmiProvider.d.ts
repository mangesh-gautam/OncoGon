import React from "react";
import { OmiClient } from "./OmiClient";
import type { OmiConnectionState, OmiDevice, Transcript } from "./types";
type OmiContextValue = {
    client: OmiClient;
    state: OmiConnectionState;
    device: OmiDevice | null;
    transcripts: Transcript[];
    connect: () => Promise<OmiDevice>;
    disconnect: () => Promise<void>;
    startAudio: () => Promise<void>;
    stopAudio: () => Promise<void>;
};
export declare const OmiContext: React.Context<OmiContextValue | null>;
export declare function OmiProvider({ children }: React.PropsWithChildren): React.JSX.Element;
export {};
//# sourceMappingURL=OmiProvider.d.ts.map