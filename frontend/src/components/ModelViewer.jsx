import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const ModelViewer = ({ segments, openings, floors, furniture, labels }) => {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const [isOpen, setIsOpen] = React.useState(true);

  useEffect(() => {
    if (!mountRef.current) return;
    
    // 1. Setup Scene, Camera, Renderer
    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    const scene = new THREE.Scene();
    sceneRef.current = scene;
    // Set background to transparent or dark grid
    scene.background = new THREE.Color(0x0a0f1c);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(15, 20, 20);
    camera.lookAt(5, 0, 5);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    // Clear mount in case of re-mounts
    while (mountRef.current.firstChild) {
      mountRef.current.removeChild(mountRef.current.firstChild);
    }
    mountRef.current.appendChild(renderer.domElement);

    // 2. Add Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(5, 0, 5);

    // 3. Add Lights (Ambient + Directional for depth)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(10, 20, 10);
    dirLight.castShadow = true;
    scene.add(dirLight);
    
    // Add cool glowing point lights to enhance aesthetics
    const pointLight = new THREE.PointLight(0x3b82f6, 1.5, 50);
    pointLight.position.set(2, 5, 2);
    scene.add(pointLight);

    // Custom Glassy Grid Helper
    const gridHelper = new THREE.GridHelper(50, 50, 0x3b82f6, 0x1e293b);
    gridHelper.position.y = -0.01;
    scene.add(gridHelper);

    // 5. Animation Loop
    let animationFrameId;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 6. Handle Resize
    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
      // Remove canvas child node if it exists
      if (mountRef.current && mountRef.current.firstChild) {
          mountRef.current.removeChild(mountRef.current.firstChild);
      }
    };
  }, []);

  useEffect(() => {
    if (!sceneRef.current || !segments) return;
    const scene = sceneRef.current;
    
    // Clear existing meshes except lights and grid
    const toRemove = [];
    scene.children.forEach(child => {
        if (child.type === 'Mesh' || child.type === 'Group') toRemove.push(child);
    });
    toRemove.forEach(child => {
        scene.remove(child);
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
            if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
            else child.material.dispose();
        }
    });

    // 1. Render Structural Wall Segments (Architectural Styling)
    const materialLoadBearing = new THREE.MeshPhysicalMaterial({ 
        color: 0xfcfcf0, metalness: 0.1, roughness: 0.2, transparent: true, opacity: 0.95, side: THREE.DoubleSide
    });
    const materialPartition = new THREE.MeshPhysicalMaterial({ 
        color: 0xf0f0e0, metalness: 0.1, roughness: 0.3, transparent: true, opacity: 0.9, side: THREE.DoubleSide
    });

    segments.forEach(seg => {
        let mat = seg.type === 'load-bearing' ? materialLoadBearing : materialPartition;
        const geometry = new THREE.BoxGeometry(seg.length, seg.height, seg.thickness);
        const mesh = new THREE.Mesh(geometry, mat);
        mesh.position.set(seg.center_x, seg.elevation, seg.center_y);
        mesh.rotation.y = -seg.rotation;
        scene.add(mesh);
    });

    // 2. Render Floors (Wood/Tile)
    if (floors) {
        floors.forEach(f => {
            const fColor = f.material_type === 'wood' ? 0xd1bfa7 : 0xe5e7eb;
            const mat = new THREE.MeshPhysicalMaterial({ color: fColor, roughness: 0.6, metalness: 0.1 });
            const geometry = new THREE.PlaneGeometry(f.width, f.length);
            const mesh = new THREE.Mesh(geometry, mat);
            mesh.rotation.x = -Math.PI / 2;
            mesh.position.set(f.center_x, 0.01, f.center_y);
            scene.add(mesh);
        });
    }

    // 3. Render Furniture Placeholders
    if (furniture) {
        furniture.forEach(f => {
            const mat = new THREE.MeshPhysicalMaterial({ color: f.color, roughness: 0.8 });
            const geometry = new THREE.BoxGeometry(f.width, f.height, f.length);
            const mesh = new THREE.Mesh(geometry, mat);
            mesh.position.set(f.x, f.y, f.z);
            scene.add(mesh);
        });
    }

    // 4. Render Openings (Glass & Door Panels)
    if (openings) {
        openings.forEach(op => {
            if (op.type === 'window') {
                const winMat = new THREE.MeshPhysicalMaterial({ color: 0x87ceeb, transparent: true, opacity: 0.3, transmission: 0.9, roughness: 0.1 });
                const geometry = new THREE.BoxGeometry(op.length, op.height, 0.05);
                const mesh = new THREE.Mesh(geometry, winMat);
                mesh.position.set(op.center_x, op.elevation, op.center_y);
                mesh.rotation.y = -op.rotation;
                scene.add(mesh);
            } else if (op.type === 'door') {
                const doorGroup = new THREE.Group();
                const doorMat = new THREE.MeshPhysicalMaterial({ color: 0x8b4513, metalness: 0.2, roughness: 0.5 });
                const geometry = new THREE.BoxGeometry(op.length, op.height, 0.04);
                const mesh = new THREE.Mesh(geometry, doorMat);
                mesh.position.x = op.length / 2;
                doorGroup.add(mesh);
                doorGroup.position.set(
                  op.center_x - (op.length / 2) * Math.cos(op.rotation),
                  op.elevation,
                  op.center_y + (op.length / 2) * Math.sin(op.rotation)
                );
                doorGroup.rotation.y = -op.rotation;
                if (isOpen) {
                  const angle = op.metadata?.swing_type === 'outswing' ? -1.5 : 1.5;
                  doorGroup.rotation.y += angle;
                }
                scene.add(doorGroup);
            }
        });
    }

    // 5. Render Floating Room Labels
    if (labels) {
        labels.forEach(l => {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.width = 256;
            canvas.height = 64;
            context.fillStyle = 'rgba(0,0,0,0)';
            context.fillRect(0, 0, 256, 64);
            context.font = 'Bold 32px Inter, Arial';
            context.textAlign = 'center';
            context.fillStyle = '#1e293b';
            context.fillText(l.text, 128, 48);
            
            const texture = new THREE.CanvasTexture(canvas);
            const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
            const sprite = new THREE.Sprite(spriteMaterial);
            sprite.scale.set(4, 1, 1);
            sprite.position.set(l.x, l.z, l.y);
            scene.add(sprite);
        });
    }

  }, [segments, openings, isOpen, floors, furniture, labels]);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        {!segments && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-400 z-10 pointer-events-none">
                <p>Awaiting Architectural Data...</p>
            </div>
        )}
        <div className="absolute bottom-4 left-4 z-20 flex gap-2">
            <button 
              onClick={() => setIsOpen(!isOpen)}
              className="bg-blue-600/80 hover:bg-blue-500 text-white text-xs px-3 py-1.5 rounded-lg backdrop-blur-md transition-colors font-bold uppercase tracking-wider shadow-lg border border-blue-400/30"
            >
              {isOpen ? 'Close Doors' : 'Open Doors'}
            </button>
        </div>
      <div ref={mountRef} style={{ width: '100%', height: '100%', borderRadius: '1.25rem', overflow: 'hidden' }} />
    </div>
  );
};

export default ModelViewer;
