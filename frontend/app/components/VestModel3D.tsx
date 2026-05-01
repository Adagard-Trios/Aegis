"use client";

import { useRef, useMemo, useState, useCallback, Suspense } from "react";
import { Canvas, useFrame, extend } from "@react-three/fiber";
import { OrbitControls, Float, MeshTransmissionMaterial } from "@react-three/drei";
import * as THREE from "three";

/* ═══════════════════════════════════════════════════
   SENSOR DATA — thermal zones
   ═══════════════════════════════════════════════════ */

const SENSOR_ZONES = [
  { id: "chest-center", label: "Chest Core", pos: [0, 0.05, 0.19] as [number, number, number], temp: 37.1 },
  { id: "chest-left", label: "Left Pectoral", pos: [-0.13, 0.12, 0.18] as [number, number, number], temp: 36.8 },
  { id: "chest-right", label: "Right Pectoral", pos: [0.13, 0.12, 0.18] as [number, number, number], temp: 36.9 },
  { id: "abdomen-left", label: "Left Abdomen", pos: [-0.11, -0.15, 0.17] as [number, number, number], temp: 37.4 },
  { id: "abdomen-right", label: "Right Abdomen", pos: [0.11, -0.15, 0.17] as [number, number, number], temp: 36.7 },
  { id: "upper-back", label: "Upper Spine", pos: [0, 0.2, -0.18] as [number, number, number], temp: 36.5 },
  { id: "lower-back", label: "Lower Back", pos: [0, -0.1, -0.19] as [number, number, number], temp: 37.6 },
  { id: "shoulder-left", label: "Left Shoulder", pos: [-0.22, 0.38, 0] as [number, number, number], temp: 35.9 },
  { id: "shoulder-right", label: "Right Shoulder", pos: [0.22, 0.38, 0] as [number, number, number], temp: 36.0 },
  { id: "left-rib", label: "Left Rib Cage", pos: [-0.23, 0.0, 0.05] as [number, number, number], temp: 36.6 },
  { id: "right-rib", label: "Right Rib Cage", pos: [0.23, 0.0, 0.05] as [number, number, number], temp: 36.5 },
];

function tempToColor(temp: number): THREE.Color {
  const t = Math.max(0, Math.min(1, (temp - 35.0) / 3.5));
  if (t < 0.33) return new THREE.Color().lerpColors(new THREE.Color(0x0066ff), new THREE.Color(0x00ffaa), t / 0.33);
  if (t < 0.66) return new THREE.Color().lerpColors(new THREE.Color(0x00ffaa), new THREE.Color(0xffbb00), (t - 0.33) / 0.33);
  return new THREE.Color().lerpColors(new THREE.Color(0xffbb00), new THREE.Color(0xff2200), (t - 0.66) / 0.34);
}

/* ═══════════════════════════════════════════════════
   FUTURISTIC SENSOR NODE — multi-ring holographic
   ═══════════════════════════════════════════════════ */

