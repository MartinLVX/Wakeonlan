import 'package:shared_preferences/shared_preferences.dart';

import '../models/device.dart';

/// Guarda los equipos en el propio teléfono.
class DeviceStore {
  static const _key = 'devices';

  Future<List<Device>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    try {
      return Device.decodeList(raw);
    } catch (_) {
      return [];
    }
  }

  Future<void> save(List<Device> devices) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, Device.encodeList(devices));
  }
}
