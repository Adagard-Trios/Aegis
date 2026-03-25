"use client";
import { VestModel3D } from '../components/VestModel3D';

export default function VestViewerPage() {
  return (
    <div style={{ width: '100vw', height: '100vh', background: 'transparent', margin: 0, padding: 0 }}>
      <VestModel3D />
    </div>
  );
}
