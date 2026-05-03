"use client";

/**
 * MedVerse vest — fully procedural realism build, no .glb assets.
 *
 * Realism techniques used (no external textures):
 *   - Procedural fabric normal + roughness maps (DataTexture) → visible weave.
 *   - Flat-ribbon webbing straps (not tubes) on a tangent-aligned BufferGeometry.
 *   - Stitching ridges traced along every panel seam.
 *   - Real centre zipper (teeth + tape + slider + pull tab).
 *   - Medical-style ECG electrodes (snap stud + silver hydrogel disc, not glowing).
 *   - Subtle status LEDs only — no neon torus halos.
 *   - PCF soft shadows + ContactShadows under the vest for grounding.
 *
 * Two exports preserved:
 *   - VestScene({ onSensorHover }) — drop-in 3D content, used by HeroCanvas.
 *   - VestModel3D() — self-contained Canvas + DOM overlays, used on /vest-viewer.
 */

import React, { Suspense, useCallback, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Environment, Float, ContactShadows } from "@react-three/drei";
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
// Procedural fabric textures — Cordura-style woven nylon
// Generated once at module load, reused across every panel.
// ═══════════════════════════════════════════════════════════════════════════

let _fabricNormal: THREE.DataTexture | null = null;
function getFabricNormal(): THREE.DataTexture {
  if (_fabricNormal) return _fabricNormal;
  const size = 256;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      // 4x4 weave cell — alternating warp / weft fibres
      const cellX = Math.floor(x / 4) % 2;
      const cellY = Math.floor(y / 4) % 2;
      const lx = (x % 4) - 1.5;
      const ly = (y % 4) - 1.5;
      let nx = 0;
      let ny = 0;
      if ((cellX + cellY) % 2 === 0) {
        // Horizontal fibre — bump along Y
        ny = Math.sin((ly / 1.5) * Math.PI * 0.5) * 0.55;
        nx = (Math.random() - 0.5) * 0.06;
      } else {
        // Vertical fibre — bump along X
        nx = Math.sin((lx / 1.5) * Math.PI * 0.5) * 0.55;
        ny = (Math.random() - 0.5) * 0.06;
      }
      const nz = Math.sqrt(Math.max(0, 1 - nx * nx - ny * ny));
      data[i + 0] = Math.floor((nx * 0.5 + 0.5) * 255);
      data[i + 1] = Math.floor((ny * 0.5 + 0.5) * 255);
      data[i + 2] = Math.floor(nz * 255);
      data[i + 3] = 255;
    }
  }
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(14, 18);
  tex.anisotropy = 4;
  tex.needsUpdate = true;
  _fabricNormal = tex;
  return tex;
}

let _fabricRough: THREE.DataTexture | null = null;
function getFabricRoughness(): THREE.DataTexture {
  if (_fabricRough) return _fabricRough;
  const size = 128;
  const data = new Uint8Array(size * size * 4);
  for (let i = 0; i < size * size; i++) {
    // Slight micro-variation in roughness so highlights aren't flat
    const r = 210 + Math.floor(Math.random() * 35);
    data[i * 4 + 0] = r;
    data[i * 4 + 1] = r;
    data[i * 4 + 2] = r;
    data[i * 4 + 3] = 255;
  }
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(14, 18);
  tex.needsUpdate = true;
  _fabricRough = tex;
  return tex;
}

// Webbing texture — coarser, more visible weave for nylon straps
let _webbingNormal: THREE.DataTexture | null = null;
function getWebbingNormal(): THREE.DataTexture {
  if (_webbingNormal) return _webbingNormal;
  const size = 128;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      // Strong horizontal bias — webbing has visible parallel stitches
      const ny = Math.sin((y / 4) * Math.PI) * 0.5;
      const nx = Math.sin((x / 8) * Math.PI) * 0.15;
      const nz = Math.sqrt(Math.max(0, 1 - nx * nx - ny * ny));
      data[i + 0] = Math.floor((nx * 0.5 + 0.5) * 255);
      data[i + 1] = Math.floor((ny * 0.5 + 0.5) * 255);
      data[i + 2] = Math.floor(nz * 255);
      data[i + 3] = 255;
    }
  }
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(2, 12);
  tex.needsUpdate = true;
  _webbingNormal = tex;
  return tex;
}


// ═══════════════════════════════════════════════════════════════════════════
// Curved torso panel — parametric BufferGeometry with proper UVs
// Slightly higher segment count for smooth fabric look + thickness via shell.
// ═══════════════════════════════════════════════════════════════════════════

interface TorsoResult {
  geom: THREE.BufferGeometry;
  perimeter: THREE.Vector3[];
}

