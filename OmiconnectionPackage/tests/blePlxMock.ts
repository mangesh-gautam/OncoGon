export class BleManager {
  startDeviceScan = jest.fn();
  stopDeviceScan = jest.fn();
  connectToDevice = jest.fn();
  state = jest.fn();
  enable = jest.fn();
  destroy = jest.fn();
}

export type Device = any;
export type Subscription = { remove(): void };
