import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const API_V1_PREFIX = import.meta.env.VITE_API_V1_PREFIX ?? "/api/v1";
export const API_URL = `${API_BASE_URL}${API_V1_PREFIX}`;
