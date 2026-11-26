# Preparar el PC para Wake on LAN

Wake on LAN funciona con la tarjeta de red **por cable** (Ethernet), que es lo
que tienes. Hay que activarlo en tres sitios.

## 1. BIOS / UEFI

1. Reinicia el PC y entra en la BIOS (suele ser `Supr`/`Del`, `F2` o `F10` al arrancar).
2. Busca una opción con alguno de estos nombres y actívala:
   - *Wake on LAN*, *Power On By PCI-E / PCI*, *Resume by PCI-E Device*,
     *Wake on PME*, *Remote Wake Up*.
   - Suele estar en *Power Management*, *APM* o *Advanced*.
3. Si existe **ErP / EuP Ready**, **desactívalo** (si está activo, la tarjeta de
   red se queda sin corriente al apagar y no puede escuchar).
4. Si hay *Deep Sleep* o *Deep Power Off*, desactívalo también.
5. Guarda y sal.

## 2. Windows: la tarjeta de red

1. Abre el **Administrador de dispositivos** (clic derecho en Inicio).
2. **Adaptadores de red** → doble clic en tu tarjeta Ethernet (Realtek, Intel…).
3. Pestaña **Administración de energía**: marca
   - *Permitir que este dispositivo reactive el equipo*
   - *Permitir solo un paquete mágico para reactivar el equipo*
4. Pestaña **Opciones avanzadas**: activa (*Enabled*) lo que aparezca de esto:
   - *Wake on Magic Packet*
   - *Wake on pattern match* (opcional)
   - *Shutdown Wake-On-Lan* / *Wake from power off state* (si existe)
   - Si existe *Energy Efficient Ethernet* o *Green Ethernet*, desactívalo si da problemas.

## 3. Windows: Inicio rápido

El *Inicio rápido* de Windows a menudo impide que el PC despierte cuando está apagado.

1. Panel de control → **Opciones de energía** → *Elegir el comportamiento de los botones de inicio/apagado*.
2. *Cambiar la configuración actualmente no disponible*.
3. Desmarca **Activar inicio rápido** y guarda.

## 4. Apuntar la MAC (y la IP)

Abre **PowerShell** o **Símbolo del sistema** y ejecuta:

```
ipconfig /all
```

En el bloque de **Adaptador de Ethernet**, apunta:
- **Dirección física**: es la MAC, por ejemplo `A1-B2-C3-D4-E5-F6`. La app la acepta con guiones o con dos puntos.
- **Dirección IPv4**: por ejemplo `192.168.1.40`. Te sirve para saber tu broadcast
  (`192.168.1.255`) y para reservar la IP en el router si más adelante quieres encender desde fuera.

Asegúrate de copiar la del adaptador **Ethernet**, no la del Wi‑Fi.

## Comprobar

1. Apaga el PC desde Inicio → Apagar (no lo desenchufes).
2. Mira el conector de red del PC: si las luces siguen encendidas, la tarjeta está escuchando. Buena señal.
3. Con el celular en el Wi‑Fi de casa, pulsa **Encender** en la app.

Si no enciende:
- Prueba primero con el PC en **suspensión**. Si despierta desde suspensión pero
  no desde apagado, el problema está en la BIOS (ErP) o en el Inicio rápido.
- Prueba la dirección de broadcast de tu subred (`192.168.1.255`) en vez de `255.255.255.255`.
- Prueba el puerto `7`.
- Algunos routers con "aislamiento de clientes Wi‑Fi" (redes de invitados) bloquean
  el broadcast entre Wi‑Fi y cable: usa la red principal.
