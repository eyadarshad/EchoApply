"use client";

import React, { useRef, useEffect, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { useTheme } from "./ThemeContext";

function ShaderBackground() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const { theme } = useTheme();
  const { size } = useThree();
  const mouseRef = useRef({ x: 0.5, y: 0.5 });
  const targetMouse = useRef({ x: 0.5, y: 0.5 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      targetMouse.current = {
        x: e.clientX / window.innerWidth,
        y: 1.0 - (e.clientY / window.innerHeight),
      };
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  useFrame((state) => {
    if (materialRef.current) {
      // Smooth mouse interpolation (ease-out lerp)
      mouseRef.current.x += (targetMouse.current.x - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (targetMouse.current.y - mouseRef.current.y) * 0.05;

      materialRef.current.uniforms.u_time.value = state.clock.getElapsedTime();
      materialRef.current.uniforms.u_mouse.value.set(mouseRef.current.x, mouseRef.current.y);
      materialRef.current.uniforms.u_dark_mode.value = THREE.MathUtils.lerp(
        materialRef.current.uniforms.u_dark_mode.value,
        theme === "dark" ? 1.0 : 0.0,
        0.08
      );
    }
  });

  const uniforms = useRef({
    u_time: { value: 0 },
    u_mouse: { value: new THREE.Vector2(0.5, 0.5) },
    u_resolution: { value: new THREE.Vector2(size.width, size.height) },
    u_dark_mode: { value: theme === "dark" ? 1.0 : 0.0 },
  });

  useEffect(() => {
    uniforms.current.u_resolution.value.set(size.width, size.height);
  }, [size]);

  // Vertex Shader deforms pos.z based on distance to the cursor (weight on fabric effect)
  const vertexShader = `
    uniform float u_time;
    uniform vec2 u_mouse;
    varying vec3 v_position;
    varying vec2 vUv;

    void main() {
      vUv = uv;
      vec3 pos = position;
      
      // Map mouse (0 to 1) to local plane size bounds (-6.0 to 6.0)
      vec2 mouse_local = (u_mouse - 0.5) * 12.0;
      float dist = distance(pos.xy, mouse_local);
      
      // Fabric pinch deformation (pull down along Z axis under cursor)
      float pinch_radius = 3.5;
      float pinch_strength = 1.35;
      float factor = smoothstep(pinch_radius, 0.0, dist);
      
      // Elastic indentation
      pos.z -= factor * pinch_strength;
      
      // Gentle wavy motion across grid lines
      pos.z += sin(pos.x * 0.65 + u_time * 0.25) * cos(pos.y * 0.65 + u_time * 0.2) * 0.12;
      
      v_position = pos;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `;

  const fragmentShader = `
    varying vec3 v_position;
    varying vec2 vUv;
    uniform float u_dark_mode;

    void main() {
      // Draw grid lines based on UV coordinates
      vec2 grid = abs(fract(vUv * 28.0 - 0.5) - 0.5) / 0.035;
      float line = min(grid.x, grid.y);
      float grid_intensity = 1.0 - min(line, 1.0);
      
      // Fade grid at outer edges to blend with background
      float fade = smoothstep(0.0, 0.22, vUv.x) * smoothstep(1.0, 0.78, vUv.x) *
                   smoothstep(0.0, 0.22, vUv.y) * smoothstep(1.0, 0.78, vUv.y);
                   
      grid_intensity *= fade * 0.26;

      // Theme background and grid colors
      vec3 bg_dark = vec3(0.02, 0.03, 0.08);
      vec3 grid_dark = vec3(0.39, 0.4, 0.95);
      
      vec3 bg_light = vec3(0.97, 0.98, 1.0);
      vec3 grid_light = vec3(0.35, 0.3, 0.85);
      
      vec3 bg_color = mix(bg_light, bg_dark, u_dark_mode);
      vec3 grid_color = mix(grid_light, grid_dark, u_dark_mode);
      
      // Blend base and grid lines
      vec3 final_color = bg_color + grid_color * grid_intensity;
      
      gl_FragColor = vec4(final_color, 1.0);
    }
  `;

  return (
    <mesh rotation={[-Math.PI / 3.2, 0, 0]} position={[0, -0.8, -0.5]}>
      <planeGeometry args={[12, 12, 60, 60]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms.current}
      />
    </mesh>
  );
}

export default function ThreeBackground() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="fixed inset-0 w-full h-full -z-20 pointer-events-none">
      <Canvas camera={{ position: [0, 0, 2.8], fov: 45 }}>
        <ambientLight intensity={1.0} />
        <ShaderBackground />
      </Canvas>
    </div>
  );
}
