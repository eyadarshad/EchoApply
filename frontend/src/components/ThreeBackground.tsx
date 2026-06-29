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

  const vertexShader = `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = vec4(position, 1.0);
    }
  `;

  const fragmentShader = `
    uniform float u_time;
    uniform vec2 u_mouse;
    uniform vec2 u_resolution;
    uniform float u_dark_mode;
    varying vec2 vUv;

    void main() {
      vec2 uv = vUv;
      
      // Transform coordinates to center (-0.5 to 0.5)
      vec2 p = uv - 0.5;
      
      // Safe gravitational distortion towards the cursor
      vec2 mouse_pos = u_mouse - 0.5;
      vec2 diff = p - mouse_pos;
      float d_mouse = length(diff);
      if (d_mouse > 0.001) {
        p += (diff / d_mouse) * (0.04 / (d_mouse + 0.15)) * 0.12;
      }
      
      // Perspective warp (grid recedes in y dimension)
      float z = 1.0 / (p.y + 1.25);
      vec2 grid_uv = vec2(p.x * z * 6.5, z * 6.5 + u_time * 0.1);
      
      // Gentle wavy grid distortion
      grid_uv.x += sin(grid_uv.y * 1.5 + u_time * 0.35) * 0.12;
      grid_uv.y += cos(grid_uv.x * 1.5 + u_time * 0.28) * 0.12;

      // Render vector grid lines
      vec2 f = abs(fract(grid_uv - 0.5) - 0.5);
      vec2 grid_lines = smoothstep(0.035 * z, 0.0, f);
      float grid_intensity = max(grid_lines.x, grid_lines.y);
      
      // Recede and fade grid into upper perspective limit
      float fade = smoothstep(-0.5, 0.2, p.y) * smoothstep(0.5, 0.2, abs(p.x));
      grid_intensity *= fade * 0.25;

      // Theme color tokens
      vec3 bg_dark = vec3(0.02, 0.03, 0.08);
      vec3 grid_dark = vec3(0.39, 0.4, 0.95);
      
      vec3 bg_light = vec3(0.97, 0.98, 1.0);
      vec3 grid_light = vec3(0.35, 0.3, 0.85);
      
      vec3 bg_color = mix(bg_light, bg_dark, u_dark_mode);
      vec3 grid_color = mix(grid_light, grid_dark, u_dark_mode);
      
      // Combine background and grid glow
      vec3 final_color = bg_color + grid_color * grid_intensity;
      
      // Mouse spotlight glow
      float glow = smoothstep(0.45, 0.0, d_mouse) * 0.05;
      final_color += grid_color * glow;

      gl_FragColor = vec4(final_color, 1.0);
    }
  `;

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms.current}
        depthWrite={false}
        depthTest={false}
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
      <Canvas camera={{ position: [0, 0, 1] }}>
        <ShaderBackground />
      </Canvas>
    </div>
  );
}
