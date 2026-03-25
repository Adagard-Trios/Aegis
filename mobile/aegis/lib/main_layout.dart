import 'package:flutter/material.dart';
import '../theme.dart';

import 'screens/dashboard_screen.dart';
import 'screens/cardiology_screen.dart';
import 'screens/respiratory_screen.dart';
import 'screens/neurology_screen.dart';
import 'screens/obstetrics_screen.dart';
import 'screens/diagnostics_screen.dart';
import 'screens/environment_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/specialists_screen.dart';
import 'screens/general_physician_screen.dart';

class MainLayout extends StatefulWidget {
  const MainLayout({super.key});

  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  int _bottomNavIndex = 0;
  
  // Custom navigation state that can point to screens outside the bottom nav
  Widget _currentView = const DashboardScreen();
  String _currentTitle = 'OVERVIEW';

  void _onBottomNavTapped(int index) {
    setState(() {
      _bottomNavIndex = index;
      switch (index) {
        case 0:
          _currentView = const DashboardScreen();
          _currentTitle = 'OVERVIEW';
          break;
        case 1:
          _currentView = SpecialistsScreen(onSelect: _navigateToSpecialist);
          _currentTitle = 'SPECIALISTS';
          break;
        case 2:
          _currentView = const DiagnosticsScreen();
          _currentTitle = 'A.I. EXPERT CHAT';
          break;
        case 3:
          _currentView = const EnvironmentScreen();
          _currentTitle = 'ENVIRONMENT';
          break;
        case 4:
          _currentView = const SettingsScreen();
          _currentTitle = 'SETTINGS';
          break;
      }
    });
  }

  void _navigateToSpecialist(String title, Widget view) {
    setState(() {
      _currentTitle = title;
      _currentView = view;
      // We don't change _bottomNavIndex so it highlights the nearest category or unselects
      _bottomNavIndex = 1; 
    });
    // Close drawer if open
    if (Scaffold.of(context).isDrawerOpen) {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          _currentTitle,
          style: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 1.5, fontSize: 18),
        ),
        centerTitle: true,
      ),
      drawer: Drawer(
        backgroundColor: AegisTheme.surface,
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            const DrawerHeader(
              decoration: BoxDecoration(color: AegisTheme.background),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Icon(Icons.health_and_safety_rounded, color: AegisTheme.primary, size: 48),
                  SizedBox(height: 12),
                  Text(
                    'Aegis Specialists',
                    style: TextStyle(color: AegisTheme.textMain, fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
            ListTile(
              leading: const Icon(Icons.monitor_heart_rounded, color: AegisTheme.ecgColor),
              title: const Text('Cardiology'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('CARDIOLOGY', const CardiologyScreen());
              },
            ),
            ListTile(
              leading: const Icon(Icons.air_rounded, color: AegisTheme.rspColor),
              title: const Text('Respiratory'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('RESPIRATORY', const RespiratoryScreen());
              },
            ),
            ListTile(
              leading: const Icon(Icons.psychology_rounded, color: AegisTheme.accent),
              title: const Text('Neurology'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('NEUROLOGY', const NeurologyScreen());
              },
            ),
            ListTile(
              leading: const Icon(Icons.pregnant_woman_rounded, color: AegisTheme.fhrColor),
              title: const Text('Obstetrics'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('OBSTETRICS', const ObstetricsScreen());
              },
            ),
            ListTile(
              leading: const Icon(Icons.medical_information_rounded, color: AegisTheme.textMain),
              title: const Text('General Physician'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('GENERAL PHYSICIAN', const GeneralPhysicianScreen());
              },
            ),
          ],
        ),
      ),
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 300),
        child: _currentView,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _bottomNavIndex,
        onTap: _onBottomNavTapped,
        selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 11),
        unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 10),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Dashboard'),
          BottomNavigationBarItem(icon: Icon(Icons.people_rounded), label: 'Specialists'),
          BottomNavigationBarItem(icon: Icon(Icons.forum_rounded), label: 'AI Chat'),
          BottomNavigationBarItem(icon: Icon(Icons.thermostat_rounded), label: 'Environment'),
          BottomNavigationBarItem(icon: Icon(Icons.settings_rounded), label: 'Settings'),
        ],
      ),
    );
  }
}
