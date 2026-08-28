"use client";

import React, { useRef } from "react";
import { motion, useInView } from "framer-motion";

interface ScrollRevealProps {
  children: React.ReactNode;
  direction?: "up" | "down" | "left" | "right" | "none";
  delay?: number;
  duration?: number;
  distance?: number;
  className?: string;
}

export default function ScrollReveal({
  children,
  direction = "up",
  delay = 0,
  duration = 0.6,
  distance = 30,
  className = ""
}: ScrollRevealProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-10% 0px" });

  const getDirectionVariants = () => {
    switch (direction) {
      case "up":
        return { hidden: { y: distance, opacity: 0 }, visible: { y: 0, opacity: 1 } };
      case "down":
        return { hidden: { y: -distance, opacity: 0 }, visible: { y: 0, opacity: 1 } };
      case "left":
        return { hidden: { x: distance, opacity: 0 }, visible: { x: 0, opacity: 1 } };
      case "right":
        return { hidden: { x: -distance, opacity: 0 }, visible: { x: 0, opacity: 1 } };
      default:
        return { hidden: { opacity: 0 }, visible: { opacity: 1 } };
    }
  };

  return (
    <motion.div
      ref={ref}
      variants={getDirectionVariants()}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{
        duration: duration,
        delay: delay,
        ease: [0.16, 1, 0.3, 1] // sleek custom cubic-bezier ease
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