function makeTorsoPanel({
  width = 0.55,
  height = 0.82,
  curveDepth = 0.16,
  segmentsX = 36,
  segmentsY = 48,
  cutNeck = true,
}: {
  width?: number;
  height?: number;
  curveDepth?: number;
  segmentsX?: number;
  segmentsY?: number;
  cutNeck?: boolean;
}): TorsoResult {
  const positions: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  const grid: THREE.Vector3[][] = [];

  for (let j = 0; j <= segmentsY; j++) {
    grid[j] = [];
    const v = j / segmentsY;
    const y = (v - 0.5) * height;
    for (let i = 0; i <= segmentsX; i++) {
      const u = i / segmentsX;
      // Slight body taper — narrower at waist (v=0.3) than chest
      const waistTaper = 1 - 0.08 * Math.exp(-Math.pow((v - 0.32) * 4, 2));
      const x = (u - 0.5) * width * waistTaper;
      // Cylindrical curvature — bows outward in the middle
      const xn = (u - 0.5) * 2;
      // Anatomical: deeper curve at chest, shallower at hip
      const chestFactor = 0.85 + 0.4 * Math.exp(-Math.pow((v - 0.65) * 3, 2));
      const z = curveDepth * (1 - xn * xn) * 0.55 * chestFactor;
      // Vertical taper at top (shoulders) + bottom (waist hem)
      const shoulderTaper = 1 - 0.16 * Math.pow(Math.max(0, v - 0.85) * 6, 2);
      const finalX = x * shoulderTaper;
      positions.push(finalX, y, z);
      grid[j][i] = new THREE.Vector3(finalX, y, z);
      // Outward normal — derived from curve gradient
      const nx = xn * 0.65;
      const nz = 1 - Math.abs(xn) * 0.4;
      const len = Math.sqrt(nx * nx + nz * nz);
      normals.push(nx / len, 0, nz / len);
      uvs.push(u, v);
    }
  }

  const stride = segmentsX + 1;
  const inNeck = (i: number, j: number): boolean => {
    if (!cutNeck) return false;
    const uMid = (i + 0.5) / segmentsX;
    const vTop = (j + 0.5) / segmentsY;
    return vTop > 0.86 && Math.abs(uMid - 0.5) < 0.18;
  };

  for (let j = 0; j < segmentsY; j++) {
    for (let i = 0; i < segmentsX; i++) {
      if (inNeck(i, j)) continue;
      const a = j * stride + i;
      const b = a + 1;
      const c = a + stride;
      const d = c + 1;
      indices.push(a, c, b, b, c, d);
    }
  }

  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  geom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geom.setIndex(indices);
  geom.computeTangents?.();

  // Build perimeter loop for stitching: bottom edge → right edge → top (around neck) → left edge
  const perimeter: THREE.Vector3[] = [];
  // Bottom edge (left to right)
  for (let i = 0; i <= segmentsX; i++) perimeter.push(grid[0][i].clone().add(new THREE.Vector3(0, 0, 0.0015)));
  // Right edge (bottom to top)
  for (let j = 1; j <= segmentsY; j++) perimeter.push(grid[j][segmentsX].clone().add(new THREE.Vector3(0, 0, 0.0015)));
  // Top edge — go right-to-left, jumping around the neck cutout
  for (let i = segmentsX; i >= 0; i--) {
    const uMid = i / segmentsX;
    if (cutNeck && Math.abs(uMid - 0.5) < 0.2) continue;
    perimeter.push(grid[segmentsY][i].clone().add(new THREE.Vector3(0, 0, 0.0015)));
  }
  // Left edge (top to bottom)
  for (let j = segmentsY - 1; j >= 0; j--) perimeter.push(grid[j][0].clone().add(new THREE.Vector3(0, 0, 0.0015)));

  return { geom, perimeter };
}


// ═══════════════════════════════════════════════════════════════════════════
// Stitching — thin dashed-tube along a curve, hugging the panel surface
// ═══════════════════════════════════════════════════════════════════════════

