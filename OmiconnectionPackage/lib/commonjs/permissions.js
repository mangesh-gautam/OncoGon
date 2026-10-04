"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.requestBluetoothPermissions = requestBluetoothPermissions;
var _reactNative = require("react-native");
/** Requests the runtime permissions required to scan and connect over BLE. */
async function requestBluetoothPermissions() {
  if (_reactNative.Platform.OS !== "android") return true;
  if (_reactNative.Platform.Version >= 31) {
    const result = await _reactNative.PermissionsAndroid.requestMultiple([_reactNative.PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN, _reactNative.PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT]);
    return Object.values(result).every(status => status === _reactNative.PermissionsAndroid.RESULTS.GRANTED);
  }
  const status = await _reactNative.PermissionsAndroid.request(_reactNative.PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION);
  return status === _reactNative.PermissionsAndroid.RESULTS.GRANTED;
}
//# sourceMappingURL=permissions.js.map