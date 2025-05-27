import 'package:flutter/material.dart';
import 'package:firebase_database/firebase_database.dart';
import 'package:fl_chart/fl_chart.dart';
import 'dart:async';
import 'dart:math';

class AnalyticsPage extends StatefulWidget {
  const AnalyticsPage({super.key});

  @override
  State<AnalyticsPage> createState() => _AnalyticsPageState();
}

class _AnalyticsPageState extends State<AnalyticsPage> {
  DatabaseReference get _db => FirebaseDatabase.instance.ref();
  List<Map<String, dynamic>> history = [];
  List<Map<String, dynamic>> alerts = [];
  bool isLoading = true;
  String filter = 'all';
  StreamSubscription? _sub;

  @override
  void initState() {
    super.initState();
    _listenToHistory();
  }

  void _listenToHistory() {
    _sub = _db.child('irrigation_data').onValue.listen((event) {
      if (event.snapshot.value != null) {
        final dataMap = Map<String, dynamic>.from(event.snapshot.value as Map);
        final List<Map<String, dynamic>> dataList = dataMap.entries.map((e) {
          return Map<String, dynamic>.from(e.value);
        }).toList();
        dataList.sort((a, b) => (a['timestamp'] ?? '').compareTo(b['timestamp'] ?? ''));
        if (!mounted) return;
        setState(() {
          history = _filterHistory(dataList);
          alerts = [];
          final Set<String> seenMessages = {};
          for (final d in dataList.reversed) {
            final double? soilMoisture = d['soil_moisture_api'] != null ? (d['soil_moisture_api'] as num) * 100 : null;
            final double? rainSensor = d['rain_sensor_value'] != null ? (d['rain_sensor_value'] as num).toDouble() : null;
            final double? precipMm = d['api_precip_mm'] != null ? (d['api_precip_mm'] as num).toDouble() : null;
            final double? temp = d['api_temp'] != null ? (d['api_temp'] as num).toDouble() : null;
            final double? humidity = d['env_moisture_api'] != null ? (d['env_moisture_api'] as num).toDouble() : null;
            final String timestamp = d['timestamp'] ?? d['api_last_update'] ?? '-';
            // 1. Soil Moisture Alerts
            if (soilMoisture != null && soilMoisture < 25) {
              final msg = 'Soil is too dry. Irrigation needed.';
              if (!seenMessages.contains(msg)) {
                alerts.add({'title': 'Low Soil Moisture', 'message': msg, 'timestamp': timestamp});
                seenMessages.add(msg);
              }
            }
            if (soilMoisture != null && soilMoisture > 80) {
              final msg = 'Soil may be oversaturated. Avoid overwatering.';
              if (!seenMessages.contains(msg)) {
                alerts.add({'title': 'Soil Oversaturation', 'message': msg, 'timestamp': timestamp});
                seenMessages.add(msg);
              }
            }
            // 2. Rain Alerts
            if (rainSensor != null && rainSensor < 100) {
              final msg = 'Rain detected. Irrigation paused.';
              if (!seenMessages.contains(msg)) {
                alerts.add({'title': 'Rain Detected', 'message': msg, 'timestamp': timestamp});
                seenMessages.add(msg);
              }
            }
            if (precipMm != null && precipMm > 2) {
              final msg = 'Rain expected soon. Postpone irrigation.';
              if (!seenMessages.contains(msg)) {
                alerts.add({'title': 'Forecasted Rain', 'message': msg, 'timestamp': timestamp});
                seenMessages.add(msg);
              }
            }
            // 3. Temperature Alerts
            if (temp != null && temp > 35) {
              final msg = 'High temperature. Watch for crop stress.';
              if (!seenMessages.contains(msg)) {
                alerts.add({'title': 'High Temperature', 'message': msg, 'timestamp': timestamp});
                seenMessages.add(msg);
              }
            }
            if (temp != null && temp < 5) {
              final msg = 'Low temperature. Frost risk possible.';
              if (!seenMessages.contains(msg)) {
                alerts.add({'title': 'Low Temperature', 'message': msg, 'timestamp': timestamp});
                seenMessages.add(msg);
              }
            }
            // 4. Humidity Alerts
            if (humidity != null && humidity < 20) {
              final msg = 'Air is too dry. Evaporation is high.';
              if (!seenMessages.contains(msg)) {
                alerts.add({'title': 'Very Low Humidity', 'message': msg, 'timestamp': timestamp});
                seenMessages.add(msg);
              }
            }
            if (humidity != null && humidity > 90) {
              final msg = 'High humidity. Risk of fungal disease.';
              if (!seenMessages.contains(msg)) {
                alerts.add({'title': 'Very High Humidity', 'message': msg, 'timestamp': timestamp});
                seenMessages.add(msg);
              }
            }
            if (alerts.length >= 10) break;
          }
          isLoading = false;
        });
      } else {
        if (!mounted) return;
        setState(() { isLoading = false; });
      }
    });
  }

