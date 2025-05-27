import 'package:flutter/material.dart';

class FAQPage extends StatelessWidget {
  const FAQPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('FAQ & Help')),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          _faqSection(
            context,
            title: 'What is ET0?',
            content: 'ET0 (reference evapotranspiration) is the amount of water lost from soil and plants through evaporation and transpiration. It helps determine how much irrigation is needed.\n\nVisual: ☀️🌱💧\nHigh ET0 means more water is needed for your crops.',
          ),
          _faqSection(
            context,
            title: 'How does the irrigation prediction work?',
            content: 'The system uses a machine learning model that considers temperature, precipitation, ET0, soil moisture, and soil temperature.\n\nInputs: Weather, Soil\nOutput: Irrigation action (ON/OFF/ALERT).\n\nVisual: 🤖 + 🌦️ + 🌱 = 💧 or 🚫 or ⚠️',
          ),
          _faqSection(
            context,
            title: 'What do the different alert colors mean?',
            content: '• Orange: High temperature (>30°C)\n• Blue: Low soil moisture (<0.2)\n• Red: ALERT or high soil temp (>28°C)\n• Purple: High ET0 (>0.1)\n\nAlerts help you act quickly to protect your crops.',
          ),
          _faqSection(
            context,
            title: 'How to use manual irrigation controls?',
            content: 'Use the green/red button on the Live page to start or stop irrigation manually. The system will show the current state (ON/OFF) and update in real time.\n\nVisual: 🟢 Start | 🔴 Stop',
          ),
          _faqSection(
            context,
            title: 'Best practices for irrigation and soil health',
            content: '• Monitor soil moisture regularly.\n• Avoid over-irrigation to prevent root rot.\n• Use alerts to guide your actions.\n• Check the Analytics page for trends and past alerts.\n• Keep your sensors clean and calibrated.\n• Schedule irrigation for early morning or late afternoon.',
          ),
          _faqSection(
            context,
            title: 'How to troubleshoot if the app says "Offline"?',
            content: '1. Check your internet connection.\n2. Make sure your phone or computer is online.\n3. If the problem persists, restart the app.\n4. Contact your technician if you still have issues.',
          ),
          _faqSection(
            context,
            title: 'How to care for your sensors?',
            content: '• Clean sensors gently with water and a soft brush.\n• Check for damage or corrosion.\n• Calibrate sensors every season for best results.\n• Place sensors at root depth for accurate readings.',
          ),
          _faqSection(
            context,
            title: 'How to interpret the Analytics page?',
            content: '• Charts show trends for temperature, soil moisture, ET0, and soil temp.\n• Use filters to see data for the last hour, day, or week.\n• Alerts are shown with color and time.\n• Look for patterns to optimize your irrigation schedule.',
          ),
          _faqSection(
            context,
            title: 'What is the ideal soil moisture for my crops?',
            content: 'Most crops grow best when soil moisture is between 0.2 and 0.4 (20-40%).\nCheck your crop guide for specific needs.',
          ),
          const SizedBox(height: 24),
          Center(child: Text('For more help, contact your local agricultural advisor or technician.', style: TextStyle(color: Colors.grey))),
        ],
      ),
    );
  }

  Widget _faqSection(BuildContext context, {required String title, required String content}) {
    return ExpansionTile(
      title: Text(title, style: Theme.of(context).textTheme.titleMedium),
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 8.0, right: 8.0, bottom: 12.0),
          child: Text(content, style: Theme.of(context).textTheme.bodyMedium),
        ),
      ],
    );
  }
}
