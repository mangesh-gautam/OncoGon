"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.useOmi = useOmi;
var _react = require("react");
var _OmiProvider = require("./OmiProvider");
function useOmi() {
  const omi = (0, _react.useContext)(_OmiProvider.OmiContext);
  if (!omi) {
    throw new Error("useOmi must be used inside <OmiProvider>.");
  }
  return omi;
}
//# sourceMappingURL=useOmi.js.map