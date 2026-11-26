import 'package:flutter_test/flutter_test.dart';
import 'package:wakeonlan/models/device.dart';
import 'package:wakeonlan/services/magic_packet.dart';

void main() {
  group('parseMac', () {
    test('acepta separadores comunes', () {
      for (final mac in [
        'AA:BB:CC:DD:EE:FF',
        'aa-bb-cc-dd-ee-ff',
        'AABB.CCDD.EEFF',
        'aabbccddeeff',
      ]) {
        expect(parseMac(mac), [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF]);
      }
    });

    test('rechaza MAC inválidas', () {
      expect(isValidMac('AA:BB:CC:DD:EE'), isFalse);
      expect(isValidMac('GG:BB:CC:DD:EE:FF'), isFalse);
      expect(isValidMac(''), isFalse);
    });

    test('normaliza', () {
      expect(normalizeMac('a1-b2-c3-d4-e5-f6'), 'A1:B2:C3:D4:E5:F6');
    });
  });

  test('paquete mágico: 6 x FF + 16 x MAC', () {
    final p = buildMagicPacket('01:23:45:67:89:AB');
    expect(p.length, 102);
    expect(p.sublist(0, 6), List.filled(6, 0xFF));
    for (var i = 0; i < 16; i++) {
      expect(p.sublist(6 + i * 6, 12 + i * 6),
          [0x01, 0x23, 0x45, 0x67, 0x89, 0xAB]);
    }
  });

  test('Device se guarda y se lee igual', () {
    final d = Device(id: '1', name: 'PC', mac: 'AA:BB:CC:DD:EE:FF',
        address: '192.168.1.255', port: 7);
    final back = Device.decodeList(Device.encodeList([d])).single;
    expect(back.toJson(), d.toJson());
  });
}
