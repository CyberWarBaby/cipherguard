export type Category =
  | "fashion"
  | "food"
  | "electronics"
  | "beauty"
  | "home"
  | "kids";

export interface Product {
  id: string;
  name: string;
  category: Category;
  price: number; // NGN, minor-unit-free (naira)
  unit: string;
  description: string;
  rating: number; // 0-5
  reviews: number;
  stock: number;
}

export interface CartItem {
  productId: string;
  qty: number;
}

export interface CustomerProfile {
  customerId: string;
  fullName: string;
  phone: string;
  email: string;
  city: string;
  address: string;
}

export interface OrderRecord {
  localId: string;
  shipfastOrderId: string;
  paymentId: string;
  trackingNumber: string;
  carrier: string;
  status: string;
  estimatedDelivery: string;
  amountNaira: number;
  itemsCount: number;
  destinationCity: string;
  createdAt: string;
}
