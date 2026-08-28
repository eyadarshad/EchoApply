/**
 * PretextSnakeEngine
 * Ultra-smooth 60FPS-120FPS physics coordinator for the cute text-parting snake.
 * 
 * Features:
 * 1. True per-millisecond character/word text parting:
 *    Automatically tokenizes page text (excluding navbar) into GPU-accelerated tokens
 *    that part smoothly around the snake's body and spring back into position.
 * 2. Slow, deliberate mouse cursor chasing:
 *    Snake tracks mouse cursor in full document coordinates.
 * 3. Victory Mini-Sound & Cursor Top-Right Respawn:
 *    When snake catches the cursor, it plays a melodic victory chime, celebrates with sparkles,
 *    and respawns the cursor at the top-right of the screen.
 * 4. Stiff button collision detection with audio bump & head injury animation.
 */

import { audioEngine } from "../app/AudioEngine";

export interface SnakePoint {
  x: number;
  y: number;
}

export interface SnakeState {
  head: SnakePoint;
  segments: SnakePoint[];
  angle: number;
  speed: number;
  radius: number;
  isInjured: boolean;
  isVictorious: boolean;
  victorySparkles: { x: number; y: number; vx: number; vy: number; color: string; life: number }[];
  active: boolean;
}

type SnakeListener = (state: SnakeState) => void;

class PretextSnakeEngine {
  // Document Coordinates
  private head: SnakePoint = { x: 300, y: 220 };
  private segments: SnakePoint[] = [];
  private angle: number = 0.2;
  private targetAngle: number = 0.2;
  private speed: number = 1.4; // Calm, deliberate slow speed
  private normalSpeed: number = 1.4;
  private radius: number = 16;
  private segmentCount: number = 18;
  private segmentSpacing: number = 11;
  private phase: number = 0;
  private active: boolean = true;
  private listeners: Set<SnakeListener> = new Set();
  private animationFrameId: number | null = null;
  private lastTime: number = 0;

  // Mouse Cursor Chase Target (Document Coordinates)
  private mouseDocX: number = 450;
  private mouseDocY: number = 300;
  private hasMouseEverMoved: boolean = false;
  private lastCatchTime: number = 0;

  // Victory State
  private isVictorious: boolean = false;
  private victoryUntil: number = 0;
  private victorySparkles: { x: number; y: number; vx: number; vy: number; color: string; life: number }[] = [];

  // Stiff Button Collision & Injury State
  private isInjured: boolean = false;
  private injuredUntil: number = 0;
  private lastBumpTime: number = 0;

  // Tokenized Text Elements for Real-Time Smooth Parting
  private trackedTokens: { element: HTMLElement; docX: number; docY: number }[] = [];
  private displacedTokens: Set<HTMLElement> = new Set();
  private cachedButtonBoxes: { rect: DOMRect; bLeft: number; bRight: number; bTop: number; bBottom: number; centerX: number; centerY: number }[] = [];
  private lastCoordScanTime: number = 0;
  private scanTimer: number = 0;

  constructor() {
    for (let i = 0; i < this.segmentCount; i++) {
      this.segments.push({ x: 300 - i * this.segmentSpacing, y: 220 });
    }
  }

  public start() {
    if (typeof window === "undefined" || this.animationFrameId !== null) return;
    this.lastTime = performance.now();

    this.initMouseListener();
    this.tokenizeDocumentText();

    this.loop = this.loop.bind(this);
    this.animationFrameId = requestAnimationFrame(this.loop);
  }

  public stop() {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    this.resetAllDisplacedTokens();
  }

  public subscribe(listener: SnakeListener): () => void {
    this.listeners.add(listener);
    listener(this.getState());
    return () => this.listeners.delete(listener);
  }

  public getState(): SnakeState {
    const now = performance.now();
    return {
      head: { ...this.head },
      segments: this.segments.map((s) => ({ ...s })),
      angle: this.angle,
      speed: this.speed,
      radius: this.radius,
      isInjured: this.isInjured && now < this.injuredUntil,
      isVictorious: this.isVictorious && now < this.victoryUntil,
      victorySparkles: [...this.victorySparkles],
      active: this.active,
    };
  }

  public setMousePosition(docX: number, docY: number) {
    this.mouseDocX = docX;
    this.mouseDocY = docY;
    this.hasMouseEverMoved = true;
  }

  private initMouseListener() {
    if (typeof window === "undefined") return;

    window.addEventListener(
      "mousemove",
      (e) => {
        const scrollX = window.scrollX || window.pageXOffset || 0;
        const scrollY = window.scrollY || window.pageYOffset || 0;
        this.mouseDocX = e.clientX + scrollX;
        this.mouseDocY = e.clientY + scrollY;
        this.hasMouseEverMoved = true;
      },
      { passive: true }
    );

    window.addEventListener(
      "resize",
      () => {
        this.refreshSpatialCoordinates();
      },
      { passive: true }
    );
  }

