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
      vec2 dist_uv = uv + (u_mouse - 0.5) * 0.12;
      
      float wave1 = sin(dist_uv.x * 3.5 + u_time * 0.2) * cos(dist_uv.y * 2.5 - u_time * 0.15);
      float wave2 = cos(dist_uv.y * 4.5 + u_time * 0.25) * sin(dist_uv.x * 1.5 - u_time * 0.1);
      float combined = (wave1 + wave2) * 0.5 + 0.5;

      vec3 color1_dark = vec3(0.02, 0.03, 0.08); 
      vec3 color2_dark = vec3(0.08, 0.05, 0.18);
      vec3 color3_dark = vec3(0.03, 0.01, 0.06);

      vec3 color1_light = vec3(0.97, 0.98, 1.0);  
      vec3 color2_light = vec3(0.91, 0.90, 0.98);   
      vec3 color3_light = vec3(0.95, 0.96, 0.99);  

      vec3 final_color_dark = mix(color1_dark, mix(color2_dark, color3_dark, combined), uv.y);
      vec3 final_color_light = mix(color1_light, mix(color2_light, color3_light, combined), uv.y);

      vec3 final_color = mix(final_color_light, final_color_dark, u_dark_mode);

      float mouse_dist = distance(uv, u_mouse);
      float glow = smoothstep(0.45, 0.0, mouse_dist) * 0.06;
      final_color += vec3(glow * 0.4, glow * 0.3, glow * 0.7);

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
