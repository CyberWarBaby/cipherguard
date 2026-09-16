"use client";

import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useReducer,
} from "react";
import { CartItem } from "./types";
import { getProduct } from "./catalog";
import { readJSON, writeJSON } from "./storage";

const KEY = "shipfast-cart";

type State = CartItem[];

type Action =
  | { type: "ADD"; productId: string; qty: number }
  | { type: "SET_QTY"; productId: string; qty: number }
  | { type: "REMOVE"; productId: string }
  | { type: "CLEAR" }
  | { type: "HYDRATE"; items: CartItem[] };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "HYDRATE":
      return action.items;
    case "ADD": {
      const existing = state.find((i) => i.productId === action.productId);
      if (existing) {
        return state.map((i) =>
          i.productId === action.productId
            ? { ...i, qty: i.qty + action.qty }
            : i
        );
      }
      return [...state, { productId: action.productId, qty: action.qty }];
    }
    case "SET_QTY":
      if (action.qty <= 0) {
        return state.filter((i) => i.productId !== action.productId);
      }
      return state.map((i) =>
        i.productId === action.productId ? { ...i, qty: action.qty } : i
      );
    case "REMOVE":
      return state.filter((i) => i.productId !== action.productId);
    case "CLEAR":
      return [];
    default:
      return state;
  }
}

interface CartContextValue {
  items: CartItem[];
  addItem: (productId: string, qty?: number) => void;
  setQty: (productId: string, qty: number) => void;
  removeItem: (productId: string) => void;
  clear: () => void;
  totalItems: number;
  subtotal: number;
}

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, dispatch] = useReducer(reducer, []);

  useEffect(() => {
    dispatch({ type: "HYDRATE", items: readJSON<CartItem[]>(KEY, []) });
  }, []);

  useEffect(() => {
    writeJSON(KEY, items);
  }, [items]);

  const { totalItems, subtotal } = useMemo(() => {
    let totalItems = 0;
    let subtotal = 0;
    for (const item of items) {
      const product = getProduct(item.productId);
      if (!product) continue;
      totalItems += item.qty;
      subtotal += product.price * item.qty;
    }
    return { totalItems, subtotal };
  }, [items]);

  const value: CartContextValue = {
    items,
    addItem: (productId, qty = 1) => dispatch({ type: "ADD", productId, qty }),
    setQty: (productId, qty) => dispatch({ type: "SET_QTY", productId, qty }),
    removeItem: (productId) => dispatch({ type: "REMOVE", productId }),
    clear: () => dispatch({ type: "CLEAR" }),
    totalItems,
    subtotal,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
