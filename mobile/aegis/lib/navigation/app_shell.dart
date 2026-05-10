import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../widgets/app_drawer.dart';
import '../widgets/offline_banner.dart';
import 'nav_destinations.dart';

/// Persistent app shell. Hosts the M3 navigation surface plus an
/// auto-attached `Scaffold.drawer` (the futuristic quick-actions
/// sidebar) — both are visible together; the drawer is opened from
/// the AppBar's hamburger when needed.
///
/// Adapts the navigation surface to the available width:
///   - **< 700 dp wide** (phones, foldables closed): bottom
///     [NavigationBar] — five tabs, M3 standard.
///   - **≥ 700 dp** (large foldables, tablets, landscape phones): a
///     side [NavigationRail] with extended labels — fingers reach
///     thumbs further on a small phone, but on wide layouts the bar
///     wastes vertical pixels.
///
/// The `StatefulNavigationShell` underneath preserves per-tab navigator
/// stacks so switching layouts (rotate phone, open foldable) keeps
/// every branch's deep state.
class AppShell extends StatelessWidget {
  final StatefulNavigationShell shell;
  const AppShell({super.key, required this.shell});

  static const double _railBreakpoint = 700;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final useRail = constraints.maxWidth >= _railBreakpoint;
        return Scaffold(
          drawer: const AegisAppDrawer(),
          appBar: _buildAppBar(context),
          body: SafeArea(
            top: false,
            child: useRail ? _buildRailLayout(context) : _buildBarLayout(),
          ),
          bottomNavigationBar: useRail ? null : _buildNavigationBar(),
        );
      },
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return AppBar(
      backgroundColor: cs.surfaceContainer,
      surfaceTintColor: cs.surfaceTint,
      elevation: 0,
      scrolledUnderElevation: 1,
      // Hamburger trigger — opens the AegisAppDrawer.
      leading: Builder(
        builder: (ctx) => IconButton(
          icon: const Icon(Icons.menu_rounded),
          tooltip: 'Open menu',
          onPressed: () => Scaffold.of(ctx).openDrawer(),
        ),
      ),
      // Brand mark — small icon + word-mark. Uppercase letter-spaced
      // for futuristic feel.
      title: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [cs.primary, cs.tertiary],
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.health_and_safety_rounded,
                color: Colors.white, size: 16),
          ),
          const SizedBox(width: 10),
          Text(
            'MedVerse',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.6,
                ),
          ),
        ],
      ),
      centerTitle: false,
    );
  }

  Widget _buildBarLayout() {
    return Column(
      children: [
        // Phase 4 IoMT banner — renders nothing in the happy path.
        const OfflineBanner(),
        Expanded(child: shell),
      ],
    );
  }

  Widget _buildRailLayout(BuildContext context) {
    return Row(
      children: [
        _SideRail(
          selectedIndex: shell.currentIndex,
          onSelected: (i) => _goBranch(i),
        ),
        VerticalDivider(
          width: 1,
          color: Theme.of(context).colorScheme.outlineVariant,
        ),
        Expanded(
          child: Column(
            children: [
              const OfflineBanner(),
              Expanded(child: shell),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildNavigationBar() {
    return _GlowNavigationBar(
      selectedIndex: shell.currentIndex,
      onDestinationSelected: (i) => _goBranch(i),
    );
  }

  void _goBranch(int i) {
    // `goBranch` jumps to the branch's root route while preserving
    // its internal navigation stack. Tap-twice-to-reset is the
    // canonical M3 NavigationBar behaviour.
    shell.goBranch(i, initialLocation: i == shell.currentIndex);
  }
}

// ── Bottom NavigationBar (phone-class layouts) ───────────────────────

class _GlowNavigationBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;
  const _GlowNavigationBar({
    required this.selectedIndex,
    required this.onDestinationSelected,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    // Subtle gradient veneer above the standard NavigationBar — pulls
    // the eye toward the selected indicator without overwhelming it.
    return Container(
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(
            color: cs.primary.withValues(alpha: 0.12),
            width: 1,
          ),
        ),
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            cs.surfaceContainer,
            cs.surfaceContainerLow,
          ],
        ),
      ),
      child: NavigationBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        selectedIndex: selectedIndex,
        onDestinationSelected: onDestinationSelected,
        destinations: navDestinations
            .map(
              (d) => NavigationDestination(
                icon: Icon(d.icon),
                selectedIcon: _GlowIcon(icon: d.selectedIcon),
                label: d.label,
                tooltip: d.semanticLabel,
              ),
            )
            .toList(),
      ),
    );
  }
}

/// Selected-icon wrapper that draws a soft accent glow behind the
/// glyph — gives the active tab a "powered" feel without breaking the
/// M3 indicator pill's geometry.
class _GlowIcon extends StatelessWidget {
  final IconData icon;
  const _GlowIcon({required this.icon});
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Stack(
      alignment: Alignment.center,
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: cs.primary.withValues(alpha: 0.35),
                blurRadius: 12,
                spreadRadius: 0.5,
              ),
            ],
          ),
        ),
        Icon(icon, color: cs.onSecondaryContainer),
      ],
    );
  }
}

// ── Side NavigationRail (tablet / wide layouts) ──────────────────────

class _SideRail extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onSelected;
  const _SideRail({required this.selectedIndex, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return NavigationRail(
      backgroundColor: cs.surfaceContainerLow,
      selectedIndex: selectedIndex,
      onDestinationSelected: onSelected,
      labelType: NavigationRailLabelType.all,
      indicatorColor: cs.secondaryContainer,
      destinations: navDestinations
          .map(
            (d) => NavigationRailDestination(
              icon: Icon(d.icon),
              selectedIcon: Icon(d.selectedIcon, color: cs.onSecondaryContainer),
              label: Text(d.label),
            ),
          )
          .toList(),
    );
  }
}