function Stitching({ points, dashLength = 0.012, gapLength = 0.006, radius = 0.0015 }: {
  points: THREE.Vector3[];
  dashLength?: number;
  gapLength?: number;
  radius?: number;
}) {
  const meshes = useMemo(() => {
    if (points.length < 2) return [];
    const curve = new THREE.CatmullRomCurve3(points, false, "catmullrom", 0.1);
    const totalLength = curve.getLength();
    const segments: { a: number; b: number }[] = [];
    let pos = 0;
    while (pos < totalLength) {
      const a = pos / totalLength;
      const b = Math.min(1, (pos + dashLength) / totalLength);
      segments.push({ a, b });
      pos += dashLength + gapLength;
    }
    return segments.map(({ a, b }, idx) => {
      const sub = new THREE.CatmullRomCurve3([curve.getPointAt(a), curve.getPointAt((a + b) / 2), curve.getPointAt(b)]);
      const geom = new THREE.TubeGeometry(sub, 4, radius, 4, false);
      return { geom, key: idx };
    });
  }, [points, dashLength, gapLength, radius]);

  return (
    <group>
      {meshes.map(({ geom, key }) => (
        <mesh key={key} geometry={geom}>
          <meshStandardMaterial color="#2a2d33" roughness={0.6} metalness={0.05} />
        </mesh>
      ))}
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Flat ribbon webbing — replaces TubeGeometry for straps
// Builds a tangent-aligned flat strap that follows a CatmullRomCurve3.
// ═══════════════════════════════════════════════════════════════════════════

function makeRibbon(curve: THREE.Curve<THREE.Vector3>, width = 0.028, segments = 80): THREE.BufferGeometry {
  const positions: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  const upRef = new THREE.Vector3(0, 1, 0);

  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const p = curve.getPointAt(t);
    const tan = curve.getTangentAt(t).normalize();
    // Right vector orthogonal to tangent + world-up; fall back if parallel
    let right = new THREE.Vector3().crossVectors(tan, upRef);
    if (right.lengthSq() < 0.001) right.set(1, 0, 0);
    right.normalize();
    const nrm = new THREE.Vector3().crossVectors(right, tan).normalize();

    const left = p.clone().addScaledVector(right, -width / 2);
    const rightP = p.clone().addScaledVector(right, width / 2);

    positions.push(left.x, left.y, left.z, rightP.x, rightP.y, rightP.z);
    normals.push(nrm.x, nrm.y, nrm.z, nrm.x, nrm.y, nrm.z);
    uvs.push(0, t * 12, 1, t * 12);
  }

  for (let i = 0; i < segments; i++) {
    const a = i * 2;
    indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
  }

  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geom.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  geom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geom.setIndex(indices);
  return geom;
}

function FlatStrap({ points, width = 0.028 }: { points: [number, number, number][]; width?: number }) {
  const geom = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(points.map(([x, y, z]) => new THREE.Vector3(x, y, z)));
    return makeRibbon(curve, width, Math.max(40, points.length * 16));
  }, [points, width]);
  const normalMap = useMemo(() => getWebbingNormal(), []);
  return (
    <mesh geometry={geom} castShadow>
      <meshStandardMaterial
        color="#15181d"
        roughness={0.9}
        metalness={0.0}
        normalMap={normalMap}
        normalScale={new THREE.Vector2(0.6, 0.6)}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Zipper — repeated tooth boxes + tape + slider with pull tab
// ═══════════════════════════════════════════════════════════════════════════

function Zipper({ position, length = 0.5 }: { position: [number, number, number]; length?: number }) {
  const teeth = useMemo(() => {
    const count = Math.floor(length / 0.008);
    return Array.from({ length: count }).map((_, i) => i);
  }, [length]);
  const sliderRef = useRef<THREE.Group>(null);
  // Slider sits about 30% down — not at the very top
  const sliderY = -length * 0.15;
  return (
    <group position={position}>
      {/* Zipper tape — left + right */}
      {[-0.012, 0.012].map((x) => (
        <mesh key={x} position={[x, 0, -0.001]}>
          <boxGeometry args={[0.014, length, 0.0015]} />
          <meshStandardMaterial color="#0e1014" roughness={0.85} metalness={0.0} />
        </mesh>
      ))}
      {/* Teeth — alternating left/right */}
      {teeth.map((i) => {
        const y = (i / teeth.length - 0.5) * length;
        const x = i % 2 === 0 ? -0.0035 : 0.0035;
        return (
          <mesh key={i} position={[x, y, 0.0008]}>
            <boxGeometry args={[0.0035, 0.005, 0.002]} />
            <meshStandardMaterial color="#3a3d44" roughness={0.35} metalness={0.85} />
          </mesh>
        );
      })}
      {/* Slider body */}
      <group ref={sliderRef} position={[0, sliderY, 0]}>
        <mesh position={[0, 0, 0.001]}>
          <boxGeometry args={[0.022, 0.024, 0.005]} />
          <meshStandardMaterial color="#2a2d34" roughness={0.3} metalness={0.85} />
        </mesh>
        {/* Slider neck */}
        <mesh position={[0, -0.014, 0.002]}>
          <boxGeometry args={[0.005, 0.005, 0.003]} />
          <meshStandardMaterial color="#3a3d44" roughness={0.3} metalness={0.85} />
        </mesh>
        {/* Pull tab */}
        <mesh position={[0, -0.024, 0.001]}>
          <boxGeometry args={[0.012, 0.014, 0.0015]} />
          <meshStandardMaterial color="#1a1d22" roughness={0.7} metalness={0.4} />
        </mesh>
      </group>
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Side / cummerbund panel — extruded shape with bevels (kept; small change)
// ═══════════════════════════════════════════════════════════════════════════

function makeSidePanel(): THREE.ExtrudeGeometry {
  const shape = new THREE.Shape();
  shape.moveTo(-0.06, 0.22);
  shape.lineTo(0.06, 0.22);
  shape.lineTo(0.07, 0);
  shape.lineTo(0.06, -0.22);
  shape.lineTo(-0.06, -0.22);
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
// Rounded rect helper for the control module
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


// ═══════════════════════════════════════════════════════════════════════════
// Control module — realistic plastic housing with screen, USB-C cutout,
// vent slits, recessed screws, single subtle status LED.
// ═══════════════════════════════════════════════════════════════════════════

function ControlModule({ position }: { position: [number, number, number] }) {
  const ledRef = useRef<THREE.MeshStandardMaterial>(null);
  const housingGeom = useMemo(() => new THREE.ExtrudeGeometry(
    makeRoundedRect(0.13, 0.085, 0.018),
    { depth: 0.022, bevelEnabled: true, bevelSize: 0.004, bevelThickness: 0.003, bevelSegments: 4 },
  ), []);

  // Slow breathing on the single status LED — far subtler than before
  useFrame(({ clock }) => {
    if (ledRef.current) {
      const t = clock.elapsedTime;
      ledRef.current.emissiveIntensity = 0.5 + Math.sin(t * 1.4) * 0.25;
    }
  });

  return (
    <group position={position}>
      {/* Housing — moulded plastic, slightly rough */}
      <mesh geometry={housingGeom} castShadow receiveShadow>
        <meshStandardMaterial color="#16181d" roughness={0.55} metalness={0.05} />
      </mesh>

      {/* Recessed screen well */}
      <mesh position={[0, 0.018, 0.022]}>
        <boxGeometry args={[0.20, 0.10, 0.0015]} />
        <meshStandardMaterial color="#0a0c10" roughness={0.4} metalness={0.0} />
      </mesh>
      {/* Active screen surface */}
      <mesh position={[0, 0.018, 0.0235]}>
        <planeGeometry args={[0.18, 0.085]} />
        <meshStandardMaterial color="#04101c" emissive="#0e3a5c" emissiveIntensity={0.4} roughness={0.15} metalness={0.0} />
      </mesh>
      {/* Faux UI ring on the screen */}
      <mesh position={[0, 0.018, 0.0238]}>
        <ringGeometry args={[0.026, 0.030, 48]} />
        <meshStandardMaterial color="#5cc7ff" emissive="#5cc7ff" emissiveIntensity={0.6} toneMapped={false} side={THREE.DoubleSide} />
      </mesh>

      {/* Vent slits along the bottom edge */}
      {[-0.06, -0.04, -0.02, 0, 0.02, 0.04, 0.06].map((x) => (
        <mesh key={x} position={[x, -0.06, 0.022]}>
          <boxGeometry args={[0.012, 0.0025, 0.002]} />
          <meshStandardMaterial color="#06080b" roughness={0.9} metalness={0.0} />
        </mesh>
      ))}

      {/* USB-C cutout indicator on the underside */}
      <mesh position={[0, -0.084, 0.011]}>
        <boxGeometry args={[0.022, 0.004, 0.018]} />
        <meshStandardMaterial color="#06080b" roughness={0.9} metalness={0.0} />
      </mesh>

      {/* Recessed screws — four corners */}
      {[[-0.115, 0.07], [0.115, 0.07], [-0.115, -0.04], [0.115, -0.04]].map(([x, y], idx) => (
        <group key={idx} position={[x, y, 0.022]}>
          <mesh>
            <cylinderGeometry args={[0.0055, 0.0055, 0.001, 16]} />
            <meshStandardMaterial color="#22252b" roughness={0.4} metalness={0.85} />
          </mesh>
          {/* Cross-head slit */}
          <mesh position={[0, 0.0006, 0]}>
            <boxGeometry args={[0.008, 0.0008, 0.001]} />
            <meshStandardMaterial color="#0a0c10" roughness={0.6} metalness={0.5} />
          </mesh>
        </group>
      ))}

      {/* Single status LED — subtle teal pulse */}
      <mesh position={[0.10, -0.075, 0.024]}>
        <sphereGeometry args={[0.003, 12, 12]} />
        <meshStandardMaterial ref={ledRef} color="#22d3ee" emissive="#22d3ee" emissiveIntensity={0.6} toneMapped={false} />
      </mesh>

      {/* Brand etch — small embossed line */}
      <mesh position={[0, -0.045, 0.0235]}>
        <planeGeometry args={[0.05, 0.005]} />
        <meshStandardMaterial color="#3a3d44" roughness={0.6} metalness={0.6} />
      </mesh>
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Sensors — three realistic styles
// ═══════════════════════════════════════════════════════════════════════════

interface SensorSpec {
  pos: [number, number, number];
  label: string;
  temp: number;
  kind: "ecg" | "ppg" | "temp" | "mic";
}

// Medical-style ECG electrode — silver hydrogel disc on a snap stud
function ECGElectrode({ spec, onHover }: { spec: SensorSpec; onHover: (s: SensorSpec | null) => void }) {
  const [hovered, setHovered] = useState(false);
  const ringRef = useRef<THREE.MeshStandardMaterial>(null);
  useFrame(({ clock }) => {
    if (ringRef.current) {
      ringRef.current.opacity = hovered ? 0.8 : 0.0;
    }
  });
  return (
    <group
      position={spec.pos}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover(spec); }}
      onPointerOut={() => { setHovered(false); onHover(null); }}
    >
      {/* Adhesive backing — slightly larger pale disc */}
      <mesh position={[0, 0, 0.001]}>
        <cylinderGeometry args={[0.024, 0.024, 0.002, 32]} />
        <meshStandardMaterial color="#d8d4c8" roughness={0.85} metalness={0.0} />
      </mesh>
      {/* Silver hydrogel pad */}
      <mesh position={[0, 0, 0.003]}>
        <cylinderGeometry args={[0.018, 0.018, 0.002, 32]} />
        <meshStandardMaterial color="#a8acb2" roughness={0.4} metalness={0.6} />
      </mesh>
      {/* Snap stud */}
      <mesh position={[0, 0, 0.007]}>
        <cylinderGeometry args={[0.006, 0.007, 0.005, 24]} />
        <meshStandardMaterial color="#c8ccd2" roughness={0.25} metalness={0.9} />
      </mesh>
      <mesh position={[0, 0, 0.0095]}>
        <sphereGeometry args={[0.005, 16, 16]} />
        <meshStandardMaterial color="#e8ecf2" roughness={0.2} metalness={0.95} />
      </mesh>
      {/* Hover halo (transparent ring) */}
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0.002]}>
        <ringGeometry args={[0.026, 0.029, 32]} />
        <meshStandardMaterial ref={ringRef} color="#a855f7" emissive="#a855f7" emissiveIntensity={0.8} toneMapped={false} transparent opacity={0} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// PPG sensor — small dark window with subtle red LED inside
function PPGSensor({ spec, onHover }: { spec: SensorSpec; onHover: (s: SensorSpec | null) => void }) {
  const [hovered, setHovered] = useState(false);
  const ledRef = useRef<THREE.MeshStandardMaterial>(null);
  useFrame(({ clock }) => {
    if (ledRef.current) {
      ledRef.current.emissiveIntensity = 0.6 + Math.sin(clock.elapsedTime * 3 + spec.pos[0] * 4) * 0.25 + (hovered ? 0.4 : 0);
    }
  });
  return (
    <group
      position={spec.pos}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover(spec); }}
      onPointerOut={() => { setHovered(false); onHover(null); }}
    >
      {/* Black plastic housing */}
      <mesh>
        <cylinderGeometry args={[0.015, 0.017, 0.006, 32]} />
        <meshStandardMaterial color="#0a0c10" roughness={0.5} metalness={0.1} />
      </mesh>
      {/* Glass window */}
      <mesh position={[0, 0, 0.0035]}>
        <cylinderGeometry args={[0.01, 0.01, 0.0008, 32]} />
        <meshPhysicalMaterial color="#020202" roughness={0.05} metalness={0.0} transmission={0.6} thickness={0.001} />
      </mesh>
      {/* Red LED inside (PPG uses ~660nm red) */}
      <mesh position={[0, 0, 0.004]}>
        <cylinderGeometry args={[0.0035, 0.0035, 0.0006, 16]} />
        <meshStandardMaterial ref={ledRef} color="#ff2030" emissive="#ff2030" emissiveIntensity={0.7} toneMapped={false} />
      </mesh>
      {/* Tiny status dot beside it */}
      <mesh position={[0.005, 0.004, 0.004]}>
        <sphereGeometry args={[0.0008, 8, 8]} />
        <meshStandardMaterial color="#22c55e" emissive="#22c55e" emissiveIntensity={0.5} toneMapped={false} />
      </mesh>
    </group>
  );
}

// Temp sensor — small embossed metal puck (DS18B20 style)
function TempSensor({ spec, onHover }: { spec: SensorSpec; onHover: (s: SensorSpec | null) => void }) {
  const [hovered, setHovered] = useState(false);
  const dotColor = useMemo(() => tempToColor(spec.temp).getHexString(), [spec.temp]);
  return (
    <group
      position={spec.pos}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover(spec); }}
      onPointerOut={() => { setHovered(false); onHover(null); }}
    >
      <mesh>
        <cylinderGeometry args={[0.014, 0.015, 0.005, 32]} />
        <meshStandardMaterial color="#3a3d44" roughness={0.35} metalness={0.85} />
      </mesh>
      <mesh position={[0, 0, 0.003]}>
        <cylinderGeometry args={[0.011, 0.011, 0.0005, 32]} />
        <meshStandardMaterial color={`#${dotColor}`} roughness={0.4} metalness={0.7} emissive={`#${dotColor}`} emissiveIntensity={hovered ? 0.4 : 0.15} toneMapped={false} />
      </mesh>
    </group>
  );
}

