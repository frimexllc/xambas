import { loadStripe } from "@stripe/stripe-js";

let cachedPromise = null;
let cachedKey = null;

export function getStripe(publishableKey) {
  if (!publishableKey) return null;
  if (cachedPromise && cachedKey === publishableKey) {
    return cachedPromise;
  }
  cachedKey = publishableKey;
  cachedPromise = loadStripe(publishableKey);
  return cachedPromise;
}
