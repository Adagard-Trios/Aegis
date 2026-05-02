"use client";

/**
 * MedVerse vest — fully procedural, no .glb assets.
 *
 * Construction:
 *   - Front + back torso panels: parametric BufferGeometry (curved to a
 *     human torso, not flat boxes).
 *   - Shoulder yokes: TubeGeometry along CatmullRomCurve3.
 *   - Side / cummerbund panels: small extruded shapes with bevels.
 *   - Control module (the ESP32-S3 brain): rounded-corner extrusion +
 *     emissive screen + status LED strip.
 *   - Sensor pads: LatheGeometry for the housing + glowing dome on top.
 *   - MOLLE webbing: array of small TubeGeometry segments.
 *   - Cable runs: TubeGeometry connecting modules.
 *   - Quick-release buckle: lathe profile + cross-bar.
 *
 * Two exports:
 *   - VestScene({ onSensorHover }) — the bare 3D content. Drop into any
 *     parent <Canvas /> (used by HeroCanvas + VestSectionCanvas).
 *   - VestModel3D() — self-contained with its own <Canvas /> + DOM
 *     overlays (tooltip, thermal scale, controls hint). Used on
 *     /vest-viewer.
 */

import React, { Suspense, useCallback, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Environment, Float } from "@react-three/drei";
import * as THREE from "three";


// ═══════════════════════════════════════════════════════════════════════════
// Color helpers
// ═══════════════════════════════════════════════════════════════════════════

function tempToColor(temp: number): THREE.Color {
  const t = Math.max(0, Math.min(1, (temp - 35.0) / 3.5));
  if (t < 0.33) return new THREE.Color().lerpColors(new THREE.Color(0x0066ff), new THREE.Color(0x00ffaa), t / 0.33);
  if (t < 0.66) return new THREE.Color().lerpColors(new THREE.Color(0x00ffaa), new THREE.Color(0xffbb00), (t - 0.33) / 0.33);
  return new THREE.Color().lerpColors(new THREE.Color(0xffbb00), new THREE.Color(0xff2200), (t - 0.66) / 0.34);
}


// ═══════════════════════════════════════════════════════════════════════════
// Materials — defined once, referenced everywhere for memory
// ═══════════════════════════════════════════════════════════════════════════

const MAT = {
  carbon: { color: "#0a0d12", roughness: 0.55, metalness: 0.05, clearcoat: 0.55, clearcoatRoughness: 0.25 } as const,
  carbonAccent: { color: "#15171d", roughness: 0.45, metalness: 0.1, clearcoat: 0.6, clearcoatRoughness: 0.2 } as const,
  strap: { color: "#0f1115", roughness: 0.92, metalness: 0.0 } as const,
  metal: { color: "#2a2e36", roughness: 0.25, metalness: 0.9 } as const,
  metalDark: { color: "#1a1d23", roughness: 0.35, metalness: 0.85 } as const,
  screen: { color: "#06121f", emissive: "#1a4d7a", emissiveIntensity: 0.6, roughness: 0.1, metalness: 0.0 } as const,
};


// ═══════════════════════════════════════════════════════════════════════════
// Curved torso panel — parametric BufferGeometry
// (Front and back of the vest, curved like a human torso)
// ═══════════════════════════════════════════════════════════════════════════

function makeTorsoPanel({
  width = 0.5,
  height = 0.78,
  curveDepth = 0.18,
  segmentsX = 24,
  segmentsY = 32,
  cutNeck = true,
}: {
  width?: number;
  height?: number;
  curveDepth?: number;
  segmentsX?: number;
  segmentsY?: number;
  cutNeck?: boolean;
}): THREE.BufferGeometry {
  const positions: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let j = 0; j <= segmentsY; j++) {
    const v = j / segmentsY;
    const y = (v - 0.5) * height;
    for (let i = 0; i <= segmentsX; i++) {
      const u = i / segmentsX;
      const x = (u - 0.5) * width;
      // Cylindrical curvature — front of vest bows outward
      const xn = (u - 0.5) * 2; // -1..1
      const z = curveDepth * (1 - xn * xn) * 0.6;
      // Slight vertical taper at top + bottom to suggest shoulder + waist
      const taper = 1 - 0.18 * Math.pow(Math.abs(v - 0.5) * 2, 3);
      positions.push(x * taper, y, z);
      // Approximate outward normal
      const nx = xn * 0.7;
      const nz = 1 - Math.abs(xn) * 0.5;
      const len = Math.sqrt(nx * nx + nz * nz);
      normals.push(nx / len, 0, nz / len);
      uvs.push(u, v);
    }
  }

  const stride = segmentsX + 1;
  for (let j = 0; j < segmentsY; j++) {
    for (let i = 0; i < segmentsX; i++) {
      const a = j * stride + i;
      const b = a + 1;
      const c = a + stride;
      const d = c + 1;
      // Skip the neck cutout — top center wedge
      if (cutNeck) {
        const uMid = (i + 0.5) / segmentsX;
        const vTop = (j + 0.5) / segmentsY;
        const inNeckCut = vTop > 0.86 && Math.abs(uMid - 0.5) < 0.16;
        if (inNeckCut) continue;
      }
      indices.push(a, c, b, b, c, d);
    }
  }

  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  geom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geom.setIndex(indices);
  return geom;
}


