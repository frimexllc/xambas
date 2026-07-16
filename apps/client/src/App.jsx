const domainModules = [
  "identity",
  "matching",
  "billing",
  "messaging",
  "reputation"
];

export default function App() {
  return (
    <main style={{ fontFamily: "system-ui", margin: "0 auto", maxWidth: 960, padding: 32 }}>
      <h1>Xambas Cliente</h1>
      <p>Base inicial del frontend cliente en React + Vite.</p>
      <p>Esta app consumira la API Gateway del monorepo y compartira contratos con el proveedor.</p>
      <ul>
        {domainModules.map((moduleName) => (
          <li key={moduleName}>{moduleName}</li>
        ))}
      </ul>
    </main>
  );
}
