import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PhotoDropzone } from "./PhotoDropzone.jsx";

function file(name) {
  return new File([new Uint8Array([1, 2, 3])], name, { type: "image/jpeg" });
}

describe("PhotoDropzone", () => {
  it("sin fotos: muestra la invitación a elegir/arrastrar", () => {
    render(<PhotoDropzone files={[]} onChange={vi.fn()} testId="dz-input" />);
    expect(screen.getByText(/arrastra tus fotos aquí/i)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("elegir un archivo por el input dispara onChange con la lista", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<PhotoDropzone files={[]} onChange={onChange} testId="dz-input" />);

    await user.upload(screen.getByTestId("dz-input"), file("cocina.jpg"));

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange.mock.calls[0][0]).toHaveLength(1);
    expect(onChange.mock.calls[0][0][0].name).toBe("cocina.jpg");
  });

  it("soltar archivos (drag & drop) también dispara onChange", () => {
    const onChange = vi.fn();
    render(<PhotoDropzone files={[]} onChange={onChange} testId="dz-input" />);

    fireEvent.drop(screen.getByRole("button"), {
      dataTransfer: { files: [file("baño.png")] },
    });

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange.mock.calls[0][0][0].name).toBe("baño.png");
  });

  it("respeta maxFiles al recortar la selección", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<PhotoDropzone files={[]} onChange={onChange} maxFiles={2} testId="dz-input" />);

    await user.upload(screen.getByTestId("dz-input"), [
      file("a.jpg"),
      file("b.jpg"),
      file("c.jpg"),
    ]);

    expect(onChange.mock.calls[0][0]).toHaveLength(2);
  });

  it("muestra una miniatura por archivo y permite quitar una", async () => {
    const onChange = vi.fn();
    const files = [file("a.jpg"), file("b.jpg")];
    const user = userEvent.setup();
    render(<PhotoDropzone files={files} onChange={onChange} testId="dz-input" />);

    expect(screen.getAllByRole("img")).toHaveLength(2);

    await user.click(screen.getByRole("button", { name: /quitar a.jpg/i }));

    expect(onChange).toHaveBeenCalledWith([files[1]]);
  });
});
