# Wake on LAN

App para el celular (Android y iPhone) que enciende tu computadora enviando un
"paquete mágico" Wake on LAN.

- Guardas uno o varios equipos (nombre, MAC, dirección de broadcast y puerto).
- Pulsas **Encender** y la app envía el paquete por UDP (3 veces, por si se pierde alguno).
- Los datos se guardan solo en el teléfono.

## Por qué Flutter

Un solo código para Android e iPhone, y Dart trae sockets UDP con broadcast de
serie (`RawDatagramSocket`), así que no hace falta ningún módulo nativo extra.
Con React Native habría que añadir un módulo UDP nativo y no funcionaría en Expo Go.

## Versión web (PWA) para iPhone y Android

Además de la app Flutter hay una **PWA** que se instala desde el navegador, sin
Mac ni tiendas, y funciona también fuera de casa. Como un navegador no puede
enviar el paquete mágico, la PWA se lo pide a un **relay** en casa (hoy un
Android viejo con Termux, mañana una Raspberry Pi), con un token y a través de
Tailscale. Guía completa: [docs/pwa-y-relay.md](docs/pwa-y-relay.md).

```
pwa/     la PWA (HTML/CSS/JS, sin compilar); se publica en GitHub Pages
relay/   el relay en Python sin dependencias (Termux, Raspberry Pi, cualquier Linux)
```

## Antes de empezar: prepara el PC

Sigue [docs/configurar-pc.md](docs/configurar-pc.md): activar Wake on LAN en la
BIOS/UEFI y en la tarjeta de red, y apuntar la MAC.

## Usar la app

1. Conecta el celular al **Wi‑Fi de casa** (la misma red que el PC).
2. Pulsa **Añadir equipo** y rellena:
   - **MAC**: la de la tarjeta de red por cable del PC.
   - **Dirección**: `255.255.255.255` sirve casi siempre. Si no funciona, usa la
     de tu subred, por ejemplo `192.168.1.255` si tu PC es `192.168.1.x`.
   - **Puerto**: `9`.
3. Apaga el PC y pulsa **Encender**.

Mantén pulsado un equipo para eliminarlo; tócalo para editarlo.

## Instalar en el teléfono

### Android

- **Sin instalar nada**: cada vez que se sube código a GitHub, la acción
  *APK de Android* compila la app. Entra en la pestaña **Actions** del
  repositorio, abre la última ejecución y descarga `wakeonlan-apk`. Pasa el
  `.apk` al teléfono y ábrelo (Android pedirá permitir "instalar apps de origen
  desconocido").
- **Desde tu PC**: instala [Flutter](https://docs.flutter.dev/get-started/install)
  y Android Studio, conecta el teléfono por USB con la depuración USB activada y ejecuta
  `flutter run --release`.

### iPhone

Apple exige compilar en un **Mac** con Xcode (o un servicio en la nube como Codemagic).
- Con una cuenta de Apple gratuita la app funciona 7 días y luego hay que volver a instalarla.
- Con la cuenta de desarrollador (99 USD/año) dura un año.
- La primera vez iOS pedirá permiso de **Red local**: acéptalo.
- Ojo: desde iOS 14.5 Apple solo deja enviar *broadcast* a apps con el permiso
  especial `com.apple.developer.networking.multicast`, que hay que solicitar a
  Apple. Si en el iPhone no funciona, la alternativa es la opción del *relay*
  descrita en [docs/encender-desde-fuera.md](docs/encender-desde-fuera.md),
  que además sirve para encender desde fuera de casa.

## Encender desde fuera de casa

La app está preparada para crecer: el envío está detrás de la interfaz
`WakeTransport` (`lib/services/wake_service.dart`). Las opciones están
explicadas en [docs/encender-desde-fuera.md](docs/encender-desde-fuera.md).

## Desarrollo

```bash
flutter pub get
flutter test
flutter run
```

Estructura:

```
lib/
  main.dart                     app y tema
  models/device.dart            equipo guardado
  services/magic_packet.dart    validación de MAC y construcción del paquete
  services/wake_service.dart    envío por UDP (WakeTransport)
  services/device_store.dart    guardado en el teléfono
  screens/                      lista de equipos y formulario
```

Relay y PWA:

```bash
python3 -m unittest relay/test_wol_relay.py
python3 relay/wol_relay.py      # sirve también la PWA en http://localhost:8787
```
