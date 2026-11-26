import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wakeonlan/models/device.dart';
import 'package:wakeonlan/services/magic_packet.dart';
import 'package:wakeonlan/services/wake_service.dart';

void main() {
  test('UdpWakeTransport envía el paquete mágico por UDP', () async {
    final receiver =
        await RawDatagramSocket.bind(InternetAddress.loopbackIPv4, 0);
    final received = <List<int>>[];
    receiver.listen((event) {
      if (event == RawSocketEvent.read) {
        final dg = receiver.receive();
        if (dg != null) received.add(dg.data);
      }
    });

    final device = Device(
        id: '1',
        name: 'PC',
        mac: 'AA:BB:CC:DD:EE:FF',
        address: '127.0.0.1',
        port: receiver.port);
    await UdpWakeTransport(repeats: 2).wake(device);
    await Future<void>.delayed(const Duration(milliseconds: 200));
    receiver.close();

    expect(received, hasLength(2));
    expect(received.first, buildMagicPacket(device.mac));
  });
}
