import { PermissionsAndroid, Platform } from "react-native";

/** Requests the runtime permissions required to scan and connect over BLE. */
export async function requestBluetoothPermissions(): Promise<boolean> {
  if (Platform.OS !== "android") return true;
  if (Platform.Version >= 31) {
    const result = await PermissionsAndroid.requestMultiple([
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
    ]);
    return Object.values(result).every((status) => status === PermissionsAndroid.RESULTS.GRANTED);
  }
  const status = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION);
  return status === PermissionsAndroid.RESULTS.GRANTED;
}
