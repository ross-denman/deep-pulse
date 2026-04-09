import React, { useState, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import DistortionMaterial from './components/shaders/DistortionMaterial';
import InstitutionalAnchor from './components/InstitutionalAnchor';
import { useSocket, useChronicle } from './hooks/useNexus';

const RegionalFloor = ({ intensity, spikes, calms }) => {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1, 0]}>
      <planeGeometry args={[20, 20, 128, 128]} />
      <distortionMaterial 
        key={DistortionMaterial.key}
        uIntensity={intensity}
        uSpikes={spikes}
        uCalms={calms}
      />
    </mesh>
  );
};

function App() {
  const [shadowMode, setShadowMode] = useState(false);
  const [timeScrub, setTimeScrub] = useState(100);
  
  const { lastSpike } = useSocket('http://localhost:4110');
  const { entries, loading } = useChronicle('http://localhost:4110');

  // Map entries to anchors
  const anchors = useMemo(() => {
    return entries
      .filter(e => e.data?.type === 'TruthPulse' || e.data?.type === 'Identity')
      .map((e, i) => ({
        id: e.id,
        name: e.data.name || e.id.substring(0, 8),
        position: [Math.sin(i * 1.5) * 6, 0, Math.cos(i * 1.5) * 6],
        isVetted: e.metadata?.status === 'verified' || e.metadata?.is_notary_vetted
      }));
  }, [entries]);

  // Calming Fields (Institutional Stability)
  const calms = useMemo(() => {
    const list = new Array(10).fill(new THREE.Vector4(0, 0, 0, 0));
    anchors.filter(a => a.isVetted).slice(0, 10).forEach((anchor, i) => {
        list[i] = new THREE.Vector4(anchor.position[0], anchor.position[2], 3.0, 1.0);
    });
    return list;
  }, [anchors]);

  // Map spikes from socket/historical data
  const spikes = useMemo(() => {
    const list = new Array(10).fill(new THREE.Vector4(0, 0, 0, 0));
    // Simulate historical rewind by reducing spike intensity based on scrub
    const intensity = timeScrub / 100;
    
    if (lastSpike) {
       list[0] = new THREE.Vector4(lastSpike.x || 0, lastSpike.y || 0, 2.0, intensity);
    }
    return list;
  }, [lastSpike, timeScrub]);

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#020205', position: 'relative' }}>
      {/* OSINT Hud */}
      <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 10, color: '#4FD1C5', fontFamily: 'monospace' }}>
        <h1 style={{ margin: 0 }}>REGIONAL HEALTH MONITOR // NEXUS-01</h1>
        <p>STATUS: {loading ? 'SYNCING CHRONICLE...' : 'LEDGER_ACTIVE'}</p>
        
        <div style={{ marginTop: 20, display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button 
            onClick={() => setShadowMode(!shadowMode)}
            style={{ padding: '10px', background: shadowMode ? '#FFD700' : '#1A202C', border: '1px solid #4FD1C5', color: shadowMode ? 'black' : 'white', cursor: 'pointer' }}
          >
            SHADOW MODE: {shadowMode ? 'ON' : 'OFF'}
          </button>
        </div>

        <div style={{ marginTop: 20 }}>
          <label>FORENSIC REWIND (24H)</label><br/>
          <input 
            type="range" min="0" max="100" value={timeScrub} 
            onChange={(e) => setTimeScrub(e.target.value)} 
            style={{ width: '200px' }}
          />
        </div>
      </div>

      <Canvas shadows>
        <PerspectiveCamera makeDefault position={[10, 10, 10]} />
        <OrbitControls />
        
        <ambientLight intensity={0.2} />
        <pointLight position={[10, 10, 10]} intensity={1.5} color="#4FD1C5" />

        {/* The Distorted Information Grid */}
        <RegionalFloor intensity={shadowMode ? 0.02 : 1.0} spikes={spikes} />

        {/* Institutional Anchors */}
        {anchors.map(anchor => (
          <InstitutionalAnchor 
            key={anchor.id}
            position={anchor.position}
            name={anchor.name}
            isVetted={anchor.isVetted}
          />
        ))}

        {/* Global Desaturation for Shadow Mode */}
        {shadowMode && <color attach="background" args={['#050510']} />}
      </Canvas>

      {/* Conflict Stream Overlay */}
      <div style={{ position: 'absolute', bottom: 20, right: 20, width: '300px', height: '200px', background: 'rgba(0,0,0,0.8)', border: '1px solid #FF3E3E', color: '#FF3E3E', padding: '10px', overflowY: 'hidden', pointerEvents: 'none' }}>
        <small>CONFLICT_STREAM_ACTIVE</small>
        {entries.filter(e => e.data?.type === 'ConflictEvent').slice(-5).map(e => (
          <div key={e.id} style={{ fontSize: '10px', marginTop: '5px' }}>
            {new Date(e.metadata.timestamp).toLocaleTimeString()} - CID: {e.id.substring(0,12)} [VOLATILITY CLASH]
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
