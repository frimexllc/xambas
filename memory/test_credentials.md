# Credenciales de prueba — Xambas

## Autenticación de clientes/proveedores (OTP)
NO hay cuentas pre-sembradas. El registro es por **correo + teléfono + OTP**.
En `development` (`OTP_PROVIDER=dev`), el código OTP se devuelve en la respuesta de
`POST /api/identity/otp/request` como `debug_code`, y la UI del cliente lo muestra
en pantalla dentro de `.hint strong`.

Flujo para crear una cuenta de cliente:
1. `POST /api/identity/bootstrap` → `{ "email": "...", "phone": "+52...", "role": "client" }`
2. `POST /api/identity/otp/request` → `{ "user_id": "<id>", "purpose": "registration", "channel": "sms" }` (devuelve `debug_code`)
3. `POST /api/identity/otp/verify` → `{ "user_id", "challenge_id", "code": "<debug_code>", "device_name": "web" }`

## Admin (panel apps/admin)
El primer administrador se crea la primera vez vía `POST /api/admin/auth/bootstrap`
(super_admin). No hay admin sembrado en este entorno todavía.

## Integraciones
- Stripe: NO configurado (STRIPE_SECRET_KEY vacío). No probar pagos hasta cargar claves.
- Twilio: NO configurado. OTP en modo dev.

## URLs
- Preview público: https://6a5a4228-856c-435a-9735-832a8c1fd2f3.preview.emergentagent.com
- API: mismas rutas bajo `/api`.