// ═══════════════════════════════════════════════════════════════════════════
// Side / cummerbund panel — extruded shape with bevels
// ═══════════════════════════════════════════════════════════════════════════

function makeSidePanel(): THREE.ExtrudeGeometry {
  const shape = new THREE.Shape();
  shape.moveTo(-0.06, 0.2);
  shape.lineTo(0.06, 0.2);
  shape.lineTo(0.07, 0);
  shape.lineTo(0.06, -0.2);
  shape.lineTo(-0.06, -0.2);
  shape.lineTo(-0.07, 0);
  shape.closePath();
  return new THREE.ExtrudeGeometry(shape, {
    depth: 0.13,
    bevelEnabled: true,
    bevelSize: 0.008,
    bevelThickness: 0.006,
    bevelSegments: 3,
  });
}


// ═══════════════════════════════════════════════════════════════════════════
// Control module (ESP32-S3 brain) — rounded-rect extrusion + screen + LED strip
// ═══════════════════════════════════════════════════════════════════════════

function makeRoundedRect(w: number, h: number, r: number): THREE.Shape {
  const shape = new THREE.Shape();
  shape.moveTo(-w + r, -h);
  shape.lineTo(w - r, -h);
  shape.quadraticCurveTo(w, -h, w, -h + r);
  shape.lineTo(w, h - r);
  shape.quadraticCurveTo(w, h, w - r, h);
  shape.lineTo(-w + r, h);
  shape.quadraticCurveTo(-w, h, -w, h - r);
  shape.lineTo(-w, -h + r);
  shape.quadraticCurveTo(-w, -h, -w + r, -h);
  return shape;
}

