import 'package:material_ui/material_ui.dart';

import '../models/device.dart';
import '../services/device_store.dart';
import '../services/wake_service.dart';
import 'device_form_screen.dart';

class DeviceListScreen extends StatefulWidget {
  const DeviceListScreen({super.key, this.store, this.transport});

  final DeviceStore? store;
  final WakeTransport? transport;

  @override
  State<DeviceListScreen> createState() => _DeviceListScreenState();
}

class _DeviceListScreenState extends State<DeviceListScreen> {
  late final DeviceStore _store = widget.store ?? DeviceStore();
  late final WakeTransport _transport =
      widget.transport ?? UdpWakeTransport();

  List<Device> _devices = [];
  bool _loading = true;
  String? _sendingId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final devices = await _store.load();
    if (!mounted) return;
    setState(() {
      _devices = devices;
      _loading = false;
    });
  }

  Future<void> _persist() => _store.save(_devices);

  Future<void> _openForm([Device? existing]) async {
    final result = await Navigator.of(context).push<Device>(
      MaterialPageRoute(builder: (_) => DeviceFormScreen(device: existing)),
    );
    if (result == null) return;
    setState(() {
      final i = _devices.indexWhere((d) => d.id == result.id);
      if (i >= 0) {
        _devices[i] = result;
      } else {
        _devices.add(result);
      }
    });
    await _persist();
  }

  Future<void> _delete(Device device) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Eliminar equipo'),
        content: Text('¿Eliminar "${device.name}"?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancelar')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Eliminar')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _devices.removeWhere((d) => d.id == device.id));
    await _persist();
  }

  Future<void> _wake(Device device) async {
    setState(() => _sendingId = device.id);
    final messenger = ScaffoldMessenger.of(context);
    final errorColor = Theme.of(context).colorScheme.error;
    try {
      await _transport.wake(device);
      messenger.showSnackBar(SnackBar(
          content: Text('Paquete enviado a ${device.name}. '
              'Puede tardar unos segundos en encender.')));
    } catch (e) {
      messenger.showSnackBar(SnackBar(
          content: Text('No se pudo enviar: $e'),
          backgroundColor: errorColor));
    } finally {
      if (mounted) setState(() => _sendingId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Wake on LAN')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openForm(),
        icon: const Icon(Icons.add),
        label: const Text('Añadir equipo'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _devices.isEmpty
              ? const _EmptyState()
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
                  itemCount: _devices.length,
                  itemBuilder: (_, i) {
                    final d = _devices[i];
                    final sending = _sendingId == d.id;
                    return Card(
                      child: ListTile(
                        contentPadding:
                            const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        leading: const Icon(Icons.computer, size: 32),
                        title: Text(d.name),
                        subtitle: Text('${d.mac}\n${d.address}:${d.port}'),
                        isThreeLine: true,
                        onTap: () => _openForm(d),
                        onLongPress: () => _delete(d),
                        trailing: FilledButton.icon(
                          onPressed: sending ? null : () => _wake(d),
                          icon: sending
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.power_settings_new),
                          label: const Text('Encender'),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Text(
          'Todavía no hay equipos.\n'
          'Pulsa "Añadir equipo" y escribe la MAC de tu PC.',
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}
