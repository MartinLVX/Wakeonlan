# PWA + relay: encender el PC desde el iPhone (y desde fuera de casa)

Los navegadores no pueden enviar el paquete mágico (UDP), así que la PWA le pide
por HTTP a un **relay** en casa que lo envíe él:

```
iPhone / Android ──(Tailscale, HTTP + token)──► relay en casa ──(UDP broadcast)──► PC
   (PWA)                                         (Android viejo,
                                                  luego Raspberry Pi)
```

- **Relay**: `relay/wol_relay.py`. Python sin dependencias, el mismo archivo
  funciona en Termux (Android) y en una Raspberry Pi.
- **PWA**: carpeta `pwa/`. La sirve el propio relay y también GitHub Pages.
- **Seguridad**: el relay solo acepta peticiones con el token secreto, bloquea
  15 minutos una IP tras 10 tokens incorrectos y **solo puede encender los equipos
  que tú pongas en su `config.json`** (la PWA nunca envía MACs). Además, con
  Tailscale el relay no queda expuesto a Internet: no abres ningún puerto del router.

> Antes de nada, el PC debe tener Wake on LAN activado: [configurar-pc.md](configurar-pc.md).

---

## 1. Instalar el relay en el Android viejo

Usa un Android que se quede **en casa, enchufado y en el Wi‑Fi**.

1. Instala desde **F‑Droid** (no desde Play Store, esa versión está abandonada):
   **Termux** y **Termux:Boot**. Abre Termux:Boot una vez para que Android lo registre.
2. En Ajustes de Android → Batería, quita la optimización de batería a **Termux**,
   **Termux:Boot** y **Tailscale** (si no, Android los cierra).
3. En Termux:
   ```sh
   pkg update && pkg install python git
   git clone https://github.com/MartinLVX/Wakeonlan
   cd Wakeonlan/relay
   python wol_relay.py          # la primera vez crea config.json con un token nuevo
   nano config.json             # (o: pkg install micro / vim)
   ```
4. En `config.json` cambia, dentro de `devices`:
   - `mac`: la MAC de la tarjeta de red por cable del PC.
   - `broadcast`: la dirección de broadcast **de tu subred**. Si el PC tiene la IP
     `192.168.0.40`, pon `192.168.0.255`. No uses `255.255.255.255` aquí: con
     Tailscale activo en el Android puede salir por la VPN en vez de por el Wi‑Fi.
   - `check_host` (opcional): la IP fija del PC, para que la PWA muestre si está
     encendido. Funciona si Windows tiene el puerto 445 abierto (Compartir archivos
     en red privada) o pon `check_port: 3389` si usas Escritorio remoto. Déjalo en
     `""` si no lo necesitas.
   - No compartas el `token`: es la llave.
5. Prueba: `python wol_relay.py`. Debe decir *escuchando en el puerto 8787*.
6. Arranque automático:
   ```sh
   mkdir -p ~/.termux/boot
   cp termux-boot.sh ~/.termux/boot/wol-relay
   chmod +x ~/.termux/boot/wol-relay
   ```
   Reinicia el Android para comprobar que arranca solo (el log queda en `~/wol-relay.log`).

## 2. Tailscale (acceso seguro desde casa y desde fuera)

1. Crea una cuenta gratis en tailscale.com.
2. Instala **Tailscale** en el Android del relay y en tu iPhone, con la misma cuenta.
3. En el Android: Ajustes → Red → VPN → Tailscale → activa **VPN siempre activa**.
4. En la app de Tailscale del Android verás su IP, tipo `100.101.102.103`.
   Esa IP no cambia.

Tu relay queda en `http://100.101.102.103:8787` y solo lo alcanzan tus dispositivos de Tailscale.

## 3. Instalar la PWA en el iPhone

1. Con Tailscale activado en el iPhone, abre en **Safari** `http://100.101.102.103:8787`
   (tu IP de Tailscale).
2. Botón **Compartir** → **Añadir a pantalla de inicio** → **Añadir**.
3. Abre **Encender PC** desde la pantalla de inicio (no desde Safari: en iPhone la app
   instalada guarda sus datos aparte).
4. La dirección ya viene puesta. Pega el **token** y pulsa **Guardar y probar**.
   - Atajo: en Termux ejecuta `python wol_relay.py link http://100.101.102.103:8787`,
     copia el enlace y pégalo en el campo *Enlace de configuración*; rellena todo solo.

En **Android** es igual: abre la dirección en Chrome → menú ⋮ → **Añadir a pantalla de inicio**.

Para usarla: pulsa el botón verde. El PC suele tardar de 10 a 60 segundos en arrancar.
Fuera de casa solo necesitas tener Tailscale activado en el teléfono.

## ¿Y la versión de GitHub Pages?

La PWA también se publica en `https://martinlvx.github.io/Wakeonlan/`
(tras activar en el repositorio **Settings → Pages → Source: GitHub Actions**).
Pero una página HTTPS no puede llamar a un relay `http://`: el navegador lo bloquea.
Por eso, **mientras el relay sea el Android, abre la PWA desde el propio relay**
(paso 3). La versión de GitHub Pages sirve en cuanto el relay tenga HTTPS, que es
justo lo que pasa con la Raspberry Pi.

---

## 4. Más adelante: pasar a la Raspberry Pi

1. Instala Raspberry Pi OS Lite (trae Python 3), conéctala **por cable** al router.
2. ```sh
   git clone https://github.com/MartinLVX/Wakeonlan ~/Wakeonlan
   ```
   Copia el `config.json` del Android (así mantienes el token y no tienes que
   reconfigurar los teléfonos) a `~/Wakeonlan/relay/`.
3. Servicio que arranca solo:
   ```sh
   cd ~/Wakeonlan/relay
   sudo cp wol-relay.service /etc/systemd/system/     # cambia "pi" si tu usuario es otro
   sudo systemctl enable --now wol-relay
   ```
4. Tailscale con HTTPS:
   ```sh
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   sudo tailscale serve --bg 8787
   ```
   Te da una dirección tipo `https://raspberrypi.tu-red.ts.net` con certificado real.
5. En la PWA → ⚙️ Ajustes, cambia la dirección del relay por esa. Ya puedes usar
   también la versión de GitHub Pages. Apaga el relay del Android.

## Alternativa sin VPN en el teléfono: Cloudflare Tunnel

Si quieres encender sin tener Tailscale en el teléfono (por ejemplo para alguien
de la familia), `cloudflared` publica el relay en una dirección HTTPS sin abrir
puertos. Necesitas un dominio propio gestionado en Cloudflare para que la dirección
sea fija. En ese caso el relay **sí** queda en Internet y solo lo protege el token,
así que es menos privado que Tailscale. Añade la dirección HTTPS en la PWA y listo.

## Problemas frecuentes

| Síntoma | Solución |
| --- | --- |
| "El relay no contesta" | ¿Tailscale activo en el teléfono? ¿Termux sigue abierto en el Android? Mira `~/wol-relay.log`. |
| "Token incorrecto" | Copia el token otra vez desde `config.json`. Tras 10 fallos hay que esperar 15 minutos. |
| Dice "Paquete enviado" pero el PC no enciende | Revisa `broadcast` (debe ser la de tu subred) y [configurar-pc.md](configurar-pc.md). Prueba la app Flutter en la misma red para descartar el PC. |
| "Esta página es HTTPS y el relay es HTTP" | Estás en la versión de GitHub Pages con el relay del Android. Abre la PWA desde `http://IP-del-relay:8787`. |
| El relay se cierra solo al rato | Quita la optimización de batería a Termux y usa Termux:Boot (que activa `termux-wake-lock`). |