// I2S mic — tiny perforated grille
function MicSensor({ spec, onHover }: { spec: SensorSpec; onHover: (s: SensorSpec | null) => void }) {
  const [hovered, setHovered] = useState(false);
  return (
    <group
      position={spec.pos}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover(spec); }}
      onPointerOut={() => { setHovered(false); onHover(null); }}
    >
      <mesh>
        <cylinderGeometry args={[0.012, 0.013, 0.005, 32]} />
        <meshStandardMaterial color="#1a1d22" roughness={0.6} metalness={0.4} />
      </mesh>
      {/* Perforation grid — center hole + 6 around */}
      <mesh position={[0, 0, 0.003]}>
        <cylinderGeometry args={[0.001, 0.001, 0.001, 12]} />
        <meshStandardMaterial color="#000" />
      </mesh>
      {Array.from({ length: 6 }).map((_, i) => {
        const a = (i / 6) * Math.PI * 2;
        return (
          <mesh key={i} position={[Math.cos(a) * 0.005, Math.sin(a) * 0.005, 0.003]}>
            <cylinderGeometry args={[0.001, 0.001, 0.001, 8]} />
            <meshStandardMaterial color="#000" />
          </mesh>
        );
      })}
      {hovered && (
        <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0.001]}>
          <ringGeometry args={[0.014, 0.017, 24]} />
          <meshStandardMaterial color="#a855f7" emissive="#a855f7" emissiveIntensity={0.8} toneMapped={false} transparent opacity={0.6} side={THREE.DoubleSide} />
        </mesh>
      )}
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// MOLLE webbing — replaced tubes with flat boxes that have webbing texture
// ═══════════════════════════════════════════════════════════════════════════

