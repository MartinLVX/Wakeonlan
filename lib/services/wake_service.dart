import 'dart:io';

import '../models/device.dart';
import 'magic_packet.dart';

/// Forma de hacer llegar el paquete mágico al PC.
///
/// Hoy existe [UdpWakeTransport] (red local, o desde fuera con redirección
/// de puertos). Para encender desde fuera vía VPN o un equipo siempre
/// encendido en casa (relay), basta con añadir otra implementación sin
/// tocar la interfaz.
abstract class WakeTransport {
  Future<void> wake(Device device);
}

/// Envía el paquete mágico por UDP a la dirección y puerto del equipo.
class UdpWakeTransport implements WakeTransport {
  UdpWakeTransport({this.repeats = 3});

  /// Se envía varias veces porque UDP no garantiza la entrega.
  final int repeats;

  @override
  Future<void> wake(Device device) async {
    final packet = buildMagicPacket(device.mac);
    final targets = await _resolveTargets(device.address);

    final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
    try {
      socket.broadcastEnabled = true;
      for (var i = 0; i < repeats; i++) {
        for (final target in targets) {
          socket.send(packet, target, device.port);
        }
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
    } finally {
      socket.close();
    }
  }

  Future<List<InternetAddress>> _resolveTargets(String address) async {
    final parsed = InternetAddress.tryParse(address);
    if (parsed != null) return [parsed];
    // Nombre de dominio (por ejemplo un DNS dinámico para encender desde fuera).
    final found = await InternetAddress.lookup(address,
        type: InternetAddressType.IPv4);
    if (found.isEmpty) {
      throw SocketException('No se pudo resolver "$address"');
    }
    return [found.first];
  }
}
