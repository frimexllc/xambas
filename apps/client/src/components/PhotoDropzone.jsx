import { useEffect, useRef, useState } from "react";

// Selector de fotos con arrastrar-y-soltar + miniaturas, en vez del
// <input type="file"> nativo del navegador (que rompía el estilo del resto
// del formulario). El input real queda oculto pero accesible: mismo
// data-testid, mismo comportamiento para clics de teclado (Enter/Espacio).
export function PhotoDropzone({ files, onChange, maxFiles = 5, testId, accept }) {
  const inputRef = useRef(null);
  const [isDragging, setDragging] = useState(false);
  const [previewUrls, setPreviewUrls] = useState([]);

  useEffect(() => {
    const urls = files.map((file) => URL.createObjectURL(file));
    setPreviewUrls(urls);
    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files]);

  function pickFiles(fileList) {
    if (!fileList || fileList.length === 0) return;
    onChange(Array.from(fileList).slice(0, maxFiles));
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    pickFiles(event.dataTransfer?.files);
  }

  function removeAt(index) {
    onChange(files.filter((_, i) => i !== index));
  }

  return (
    <div className="dropzone-wrap">
      <div
        className={`dropzone${isDragging ? " dropzone-active" : ""}`}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple
          hidden
          data-testid={testId}
          onChange={(event) => pickFiles(event.target.files)}
        />
        <span className="dropzone-icon" aria-hidden="true">
          📷
        </span>
        <p className="dropzone-text">
          <strong>Arrastra tus fotos aquí</strong> o haz clic para elegir
        </p>
        <p className="dropzone-hint">
          JPEG, PNG o WebP · hasta {maxFiles} foto{maxFiles === 1 ? "" : "s"}
        </p>
      </div>

      {files.length > 0 && (
        <ul className="dropzone-previews">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`} className="dropzone-preview">
              <img src={previewUrls[index]} alt={file.name} />
              <button
                type="button"
                className="dropzone-remove"
                onClick={(event) => {
                  event.stopPropagation();
                  removeAt(index);
                }}
                aria-label={`Quitar ${file.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
