import 'dart:convert';

/// Un equipo que se puede encender con Wake on LAN.
class Device {
  Device({
    required this.id,
    required this.name,
    required this.mac,
    this.address = '255.255.255.255',
    this.port = 9,
  });

  final String id;

  /// Nombre visible, por ejemplo "PC de escritorio".
  final String name;

  /// Dirección MAC de la tarjeta de red cableada del PC.
  final String mac;

  /// Destino del paquete. En la red local es la dirección de broadcast
  /// (255.255.255.255 o la de tu subred, como 192.168.1.255).
  /// Más adelante puede ser un nombre de dominio o IP pública para
  /// encender desde fuera (redirección de puertos en el router).
  final String address;

  /// Puerto UDP. Lo habitual es 9 (a veces 7).
  final int port;

  Device copyWith({String? name, String? mac, String? address, int? port}) =>
      Device(
        id: id,
        name: name ?? this.name,
        mac: mac ?? this.mac,
        address: address ?? this.address,
        port: port ?? this.port,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'mac': mac,
        'address': address,
        'port': port,
      };

  factory Device.fromJson(Map<String, dynamic> json) => Device(
        id: json['id'] as String,
        name: json['name'] as String,
        mac: json['mac'] as String,
        address: (json['address'] as String?) ?? '255.255.255.255',
        port: (json['port'] as int?) ?? 9,
      );

  static String encodeList(List<Device> devices) =>
      jsonEncode(devices.map((d) => d.toJson()).toList());

  static List<Device> decodeList(String raw) => (jsonDecode(raw) as List)
      .map((e) => Device.fromJson(e as Map<String, dynamic>))
      .toList();
}