  /**
   * Refreshes precomputed document coordinates for tokens and buttons
   * without triggering per-frame layout thrashing.
   */
  public refreshSpatialCoordinates() {
    if (typeof window === "undefined") return;
    const scrollX = window.scrollX || window.pageXOffset || 0;
    const scrollY = window.scrollY || window.pageYOffset || 0;

    // 1. Update token coordinates
    this.trackedTokens.forEach((item) => {
      const rect = item.element.getBoundingClientRect();
      item.docX = rect.left + scrollX + rect.width / 2;
      item.docY = rect.top + scrollY + rect.height / 2;
    });

    // 2. Cache button collision boxes
    const buttons = document.querySelectorAll<HTMLElement>(
      "button, a.btn, [role='button'], .glass-card a, button.p-2, .action-btn"
    );
    const boxes: typeof this.cachedButtonBoxes = [];
    buttons.forEach((btn) => {
      const rect = btn.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        boxes.push({
          rect,
          bLeft: rect.left + scrollX - this.radius,
          bRight: rect.right + scrollX + this.radius,
          bTop: rect.top + scrollY - this.radius,
          bBottom: rect.bottom + scrollY + this.radius,
          centerX: rect.left + scrollX + rect.width / 2,
          centerY: rect.top + scrollY + rect.height / 2,
        });
      }
    });
    this.cachedButtonBoxes = boxes;
    this.lastCoordScanTime = performance.now();
  }

  /**
   * Tokenizes text across the page into GPU-accelerated word tokens.
   */
  public tokenizeDocumentText() {
    if (typeof window === "undefined") return;

    const containers = document.querySelectorAll<HTMLElement>(
      "h1, h2, h3, h4, p, li, .hero-subtitle, .token-container"
    );

    const tokenList: HTMLElement[] = [];

    containers.forEach((container) => {
      if (
        container.closest("nav") ||
        container.closest(".navbar") ||
        container.closest("#main-navbar") ||
        container.closest("button") ||
        container.closest("input") ||
        container.closest("textarea") ||
        container.closest(".no-snake-part")
      ) {
        return;
      }

      if (container.dataset.pretextTokenized === "true") {
        container.querySelectorAll<HTMLElement>(".pretext-word-token").forEach((t) => {
          tokenList.push(t);
        });
        return;
      }

      const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
      const textNodes: Text[] = [];
      let current = walker.nextNode();
      while (current) {
        if (current.textContent && current.textContent.trim().length > 0) {
          textNodes.push(current as Text);
        }
        current = walker.nextNode();
      }

      textNodes.forEach((node) => {
        const text = node.textContent || "";
        const words = text.split(/(\s+)/);
        const fragment = document.createDocumentFragment();

        words.forEach((w) => {
          if (w.trim() === "") {
            fragment.appendChild(document.createTextNode(w));
          } else {
            const span = document.createElement("span");
            span.className = "pretext-word-token inline-block transition-transform duration-75 will-change-transform";
            span.textContent = w;
            fragment.appendChild(span);
            tokenList.push(span);
          }
        });

        node.parentNode?.replaceChild(fragment, node);
      });

      container.dataset.pretextTokenized = "true";
    });

    const scrollX = window.scrollX || window.pageXOffset || 0;
    const scrollY = window.scrollY || window.pageYOffset || 0;

    this.trackedTokens = tokenList.map((element) => {
      const rect = element.getBoundingClientRect();
      return {
        element,
        docX: rect.left + scrollX + rect.width / 2,
        docY: rect.top + scrollY + rect.height / 2,
      };
    });

    this.refreshSpatialCoordinates();
  }

  /**
   * Applies real-time parting using fast pure-math distance calculations on cached coordinates.
   * Zero DOM layout thrashing.
   */
  private applyRealTimeTokenParting() {
    if (typeof window === "undefined") return;

    const now = performance.now();
    // Periodically refresh coordinates to account for dynamic layout changes
    if (now - this.lastCoordScanTime > 1200) {
      this.refreshSpatialCoordinates();
    }

    const repulsionRadius = 55;
    const currentlyDisplaced = new Set<HTMLElement>();
    const headX = this.head.x;
    const headY = this.head.y;
    const checkCount = Math.min(8, this.segments.length);

    for (let t = 0; t < this.trackedTokens.length; t++) {
      const item = this.trackedTokens[t];
      const hDx = item.docX - headX;
      const hDy = item.docY - headY;

      // Fast bounding box rejection
      if (Math.abs(hDx) > repulsionRadius + 30 || Math.abs(hDy) > repulsionRadius + 30) {
        continue;
      }

      const hDist = Math.hypot(hDx, hDy);
      let totalDispX = 0;
      let totalDispY = 0;
      let minDistance = Infinity;

      // 1. Repulsion from Head
      if (hDist < repulsionRadius && hDist > 0) {
        const force = (1 - hDist / repulsionRadius) * 32;
        totalDispX += (hDx / hDist) * force;
        totalDispY += (hDy / hDist) * force * 0.65;
        minDistance = Math.min(minDistance, hDist);
      }

      // 2. Repulsion from first 8 body segments
      for (let i = 0; i < checkCount; i++) {
        const seg = this.segments[i];
        const sDx = item.docX - seg.x;
        const sDy = item.docY - seg.y;
        const sDist = Math.hypot(sDx, sDy);
        if (sDist < repulsionRadius && sDist > 0) {
          const force = (1 - sDist / repulsionRadius) * 26 * (1 - i / checkCount);
          totalDispX += (sDx / sDist) * force;
          totalDispY += (sDy / sDist) * force * 0.55;
          minDistance = Math.min(minDistance, sDist);
        }
      }

      // Apply transform if inside corridor
      if (minDistance < repulsionRadius) {
        item.element.style.transform = `translate3d(${totalDispX.toFixed(1)}px, ${totalDispY.toFixed(1)}px, 0) scale(1.02)`;
        item.element.style.color = "var(--snake-text-glow, #10b981)";
        item.element.style.textShadow = "0 0 10px rgba(16, 185, 129, 0.4)";
        item.element.style.transition = "transform 0.05s ease-out";
        currentlyDisplaced.add(item.element);
        this.displacedTokens.add(item.element);
      }
    }

    // Reset tokens that are no longer near the snake
    this.displacedTokens.forEach((token) => {
      if (!currentlyDisplaced.has(token)) {
        token.style.transform = "translate3d(0, 0, 0)";
        token.style.color = "";
        token.style.textShadow = "";
        token.style.transition = "transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), color 0.25s";
        this.displacedTokens.delete(token);
      }
    });
  }

  private resetAllDisplacedTokens() {
    this.displacedTokens.forEach((token) => {
      token.style.transform = "translate3d(0, 0, 0)";
      token.style.color = "";
      token.style.textShadow = "";
    });
    this.displacedTokens.clear();
  }

  /**
   * Stiff button collision detection on cached coordinates.
   */
  private checkButtonCollisions(): boolean {
    if (typeof window === "undefined") return false;
    const now = performance.now();
    if (now - this.lastBumpTime < 550) return false;

    for (let i = 0; i < this.cachedButtonBoxes.length; i++) {
      const box = this.cachedButtonBoxes[i];
      if (
        this.head.x >= box.bLeft &&
        this.head.x <= box.bRight &&
        this.head.y >= box.bTop &&
        this.head.y <= box.bBottom
      ) {
        this.triggerButtonHit(box.centerX, box.centerY);
        return true;
      }
    }

    return false;
  }

  private triggerButtonHit(btnCenterX: number, btnCenterY: number) {
    const now = performance.now();
    this.lastBumpTime = now;
    this.isInjured = true;
    this.injuredUntil = now + 900;

    try {
      audioEngine.playBumpSound();
    } catch (e) {}

    const deflectAngle = Math.atan2(this.head.y - btnCenterY, this.head.x - btnCenterX);

    this.angle = deflectAngle + (Math.random() - 0.5) * 0.7;
    this.targetAngle = this.angle;

    this.head.x += Math.cos(this.angle) * 18;
    this.head.y += Math.sin(this.angle) * 18;

    this.speed = 0.5;
    setTimeout(() => {
      this.speed = this.normalSpeed;
    }, 750);
  }

  /**
   * Checks if snake caught the mouse cursor.
   * If caught: plays victory chime, sparkles, and respawns cursor at top-right corner.
   */
  private checkCursorCatch(now: number) {
    if (typeof window === "undefined" || !this.hasMouseEverMoved) return;
    if (now - this.lastCatchTime < 1400) return; // catch cooldown

    const dist = Math.hypot(this.mouseDocX - this.head.x, this.mouseDocY - this.head.y);

    if (dist < 24) {
      this.lastCatchTime = now;
      this.isVictorious = true;
      this.victoryUntil = now + 850;

      // 1. Play Cute Melodic Victory Chime
      try {
        audioEngine.playVictoryChime();
      } catch (e) {}

      // 2. Spawn Victory Sparkles Burst
      this.victorySparkles = [];
      const colors = ["#facc15", "#34d399", "#38bdf8", "#f472b6", "#a855f7"];
      for (let i = 0; i < 14; i++) {
        const a = (i / 14) * Math.PI * 2 + Math.random() * 0.4;
        const v = 2.5 + Math.random() * 3.5;
        this.victorySparkles.push({
          x: this.head.x,
          y: this.head.y,
          vx: Math.cos(a) * v,
          vy: Math.sin(a) * v,
          color: colors[i % colors.length],
          life: 1.0,
        });
      }

      // 3. Respawn Cursor at Top-Right Corner of Screen
      const scrollX = window.scrollX || window.pageXOffset || 0;
      const scrollY = window.scrollY || window.pageYOffset || 0;
      const respawnScreenX = window.innerWidth - 75;
      const respawnScreenY = 85;

      const newDocX = respawnScreenX + scrollX;
      const newDocY = respawnScreenY + scrollY;

      this.mouseDocX = newDocX;
      this.mouseDocY = newDocY;

      // Dispatch global event for CustomCursor to teleport
      window.dispatchEvent(
        new CustomEvent("snake-cursor-respawn", {
          detail: { clientX: respawnScreenX, clientY: respawnScreenY },
        })
      );
    }
  }

  private loop(now: number) {
    if (!this.active) {
      this.animationFrameId = requestAnimationFrame(this.loop);
      return;
    }

    const dt = Math.min(32, now - this.lastTime) / 16.66;
    this.lastTime = now;
    this.phase += 0.08 * dt;
    this.scanTimer += dt;

    // Rescan / tokenize new text periodically
    if (this.scanTimer > 200) {
      this.scanTimer = 0;
      this.tokenizeDocumentText();
    }

    // Check Button Collisions
    this.checkButtonCollisions();

    // Check Mouse Cursor Catch
    this.checkCursorCatch(now);

    // Update Victory Sparkles
    for (let i = this.victorySparkles.length - 1; i >= 0; i--) {
      const sp = this.victorySparkles[i];
      sp.x += sp.vx * dt;
      sp.y += sp.vy * dt;
      sp.vy += 0.08 * dt; // gravity
      sp.life -= 0.03 * dt;
      if (sp.life <= 0) {
        this.victorySparkles.splice(i, 1);
      }
    }

    const isInjured = this.isInjured && now < this.injuredUntil;

    // Steer towards mouse cursor
    if (!isInjured) {
      const dx = this.mouseDocX - this.head.x;
      const dy = this.mouseDocY - this.head.y;
      this.targetAngle = Math.atan2(dy, dx);
    }

    // Smooth angle turning
    let angleDiff = this.targetAngle - this.angle;
    while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
    while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
    this.angle += angleDiff * 0.05 * dt;

    // Undulating Slither
    const slither = isInjured
      ? Math.sin(now * 0.04) * 0.08
      : Math.sin(this.phase) * 0.24;
    const curAngle = this.angle + slither;

    // Move Head in Document Coordinates
    this.head.x += Math.cos(curAngle) * this.speed * dt;
    this.head.y += Math.sin(curAngle) * this.speed * dt;

    // Document Constraints
    if (typeof window !== "undefined") {
      const docW = Math.max(window.innerWidth, document.documentElement.scrollWidth || 1000);
      const docH = Math.max(window.innerHeight, document.documentElement.scrollHeight || 1600);

      if (this.head.x < 30) this.head.x = 30;
      if (this.head.x > docW - 30) this.head.x = docW - 30;
      if (this.head.y < 65) this.head.y = 65;
      if (this.head.y > docH - 40) this.head.y = docH - 40;
    }

    // Segment Kinematics
    let prevX = this.head.x;
    let prevY = this.head.y;

    for (let i = 0; i < this.segments.length; i++) {
      const seg = this.segments[i];
      const sDx = prevX - seg.x;
      const sDy = prevY - seg.y;
      const sAngle = Math.atan2(sDy, sDx);

      seg.x = prevX - Math.cos(sAngle) * this.segmentSpacing;
      seg.y = prevY - Math.sin(sAngle) * this.segmentSpacing;

      const wave = Math.sin(this.phase - i * 0.38) * (i * 0.3);
      seg.x += Math.cos(sAngle + Math.PI / 2) * wave * 0.1;
      seg.y += Math.sin(sAngle + Math.PI / 2) * wave * 0.1;

      prevX = seg.x;
      prevY = seg.y;
    }

    // Apply Real-Time Per-Word Token Parting
    this.applyRealTimeTokenParting();

    this.notify();
    this.animationFrameId = requestAnimationFrame(this.loop);
  }

  private notify() {
    const state = this.getState();
    this.listeners.forEach((fn) => fn(state));
  }
}

export const pretextSnakeEngine = new PretextSnakeEngine();
