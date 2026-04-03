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
import 'screens/digital_twin_screen.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
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
          _currentView = const DigitalTwinScreen();
          _currentTitle = 'DIGITAL TWIN';
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
      _bottomNavIndex = 1; 
    });
    if (Scaffold.of(context).isDrawerOpen) {
      Navigator.of(context).pop();
    }
  }

  Future<void> _uploadLabResult() async {
    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);
    
    if (image != null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Processing Lab Results via MedVerse AI...')),
        );
      }
      
      try {
        var request = http.MultipartRequest('POST', Uri.parse('http://10.0.2.2:8000/api/upload-lab-results'));
        request.files.add(await http.MultipartFile.fromPath('file', image.path));
        var response = await request.send();

        if (response.statusCode == 200 && mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Lab Results Processed & Pharmacological Profile Updated!')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Upload failed: $e')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MedVerse', style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: 1.2, fontSize: 18)),
        centerTitle: true,
      ),
      drawer: Drawer(
        backgroundColor: MedVerseTheme.surface,
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            const DrawerHeader(
              decoration: BoxDecoration(color: MedVerseTheme.background),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Icon(Icons.health_and_safety_rounded, color: MedVerseTheme.primary, size: 48),
                  SizedBox(height: 12),
                  Text(
                    'MedVerse Specialists',
                    style: TextStyle(color: MedVerseTheme.textMain, fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
            ListTile(
              leading: const Icon(Icons.monitor_heart_rounded, color: MedVerseTheme.ecgColor),
              title: const Text('Cardiology'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('CARDIOLOGY', const CardiologyScreen());
              },
            ),
            ListTile(
              leading: const Icon(Icons.air_rounded, color: MedVerseTheme.rspColor),
              title: const Text('Respiratory'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('RESPIRATORY', const RespiratoryScreen());
              },
            ),
            ListTile(
              leading: const Icon(Icons.psychology_rounded, color: MedVerseTheme.accent),
              title: const Text('Neurology'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('NEUROLOGY', const NeurologyScreen());
              },
            ),
            ListTile(
              leading: const Icon(Icons.pregnant_woman_rounded, color: MedVerseTheme.fhrColor),
              title: const Text('Obstetrics'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('OBSTETRICS', const ObstetricsScreen());
              },
            ),
            ListTile(
              leading: const Icon(Icons.medical_information_rounded, color: MedVerseTheme.textMain),
              title: const Text('General Physician'),
              onTap: () {
                Navigator.pop(context);
                _navigateToSpecialist('GENERAL PHYSICIAN', const GeneralPhysicianScreen());
              },
            ),
            const Divider(color: MedVerseTheme.border),
            ListTile(
              leading: const Icon(Icons.accessibility_new_rounded, color: Colors.blueAccent),
              title: const Text('3D Digital Twin'),
              onTap: () {
                Navigator.pop(context);
                setState(() {
                  _currentTitle = 'DIGITAL TWIN';
                  _currentView = const DigitalTwinScreen();
                });
              },
            ),
            ListTile(
              leading: const Icon(Icons.upload_file_rounded, color: MedVerseTheme.primary),
              title: const Text('Upload Lab Results'),
              onTap: () {
                Navigator.pop(context);
                _uploadLabResult();
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
        type: BottomNavigationBarType.fixed,
        backgroundColor: MedVerseTheme.background,
        selectedItemColor: MedVerseTheme.primary,
        unselectedItemColor: MedVerseTheme.textMuted,
        currentIndex: _bottomNavIndex,
        onTap: _onBottomNavTapped,
        selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 11),
        unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 10),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Dashboard'),
          BottomNavigationBarItem(icon: Icon(Icons.people_rounded), label: 'Specialists'),
          BottomNavigationBarItem(icon: Icon(Icons.accessibility_new_rounded), label: '3D Twin'),
          BottomNavigationBarItem(icon: Icon(Icons.thermostat_rounded), label: 'Environment'),
          BottomNavigationBarItem(icon: Icon(Icons.settings_rounded), label: 'Settings'),
        ],
      ),
    );
  }
}