function ControlModule({ position }: { position: [number, number, number] }) {
  const ledRef = useRef<THREE.MeshStandardMaterial>(null);
  const housingGeom = useMemo(() => new THREE.ExtrudeGeometry(
    makeRoundedRect(0.13, 0.085, 0.018),
    { depth: 0.022, bevelEnabled: true, bevelSize: 0.004, bevelThickness: 0.003, bevelSegments: 3 },
  ), []);

  // Pulsing breathing for the LED strip
  useFrame(({ clock }) => {
    if (ledRef.current) {
      const t = clock.elapsedTime;
      ledRef.current.emissiveIntensity = 0.7 + Math.sin(t * 1.6) * 0.5;
    }
  });

  return (
    <group position={position}>
      {/* Housing */}
      <mesh geometry={housingGeom} castShadow receiveShadow>
        <meshPhysicalMaterial {...MAT.carbonAccent} />
      </mesh>
      {/* Screen face */}
      <mesh position={[0, 0.018, 0.024]}>
        <planeGeometry args={[0.21, 0.11]} />
        <meshStandardMaterial {...MAT.screen} />
      </mesh>
      {/* Screen bezel */}
      <mesh position={[0, 0.018, 0.0235]}>
        <ringGeometry args={[0.094, 0.105, 32]} />
        <meshStandardMaterial {...MAT.metalDark} side={THREE.DoubleSide} />
      </mesh>
      {/* LED strip — bottom */}
      <mesh ref={undefined} position={[0, -0.075, 0.024]}>
        <boxGeometry args={[0.18, 0.005, 0.001]} />
        <meshStandardMaterial ref={ledRef} color="#a855f7" emissive="#a855f7" emissiveIntensity={1.0} toneMapped={false} />
      </mesh>
      {/* Two screw heads */}
      {[-0.115, 0.115].map((x) => (
        <mesh key={x} position={[x, 0, 0.022]}>
          <cylinderGeometry args={[0.006, 0.006, 0.003, 16]} />
          <meshStandardMaterial {...MAT.metal} />
        </mesh>
      ))}
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Sensor pad — lathe-revolved housing + glowing dome
// ═══════════════════════════════════════════════════════════════════════════

interface SensorSpec {
  pos: [number, number, number];
  label: string;
  temp: number;
  hue?: number; // optional override; defaults to temp-based color
}

function SensorPad({ spec, onHover }: { spec: SensorSpec; onHover: (s: SensorSpec | null) => void }) {
  const domeRef = useRef<THREE.MeshStandardMaterial>(null);
  const haloRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  // Lathe profile — disc with a slight dome
  const housingGeom = useMemo(() => {
    const points = [
      new THREE.Vector2(0, 0),
      new THREE.Vector2(0.018, 0),
      new THREE.Vector2(0.022, 0.004),
      new THREE.Vector2(0.022, 0.012),
      new THREE.Vector2(0.018, 0.014),
      new THREE.Vector2(0.0, 0.016),
    ];
    return new THREE.LatheGeometry(points, 32);
  }, []);

  const color = useMemo(() => tempToColor(spec.temp), [spec.temp]);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    if (domeRef.current) {
      domeRef.current.emissiveIntensity = 0.4 + Math.sin(t * 2 + spec.pos[0] * 4) * 0.25 + (hovered ? 0.6 : 0);
    }
    if (haloRef.current) {
      haloRef.current.scale.setScalar(1 + Math.sin(t * 2 + spec.pos[1] * 4) * 0.1 + (hovered ? 0.3 : 0));
    }
  });

  return (
    <group
      position={spec.pos}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover(spec); }}
      onPointerOut={() => { setHovered(false); onHover(null); }}
    >
      {/* Housing */}
      <mesh geometry={housingGeom}>
        <meshPhysicalMaterial {...MAT.carbonAccent} />
      </mesh>
      {/* Glowing dome */}
      <mesh position={[0, 0.018, 0]}>
        <sphereGeometry args={[0.01, 16, 16]} />
        <meshStandardMaterial
          ref={domeRef}
          color={`#${color.getHexString()}`}
          emissive={`#${color.getHexString()}`}
          emissiveIntensity={0.6}
          toneMapped={false}
        />
      </mesh>
      {/* Halo ring — pulses on hover */}
      <mesh ref={haloRef} position={[0, 0.018, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.024, 0.028, 24]} />
        <meshBasicMaterial color={`#${color.getHexString()}`} transparent opacity={0.45} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Strap — TubeGeometry along a CatmullRomCurve3
// ═══════════════════════════════════════════════════════════════════════════

