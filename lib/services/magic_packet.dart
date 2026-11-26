import 'dart:typed_data';

/// Convierte una MAC escrita como "AA:BB:CC:DD:EE:FF", "AA-BB-CC-DD-EE-FF",
/// "AABB.CCDD.EEFF" o "AABBCCDDEEFF" en sus 6 bytes.
/// Lanza [FormatException] si no es válida.
Uint8List parseMac(String input) {
  final hex = input.replaceAll(RegExp(r'[\s:\-\.]'), '');
  if (!RegExp(r'^[0-9a-fA-F]{12}$').hasMatch(hex)) {
    throw FormatException('MAC no válida: "$input"');
  }
  final bytes = Uint8List(6);
  for (var i = 0; i < 6; i++) {
    bytes[i] = int.parse(hex.substring(i * 2, i * 2 + 2), radix: 16);
  }
  return bytes;
}

bool isValidMac(String input) {
  try {
    parseMac(input);
    return true;
  } on FormatException {
    return false;
  }
}

/// Devuelve la MAC en formato AA:BB:CC:DD:EE:FF.
String normalizeMac(String input) => parseMac(input)
    .map((b) => b.toRadixString(16).padLeft(2, '0').toUpperCase())
    .join(':');

/// Construye el "paquete mágico": 6 bytes 0xFF seguidos de la MAC
/// repetida 16 veces (102 bytes en total).
Uint8List buildMagicPacket(String mac) {
  final macBytes = parseMac(mac);
  final packet = Uint8List(6 + 16 * 6);
  packet.fillRange(0, 6, 0xFF);
  for (var i = 0; i < 16; i++) {
    packet.setRange(6 + i * 6, 12 + i * 6, macBytes);
  }
  return packet;
}
