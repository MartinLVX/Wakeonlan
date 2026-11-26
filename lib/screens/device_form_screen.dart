import 'package:material_ui/material_ui.dart';

import '../models/device.dart';
import '../services/magic_packet.dart';

class DeviceFormScreen extends StatefulWidget {
  const DeviceFormScreen({super.key, this.device});

  final Device? device;

  @override
  State<DeviceFormScreen> createState() => _DeviceFormScreenState();
}

class _DeviceFormScreenState extends State<DeviceFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final _name = TextEditingController(text: widget.device?.name ?? '');
  late final _mac = TextEditingController(text: widget.device?.mac ?? '');
  late final _address = TextEditingController(
      text: widget.device?.address ?? '255.255.255.255');
  late final _port =
      TextEditingController(text: (widget.device?.port ?? 9).toString());

  @override
  void dispose() {
    _name.dispose();
    _mac.dispose();
    _address.dispose();
    _port.dispose();
    super.dispose();
  }

  void _save() {
    if (!_formKey.currentState!.validate()) return;
    final device = Device(
      id: widget.device?.id ??
          DateTime.now().microsecondsSinceEpoch.toString(),
      name: _name.text.trim(),
      mac: normalizeMac(_mac.text),
      address: _address.text.trim(),
      port: int.parse(_port.text.trim()),
    );
    Navigator.of(context).pop(device);
  }

  @override
  Widget build(BuildContext context) {
    final editing = widget.device != null;
    return Scaffold(
      appBar: AppBar(title: Text(editing ? 'Editar equipo' : 'Nuevo equipo')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _name,
              decoration: const InputDecoration(
                  labelText: 'Nombre', hintText: 'PC de escritorio'),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Escribe un nombre' : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _mac,
              decoration: const InputDecoration(
                  labelText: 'Dirección MAC',
                  hintText: 'AA:BB:CC:DD:EE:FF',
                  helperText: 'La de la tarjeta de red por cable del PC'),
              textCapitalization: TextCapitalization.characters,
              validator: (v) => (v != null && isValidMac(v))
                  ? null
                  : 'MAC no válida (12 dígitos hexadecimales)',
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _address,
              decoration: const InputDecoration(
                  labelText: 'Dirección de broadcast o host',
                  helperText:
                      'En casa: 255.255.255.255 o la de tu red (ej. 192.168.1.255)',
                  helperMaxLines: 2),
              keyboardType: TextInputType.url,
              validator: (v) => (v == null || v.trim().isEmpty)
                  ? 'Escribe una dirección'
                  : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _port,
              decoration: const InputDecoration(
                  labelText: 'Puerto UDP', helperText: 'Normalmente 9'),
              keyboardType: TextInputType.number,
              validator: (v) {
                final p = int.tryParse(v?.trim() ?? '');
                return (p == null || p < 1 || p > 65535)
                    ? 'Puerto entre 1 y 65535'
                    : null;
              },
            ),
            const SizedBox(height: 24),
            FilledButton(onPressed: _save, child: const Text('Guardar')),
          ],
        ),
      ),
    );
  }
}
