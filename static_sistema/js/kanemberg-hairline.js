/**
 * kanemberg-hairline.js — Background Wireframe Isométrico Reativo ao Mouse
 * Puro HTML5 Canvas (Zero dependências) — Otimizado com modo Idle e Respiração (< 150 linhas)
 */
(function () {
  'use strict';

  const canvas = document.getElementById('kanemberg-hairline-canvas') || (() => {
    const c = document.createElement('canvas');
    c.id = 'kanemberg-hairline-canvas';
    document.body.prepend(c);
    return c;
  })();

  const ctx = canvas.getContext('2d');
  const COLS = 64, ROWS = 24;
  const REST_OPACITY = 0.28, PEAK_OPACITY = 0.65;
  const COLOR = { r: 255, g: 215, b: 0 }; // Ouro/Âmbar #ffd700

  let w = 0, h = 0, dpr = 1, pts = [];
  let mx = -9999, my = -9999, active = false;
  let running = false, rafId = null, hasEnergy = false;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = window.innerWidth;
    h = window.innerHeight;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    pts = [];
    const horizon = h * 0.32;
    for (let j = 0; j < ROWS; j++) {
      const v = j / (ROWS - 1);
      const p = Math.pow(v, 1.15);
      const y0 = horizon + (h * 1.08 - horizon) * p;
      const spread = 0.55 + 0.45 * p; // Overscan dinâmico eliminando vazios laterais
      for (let i = 0; i < COLS; i++) {
        const u = (i / (COLS - 1)) - 0.5;
        const x0 = (w * 0.5) + u * (w * 2.6) * spread; // Span de 260% (-0.8w a 1.8w)
        const topo = (Math.sin(u * 9) * 8 + Math.cos(v * 7) * 6) * Math.pow(v, 0.7);
        pts.push({ x: x0, y: y0, topo, z: 0, vz: 0, u, v, cy: y0 - topo });
      }
    }
    wake();
  }

  function wake() {
    if (!running) { running = true; rafId = requestAnimationFrame(loop); }
  }

  function loop(now) {
    if (!running) return;
    const t = now * 0.001;
    let energy = 0;
    const rad = 260, radSq = rad * rad;
    const horizon = h * 0.32;
    const isInteracting = active && my >= horizon - 50;

    for (let j = 0; j < ROWS; j++) {
      const rOff = j * COLS;
      for (let i = 0; i < COLS; i++) {
        const idx = rOff + i;
        const p = pts[idx];
        // Respiração senoidal orgânica contínua de baixa frequência
        const breathe = (Math.sin(t * 1.1 + p.u * 4.5) * 4 + Math.cos(t * 0.85 + p.v * 3.5) * 3) * (0.35 + 0.65 * p.v);

        let target = 0;
        if (isInteracting) {
          const curY = p.y - p.topo - p.z - breathe;
          const dx = p.x - mx, dy = curY - my;
          const dSq = dx * dx + dy * dy;
          if (dSq < radSq) {
            const q = 1 - Math.sqrt(dSq) / rad;
            target = 58 * (q * q);
          }
        }

        // Amortecimento de mola e propagação por vizinhos (bypass inteligente no repouso)
        if (hasEnergy || isInteracting) {
          const left = i > 0 ? pts[idx - 1].z : p.z;
          const right = i < COLS - 1 ? pts[idx + 1].z : p.z;
          const top = j > 0 ? pts[idx - COLS].z : p.z;
          const bot = j < ROWS - 1 ? pts[idx + COLS].z : p.z;
          const wave = ((left + right + top + bot) * 0.25 - p.z) * 0.055;

          p.vz = (p.vz + (target - p.z) * 0.045 + wave) * 0.88;
          p.z += p.vz;
          if (Math.abs(p.z) < 0.01 && Math.abs(p.vz) < 0.01) { p.z = 0; p.vz = 0; }
          energy += Math.abs(p.vz) + Math.abs(p.z);
        }

        p.cy = p.y - p.topo - p.z - breathe;
      }
    }
    hasEnergy = energy > 0.04;

    ctx.fillStyle = '#09090b';
    ctx.fillRect(0, 0, w, h);

    let strokeStyle = `rgba(${COLOR.r},${COLOR.g},${COLOR.b},${REST_OPACITY})`;
    if (isInteracting) {
      const grad = ctx.createRadialGradient(mx, my, 0, mx, my, 280);
      grad.addColorStop(0, `rgba(${COLOR.r},${COLOR.g},${COLOR.b},${PEAK_OPACITY})`);
      grad.addColorStop(0.5, `rgba(${COLOR.r},${COLOR.g},${COLOR.b},${(REST_OPACITY + PEAK_OPACITY) * 0.5})`);
      grad.addColorStop(1, strokeStyle);
      strokeStyle = grad;
    }
    ctx.lineWidth = 1;
    ctx.strokeStyle = strokeStyle;

    ctx.beginPath();
    for (let j = 0; j < ROWS; j++) {
      const rOff = j * COLS;
      for (let i = 0; i < COLS; i++) {
        const p = pts[rOff + i];
        i === 0 ? ctx.moveTo(p.x, p.cy) : ctx.lineTo(p.x, p.cy);
      }
    }
    for (let i = 0; i < COLS; i++) {
      for (let j = 0; j < ROWS; j++) {
        const p = pts[j * COLS + i];
        j === 0 ? ctx.moveTo(p.x, p.cy) : ctx.lineTo(p.x, p.cy);
      }
    }
    ctx.stroke();

    const fGrad = ctx.createLinearGradient(0, horizon - 25, 0, horizon + 80);
    fGrad.addColorStop(0, '#09090b');
    fGrad.addColorStop(0.35, '#09090b');
    fGrad.addColorStop(1, 'rgba(9,9,11,0)');
    ctx.fillStyle = fGrad;
    ctx.fillRect(0, 0, w, horizon + 80);

    rafId = requestAnimationFrame(loop);
  }

  window.addEventListener('mousemove', (e) => { mx = e.clientX; my = e.clientY; active = true; wake(); }, { passive: true });
  window.addEventListener('mouseleave', () => { active = false; mx = -9999; my = -9999; });
  window.addEventListener('resize', resize, { passive: true });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { running = false; if (rafId) cancelAnimationFrame(rafId); } else wake();
  });

  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', resize) : resize();
})();
