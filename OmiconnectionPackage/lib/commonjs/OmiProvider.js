"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.OmiContext = void 0;
exports.OmiProvider = OmiProvider;
var _react = _interopRequireWildcard(require("react"));
var _BleOmiTransport = require("./BleOmiTransport");
var _OmiClient = require("./OmiClient");
function _interopRequireWildcard(e, t) { if ("function" == typeof WeakMap) var r = new WeakMap(), n = new WeakMap(); return (_interopRequireWildcard = function (e, t) { if (!t && e && e.__esModule) return e; var o, i, f = { __proto__: null, default: e }; if (null === e || "object" != typeof e && "function" != typeof e) return f; if (o = t ? n : r) { if (o.has(e)) return o.get(e); o.set(e, f); } for (const t in e) "default" !== t && {}.hasOwnProperty.call(e, t) && ((i = (o = Object.defineProperty) && Object.getOwnPropertyDescriptor(e, t)) && (i.get || i.set) ? o(f, t, i) : f[t] = e[t]); return f; })(e, t); }
const OmiContext = exports.OmiContext = /*#__PURE__*/(0, _react.createContext)(null);
function OmiProvider({
  children
}) {
  const client = (0, _react.useMemo)(() => new _OmiClient.OmiClient(new _BleOmiTransport.BleOmiTransport()), []);
  const [state, setState] = (0, _react.useState)(client.getState());
  const [device, setDevice] = (0, _react.useState)(client.getDevice());
  const [transcripts, setTranscripts] = (0, _react.useState)([]);
  (0, _react.useEffect)(() => {
    const unsubscribeState = client.onState(setState);
    const unsubscribeTranscript = client.onTranscript(item => setTranscripts(current => [item, ...current]));
    return () => {
      unsubscribeState();
      unsubscribeTranscript();
      client.destroy();
    };
  }, [client]);
  const value = {
    client,
    state,
    device,
    transcripts,
    connect: async () => {
      const connectedDevice = await client.connect();
      setDevice(connectedDevice);
      return connectedDevice;
    },
    disconnect: async () => {
      await client.disconnect();
      setDevice(null);
    },
    startAudio: () => client.startAudio(),
    stopAudio: () => client.stopAudio()
  };
  return /*#__PURE__*/_react.default.createElement(OmiContext.Provider, {
    value: value
  }, children);
}
//# sourceMappingURL=OmiProvider.js.map