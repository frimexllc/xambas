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

const FONT_STACK =
  '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif';

// Sin esto, el formulario de pago de Stripe renderiza con su tema azul/blanco
// por defecto, que desentona contra el resto de la interfaz. Se resuelve el
// tema efectivo (elegido a mano o del sistema, ver src/theme.js) una vez al
// montar el checkout y se le pasan los mismos tokens cálidos.
export function getStripeAppearance() {
  const explicit = document.documentElement.getAttribute("data-theme");
  const isDark =
    explicit === "dark" ||
    (explicit !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  return {
    theme: isDark ? "night" : "stripe",
    variables: isDark
      ? {
          colorPrimary: "#ff8b63",
          colorBackground: "#262019",
          colorText: "rgba(255, 246, 240, 0.94)",
          colorTextSecondary: "rgba(255, 230, 210, 0.62)",
          colorDanger: "#ff5c72",
          fontFamily: FONT_STACK,
          borderRadius: "10px",
        }
      : {
          colorPrimary: "#ff6b47",
          colorBackground: "#ffffff",
          colorText: "#241c16",
          colorTextSecondary: "rgba(60, 47, 37, 0.62)",
          colorDanger: "#d7263d",
          fontFamily: FONT_STACK,
          borderRadius: "10px",
        },
  };
}
