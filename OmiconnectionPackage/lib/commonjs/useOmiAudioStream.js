"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.useOmiAudioStream = useOmiAudioStream;
var _react = require("react");
/** React hook for controlling an Omi audio stream. It always stops on unmount. */
function useOmiAudioStream(connection, onAudio, includePacketHeader = false) {
  const [isStreaming, setIsStreaming] = (0, _react.useState)(false);
  const [error, setError] = (0, _react.useState)(null);
  const stopRef = (0, _react.useRef)(null);
  const stop = (0, _react.useCallback)(() => {
    var _stopRef$current;
    (_stopRef$current = stopRef.current) === null || _stopRef$current === void 0 || _stopRef$current.call(stopRef);
    stopRef.current = null;
    connection === null || connection === void 0 || connection.stopAudioStream();
    setIsStreaming(false);
  }, [connection]);
  const start = (0, _react.useCallback)(async () => {
    if (!connection) {
      const reason = new Error("Connect an Omi device before starting the audio stream.");
      setError(reason);
      throw reason;
    }
    stop();
    try {
      stopRef.current = await connection.startAudioStream(onAudio, includePacketHeader);
      setError(null);
      setIsStreaming(true);
    } catch (cause) {
      const reason = cause instanceof Error ? cause : new Error(String(cause));
      setError(reason);
      throw reason;
    }
  }, [connection, includePacketHeader, onAudio, stop]);
  (0, _react.useEffect)(() => stop, [stop]);
  return {
    isStreaming,
    error,
    start,
    stop
  };
}
//# sourceMappingURL=useOmiAudioStream.js.map