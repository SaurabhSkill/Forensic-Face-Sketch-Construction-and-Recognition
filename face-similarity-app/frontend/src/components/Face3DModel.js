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

    let renderer, controls, animationFrameId;
    let cleanupComplete = false;

    const initScene = async () => {
      try {
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
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
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
        controls = new OrbitControls(camera, renderer.domElement);
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

        // Load 3D model with timeout
        const loadModelWithTimeout = () => {
          return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
              reject(new Error('Model loading timed out'));
            }, 30000); // 30 second timeout (increased from 10)

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
                    clearTimeout(timeout);
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
                    resolve();
                  },
                  (xhr) => {
                    // Progress callback (silent)
                  },
                  (error) => {
                    clearTimeout(timeout);
                    reject(error);
                  }
                );
              },
              undefined,
              (error) => {
                clearTimeout(timeout);
                reject(error);
              }
            );
          });
        };

        // Try to load model, but continue animation even if it fails
        try {
          await loadModelWithTimeout();
          setLoading(false);
        } catch (error) {
          // Silently handle model loading failure - animation will continue
          console.info('3D model not loaded, using animation only');
          setError(null); // Don't show error to user
          setLoading(false);
        }

        // Animation loop
        let scanDirection = 1;
        
        const animate = () => {
          if (cleanupComplete) return;
          animationFrameId = requestAnimationFrame(animate);

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
          if (!mountRef.current || cleanupComplete) return;
          
          const width = mountRef.current.clientWidth;
          const height = mountRef.current.clientHeight;

          camera.aspect = width / height;
          camera.updateProjectionMatrix();
          renderer.setSize(width, height);
        };

        window.addEventListener('resize', handleResize);

        // Cleanup function
        return () => {
          cleanupComplete = true;
          window.removeEventListener('resize', handleResize);
          
          // Stop animation loop
          if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
          }
          
          // Dispose of Three.js resources
          scene.traverse((object) => {
            if (object.geometry) {
              object.geometry.dispose();
            }
            if (object.material) {
              if (Array.isArray(object.material)) {
                object.material.forEach(material => material.dispose());
              } else {
                object.material.dispose();
              }
            }
          });
          
          // Dispose renderer and controls
          if (renderer) {
            renderer.dispose();
            
            // Force WebGL context loss to free resources
            const gl = renderer.getContext();
            if (gl && gl.getExtension('WEBGL_lose_context')) {
              gl.getExtension('WEBGL_lose_context').loseContext();
            }
          }
          
          if (controls) {
            controls.dispose();
          }
          
          // Remove DOM element
          if (mountRef.current && renderer && renderer.domElement) {
            mountRef.current.removeChild(renderer.domElement);
          }
        };
      } catch (error) {
        console.error('Error initializing 3D scene:', error);
        setError('Failed to initialize 3D visualization');
        setLoading(false);
        return () => {};
      }
    };

    const cleanup = initScene();
    
    return () => {
      cleanup.then(cleanupFn => {
        if (cleanupFn) cleanupFn();
      });
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
