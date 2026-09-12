import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// jsdom no implementa el Object URL API (usado por PhotoDropzone para
// previsualizar fotos); los navegadores reales sí lo tienen.
if (!global.URL.createObjectURL) {
  global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
}
if (!global.URL.revokeObjectURL) {
  global.URL.revokeObjectURL = vi.fn();
}

afterEach(() => {
  cleanup();
});
