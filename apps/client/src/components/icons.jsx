// Set de íconos en línea (trazo, sin relleno) para el sistema "Orden de
// trabajo, refinado". Nada de emoji en la interfaz: solo en el copy, si
// alguna vez hace falta — la marca ya usa emoji para categorías en el
// landing, pero la interfaz de trabajo usa trazo técnico, como el resto
// del lenguaje visual (checks, plano, fichas).
const base = { fill: "none", xmlns: "http://www.w3.org/2000/svg" };

export function ClipboardIcon({ size = 28, color = "currentColor" }) {
  return (
    <svg {...base} width={size} height={size} viewBox="0 0 24 24">
      <rect x="6" y="4.5" width="12" height="16" rx="1.5" stroke={color} strokeWidth="1.4" />
      <rect x="9" y="3" width="6" height="3" rx="1" stroke={color} strokeWidth="1.4" />
      <path d="M9 11h6M9 14.5h6M9 18h3.5" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function RepeatIcon({ size = 28, color = "currentColor" }) {
  return (
    <svg {...base} width={size} height={size} viewBox="0 0 24 24">
      <path
        d="M4.5 11.5V9a3.5 3.5 0 0 1 3.5-3.5h9M17 5.5l-2-2M17 5.5l-2 2"
        stroke={color}
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M19.5 12.5V15a3.5 3.5 0 0 1-3.5 3.5H7M7 18.5l2 2M7 18.5l2-2"
        stroke={color}
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function CameraIcon({ size = 26, color = "currentColor" }) {
  return (
    <svg {...base} width={size} height={size} viewBox="0 0 24 24">
      <path
        d="M4 8.5C4 7.67 4.67 7 5.5 7H7.8L8.9 5.3C9.16 4.9 9.6 4.67 10.08 4.67H13.92C14.4 4.67 14.84 4.9 15.1 5.3L16.2 7H18.5C19.33 7 20 7.67 20 8.5V17.5C20 18.33 19.33 19 18.5 19H5.5C4.67 19 4 18.33 4 17.5V8.5Z"
        stroke={color}
        strokeWidth="1.4"
      />
      <circle cx="12" cy="13" r="3.4" stroke={color} strokeWidth="1.4" />
    </svg>
  );
}

export function ReceiptIcon({ size = 28, color = "currentColor" }) {
  return (
    <svg {...base} width={size} height={size} viewBox="0 0 24 24">
      <path
        d="M6 3.5h12v17l-2-1.3-2 1.3-2-1.3-2 1.3-2-1.3-2 1.3v-17Z"
        stroke={color}
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M9 8h6M9 11.5h6M9 15h3.5" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function CheckIcon({ size = 14, color = "#2F7A4D" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="7" stroke={color} strokeWidth="1.4" />
      <path
        d="M5 8.2L7 10.2L11 6"
        stroke={color}
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ImagePlaceholderIcon({ size = 20, color = "currentColor" }) {
  return (
    <svg {...base} width={size} height={size} viewBox="0 0 24 24">
      <rect x="3" y="5" width="18" height="14" rx="1.5" stroke={color} strokeWidth="1.3" />
      <circle cx="8.5" cy="10" r="1.6" stroke={color} strokeWidth="1.2" />
      <path d="M4 16L9 12L13 15L16 12.5L20 16" stroke={color} strokeWidth="1.2" />
    </svg>
  );
}

export function LockIcon({ size = 13, color = "currentColor", open = false }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <rect x="3.5" y="7" width="9" height="6.5" rx="1.2" stroke={color} strokeWidth="1.3" />
      {open ? (
        <path d="M5.5 7V5.2a2.5 2.5 0 0 1 4.6-1.4" stroke={color} strokeWidth="1.3" strokeLinecap="round" />
      ) : (
        <path d="M5.5 7V4.8a2.5 2.5 0 0 1 5 0V7" stroke={color} strokeWidth="1.3" />
      )}
    </svg>
  );
}

export function SealIcon({ size = 22, color = "#2F7A4D" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9.5" stroke={color} strokeWidth="1.4" strokeDasharray="2.4 2.4" />
      <path d="M8 12.3L10.5 14.8L16 9" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
