const providerCapabilities = [
  "matching opportunities",
  "quotes",
  "availability",
  "billing",
  "reputation"
];

export default function App() {
  return (
    <main style={{ fontFamily: "system-ui", margin: "0 auto", maxWidth: 960, padding: 32 }}>
      <h1>Xambas Proveedor</h1>
      <p>Base inicial del frontend proveedor en React + Vite.</p>
      <p>Este panel crecera con foco en negocio, conversion y operacion diaria del proveedor.</p>
      <ul>
        {providerCapabilities.map((capability) => (
          <li key={capability}>{capability}</li>
        ))}
      </ul>
    </main>
  );
}