  List<Map<String, dynamic>> _filterHistory(List<Map<String, dynamic>> dataList) {
    if (filter == 'all') return dataList;
    final now = DateTime.now();
    if (filter == 'hour') {
      return dataList.where((d) {
        final t = DateTime.tryParse(d['timestamp'] ?? '') ?? now;
        return now.difference(t).inHours < 1;
      }).toList();
    } else if (filter == 'day') {
      return dataList.where((d) {
        final t = DateTime.tryParse(d['timestamp'] ?? '') ?? now;
        return now.difference(t).inDays < 1;
      }).toList();
    } else if (filter == 'week') {
      return dataList.where((d) {
        final t = DateTime.tryParse(d['timestamp'] ?? '') ?? now;
        return now.difference(t).inDays < 7;
      }).toList();
    }
    return dataList;
  }

  Widget _dashboardChartCard({required String title, required List<FlSpot> spots, required Color color, required String unit, IconData? icon, List<String>? xLabels, double? yInterval}) {
    // Prepare Y axis min/max for better rounding
    double? minY, maxY;
    if (spots.isNotEmpty) {
      minY = spots.map((e) => e.y).reduce((a, b) => a < b ? a : b);
      maxY = spots.map((e) => e.y).reduce((a, b) => a > b ? a : b);
      // Round to nearest 1 or 0.1 for clarity
      double range = maxY - minY;
      if (range < 2) {
        minY = (minY * 10).floor() / 10;
        maxY = (maxY * 10).ceil() / 10;
      } else {
        minY = minY.floorToDouble();
        maxY = maxY.ceilToDouble();
      }
    }
    return Card(
      elevation: 8,
      margin: const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      color: Colors.white, // Modern white background
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (icon != null) Icon(icon, color: color, size: 28),
                if (icon != null) const SizedBox(width: 8),
                Text(title, style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 18)),
              ],
            ),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: color,
                      barWidth: 4,
                      dotData: FlDotData(show: false), // Hide dots
                      belowBarData: BarAreaData(show: true, color: color.withOpacity(0.10)),
                    ),
                  ],
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 32,
                        getTitlesWidget: (value, meta) {
                          // Show only rounded Y values
                          return Text(value.toStringAsFixed((maxY != null && maxY - minY! < 2) ? 1 : 0), style: const TextStyle(fontSize: 11));
                        },
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 36,
                        interval: spots.length > 1 ? (spots.length - 1).toDouble() : 1,
                        getTitlesWidget: (value, meta) {
                          // Show only first and last time label
                          if (xLabels != null && xLabels.isNotEmpty) {
                            if (value.toInt() == 0) {
                              return Padding(
                                padding: const EdgeInsets.only(top: 8.0),
                                child: Text(xLabels.first, style: const TextStyle(fontSize: 10)),
                              );
                            } else if (value.toInt() == xLabels.length - 1) {
                              return Padding(
                                padding: const EdgeInsets.only(top: 8.0),
                                child: Text(xLabels.last, style: const TextStyle(fontSize: 10)),
                              );
                            }
                          }
                          return const SizedBox.shrink();
                        },
                      ),
                    ),
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: false),
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: true,
                    horizontalInterval: yInterval,
                    verticalInterval: null,
                    getDrawingHorizontalLine: (value) => FlLine(color: Colors.grey.withOpacity(0.10), strokeWidth: 1),
                    getDrawingVerticalLine: (value) => FlLine(color: Colors.grey.withOpacity(0.07), strokeWidth: 1),
                  ),
                  lineTouchData: LineTouchData(
                    enabled: true,
                    touchTooltipData: LineTouchTooltipData(
                      tooltipBgColor: color.withOpacity(0.85),
                      getTooltipItems: (touchedSpots) => touchedSpots.map((spot) {
                        String timeLabel = '';
                        if (xLabels != null && spot.x.toInt() >= 0 && spot.x.toInt() < xLabels.length && xLabels[spot.x.toInt()].isNotEmpty) {
                          timeLabel = xLabels[spot.x.toInt()];
                        }
                        return LineTooltipItem(
                          '${spot.y.toStringAsFixed((yInterval != null && yInterval < 2) ? 1 : 0)} $unit' + (timeLabel.isNotEmpty ? '\n$timeLabel' : ''),
                          const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                        );
                      }).toList(),
                    ),
                  ),
                  minX: 0,
                  maxX: (spots.isNotEmpty ? spots.length - 1 : 0).toDouble(),
                  minY: minY,
                  maxY: maxY,
                  showingTooltipIndicators: [],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFE8F5E9), // agri dashboard background
      appBar: AppBar(
        title: const Text('Analytics'),
        backgroundColor: const Color(0xFF388E3C),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_alt),
            onSelected: (v) => setState(() { filter = v; _listenToHistory(); }),
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'all', child: Text('All')),
              const PopupMenuItem(value: 'hour', child: Text('Last Hour')),
              const PopupMenuItem(value: 'day', child: Text('Last Day')),
              const PopupMenuItem(value: 'week', child: Text('Last Week')),
            ],
          ),
        ],
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : history.isEmpty
              ? const Center(child: Text('No historical data available'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(8.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Recent Alerts', style: Theme.of(context).textTheme.titleLarge),
                      ...alerts.map((alert) => Card(
                            color: Colors.orange.withOpacity(0.15),
                            child: ListTile(
                              leading: const Icon(Icons.warning, color: Colors.orange),
                              title: Text(alert['title'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold)),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(alert['message'] ?? ''),
                                  Text('Time: ${alert['timestamp']}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                                ],
                              ),
                            ),
                          )),
                      const SizedBox(height: 16),
                      // Prepare time labels for X axis (show only a few for clarity)
                      ..._buildAllCharts(),
                    ],
                  ),
                ),
    );
  }

  List<Widget> _buildAllCharts() {
    // Helper to extract time labels for X axis with more visible ticks
    List<String> _getTimeLabels(String key) {
      final labels = <String>[];
      if (history.isEmpty) return labels;
      for (final d in history) {
        final ts = d['timestamp'] ?? d['api_last_update'] ?? '';
        if (ts.isNotEmpty) {
          final dt = DateTime.tryParse(ts);
          if (dt != null) {
            labels.add(dt.hour.toString().padLeft(2, '0') + ':' + dt.minute.toString().padLeft(2, '0'));
          } else {
            labels.add('');
          }
        } else {
          labels.add('');
        }
      }
      // Show about 5-7 labels: first, last, and evenly spaced in between
      int n = labels.length;
      int ticks = n < 7 ? n : 7;
      if (n > 2) {
        for (int i = 0; i < n; i++) {
          if (i != 0 && i != n - 1 && (i % (n ~/ (ticks - 1)) != 0)) {
            labels[i] = '';
          }
        }
      }
      return labels;
    }

    // Helper for Y axis interval (echelle)
    double? _getYInterval(List<FlSpot> spots) {
      if (spots.isEmpty) return null;
      double minY = spots.map((e) => e.y).reduce((a, b) => a < b ? a : b);
      double maxY = spots.map((e) => e.y).reduce((a, b) => a > b ? a : b);
      double range = maxY - minY;
      if (range == 0) return 1;
      // Make step about 1/5 of range, rounded to 1, 2, 5, 10, etc.
      double rawStep = range / 5;
      double magnitude = rawStep == 0 ? 1 : (log(rawStep.abs()) / log(10)).floorToDouble();
      double base = pow(10, magnitude).toDouble();
      double step = (rawStep / base).ceil() * base;
      if (step < 1) step = 1;
      return step;
    }

    return [
      _dashboardChartCard(
        title: 'Temperature (°C)',
        spots: [for (int i = 0; i < history.length; i++) if (history[i]['api_temp'] != null) FlSpot(i.toDouble(), (history[i]['api_temp'] as num).toDouble())],
        color: Colors.orange,
        unit: '°C',
        icon: Icons.thermostat,
        xLabels: _getTimeLabels('api_temp'),
        yInterval: _getYInterval([for (int i = 0; i < history.length; i++) if (history[i]['api_temp'] != null) FlSpot(i.toDouble(), (history[i]['api_temp'] as num).toDouble())]),
      ),
      _dashboardChartCard(
        title: 'Soil Moisture (%)',
        spots: [for (int i = 0; i < history.length; i++) if (history[i]['soil_moisture_api'] != null) FlSpot(i.toDouble(), ((history[i]['soil_moisture_api'] as num) * 100))],
        color: Colors.blue,
        unit: '%',
        icon: Icons.water_drop,
        xLabels: _getTimeLabels('soil_moisture_api'),
        yInterval: _getYInterval([for (int i = 0; i < history.length; i++) if (history[i]['soil_moisture_api'] != null) FlSpot(i.toDouble(), ((history[i]['soil_moisture_api'] as num) * 100))]),
      ),
      _dashboardChartCard(
        title: 'ET0',
        spots: [for (int i = 0; i < history.length; i++) if (history[i]['et0'] != null) FlSpot(i.toDouble(), (history[i]['et0'] as num).toDouble())],
        color: Colors.green,
        unit: '',
        icon: Icons.opacity,
        xLabels: _getTimeLabels('et0'),
        yInterval: _getYInterval([for (int i = 0; i < history.length; i++) if (history[i]['et0'] != null) FlSpot(i.toDouble(), (history[i]['et0'] as num).toDouble())]),
      ),
      _dashboardChartCard(
        title: 'Soil Temp (°C)',
        spots: [for (int i = 0; i < history.length; i++) if (history[i]['soil_temp'] != null) FlSpot(i.toDouble(), (history[i]['soil_temp'] as num).toDouble())],
        color: Colors.redAccent,
        unit: '°C',
        icon: Icons.thermostat_auto,
        xLabels: _getTimeLabels('soil_temp'),
        yInterval: _getYInterval([for (int i = 0; i < history.length; i++) if (history[i]['soil_temp'] != null) FlSpot(i.toDouble(), (history[i]['soil_temp'] as num).toDouble())]),
      ),
    ];
  }
}
