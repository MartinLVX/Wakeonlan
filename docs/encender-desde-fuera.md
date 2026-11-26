# Encender el PC desde fuera de casa

El paquete mágico es un *broadcast* de la red local: los routers no lo dejan
pasar desde Internet tal cual. Hay tres maneras de resolverlo, de más simple a
más robusta.

## Opción 1: redirección de puertos en el router

El router recibe un paquete UDP desde Internet y lo reenvía al PC.

1. Reserva una IP fija para el PC en el router (DHCP estático), por ejemplo `192.168.1.40`.
2. Crea una regla de redirección: UDP, puerto externo (por ejemplo `40009`) → `192.168.1.40`, puerto `9`.
   - Mejor aún, si el router lo permite, reenvía a la dirección de broadcast (`192.168.1.255`).
     Muchos routers no lo permiten.
3. Si tu IP pública cambia, usa un DNS dinámico (DuckDNS, No‑IP o el que traiga el router).
4. En la app, crea otro equipo con **Dirección** = tu dominio o IP pública y **Puerto** = `40009`.
   **La app ya soporta esto**, no hace falta cambiar código.

Limitaciones: cuando el PC lleva un rato apagado, el router suele "olvidar" a qué
MAC corresponde la IP (tabla ARP) y el paquete se pierde. Algunos routers permiten
una entrada ARP estática, que lo soluciona. Tampoco funciona si tu proveedor usa
CG‑NAT (no tienes IP pública propia).

## Opción 2: VPN (Tailscale, WireGuard)

Con una VPN el celular "está en casa" aunque esté fuera. Pero las VPN no
transportan broadcast, así que necesitas **algo en casa que esté siempre
encendido** y que reenvíe el paquete:

- **Router con WireGuard** (muchos ASUS, GL.iNet, OpenWrt, Fritz!Box): conectas el
  celular a la VPN del router y envías a la dirección de broadcast de casa.
  Algunos routers dejan pasar el broadcast de la subred y otros no.
- **Tailscale + un equipo siempre encendido** (Raspberry Pi, NAS, router compatible):
  ese equipo hace de "subnet router" o de relay (opción 3).

Ventaja: no expones nada a Internet, y funciona aunque tengas CG‑NAT.

## Opción 3: relay en casa (la más fiable)

Un equipo pequeño siempre encendido en la red de casa (Raspberry Pi, NAS, un
router con OpenWrt, un viejo Android enchufado…) recibe una orden del celular y
él mismo envía el paquete mágico en la red local.

- La orden llega por la VPN (Tailscale) o por un servicio con autenticación.
- Funciona igual dentro y fuera de casa, y también evita la restricción de
  broadcast del iPhone.
- En la app sería una nueva implementación de `WakeTransport` (por ejemplo
  `RelayWakeTransport`, que hace una petición HTTP al relay) y un campo más en el equipo.

## Recomendación

1. Ahora: red local (ya funciona).
2. Si tienes IP pública y un router que lo permita: opción 1, sin cambiar código.
3. Si tienes un Raspberry Pi o un NAS, o usas iPhone: opción 3 con Tailscale.