function SensorNode({
  pos, temp, label, onHover,
}: {
  pos: [number, number, number]; temp: number; label: string;
  onHover: (label: string | null, temp: number) => void;
}) {
  const outerRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);
  const pulseRef = useRef<THREE.Mesh>(null);
  const color = useMemo(() => tempToColor(temp), [temp]);
  const [hovered, setHovered] = useState(false);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    if (outerRef.current) outerRef.current.rotation.z = t * 0.8;
    if (innerRef.current) innerRef.current.rotation.z = -t * 1.2;
    if (pulseRef.current) {
      const s = 1 + Math.sin(t * 3) * 0.3;
      pulseRef.current.scale.setScalar(s);
      (pulseRef.current.material as THREE.MeshBasicMaterial).opacity = 0.12 - Math.sin(t * 3) * 0.06;
    }
  });

  return (
    <group position={pos}>
      {/* Expanding pulse sphere */}
      <mesh ref={pulseRef}>
        <sphereGeometry args={[0.05, 16, 16]} />
        <meshBasicMaterial color={color} transparent opacity={0.08} depthWrite={false} />
      </mesh>
      {/* Outer ring */}
      <mesh ref={outerRef}>
        <torusGeometry args={[0.035, 0.0015, 6, 24]} />
        <meshBasicMaterial color={color} transparent opacity={hovered ? 0.9 : 0.35} />
      </mesh>
      {/* Inner ring — counter-rotating */}
      <mesh ref={innerRef}>
        <torusGeometry args={[0.022, 0.001, 6, 16]} />
        <meshBasicMaterial color={color} transparent opacity={hovered ? 0.7 : 0.2} />
      </mesh>
      {/* Core sphere — glowing */}
      <mesh
        onPointerOver={() => { setHovered(true); onHover(label, temp); document.body.style.cursor = "pointer"; }}
        onPointerOut={() => { setHovered(false); onHover(null, 0); document.body.style.cursor = "auto"; }}
      >
        <sphereGeometry args={[hovered ? 0.018 : 0.012, 16, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={hovered ? 5 : 2.5} toneMapped={false} />
      </mesh>
    </group>
  );
}

/* ═══════════════════════════════════════════════════
   ANIMATED DATA FLOW — light pulses along circuits
   ═══════════════════════════════════════════════════ */

function DataFlowLine({ points, speed = 1, color = "#00d4ff" }: {
  points: THREE.Vector3[]; speed?: number; color?: string;
}) {
  const dotRef = useRef<THREE.Mesh>(null);
  const trailRef = useRef<THREE.Mesh>(null);
  const curve = useMemo(() => new THREE.CatmullRomCurve3(points), [points]);

  useFrame(({ clock }) => {
    const t = ((clock.elapsedTime * speed * 0.15) % 1);
    const pos = curve.getPoint(t);
    if (dotRef.current) {
      dotRef.current.position.copy(pos);
    }
    if (trailRef.current) {
      const tBack = ((t - 0.03) + 1) % 1;
      trailRef.current.position.copy(curve.getPoint(tBack));
    }
  });

  const lineGeo = useMemo(() => {
    const pts = curve.getPoints(60);
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, [curve]);

  return (
    <group>
      <line geometry={lineGeo}>
        <lineBasicMaterial color={color} transparent opacity={0.08} />
      </line>
      <mesh ref={dotRef}>
        <sphereGeometry args={[0.006, 8, 8]} />
        <meshBasicMaterial color={color} transparent opacity={0.9} toneMapped={false} />
      </mesh>
      <mesh ref={trailRef}>
        <sphereGeometry args={[0.004, 6, 6]} />
        <meshBasicMaterial color={color} transparent opacity={0.4} />
      </mesh>
    </group>
  );
}

/* ═══════════════════════════════════════════════════
   FLOATING PARTICLES — ambient tech atmosphere
   ═══════════════════════════════════════════════════ */

function FloatingParticles({ count = 80 }: { count?: number }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const speeds = useMemo(() => Array.from({ length: count }, () => ({
    x: (Math.random() - 0.5) * 0.8,
    y: (Math.random() - 0.5) * 1.2,
    z: (Math.random() - 0.5) * 0.8,
    speed: 0.1 + Math.random() * 0.3,
    phase: Math.random() * Math.PI * 2,
  })), [count]);

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    speeds.forEach((s, i) => {
      const t = clock.elapsedTime * s.speed + s.phase;
      dummy.position.set(
        s.x + Math.sin(t * 0.7) * 0.15,
        s.y + Math.sin(t * 0.5) * 0.2,
        s.z + Math.cos(t * 0.4) * 0.15,
      );
      const scale = 0.002 + Math.sin(t * 2) * 0.001;
      dummy.scale.setScalar(scale);
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
      <sphereGeometry args={[1, 4, 4]} />
      <meshBasicMaterial color="#00d4ff" transparent opacity={0.4} toneMapped={false} />
    </instancedMesh>
  );
}

/* ═══════════════════════════════════════════════════
   SCANNING LINE — sweeping holographic scan
   ═══════════════════════════════════════════════════ */

function ScanLine() {
  const ref = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (ref.current) {
      const t = clock.elapsedTime;
      // Sweeps up and down over 4 seconds
      const y = Math.sin(t * 0.8) * 0.45;
      ref.current.position.y = y;
      (ref.current.material as THREE.MeshBasicMaterial).opacity = 0.04 + Math.abs(Math.cos(t * 0.8)) * 0.04;
    }
  });

  return (
    <mesh ref={ref} position={[0, 0, 0.01]}>
      <planeGeometry args={[0.6, 0.008]} />
      <meshBasicMaterial color="#00d4ff" transparent opacity={0.06} side={THREE.DoubleSide} depthWrite={false} />
    </mesh>
  );
}

/* ═══════════════════════════════════════════════════
   VEST TORSO SHAPE BUILDER
   ═══════════════════════════════════════════════════ */

function createTorsoShape(wTop: number, wBot: number, h: number, waistNarrow: number): THREE.Shape {
  const shape = new THREE.Shape();
  const ht = h / 2, wt = wTop / 2, wb = wBot / 2;
  const wm = (wt + wb) / 2 - waistNarrow;

  shape.moveTo(-wb, -ht);
  shape.lineTo(wb, -ht);
  shape.bezierCurveTo(wb + 0.01, -ht * 0.3, wm + 0.01, -ht * 0.1, wm, 0);
  shape.bezierCurveTo(wm + 0.01, ht * 0.2, wt - 0.01, ht * 0.6, wt, ht);
  shape.bezierCurveTo(wt * 0.7, ht + 0.02, wt * 0.3, ht + 0.03, 0, ht + 0.01);
  shape.bezierCurveTo(-wt * 0.3, ht + 0.03, -wt * 0.7, ht + 0.02, -wt, ht);
  shape.bezierCurveTo(-wt + 0.01, ht * 0.6, -wm - 0.01, ht * 0.2, -wm, 0);
  shape.bezierCurveTo(-wm - 0.01, -ht * 0.1, -wb - 0.01, -ht * 0.3, -wb, -ht);

  return shape;
}

/* ═══ Front panel — curved, multi-layered ═══ */

function FrontPanel() {
  const geo = useMemo(() => {
    const shape = createTorsoShape(0.36, 0.32, 0.72, 0.02);
    const g = new THREE.ExtrudeGeometry(shape, {
      depth: 0.028,
      bevelEnabled: true,
      bevelThickness: 0.006,
      bevelSize: 0.006,
      bevelSegments: 3,
      curveSegments: 32,
    });
    const posAttr = g.getAttribute("position");
    for (let i = 0; i < posAttr.count; i++) {
      const x = posAttr.getX(i);
      const z = posAttr.getZ(i);
      posAttr.setZ(i, z + 0.09 * (1 - (x * x) / 0.04));
    }
    posAttr.needsUpdate = true;
    g.computeVertexNormals();
    return g;
  }, []);

  return (
    <group>
      {/* Main panel */}
      <mesh geometry={geo} position={[0, 0, 0.08]}>
        <meshPhysicalMaterial
          color="#0c1628"
          metalness={0.3}
          roughness={0.6}
          clearcoat={0.4}
          clearcoatRoughness={0.3}
          envMapIntensity={0.5}
          side={THREE.DoubleSide}
        />
      </mesh>
      {/* Outer shell — slight transparency for layered look */}
      <mesh geometry={geo} position={[0, 0, 0.083]} scale={[1.01, 1.01, 0.3]}>
        <meshPhysicalMaterial
          color="#1a2a45"
          metalness={0.2}
          roughness={0.4}
          transparent
          opacity={0.35}
          clearcoat={0.8}
          clearcoatRoughness={0.1}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
}

/* ═══ Back panel ═══ */

function BackPanel() {
  const geo = useMemo(() => {
    const shape = createTorsoShape(0.34, 0.30, 0.74, 0.015);
    const g = new THREE.ExtrudeGeometry(shape, {
      depth: 0.024,
      bevelEnabled: true,
      bevelThickness: 0.005,
      bevelSize: 0.005,
      bevelSegments: 3,
      curveSegments: 32,
    });
    const posAttr = g.getAttribute("position");
    for (let i = 0; i < posAttr.count; i++) {
      const x = posAttr.getX(i);
      const z = posAttr.getZ(i);
      posAttr.setZ(i, z - 0.07 * (1 - (x * x) / 0.035));
    }
    posAttr.needsUpdate = true;
    g.computeVertexNormals();
    return g;
  }, []);

  return (
    <mesh geometry={geo} position={[0, 0, -0.13]} rotation={[0, Math.PI, 0]}>
      <meshPhysicalMaterial
        color="#0a1220"
        metalness={0.25}
        roughness={0.65}
        clearcoat={0.3}
        clearcoatRoughness={0.4}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

/* ═══ Side panels ═══ */

function SidePanel({ side }: { side: "left" | "right" }) {
  const xSign = side === "left" ? -1 : 1;
  const geo = useMemo(() => {
    const shape = new THREE.Shape();
    shape.moveTo(0, -0.36);
    shape.lineTo(0.13, -0.36);
    shape.bezierCurveTo(0.15, -0.1, 0.14, 0.1, 0.13, 0.36);
    shape.lineTo(0, 0.36);
    shape.bezierCurveTo(0.01, 0.1, 0.01, -0.1, 0, -0.36);
    return new THREE.ExtrudeGeometry(shape, { depth: 0.018, bevelEnabled: false, curveSegments: 20 });
  }, []);

  return (
    <mesh geometry={geo} position={[xSign * 0.16, 0, -0.08]} rotation={[0, (Math.PI / 2) * xSign, 0]}>
      <meshPhysicalMaterial color="#0e1828" metalness={0.25} roughness={0.7} clearcoat={0.2} side={THREE.DoubleSide} />
    </mesh>
  );
}

/* ═══ Shoulder strap — contoured CatmullRom ═══ */

function ShoulderStrap({ side }: { side: "left" | "right" }) {
  const xSign = side === "left" ? -1 : 1;
  const geo = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(xSign * 0.1, 0.37, 0.15),
      new THREE.Vector3(xSign * 0.14, 0.45, 0.1),
      new THREE.Vector3(xSign * 0.19, 0.51, 0.02),
      new THREE.Vector3(xSign * 0.17, 0.49, -0.06),
      new THREE.Vector3(xSign * 0.13, 0.39, -0.12),
    ]);
    const strapShape = new THREE.Shape();
    strapShape.moveTo(-0.032, -0.009);
    strapShape.lineTo(0.032, -0.009);
    strapShape.lineTo(0.032, 0.009);
    strapShape.lineTo(-0.032, 0.009);
    strapShape.lineTo(-0.032, -0.009);
    return new THREE.ExtrudeGeometry(strapShape, { steps: 40, extrudePath: curve });
  }, [xSign]);

  return (
    <mesh geometry={geo}>
      <meshPhysicalMaterial
        color="#141f35"
        metalness={0.35}
        roughness={0.55}
        clearcoat={0.5}
        clearcoatRoughness={0.2}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

/* ═══ Shoulder pad — ergonomic ═══ */

function StrapPad({ side }: { side: "left" | "right" }) {
  const xSign = side === "left" ? -1 : 1;
  return (
    <mesh position={[xSign * 0.18, 0.49, 0.01]} rotation={[0.1, 0, xSign * 0.15]}>
      <boxGeometry args={[0.055, 0.13, 0.1]} />
      <meshPhysicalMaterial color="#1a2840" roughness={0.85} metalness={0.08} clearcoat={0.1} />
    </mesh>
  );
}

/* ═══ MOLLE webbing ═══ */

function MolleStrip({ position, width, height, rotY = 0 }: {
  position: [number, number, number]; width: number; height: number; rotY?: number;
}) {
  const rows = Math.floor(height / 0.04);
  return (
    <group position={position} rotation={[0, rotY, 0]}>
      {Array.from({ length: rows }, (_, i) => (
        <group key={i}>
          <mesh position={[0, i * 0.04 - height / 2, 0]}>
            <boxGeometry args={[width, 0.014, 0.005]} />
            <meshPhysicalMaterial color="#182a42" metalness={0.2} roughness={0.75} clearcoat={0.3} />
          </mesh>
          {Array.from({ length: Math.floor(width / 0.035) }, (_, j) => (
            <mesh key={j} position={[j * 0.035 - width / 2 + 0.018, i * 0.04 - height / 2, 0.003]}>
              <boxGeometry args={[0.018, 0.005, 0.003]} />
              <meshStandardMaterial color="#0a1220" roughness={0.95} />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
}

/* ═══ Glowing edge trim ═══ */

function EdgeTrimLine({ points, color = "#00d4ff", intensity = 0.5 }: {
  points: [number, number, number][]; color?: string; intensity?: number;
}) {
  const geo = useMemo(() => {
    return new THREE.BufferGeometry().setFromPoints(points.map(p => new THREE.Vector3(...p)));
  }, [points]);

  return (
    <line geometry={geo}>
      <lineBasicMaterial color={color} transparent opacity={intensity} />
    </line>
  );
}

/* ═══════════════════════════════════════════════════
   FULL VEST ASSEMBLY
   ═══════════════════════════════════════════════════ */

function FuturisticVest() {
  const groupRef = useRef<THREE.Group>(null);
  const cyan = "#00d4ff";
  const teal = "#00ffaa";

  useFrame(({ clock }) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(clock.elapsedTime * 0.12) * 0.015;
    }
  });

  return (
    <group ref={groupRef}>
      {/* === Structural panels === */}
      <FrontPanel />
      <BackPanel />
      <SidePanel side="left" />
      <SidePanel side="right" />

      {/* === Shoulder straps === */}
      <ShoulderStrap side="left" />
      <ShoulderStrap side="right" />
      <StrapPad side="left" />
      <StrapPad side="right" />

      {/* === Neckline ring === */}
      <mesh position={[0, 0.39, 0]} rotation={[0.15, 0, 0]}>
        <torusGeometry args={[0.13, 0.012, 8, 24, Math.PI * 2]} />
        <meshPhysicalMaterial color="#0a1420" metalness={0.3} roughness={0.7} clearcoat={0.2} />
      </mesh>

      {/* === MOLLE === */}
      <MolleStrip position={[0, -0.05, 0.2]} width={0.22} height={0.3} />
      <MolleStrip position={[0, -0.05, -0.2]} width={0.22} height={0.3} rotY={Math.PI} />

      {/* === Glowing circuit traces — FRONT === */}
      {[0.24, 0.12, 0.0, -0.1, -0.2].map((y, i) => (
        <mesh key={`fh-${i}`} position={[0, y, 0.205]}>
          <boxGeometry args={[0.2 - i * 0.008, 0.0015, 0.001]} />
          <meshBasicMaterial color={cyan} transparent opacity={0.5} toneMapped={false} />
        </mesh>
      ))}
      {[-0.08, -0.03, 0.03, 0.08].map((x, i) => (
        <mesh key={`fv-${i}`} position={[x, 0.02, 0.205]}>
          <boxGeometry args={[0.001, 0.42, 0.001]} />
          <meshBasicMaterial color={cyan} transparent opacity={0.35} toneMapped={false} />
        </mesh>
      ))}

      {/* === Glowing circuit traces — BACK === */}
      {[0.2, 0.08, -0.04, -0.16].map((y, i) => (
        <mesh key={`bh-${i}`} position={[0, y, -0.205]}>
          <boxGeometry args={[0.18 - i * 0.01, 0.0015, 0.001]} />
          <meshBasicMaterial color={teal} transparent opacity={0.3} toneMapped={false} />
        </mesh>
      ))}

      {/* === Animated data flow lines === */}
      <DataFlowLine
        points={[
          new THREE.Vector3(-0.08, -0.25, 0.206),
          new THREE.Vector3(-0.08, 0.0, 0.206),
          new THREE.Vector3(-0.05, 0.15, 0.206),
          new THREE.Vector3(0, 0.25, 0.206),
        ]}
        speed={1.2}
        color={cyan}
      />
      <DataFlowLine
        points={[
          new THREE.Vector3(0.08, -0.25, 0.206),
          new THREE.Vector3(0.08, 0.0, 0.206),
          new THREE.Vector3(0.05, 0.15, 0.206),
          new THREE.Vector3(0, 0.25, 0.206),
        ]}
        speed={0.9}
        color={teal}
      />
      <DataFlowLine
        points={[
          new THREE.Vector3(0, -0.2, -0.206),
          new THREE.Vector3(0, 0.05, -0.206),
          new THREE.Vector3(0, 0.2, -0.206),
        ]}
        speed={0.7}
        color={teal}
      />

      {/* === Sensor pocket hexagons on front === */}
      {([[-0.07, 0.1], [0.07, 0.1], [0, -0.05], [-0.07, -0.18], [0.07, -0.18]] as [number, number][]).map(([x, y], i) => (
        <mesh key={`hex-${i}`} position={[x, y, 0.206]}>
          <circleGeometry args={[0.02, 6]} />
          <meshBasicMaterial color={cyan} transparent opacity={0.12} toneMapped={false} side={THREE.DoubleSide} />
        </mesh>
      ))}

      {/* === MedVerse emblem — glowing hexagon === */}
      <mesh position={[0, 0.29, 0.208]}>
        <circleGeometry args={[0.022, 6]} />
        <meshBasicMaterial color="#ffffff" toneMapped={false} />
      </mesh>
      <mesh position={[0, 0.29, 0.207]}>
        <circleGeometry args={[0.028, 6]} />
        <meshBasicMaterial color={cyan} transparent opacity={0.4} toneMapped={false} />
      </mesh>
      <mesh position={[0, 0.29, 0.206]}>
        <circleGeometry args={[0.035, 6]} />
        <meshBasicMaterial color={cyan} transparent opacity={0.15} toneMapped={false} side={THREE.DoubleSide} />
      </mesh>

      {/* === Scanning line === */}
      <ScanLine />

      {/* === Edge trim glow lines (outline effect) === */}
      <EdgeTrimLine
        points={[[-0.18, -0.36, 0.17], [-0.16, 0.0, 0.2], [-0.14, 0.26, 0.19], [-0.1, 0.37, 0.15]]}
        intensity={0.2}
      />
      <EdgeTrimLine
        points={[[0.18, -0.36, 0.17], [0.16, 0.0, 0.2], [0.14, 0.26, 0.19], [0.1, 0.37, 0.15]]}
        intensity={0.2}
      />

      {/* === Waistband — tactical cummerbund === */}
      <mesh position={[0, -0.36, 0]}>
        <boxGeometry args={[0.38, 0.065, 0.34]} />
        <meshPhysicalMaterial color="#060c18" metalness={0.45} roughness={0.4} clearcoat={0.6} clearcoatRoughness={0.15} />
      </mesh>
      {/* Waistband glow trim */}
      <mesh position={[0, -0.33, 0]}>
        <boxGeometry args={[0.385, 0.003, 0.345]} />
        <meshBasicMaterial color={cyan} transparent opacity={0.15} toneMapped={false} />
      </mesh>

      {/* === Metal QD buckles === */}
      {[-0.2, 0.2].map((x, i) => (
        <group key={`qd-${i}`} position={[x, -0.08, 0.18]}>
          <mesh>
            <boxGeometry args={[0.03, 0.045, 0.016]} />
            <meshPhysicalMaterial color="#8899bb" metalness={0.95} roughness={0.03} clearcoat={1} />
          </mesh>
          <mesh position={[0, 0, 0.009]}>
            <boxGeometry args={[0.016, 0.025, 0.003]} />
            <meshPhysicalMaterial color="#667799" metalness={0.9} roughness={0.08} clearcoat={1} />
          </mesh>
        </group>
      ))}

      {/* === D-rings on shoulders === */}
      {[[-0.2, 0.47, 0.06], [0.2, 0.47, 0.06]].map(([x, y, z], i) => (
        <mesh key={`dr-${i}`} position={[x, y, z]}>
          <torusGeometry args={[0.012, 0.003, 6, 12]} />
          <meshPhysicalMaterial color="#8899bb" metalness={0.95} roughness={0.03} clearcoat={1} />
        </mesh>
      ))}

      {/* === Side adjustment straps with glow === */}
      {([-1, 1] as const).map((xSign) => (
        <group key={`adj-${xSign}`}>
          <mesh position={[xSign * 0.24, -0.08, 0]}>
            <boxGeometry args={[0.02, 0.22, 0.008]} />
            <meshPhysicalMaterial color="#121e32" metalness={0.15} roughness={0.8} clearcoat={0.2} />
          </mesh>
          <mesh position={[xSign * 0.24, 0.02, 0]}>
            <boxGeometry args={[0.028, 0.012, 0.015]} />
            <meshPhysicalMaterial color="#8899bb" metalness={0.9} roughness={0.08} clearcoat={1} />
          </mesh>
          {/* Side glow accent */}
          <mesh position={[xSign * 0.245, -0.08, 0]}>
            <boxGeometry args={[0.001, 0.2, 0.006]} />
            <meshBasicMaterial color={cyan} transparent opacity={0.12} toneMapped={false} />
          </mesh>
        </group>
      ))}

      {/* === Back spine channel === */}
      <mesh position={[0, 0.05, -0.205]}>
        <boxGeometry args={[0.018, 0.5, 0.003]} />
        <meshPhysicalMaterial color="#0a1018" roughness={0.85} metalness={0.1} />
      </mesh>

      {/* === Velcro name tape areas === */}
      {([[0, 0.29, 0.21], [-0.15, 0.46, 0.08], [0.15, 0.46, 0.08]] as [number, number, number][]).map((pos, i) => (
        <mesh key={`vel-${i}`} position={pos}>
          <boxGeometry args={[i === 0 ? 0.12 : 0.05, i === 0 ? 0.035 : 0.03, 0.004]} />
          <meshPhysicalMaterial color="#1e2e48" roughness={0.98} metalness={0.02} />
        </mesh>
      ))}

      {/* === Front panel piping/accent lines === */}
      <mesh position={[0, 0.0, 0.21]}>
        <boxGeometry args={[0.32, 0.003, 0.001]} />
        <meshBasicMaterial color={cyan} transparent opacity={0.12} toneMapped={false} />
      </mesh>
    </group>
  );
}

/* ═══════════════════════════════════════════════════
   SCENE — dramatic lighting
   ═══════════════════════════════════════════════════ */

function VestScene({ onSensorHover }: { onSensorHover: (label: string | null, temp: number) => void }) {
  return (
    <>
      {/* Key light — warm white */}
      <directionalLight position={[3, 5, 4]} intensity={0.5} color="#f8f0e8" />
      {/* Fill — cool cyan */}
      <directionalLight position={[-3, 3, -2]} intensity={0.25} color="#00d4ff" />
      {/* Ambient — very dim */}
      <ambientLight intensity={0.2} />
      {/* Rim lights — dramatic edge glow */}
      <pointLight position={[0, 0, 2.5]} intensity={0.5} color="#00d4ff" distance={5} decay={2} />
      <pointLight position={[0, -1, -2]} intensity={0.2} color="#4400ff" distance={4} decay={2} />
      <pointLight position={[1.5, 1.5, 0]} intensity={0.15} color="#00ff88" distance={3.5} decay={2} />
      {/* Under-light — subtle purple */}
      <pointLight position={[0, -1.5, 0.5]} intensity={0.08} color="#6622cc" distance={3} decay={2} />

      <Float speed={0.8} rotationIntensity={0.01} floatIntensity={0.03}>
        <FuturisticVest />
        {SENSOR_ZONES.map((zone) => (
          <SensorNode key={zone.id} pos={zone.pos} temp={zone.temp} label={zone.label} onHover={onSensorHover} />
        ))}
      </Float>

      <FloatingParticles count={60} />

      <OrbitControls
        enablePan={false}
        enableZoom={true}
        minDistance={1.2}
        maxDistance={3.5}
        minPolarAngle={Math.PI / 6}
        maxPolarAngle={Math.PI / 1.35}
        autoRotate
        autoRotateSpeed={0.9}
      />
    </>
  );
}

/* ═══ Loading ═══ */

function LoadingFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center z-10">
      <div className="flex flex-col items-center gap-3">
        <div className="w-12 h-12 border-2 border-primary/15 border-t-primary rounded-full animate-spin" />
        <span className="text-[10px] text-muted-foreground font-display tracking-[0.2em] uppercase">
          Initializing 3D Telemetry...
        </span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   EXPORTED COMPONENT
   ═══════════════════════════════════════════════════ */

export function VestModel3D() {
  const [hoveredSensor, setHoveredSensor] = useState<{ label: string; temp: number } | null>(null);

  const handleSensorHover = useCallback((label: string | null, temp: number) => {
    setHoveredSensor(label ? { label, temp } : null);
  }, []);

  return (
    <div className="relative w-full h-full min-h-[420px]">
      {/* Sensor tooltip */}
      {hoveredSensor && (
        <div className="absolute top-4 left-4 z-10 bg-secondary/95 backdrop-blur-md border border-primary/20 rounded-lg px-4 py-3 glow-cyan">
          <p className="text-[10px] font-semibold text-primary font-display uppercase tracking-[0.15em]">
            {hoveredSensor.label}
          </p>
          <p className="text-2xl font-bold text-foreground font-display mt-0.5">
            {hoveredSensor.temp.toFixed(1)}°C
          </p>
          <div className="flex items-center gap-2 mt-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: `#${tempToColor(hoveredSensor.temp).getHexString()}` }} />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">
              {hoveredSensor.temp > 37.3 ? "Elevated" : hoveredSensor.temp < 36.0 ? "Cool Zone" : "Normal"}
            </span>
          </div>
        </div>
      )}

      {/* Thermal scale */}
      <div className="absolute bottom-4 left-4 z-10 bg-secondary/80 backdrop-blur-md border border-border/50 rounded-lg px-3 py-2">
        <p className="text-[8px] text-primary/60 uppercase tracking-[0.2em] mb-1 font-display font-semibold">
          Thermal Gradient
        </p>
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-muted-foreground font-mono">35.0</span>
          <div className="w-20 h-2 rounded-sm" style={{ background: "linear-gradient(90deg, #0066ff, #00ffaa, #ffbb00, #ff2200)" }} />
          <span className="text-[9px] text-muted-foreground font-mono">38.5</span>
        </div>
      </div>

      {/* Controls hint */}
      <div className="absolute top-4 right-4 z-10 bg-secondary/50 backdrop-blur-md border border-border/30 rounded-lg px-3 py-1.5">
        <p className="text-[8px] text-muted-foreground/70 uppercase tracking-[0.2em] font-display">
          Drag to rotate • Scroll to zoom
        </p>
      </div>

      {/* Canvas */}
      <Suspense fallback={<LoadingFallback />}>
        <Canvas
          camera={{ position: [0, 0.12, 1.8], fov: 38 }}
          style={{ background: "transparent" }}
          gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
          dpr={[1, 2]}
        >
          <VestScene onSensorHover={handleSensorHover} />
        </Canvas>
      </Suspense>
    </div>
  );
}