function Strap({
  points,
  radius = 0.014,
  matKey = "strap" as keyof typeof MAT,
}: {
  points: [number, number, number][];
  radius?: number;
  matKey?: keyof typeof MAT;
}) {
  const geom = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(points.map(([x, y, z]) => new THREE.Vector3(x, y, z)));
    return new THREE.TubeGeometry(curve, Math.max(40, points.length * 12), radius, 12, false);
  }, [points, radius]);
  const mat = MAT[matKey];
  return (
    <mesh geometry={geom} castShadow>
      <meshPhysicalMaterial {...mat} />
    </mesh>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// MOLLE webbing — repeated short tubes across a panel
// ═══════════════════════════════════════════════════════════════════════════

function MolleWebbing({
  position,
  rows = 3,
  cols = 4,
  rowGap = 0.06,
  colGap = 0.05,
}: {
  position: [number, number, number];
  rows?: number;
  cols?: number;
  rowGap?: number;
  colGap?: number;
}) {
  return (
    <group position={position}>
      {Array.from({ length: rows }).map((_, r) =>
        Array.from({ length: cols }).map((_, c) => {
          const x = (c - (cols - 1) / 2) * colGap;
          const y = (r - (rows - 1) / 2) * rowGap;
          return (
            <mesh key={`${r}-${c}`} position={[x, y, 0]} rotation={[0, 0, 0]}>
              <boxGeometry args={[0.04, 0.012, 0.005]} />
              <meshStandardMaterial {...MAT.strap} />
            </mesh>
          );
        })
      )}
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Quick-release buckle — center chest
// ═══════════════════════════════════════════════════════════════════════════

function QuickReleaseBuckle({ position }: { position: [number, number, number] }) {
  const ringGeom = useMemo(() => new THREE.LatheGeometry(
    [
      new THREE.Vector2(0.025, -0.005),
      new THREE.Vector2(0.03, -0.005),
      new THREE.Vector2(0.03, 0.005),
      new THREE.Vector2(0.025, 0.005),
    ],
    24,
  ), []);
  return (
    <group position={position}>
      <mesh geometry={ringGeom}>
        <meshStandardMaterial {...MAT.metal} />
      </mesh>
      <mesh>
        <torusGeometry args={[0.022, 0.0035, 12, 24]} />
        <meshStandardMaterial {...MAT.metal} />
      </mesh>
      {/* Center release button */}
      <mesh position={[0, 0, 0.006]}>
        <cylinderGeometry args={[0.012, 0.012, 0.004, 24]} />
        <meshStandardMaterial color="#a855f7" emissive="#a855f7" emissiveIntensity={0.3} toneMapped={false} />
      </mesh>
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Status LED — small emissive dot with halo
// ═══════════════════════════════════════════════════════════════════════════

function StatusLED({ position, color = "#06b6d4", phase = 0 }: { position: [number, number, number]; color?: string; phase?: number }) {
  const ref = useRef<THREE.MeshStandardMaterial>(null);
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.emissiveIntensity = 0.5 + Math.sin(clock.elapsedTime * 2.5 + phase) * 0.4;
    }
  });
  return (
    <mesh position={position}>
      <sphereGeometry args={[0.005, 12, 12]} />
      <meshStandardMaterial ref={ref} color={color} emissive={color} emissiveIntensity={0.7} toneMapped={false} />
    </mesh>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// THE VEST — composed scene
// ═══════════════════════════════════════════════════════════════════════════

const SENSORS: SensorSpec[] = [
  { pos: [-0.18, 0.18, 0.21], label: "PPG · Left pectoral", temp: 36.7 },
  { pos: [0.18, 0.18, 0.21], label: "PPG · Right pectoral", temp: 36.8 },
  { pos: [0.0, 0.32, 0.20], label: "PPG · Cervical", temp: 37.0 },
  { pos: [-0.10, 0.05, 0.23], label: "ECG · Lead I", temp: 36.6 },
  { pos: [0.10, 0.05, 0.23], label: "ECG · Lead II", temp: 36.6 },
  { pos: [0.0, -0.05, 0.23], label: "ECG · Lead III", temp: 36.6 },
  { pos: [-0.16, -0.18, 0.21], label: "DS18B20 · Skin temp L", temp: 36.4 },
  { pos: [0.16, -0.18, 0.21], label: "DS18B20 · Skin temp R", temp: 36.5 },
  { pos: [0.0, -0.22, 0.22], label: "INMP441 · I²S mic", temp: 36.3 },
];

export function VestScene({ onSensorHover }: { onSensorHover: (label: string | null, temp: number) => void }) {
  const handleHover = useCallback((s: SensorSpec | null) => {
    if (s) onSensorHover(s.label, s.temp);
    else onSensorHover(null, 0);
  }, [onSensorHover]);

  // Geometries cached once
  const frontTorso = useMemo(() => makeTorsoPanel({ width: 0.55, height: 0.78, curveDepth: 0.16, cutNeck: true }), []);
  const backTorso = useMemo(() => makeTorsoPanel({ width: 0.55, height: 0.78, curveDepth: 0.16, cutNeck: true }), []);
  const sidePanelGeom = useMemo(() => makeSidePanel(), []);

  // Shoulder yoke curve — over the shoulder from front to back
  const leftShoulderPoints: [number, number, number][] = [
    [-0.27, 0.36, 0.16],
    [-0.32, 0.42, 0.05],
    [-0.30, 0.42, -0.05],
    [-0.27, 0.36, -0.16],
  ];
  const rightShoulderPoints: [number, number, number][] = leftShoulderPoints.map(([x, y, z]) => [-x, y, z] as [number, number, number]);

  // Side straps connecting front + back at the waist
  const leftSideStrap: [number, number, number][] = [
    [-0.27, 0, 0.16],
    [-0.36, 0, 0.0],
    [-0.27, 0, -0.16],
  ];
  const rightSideStrap: [number, number, number][] = leftSideStrap.map(([x, y, z]) => [-x, y, z] as [number, number, number]);

  // Cable runs — from sensors to control module (located at center chest)
  const cableTo: [number, number, number] = [0, 0.05, 0.21];
  const cables: { from: [number, number, number]; to: [number, number, number] }[] = [
    { from: [-0.18, 0.18, 0.21], to: cableTo },
    { from: [0.18, 0.18, 0.21], to: cableTo },
    { from: [0.0, 0.32, 0.20], to: cableTo },
    { from: [-0.16, -0.18, 0.21], to: cableTo },
    { from: [0.16, -0.18, 0.21], to: cableTo },
  ];

  return (
    <>
      {/* Lighting — three-point + rims */}
      <ambientLight intensity={0.35} />
      <directionalLight position={[3, 5, 4]} intensity={0.6} color="#fdf6e8" />
      <directionalLight position={[-3, 2, -2]} intensity={0.25} color="#7dd3fc" />
      <pointLight position={[0, 0.2, 1.5]} intensity={0.45} color="#a855f7" distance={3} decay={2} />
      <pointLight position={[0.8, -0.2, 0.6]} intensity={0.3} color="#d946ef" distance={2.5} decay={2} />
      <pointLight position={[-0.8, 0.4, -0.5]} intensity={0.2} color="#06b6d4" distance={2.5} decay={2} />

      <Float speed={1} rotationIntensity={0.05} floatIntensity={0.15} floatingRange={[-0.005, 0.005]}>
        <group rotation={[0, 0, 0]} position={[0, 0, 0]}>

          {/* ── Front torso panel ── */}
          <mesh geometry={frontTorso} castShadow receiveShadow>
            <meshPhysicalMaterial {...MAT.carbon} side={THREE.DoubleSide} />
          </mesh>

          {/* Center spine accent stripe (front) */}
          <mesh position={[0, -0.05, 0.205]}>
            <boxGeometry args={[0.018, 0.55, 0.002]} />
            <meshPhysicalMaterial {...MAT.carbonAccent} />
          </mesh>

          {/* ── Back torso panel ── */}
          <group rotation={[0, Math.PI, 0]}>
            <mesh geometry={backTorso} castShadow receiveShadow>
              <meshPhysicalMaterial {...MAT.carbon} side={THREE.DoubleSide} />
            </mesh>
          </group>

          {/* ── Side cummerbund panels ── */}
          {[
            { x: -0.34, rot: -0.18 },
            { x: 0.34, rot: 0.18 },
          ].map(({ x, rot }, i) => (
            <mesh
              key={i}
              geometry={sidePanelGeom}
              position={[x, 0, -0.06]}
              rotation={[0, rot, 0]}
              castShadow
            >
              <meshPhysicalMaterial {...MAT.carbon} />
            </mesh>
          ))}

          {/* ── Shoulder yokes ── */}
          <Strap points={leftShoulderPoints} radius={0.025} matKey="carbonAccent" />
          <Strap points={rightShoulderPoints} radius={0.025} matKey="carbonAccent" />

          {/* ── Side straps ── */}
          <Strap points={leftSideStrap} radius={0.018} matKey="strap" />
          <Strap points={rightSideStrap} radius={0.018} matKey="strap" />

          {/* ── Control module (center chest) ── */}
          <ControlModule position={[0, 0.05, 0.215]} />

          {/* ── Quick-release buckle (below control module) ── */}
          <QuickReleaseBuckle position={[0, -0.10, 0.215]} />

          {/* ── MOLLE webbing on the lower abdomen ── */}
          <MolleWebbing position={[0, -0.30, 0.21]} rows={2} cols={5} rowGap={0.06} colGap={0.06} />
          {/* MOLLE on the back */}
          <group rotation={[0, Math.PI, 0]}>
            <MolleWebbing position={[0, -0.10, 0.21]} rows={3} cols={5} />
          </group>

          {/* ── Cable runs from sensors to control module ── */}
          {cables.map((c, i) => {
            const mid: [number, number, number] = [
              (c.from[0] + c.to[0]) / 2,
              (c.from[1] + c.to[1]) / 2,
              0.218,
            ];
            return (
              <Strap
                key={i}
                points={[c.from, mid, c.to]}
                radius={0.0035}
                matKey="metalDark"
              />
            );
          })}

          {/* ── Sensor pads ── */}
          {SENSORS.map((s, i) => (
            <SensorPad key={i} spec={s} onHover={handleHover} />
          ))}

          {/* ── Status LEDs scattered along the upper chest ── */}
          <StatusLED position={[-0.22, 0.0, 0.218]} color="#06b6d4" phase={0.0} />
          <StatusLED position={[0.22, 0.0, 0.218]} color="#06b6d4" phase={0.6} />
          <StatusLED position={[-0.22, -0.04, 0.218]} color="#10b981" phase={1.2} />
          <StatusLED position={[0.22, -0.04, 0.218]} color="#10b981" phase={1.8} />

          {/* ── Shoulder accent strips (LED line along the yoke) ── */}
          <mesh position={[-0.30, 0.40, 0.0]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.06, 0.0015, 8, 24, Math.PI]} />
            <meshStandardMaterial color="#a855f7" emissive="#a855f7" emissiveIntensity={1.2} toneMapped={false} />
          </mesh>
          <mesh position={[0.30, 0.40, 0.0]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.06, 0.0015, 8, 24, Math.PI]} />
            <meshStandardMaterial color="#a855f7" emissive="#a855f7" emissiveIntensity={1.2} toneMapped={false} />
          </mesh>

        </group>
      </Float>
    </>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Loading fallback
// ═══════════════════════════════════════════════════════════════════════════

function LoadingFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-2 text-violet-300">
        <div className="w-8 h-8 rounded-full border-2 border-violet-300 border-t-transparent animate-spin" />
        <p className="text-xs font-mono uppercase tracking-wider">Loading vest…</p>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// VestModel3D — self-contained: own Canvas + DOM overlays
// ═══════════════════════════════════════════════════════════════════════════

export function VestModel3D() {
  const [hovered, setHovered] = useState<{ label: string; temp: number } | null>(null);

  const handleHover = useCallback((label: string | null, temp: number) => {
    setHovered(label ? { label, temp } : null);
  }, []);

  return (
    <div className="relative w-full h-full min-h-[420px]">

      {/* Hover tooltip */}
      {hovered && (
        <div className="absolute top-4 left-4 z-10 bg-black/80 backdrop-blur-md border border-violet-500/40 rounded-lg px-4 py-3 shadow-[0_0_24px_rgba(168,85,247,0.4)]">
          <p className="text-[10px] font-semibold text-violet-300 uppercase tracking-[0.15em]">
            {hovered.label}
          </p>
          <p className="text-2xl font-bold text-white mt-0.5 font-mono">
            {hovered.temp.toFixed(1)}°C
          </p>
          <div className="flex items-center gap-2 mt-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: `#${tempToColor(hovered.temp).getHexString()}` }} />
            <span className="text-[10px] text-white/60 uppercase tracking-wider font-medium">
              {hovered.temp > 37.3 ? "Elevated" : hovered.temp < 36.0 ? "Cool zone" : "Normal"}
            </span>
          </div>
        </div>
      )}

      {/* Thermal scale */}
      <div className="absolute bottom-4 left-4 z-10 bg-black/70 backdrop-blur-md border border-white/10 rounded-lg px-3 py-2">
        <p className="text-[8px] text-violet-300/70 uppercase tracking-[0.2em] mb-1 font-semibold">
          Thermal gradient
        </p>
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-white/50 font-mono">35.0</span>
          <div className="w-20 h-2 rounded-sm" style={{ background: "linear-gradient(90deg, #0066ff, #00ffaa, #ffbb00, #ff2200)" }} />
          <span className="text-[9px] text-white/50 font-mono">38.5</span>
        </div>
      </div>

      {/* Controls hint */}
      <div className="absolute top-4 right-4 z-10 bg-black/50 backdrop-blur-md border border-white/10 rounded-lg px-3 py-1.5">
        <p className="text-[8px] text-white/60 uppercase tracking-[0.2em]">
          Drag to rotate · scroll to zoom
        </p>
      </div>

      <Suspense fallback={<LoadingFallback />}>
        <Canvas
          camera={{ position: [0, 0.05, 1.6], fov: 38 }}
          style={{ background: "transparent" }}
          gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
          dpr={[1, 2]}
          shadows
        >
          <VestScene onSensorHover={handleHover} />
          <OrbitControls
            enablePan={false}
            minDistance={1.0}
            maxDistance={3.5}
            minPolarAngle={Math.PI / 4}
            maxPolarAngle={(Math.PI * 3) / 4}
            target={[0, 0.05, 0]}
          />
          <Environment preset="city" />
        </Canvas>
      </Suspense>
    </div>
  );
}
