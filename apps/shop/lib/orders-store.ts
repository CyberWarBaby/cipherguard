import { OrderRecord } from "./types";
import { readJSON, writeJSON } from "./storage";

const KEY = "shipfast-orders";

export function getOrderHistory(): OrderRecord[] {
  return readJSON<OrderRecord[]>(KEY, []);
}

export function saveOrder(order: OrderRecord): void {
  const existing = getOrderHistory();
  writeJSON(KEY, [order, ...existing]);
}
