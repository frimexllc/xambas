# Variables de entorno

Este proyecto separa variables por aplicacion y por ambiente.

- `env/api`: configuracion del backend FastAPI.
- `env/client`: configuracion del frontend cliente.
- `env/provider`: configuracion del frontend proveedor.

Flujo recomendado:

1. Copia el archivo del ambiente que vayas a usar.
2. Renombralo a `.env` dentro de la app correspondiente.
3. Ajusta solo los secretos y endpoints necesarios para ese ambiente.

Ejemplos:

- `Copy-Item env\\api\\.env.development.example apps\\api\\.env`
- `Copy-Item env\\client\\.env.development.example apps\\client\\.env`
- `Copy-Item env\\provider\\.env.development.example apps\\provider\\.env`
