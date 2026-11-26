import 'package:material_ui/material_ui.dart';

import 'screens/device_list_screen.dart';

void main() {
  runApp(const WakeOnLanApp());
}

class WakeOnLanApp extends StatelessWidget {
  const WakeOnLanApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Wake on LAN',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.teal,
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: Colors.teal,
        brightness: Brightness.dark,
        useMaterial3: true,
      ),
      home: const DeviceListScreen(),
    );
  }
}
