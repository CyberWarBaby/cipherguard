"use client";

import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { CustomerProfile } from "./types";
import { readJSON, writeJSON } from "./storage";

const KEY = "shipfast-customer";

function generateCustomerId(phone: string): string {
  const digits = phone.replace(/\D/g, "").slice(-6) || "000000";
  return `cust_${digits}${Date.now().toString(36).slice(-3)}`;
}

interface CustomerContextValue {
  profile: CustomerProfile | null;
  saveProfile: (input: Omit<CustomerProfile, "customerId">) => CustomerProfile;
  clearProfile: () => void;
}

const CustomerContext = createContext<CustomerContextValue | null>(null);

export function CustomerProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setProfile(readJSON<CustomerProfile | null>(KEY, null));
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    writeJSON(KEY, profile);
  }, [profile, hydrated]);

  const value: CustomerContextValue = {
    profile,
    saveProfile: (input) => {
      const customerId = profile?.customerId ?? generateCustomerId(input.phone);
      const next: CustomerProfile = { ...input, customerId };
      setProfile(next);
      return next;
    },
    clearProfile: () => setProfile(null),
  };

  return (
    <CustomerContext.Provider value={value}>{children}</CustomerContext.Provider>
  );
}

export function useCustomer(): CustomerContextValue {
  const ctx = useContext(CustomerContext);
  if (!ctx) throw new Error("useCustomer must be used within CustomerProvider");
  return ctx;
}
