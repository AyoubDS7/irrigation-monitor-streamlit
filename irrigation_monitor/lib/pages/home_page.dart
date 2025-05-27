import 'package:flutter/material.dart';
import 'package:firebase_database/firebase_database.dart';
import 'dart:async';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  DatabaseReference get _db => FirebaseDatabase.instance.ref();
  Map<String, dynamic>? latestData;
  String? latestKey;
  bool isLoading = true;
  bool irrigateButtonLoading = false;
  bool irrigationState = false;
  StreamSubscription? _irrigationSub;
  bool connected = false;
  Timer? _connectionTimer;
  String alertMsg = '';
  Color alertColor = Colors.transparent;

  @override
  void initState() {
    super.initState();
    _listenToLatestData();
    _listenToIrrigationState();
    _startConnectionCheck();
  }

  void _startConnectionCheck() {
    _connectionTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      setState(() {
        connected = !isLoading;
      });
    });
  }

  void _listenToIrrigationState() {
    _irrigationSub = _db.child('irrigation_control/irrigate').onValue.listen((event) {
      setState(() {
        irrigationState = event.snapshot.value == true;
      });
    });
  }

  void _listenToLatestData() {
    _db.child('irrigation_data').orderByKey().limitToLast(1).onValue.listen((event) {
      if (event.snapshot.value != null) {
        final dataMap = Map<String, dynamic>.from(event.snapshot.value as Map);
        final key = dataMap.keys.first;
        final data = Map<String, dynamic>.from(dataMap[key]);
        setState(() {
          latestKey = key;
          latestData = data;
          isLoading = false;
        });
        _checkAlerts(data);
      }
    });
  }

  void _checkAlerts(Map<String, dynamic> data) {
    String msg = '';
    Color color = Colors.transparent;
    // Only show one alert at a time, in order of severity
    if ((data['prediction'] ?? 0) == 3) {
      msg = 'ALERT: Check system!';
      color = Colors.red;
    } else if ((data['api_temp'] ?? 0) > 35) {
      msg = 'High temperature!';
      color = Colors.orange;
    } else if ((data['api_temp'] ?? 0) < 5) {
      msg = 'Low temperature!';
      color = Colors.blueGrey;
    } else if ((data['soil_moisture_api'] ?? 1.0) * 100 < 25) {
      msg = 'Soil is too dry. Irrigation needed.';
      color = Colors.blue;
    } else if ((data['soil_moisture_api'] ?? 0) * 100 > 80) {
      msg = 'Soil may be oversaturated. Avoid overwatering.';
      color = Colors.teal;
    } else if ((data['env_moisture_api'] ?? 100) < 20) {
      msg = 'Air is too dry. Evaporation is high.';
      color = Colors.indigo;
    } else if ((data['env_moisture_api'] ?? 0) > 90) {
      msg = 'High humidity. Risk of fungal disease.';
      color = Colors.purple;
    } else if ((data['api_precip_mm'] ?? 0) > 2) {
      msg = 'Rain expected soon. Postpone irrigation.';
      color = Colors.blueAccent;
    } else if ((data['rain_sensor_value'] ?? 9999) < 100) {
      msg = 'Rain detected. Irrigation paused.';
      color = Colors.blueAccent;
    } else {
      msg = '';
      color = Colors.transparent;
    }
    if (msg != alertMsg) {
      setState(() {
        alertMsg = msg;
        alertColor = color;
      });
    }
  }

  Future<void> _toggleIrrigation() async {
    setState(() { irrigateButtonLoading = true; });
    await _db.child('irrigation_control/irrigate').set(!irrigationState);
    await Future.delayed(const Duration(seconds: 1));
    setState(() { irrigateButtonLoading = false; });
  }

  Widget _liveCard({required String label, required String value, required IconData icon, required Color color, String? unit}) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 500),
      curve: Curves.easeInOut,
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color, width: 1.5),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(width: 16),
          Expanded(child: Text(label, style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 18))),
          Text(value, style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 20)),
          if (unit != null) Text(' $unit', style: TextStyle(color: color, fontSize: 16)),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _irrigationSub?.cancel();
    _connectionTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFE8F5E9), // light green agri background
      appBar: AppBar(
        title: const Text('Live Data'),
        backgroundColor: const Color(0xFF388E3C),
        actions: [
          Row(
            children: [
              Icon(Icons.circle, color: connected ? Colors.green : Colors.red, size: 14),
              const SizedBox(width: 4),
              Text(connected ? 'Connected' : 'Offline', style: TextStyle(color: connected ? Colors.green : Colors.red)),
              const SizedBox(width: 16),
            ],
          ),
        ],
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : latestData == null
              ? const Center(child: Text('No data available'))
              : Stack(
                  children: [
                    ListView(
                      padding: const EdgeInsets.all(16.0),
                      children: [
                        if (alertMsg.isNotEmpty)
                          AnimatedContainer(
                            duration: const Duration(milliseconds: 500),
                            padding: const EdgeInsets.all(12),
                            margin: const EdgeInsets.only(bottom: 12),
                            decoration: BoxDecoration(
                              color: alertColor.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: alertColor, width: 1.5),
                            ),
                            child: Row(
                              children: [
                                Icon(Icons.warning, color: alertColor),
                                const SizedBox(width: 8),
                                Expanded(child: Text(alertMsg, style: TextStyle(color: alertColor, fontWeight: FontWeight.bold))),
                              ],
                            ),
                          ),
                        _liveCard(
                          label: 'Temperature',
                          value: latestData!['api_temp'] != null ? latestData!['api_temp'].toStringAsFixed(1) : '-',
                          icon: Icons.thermostat,
                          color: (latestData!['api_temp'] ?? 0) > 35 ? Colors.red : Colors.orange,
                          unit: '°C',
                        ),
                        _liveCard(
                          label: 'Precipitation',
                          value: latestData!['api_precip_mm']?.toString() ?? '-',
                          icon: Icons.grain,
                          color: Colors.blue,
                          unit: 'mm',
                        ),
                        _liveCard(
                          label: 'Soil Moisture',
                          value: latestData!['soil_moisture_api'] != null ? (latestData!['soil_moisture_api'] * 100).toStringAsFixed(1) : '-',
                          icon: Icons.water_drop,
                          color: (latestData!['soil_moisture_api'] ?? 1.0) < 0.2 ? Colors.blue : Colors.teal,
                          unit: '%',
                        ),
                        _liveCard(
                          label: 'Soil Temp',
                          value: latestData!['soil_temp'] != null ? latestData!['soil_temp'].toStringAsFixed(1) : '-',
                          icon: Icons.thermostat_auto,
                          color: (latestData!['soil_temp'] ?? 0) > 28 ? Colors.redAccent : Colors.brown,
                          unit: '°C',
                        ),
                        _liveCard(
                          label: 'Relative Humidity',
                          value: latestData!['env_moisture_api'] != null ? latestData!['env_moisture_api'].toStringAsFixed(1) : '-',
                          icon: Icons.cloud,
                          color: Colors.indigo,
                          unit: '%',
                        ),
                        _liveCard(
                          label: 'ET0',
                          value: latestData!['et0'] != null ? latestData!['et0'].toStringAsFixed(3) : '-',
                          icon: Icons.opacity,
                          color: Colors.blueGrey,
                          unit: 'mm',
                        ),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            Text('Prediction: ', style: Theme.of(context).textTheme.titleMedium),
                            _buildPrediction(latestData!['prediction'] is int ? latestData!['prediction'] : int.tryParse(latestData!['prediction'].toString())),
                          ],
                        ),
                        const SizedBox(height: 24),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            AnimatedContainer(
                              duration: const Duration(milliseconds: 500),
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              decoration: BoxDecoration(
                                color: irrigationState ? Colors.green : Colors.grey,
                                borderRadius: BorderRadius.circular(24),
                              ),
                              child: Row(
                                children: [
                                  Icon(irrigationState ? Icons.water : Icons.block, color: Colors.white),
                                  const SizedBox(width: 8),
                                  Text(irrigationState ? 'Irrigation ON' : 'Irrigation OFF', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 32),
                        Text('Last Update: ${latestData!['api_last_update'] ?? '-'}', style: Theme.of(context).textTheme.bodySmall),
                      ],
                    ),
                    // Floating alert notification button
                    if (alertMsg.isNotEmpty)
                      Positioned(
                        top: 24,
                        left: 24,
                        right: 24,
                        child: AnimatedOpacity(
                          opacity: alertMsg.isNotEmpty ? 1.0 : 0.0,
                          duration: const Duration(milliseconds: 400),
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: alertColor.withOpacity(0.95),
                              foregroundColor: Colors.white,
                              elevation: 8,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                              padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
                            ),
                            icon: Icon(Icons.notification_important, color: Colors.white),
                            label: Text(
                              alertMsg,
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                            ),
                            onPressed: () {}, // Could expand to show more info or dismiss
                          ),
                        ),
                      ),
                    Positioned(
                      bottom: 24,
                      right: 24,
                      child: FloatingActionButton.extended(
                        backgroundColor: irrigationState ? Colors.red : Colors.green,
                        icon: irrigateButtonLoading
                            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : Icon(irrigationState ? Icons.stop : Icons.play_arrow),
                        label: Text(irrigationState ? 'Stop Irrigation' : 'Start Irrigation'),
                        onPressed: irrigateButtonLoading ? null : _toggleIrrigation,
                      ),
                    ),
                  ],
                ),
    );
  }

  Widget _buildPrediction(int? prediction) {
    if (prediction == null) return const Text('No prediction');
    switch (prediction) {
      case 0:
        return const Chip(label: Text('OFF'), backgroundColor: Colors.grey);
      case 1:
        return const Chip(label: Text('ON'), backgroundColor: Colors.green);
      case 2:
        return const Chip(label: Text('No adjustment'), backgroundColor: Colors.blueGrey);
      case 3:
        return const Chip(label: Text('ALERT'), backgroundColor: Colors.red);
      default:
        return Text('Unknown ([38;5;9m$prediction[0m)');
    }
  }
}