function MolleWebbing({ position, rows = 3, cols = 4, rowGap = 0.06, colGap = 0.05 }: {
  position: [number, number, number];
  rows?: number;
  cols?: number;
  rowGap?: number;
  colGap?: number;
}) {
  const normalMap = useMemo(() => getWebbingNormal(), []);
  return (
    <group position={position}>
      {Array.from({ length: rows }).map((_, r) =>
        Array.from({ length: cols }).map((_, c) => {
          const x = (c - (cols - 1) / 2) * colGap;
          const y = (r - (rows - 1) / 2) * rowGap;
          return (
            <mesh key={`${r}-${c}`} position={[x, y, 0]} castShadow>
              <boxGeometry args={[0.04, 0.012, 0.005]} />
              <meshStandardMaterial color="#15181d" roughness={0.95} metalness={0.0} normalMap={normalMap} normalScale={new THREE.Vector2(0.5, 0.5)} />
            </mesh>
          );
        })
      )}
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// Quick-release buckle — center chest, neutral metal (no glowing button)
// ═══════════════════════════════════════════════════════════════════════════

function QuickReleaseBuckle({ position }: { position: [number, number, number] }) {
  const ringGeom = useMemo(() => new THREE.LatheGeometry(
    [
      new THREE.Vector2(0.025, -0.005),
      new THREE.Vector2(0.030, -0.005),
      new THREE.Vector2(0.030, 0.005),
      new THREE.Vector2(0.025, 0.005),
    ],
    24,
  ), []);
  return (
    <group position={position}>
      <mesh geometry={ringGeom} castShadow>
        <meshStandardMaterial color="#2a2d34" roughness={0.3} metalness={0.9} />
      </mesh>
      <mesh castShadow>
        <torusGeometry args={[0.022, 0.0035, 12, 24]} />
        <meshStandardMaterial color="#2a2d34" roughness={0.3} metalness={0.9} />
      </mesh>
      <mesh position={[0, 0, 0.006]}>
        <cylinderGeometry args={[0.012, 0.012, 0.004, 24]} />
        <meshStandardMaterial color="#1a1d22" roughness={0.55} metalness={0.5} />
      </mesh>
    </group>
  );
}


// ═══════════════════════════════════════════════════════════════════════════
// THE VEST — composed scene
// ═══════════════════════════════════════════════════════════════════════════

const SENSORS: SensorSpec[] = [
  { pos: [-0.18, 0.18, 0.21], label: "PPG · Left pectoral", temp: 36.7, kind: "ppg" },
  { pos: [0.18, 0.18, 0.21], label: "PPG · Right pectoral", temp: 36.8, kind: "ppg" },
  { pos: [0.0, 0.32, 0.20], label: "PPG · Cervical", temp: 37.0, kind: "ppg" },
  { pos: [-0.10, 0.05, 0.23], label: "ECG · Lead I", temp: 36.6, kind: "ecg" },
  { pos: [0.10, 0.05, 0.23], label: "ECG · Lead II", temp: 36.6, kind: "ecg" },
  { pos: [0.0, -0.05, 0.23], label: "ECG · Lead III", temp: 36.6, kind: "ecg" },
  { pos: [-0.16, -0.18, 0.21], label: "DS18B20 · Skin temp L", temp: 36.4, kind: "temp" },
  { pos: [0.16, -0.18, 0.21], label: "DS18B20 · Skin temp R", temp: 36.5, kind: "temp" },
  { pos: [0.0, -0.22, 0.22], label: "INMP441 · I²S mic", temp: 36.3, kind: "mic" },
];

export function VestScene({ onSensorHover }: { onSensorHover: (label: string | null, temp: number) => void }) {
  const handleHover = useCallback((s: SensorSpec | null) => {
    if (s) onSensorHover(s.label, s.temp);
    else onSensorHover(null, 0);
  }, [onSensorHover]);

  // Procedural fabric textures
  const fabricNormal = useMemo(() => getFabricNormal(), []);
  const fabricRough = useMemo(() => getFabricRoughness(), []);

  // Geometries
  const front = useMemo(() => makeTorsoPanel({ width: 0.55, height: 0.82, curveDepth: 0.16, cutNeck: true }), []);
  const back = useMemo(() => makeTorsoPanel({ width: 0.55, height: 0.82, curveDepth: 0.16, cutNeck: true }), []);
  const sidePanelGeom = useMemo(() => makeSidePanel(), []);

  // Shoulder yoke curves — used as flat ribbons
  const leftShoulderPoints: [number, number, number][] = [
    [-0.25, 0.36, 0.18],
    [-0.30, 0.43, 0.05],
    [-0.30, 0.43, -0.05],
    [-0.25, 0.36, -0.18],
  ];
  const rightShoulderPoints: [number, number, number][] = leftShoulderPoints.map(([x, y, z]) => [-x, y, z]);

  // Side waist straps
  const leftSideStrap: [number, number, number][] = [
    [-0.27, 0, 0.16],
    [-0.36, 0, 0.0],
    [-0.27, 0, -0.16],
  ];
  const rightSideStrap: [number, number, number][] = leftSideStrap.map(([x, y, z]) => [-x, y, z]);

  // Cable runs from each non-mic sensor back to the control module
  const cableTo: [number, number, number] = [0, 0.05, 0.218];
  const cables = SENSORS.filter((s) => s.kind !== "mic").map((s) => ({
    from: s.pos,
    via: [(s.pos[0] + cableTo[0]) / 2, (s.pos[1] + cableTo[1]) / 2, 0.222] as [number, number, number],
    to: cableTo,
  }));

  return (
    <>
      {/* Lighting — softer, more neutral. Key light + cool fill + warm rim */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[3, 4, 4]} intensity={0.85} color="#fff5e6" castShadow shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[-2, 2, -3]} intensity={0.3} color="#9ec5ff" />
      <pointLight position={[0, 0.2, 1.4]} intensity={0.3} color="#cdb5ff" distance={3} decay={2} />

      <Float speed={1} rotationIntensity={0.04} floatIntensity={0.12} floatingRange={[-0.004, 0.004]}>
        <group position={[0, 0, 0]}>

          {/* ── Front torso (woven fabric) ── */}
          <mesh geometry={front.geom} castShadow receiveShadow>
            <meshStandardMaterial
              color="#1c1f25"
              roughness={0.85}
              metalness={0.05}
              normalMap={fabricNormal}
              normalScale={new THREE.Vector2(0.85, 0.85)}
              roughnessMap={fabricRough}
              side={THREE.DoubleSide}
            />
          </mesh>
          {/* Stitching around the front-panel perimeter */}
          <Stitching points={front.perimeter} dashLength={0.014} gapLength={0.008} radius={0.0014} />

          {/* ── Back torso ── */}
          <group rotation={[0, Math.PI, 0]}>
            <mesh geometry={back.geom} castShadow receiveShadow>
              <meshStandardMaterial
                color="#1c1f25"
                roughness={0.88}
                metalness={0.05}
                normalMap={fabricNormal}
                normalScale={new THREE.Vector2(0.85, 0.85)}
                roughnessMap={fabricRough}
                side={THREE.DoubleSide}
              />
            </mesh>
            <Stitching points={back.perimeter} dashLength={0.014} gapLength={0.008} radius={0.0014} />
          </group>

          {/* ── Side cummerbund panels ── */}
          {[
            { x: -0.34, rot: -0.18 },
            { x: 0.34, rot: 0.18 },
          ].map(({ x, rot }, i) => (
            <mesh key={i} geometry={sidePanelGeom} position={[x, 0, -0.06]} rotation={[0, rot, 0]} castShadow>
              <meshStandardMaterial
                color="#1a1d22"
                roughness={0.85}
                metalness={0.05}
                normalMap={fabricNormal}
                normalScale={new THREE.Vector2(0.6, 0.6)}
              />
            </mesh>
          ))}

          {/* ── Centre zipper (front) ── */}
          <Zipper position={[0, 0.0, 0.213]} length={0.55} />

          {/* ── Shoulder yokes — flat webbing ribbons ── */}
          <FlatStrap points={leftShoulderPoints} width={0.045} />
          <FlatStrap points={rightShoulderPoints} width={0.045} />

          {/* ── Side waist straps ── */}
          <FlatStrap points={leftSideStrap} width={0.032} />
          <FlatStrap points={rightSideStrap} width={0.032} />

          {/* ── Control module (centre chest) ── */}
          <ControlModule position={[0, 0.20, 0.218]} />

          {/* ── Quick-release buckle (sternum) ── */}
          <QuickReleaseBuckle position={[0, 0.05, 0.215]} />

          {/* ── MOLLE webbing — lower abdomen + back ── */}
          <MolleWebbing position={[-0.13, -0.30, 0.213]} rows={2} cols={3} rowGap={0.05} colGap={0.05} />
          <MolleWebbing position={[0.13, -0.30, 0.213]} rows={2} cols={3} rowGap={0.05} colGap={0.05} />
          <group rotation={[0, Math.PI, 0]}>
            <MolleWebbing position={[0, -0.10, 0.213]} rows={3} cols={5} rowGap={0.06} colGap={0.06} />
          </group>

          {/* ── Cable runs ── thin dark sleeves */}
          {cables.map((c, i) => {
            const points = [c.from, c.via, c.to].map(([x, y, z]) => new THREE.Vector3(x, y, z));
            const curve = new THREE.CatmullRomCurve3(points);
            const geom = new THREE.TubeGeometry(curve, 32, 0.0028, 8, false);
            return (
              <mesh key={i} geometry={geom}>
                <meshStandardMaterial color="#0a0c10" roughness={0.7} metalness={0.1} />
              </mesh>
            );
          })}

          {/* ── Sensors ── */}
          {SENSORS.map((s, i) => {
            switch (s.kind) {
              case "ecg": return <ECGElectrode key={i} spec={s} onHover={handleHover} />;
              case "ppg": return <PPGSensor key={i} spec={s} onHover={handleHover} />;
              case "temp": return <TempSensor key={i} spec={s} onHover={handleHover} />;
              case "mic": return <MicSensor key={i} spec={s} onHover={handleHover} />;
            }
          })}

          {/* ── Subtle reflective trim along the shoulder seam ── */}
          {[-1, 1].map((side) => (
            <mesh key={side} position={[side * 0.20, 0.30, 0.205]} rotation={[0, 0, side * 0.4]}>
              <boxGeometry args={[0.16, 0.004, 0.001]} />
              <meshStandardMaterial color="#3d3f45" roughness={0.4} metalness={0.6} />
            </mesh>
          ))}

        </group>
      </Float>

      {/* Soft contact shadow on the ground */}
      <ContactShadows position={[0, -0.45, 0]} opacity={0.5} scale={3} blur={2.5} far={1.2} resolution={512} color="#000000" />
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
          <Environment preset="studio" />
        </Canvas>
      </Suspense>
    </div>
  );
}
