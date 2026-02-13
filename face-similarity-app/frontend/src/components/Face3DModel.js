import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import './Face3DModel.css';

const Face3DModel = () => {
  const mountRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!mountRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a1628);

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      45,
      mountRef.current.clientWidth / mountRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 0, 3);

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    mountRef.current.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight1.position.set(5, 5, 5);
    scene.add(directionalLight1);

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
    directionalLight2.position.set(-5, -5, -5);
    scene.add(directionalLight2);

    // OrbitControls for interaction
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enableZoom = true;
    controls.enablePan = false;
    controls.minDistance = 1.5;
    controls.maxDistance = 5;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 1.0;

    // Scanning grid overlay
    const gridGeometry = new THREE.PlaneGeometry(4, 4, 20, 20);
    const gridMaterial = new THREE.MeshBasicMaterial({
      color: 0x00ff88,
      wireframe: true,
      transparent: true,
      opacity: 0.15,
    });
    const grid = new THREE.Mesh(gridGeometry, gridMaterial);
    grid.position.z = 0.5;
    scene.add(grid);

    // Scanning line
    const lineGeometry = new THREE.PlaneGeometry(4, 0.02);
    const lineMaterial = new THREE.MeshBasicMaterial({
      color: 0x00ff88,
      transparent: true,
      opacity: 0.8,
    });
    const scanLine = new THREE.Mesh(lineGeometry, lineMaterial);
    scanLine.position.z = 0.6;
    scene.add(scanLine);

    // Load 3D model
    const mtlLoader = new MTLLoader();
    mtlLoader.setPath('/head/');
    
    mtlLoader.load(
      'head.mtl',
      (materials) => {
        materials.preload();

        const objLoader = new OBJLoader();
        objLoader.setMaterials(materials);
        objLoader.setPath('/head/');

        objLoader.load(
          'head.OBJ',
          (object) => {
            // Center and scale the model
            const box = new THREE.Box3().setFromObject(object);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());

            const maxDim = Math.max(size.x, size.y, size.z);
            const scale = 2 / maxDim;

            object.scale.set(scale, scale, scale);
            object.position.sub(center.multiplyScalar(scale));
            object.position.y -= 0.2; // Adjust vertical position

            scene.add(object);
            setLoading(false);
          },
          undefined,
          (error) => {
            console.error('Error loading OBJ:', error);
            setError('Failed to load 3D model');
            setLoading(false);
          }
        );
      },
      undefined,
      (error) => {
        console.error('Error loading MTL:', error);
        setError('Failed to load model materials');
        setLoading(false);
      }
    );

    // Animation loop
    let scanDirection = 1;
    const animate = () => {
      requestAnimationFrame(animate);

      // Animate scanning line
      scanLine.position.y += 0.01 * scanDirection;
      if (scanLine.position.y > 2 || scanLine.position.y < -2) {
        scanDirection *= -1;
      }

      // Pulse grid opacity
      grid.material.opacity = 0.1 + Math.sin(Date.now() * 0.001) * 0.05;

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    // Handle window resize
    const handleResize = () => {
      if (!mountRef.current) return;
      
      const width = mountRef.current.clientWidth;
      const height = mountRef.current.clientHeight;

      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
      controls.dispose();
    };
  }, []);

  return (
    <div className="face-3d-container">
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Loading 3D Model...</p>
        </div>
      )}
      {error && (
        <div className="error-overlay">
          <p>⚠️ {error}</p>
        </div>
      )}
      <div ref={mountRef} className="face-3d-canvas" />
      
      {/* Forensic HUD Overlay */}
      <div className="forensic-hud">
        <div className="hud-corner tl"></div>
        <div className="hud-corner tr"></div>
        <div className="hud-corner bl"></div>
        <div className="hud-corner br"></div>
        
        <div className="hud-info top-left">
          <div className="hud-text">3D FACIAL SCAN</div>
          <div className="hud-text-small">INTERACTIVE MODEL</div>
        </div>
        
        <div className="hud-info top-right">
          <div className="hud-text">STATUS: <span className="active">ACTIVE</span></div>
          <div className="hud-text-small">ROTATE • ZOOM • SCAN</div>
        </div>
        
        <div className="hud-info bottom-left">
          <div className="hud-indicator">
            <div className="indicator-dot"></div>
            <span>BIOMETRIC SCAN</span>
          </div>
          <div className="hud-indicator">
            <div className="indicator-dot"></div>
            <span>3D MAPPING</span>
          </div>
        </div>
        
        <div className="hud-info bottom-right">
          <div className="hud-text-small">RESOLUTION: HIGH</div>
          <div className="hud-text-small">QUALITY: 100%</div>
        </div>
      </div>
    </div>
  );
};

export default Face3DModel;
