<script lang="ts">
  /**
   * AntennaBackground — WebGL 2.0 instanced antenna field.
   *
   * A grid of parabolic dish antennas that rotate to track the mouse and emit
   * animated signal beams.  Default palette tuned for the dark-navy page bg:
   *   - Antenna idle:  deep slate  (#1c2a3e)  — subtle, barely there
   *   - Antenna active: steel blue (#7eb8da)  — holographic glow
   *   - Signal beam:   brand red   (#B12142)  — consistent with theme
   *
   * Colors can be overridden via props for light-mode palettes.
   * The canvas is fixed full-screen behind all content by default.
   */
  import { onMount, onDestroy } from "svelte";
  import shaderSource from "$lib/shaders/antenna.glsl?raw";

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function hexToRgb(hex: string): [number, number, number] {
    hex = hex.replace(/^#/, "");
    if (hex.length === 3)
      hex = hex
        .split("")
        .map((c) => c + c)
        .join("");
    const n = parseInt(hex, 16);
    return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  }

  // ── Props ────────────────────────────────────────────────────────────────────

  let {
    // Grid
    spacing = 120,
    scale = 1.0,
    // Interaction
    maxDist = 300,
    beamWidth = 125,
    smoothness = 0.05,
    // Theme
    lightMode = false,
    // Colors — tuned for dark-navy page background
    beamColor = "#B12142", // project brand red — signal beam
    colorOff = "#1c2a3e", // deep slate — subtle idle dish
    colorOn = "#7eb8da", // steel blue — holographic active glow
    // Geometry (keep original proportions)
    dishRadius = 15.0,
    dishWidth = 1.5,
    rodLength = 24.0,
    rodWidth = 1.0,
    tipSize = 2.5,
    // Signal (keep original feel)
    signalSpeed = 1.5,
    signalAmplitude = 4.5,
    signalFreq = 1.5,
    signalPacketFreq = 1.5,
    signalPacketSpeed = 3.0,
    signalWidth = 0.75,
    signalFadeScale = 1.5,
    antennaFadeScale = 1.0,
  } = $props();

  // ── Derived RGB ──────────────────────────────────────────────────────────────

  const rgbBeam = $derived(hexToRgb(beamColor));
  const rgbOff = $derived(hexToRgb(colorOff));
  const rgbOn = $derived(hexToRgb(colorOn));

  // ── State ────────────────────────────────────────────────────────────────────

  let canvas: HTMLCanvasElement;
  let gl: WebGL2RenderingContext | null = null;
  let animationId: number;
  let program: WebGLProgram;
  let vao: WebGLVertexArrayObject | null = null;
  let instanceCount = 0;

  let innerWidth = 0;
  let innerHeight = 0;
  let targetX = 0,
    targetY = 0;
  let followX = 0,
    followY = 0;
  let currentX = 0,
    currentY = 0;
  let hasMoved = false;

  let opacity = 0;
  const FADE_DURATION = 1500;
  let startTime: number | null = null;

  // Uniform locations
  let locResolution: WebGLUniformLocation | null;
  let locMouse: WebGLUniformLocation | null;
  let locTime: WebGLUniformLocation | null;
  let locOpacity: WebGLUniformLocation | null;
  let locScale: WebGLUniformLocation | null;
  let locBeamColor: WebGLUniformLocation | null;
  let locColorOff: WebGLUniformLocation | null;
  let locColorOn: WebGLUniformLocation | null;
  let locMaxDist: WebGLUniformLocation | null;
  let locBeamWidth: WebGLUniformLocation | null;
  let locDishRadius: WebGLUniformLocation | null;
  let locDishWidth: WebGLUniformLocation | null;
  let locRodLength: WebGLUniformLocation | null;
  let locRodWidth: WebGLUniformLocation | null;
  let locTipSize: WebGLUniformLocation | null;
  let locSignalSpeed: WebGLUniformLocation | null;
  let locSignalAmp: WebGLUniformLocation | null;
  let locSignalFreq: WebGLUniformLocation | null;
  let locSignalPacketFreq: WebGLUniformLocation | null;
  let locSignalPacketSpeed: WebGLUniformLocation | null;
  let locSignalWidth: WebGLUniformLocation | null;
  let locSignalFadeScale: WebGLUniformLocation | null;
  let locAntennaFadeScale: WebGLUniformLocation | null;

  // ── Pointer tracking (passive, window-wide) ──────────────────────────────────

  function trackPointer(node: HTMLElement) {
    function update(e: Event) {
      hasMoved = true;
      if (
        window.TouchEvent &&
        e instanceof TouchEvent &&
        e.touches.length > 0
      ) {
        targetX = e.touches[0].clientX;
        targetY = e.touches[0].clientY;
      } else if (e instanceof MouseEvent) {
        targetX = e.clientX;
        targetY = e.clientY;
      }
    }
    const opts = { passive: true, capture: true };
    window.addEventListener("pointerdown", update, opts);
    window.addEventListener("pointermove", update, opts);
    window.addEventListener("dragover", update, opts);
    window.addEventListener("touchmove", update, opts);
    return {
      destroy() {
        window.removeEventListener("pointerdown", update, { capture: true });
        window.removeEventListener("pointermove", update, { capture: true });
        window.removeEventListener("dragover", update, { capture: true });
        window.removeEventListener("touchmove", update, { capture: true });
      },
    };
  }

  // ── WebGL helpers ─────────────────────────────────────────────────────────────

  function createShader(
    gl: WebGL2RenderingContext,
    type: number,
    source: string,
  ) {
    const s = gl.createShader(type);
    if (!s) return null;
    gl.shaderSource(s, source);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.error("Shader compile error:", gl.getShaderInfoLog(s));
      gl.deleteShader(s);
      return null;
    }
    return s;
  }

  function createProgram(
    gl: WebGL2RenderingContext,
    vsSource: string,
    fsSource: string,
  ) {
    const vs = createShader(gl, gl.VERTEX_SHADER, vsSource);
    const fs = createShader(gl, gl.FRAGMENT_SHADER, fsSource);
    if (!vs || !fs) return null;
    const prog = gl.createProgram();
    if (!prog) return null;
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.error("Program link error:", gl.getProgramInfoLog(prog));
      return null;
    }
    return prog;
  }

  // ── Grid rebuild (called on resize) ──────────────────────────────────────────

  function updateGrid() {
    if (!gl || !program || !vao) return;
    const cols = Math.max(2, Math.round(innerWidth / spacing));
    const rows = Math.max(2, Math.round(innerHeight / spacing));
    instanceCount = cols * rows;

    const gridData = new Float32Array(instanceCount * 2);
    let i = 0;
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const tx = cols > 1 ? x / (cols - 1) : 0.5;
        const ty = rows > 1 ? y / (rows - 1) : 0.5;
        gridData[i++] = 30.0 + (innerWidth - 60.0) * tx;
        gridData[i++] = innerHeight - 60.0 - (innerHeight - 120.0) * ty;
      }
    }

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, gridData, gl.STATIC_DRAW);
    gl.bindVertexArray(vao);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 0, 0);
    gl.vertexAttribDivisor(1, 1);
    gl.bindVertexArray(null);
  }

  function resize() {
    if (!canvas || !gl) return;
    const dpr = window.devicePixelRatio || 1;
    innerWidth = window.innerWidth;
    innerHeight = window.innerHeight;
    canvas.width = innerWidth * dpr;
    canvas.height = innerHeight * dpr;
    gl.viewport(0, 0, canvas.width, canvas.height);
    if (!hasMoved) {
      targetX = currentX = innerWidth / 2;
      targetY = currentY = innerHeight / 2;
    }
    updateGrid();
  }

  // ── Render loop ───────────────────────────────────────────────────────────────

  function render(time: number) {
    if (!gl || !program || !vao) return;

    if (hasMoved) {
      if (startTime === null) startTime = time;
      opacity = Math.min((time - startTime) / FADE_DURATION, 1.0);
    } else {
      opacity = 0;
    }

    // Double exponential smoothing for a non-linear ease-in/ease-out delay
    // Multiplier of 1.5 keeps the overall tracking speed similar to the original 
    // while providing a much smoother initial acceleration curve.
    followX += (targetX - followX) * (smoothness * 1.5);
    followY += (targetY - followY) * (smoothness * 1.5);
    
    currentX += (followX - currentX) * (smoothness * 1.5);
    currentY += (followY - currentY) * (smoothness * 1.5);

    gl.useProgram(program);

    if (locResolution) gl.uniform2f(locResolution, innerWidth, innerHeight);
    if (locMouse) gl.uniform2f(locMouse, currentX, currentY);
    if (locTime) gl.uniform1f(locTime, time / 1000);
    if (locOpacity) gl.uniform1f(locOpacity, opacity);
    if (locScale) gl.uniform1f(locScale, scale);

    if (locBeamColor)
      gl.uniform3f(locBeamColor, rgbBeam[0], rgbBeam[1], rgbBeam[2]);
    if (locColorOff) gl.uniform3f(locColorOff, rgbOff[0], rgbOff[1], rgbOff[2]);
    if (locColorOn) gl.uniform3f(locColorOn, rgbOn[0], rgbOn[1], rgbOn[2]);

    if (locMaxDist) gl.uniform1f(locMaxDist, maxDist);
    if (locBeamWidth) gl.uniform1f(locBeamWidth, beamWidth);

    if (locDishRadius) gl.uniform1f(locDishRadius, dishRadius);
    if (locDishWidth) gl.uniform1f(locDishWidth, dishWidth);
    if (locRodLength) gl.uniform1f(locRodLength, rodLength);
    if (locRodWidth) gl.uniform1f(locRodWidth, rodWidth);
    if (locTipSize) gl.uniform1f(locTipSize, tipSize);

    if (locSignalSpeed) gl.uniform1f(locSignalSpeed, signalSpeed);
    if (locSignalAmp) gl.uniform1f(locSignalAmp, signalAmplitude);
    if (locSignalFreq) gl.uniform1f(locSignalFreq, signalFreq);
    if (locSignalPacketFreq)
      gl.uniform1f(locSignalPacketFreq, signalPacketFreq);
    if (locSignalPacketSpeed)
      gl.uniform1f(locSignalPacketSpeed, signalPacketSpeed);
    if (locSignalWidth) gl.uniform1f(locSignalWidth, signalWidth);
    if (locSignalFadeScale) gl.uniform1f(locSignalFadeScale, signalFadeScale);
    if (locAntennaFadeScale)
      gl.uniform1f(locAntennaFadeScale, antennaFadeScale);

    gl.bindVertexArray(vao);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, instanceCount);
    gl.bindVertexArray(null);

    animationId = requestAnimationFrame(render);
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────────

  onMount(() => {
    gl = canvas.getContext("webgl2", {
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    if (!gl) {
      console.error("WebGL 2 not supported");
      return;
    }

    targetX = currentX = window.innerWidth / 2;
    targetY = currentY = window.innerHeight / 2;

    const version = "#version 300 es\n";
    const rest = shaderSource.replace(version, "");
    const vs = version + "#define VERTEX_SHADER\n" + rest;
    const fs = version + "#define FRAGMENT_SHADER\n" + rest;

    const prog = createProgram(gl, vs, fs);
    if (!prog) return;
    program = prog;

    locResolution = gl.getUniformLocation(program, "u_resolution");
    locMouse = gl.getUniformLocation(program, "u_mouse");
    locTime = gl.getUniformLocation(program, "u_time");
    locOpacity = gl.getUniformLocation(program, "u_opacity");
    locScale = gl.getUniformLocation(program, "u_scale");
    locBeamColor = gl.getUniformLocation(program, "u_beam_color");
    locColorOff = gl.getUniformLocation(program, "u_color_off");
    locColorOn = gl.getUniformLocation(program, "u_color_on");
    locMaxDist = gl.getUniformLocation(program, "u_max_dist");
    locBeamWidth = gl.getUniformLocation(program, "u_beam_width");
    locDishRadius = gl.getUniformLocation(program, "u_dish_radius");
    locDishWidth = gl.getUniformLocation(program, "u_dish_width");
    locRodLength = gl.getUniformLocation(program, "u_rod_length");
    locRodWidth = gl.getUniformLocation(program, "u_rod_width");
    locTipSize = gl.getUniformLocation(program, "u_tip_size");
    locSignalSpeed = gl.getUniformLocation(program, "u_signal_speed");
    locSignalAmp = gl.getUniformLocation(program, "u_signal_amp");
    locSignalFreq = gl.getUniformLocation(program, "u_signal_freq");
    locSignalPacketFreq = gl.getUniformLocation(
      program,
      "u_signal_packet_freq",
    );
    locSignalPacketSpeed = gl.getUniformLocation(
      program,
      "u_signal_packet_speed",
    );
    locSignalWidth = gl.getUniformLocation(program, "u_signal_width");
    locSignalFadeScale = gl.getUniformLocation(program, "u_signal_fade_scale");
    locAntennaFadeScale = gl.getUniformLocation(
      program,
      "u_antenna_fade_scale",
    );

    // Unit quad
    vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const posBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-0.5, -0.5, 0.5, -0.5, -0.5, 0.5, 0.5, 0.5]),
      gl.STATIC_DRAW,
    );
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);

    resize();
    window.addEventListener("resize", resize);
    animationId = requestAnimationFrame(render);
  });

  onDestroy(() => {
    if (typeof window === "undefined") return;
    window.removeEventListener("resize", resize);
    cancelAnimationFrame(animationId);
  });
</script>

<!--
  The canvas is transparent (alpha: true in WebGL context) and sits behind
  all page content.  The actual page background color is set on <html> in
  app.css, so the gradient shows through the antenna field.
-->
<canvas
  bind:this={canvas}
  use:trackPointer
  style="touch-action: none;"
  class="fixed inset-0 -z-10 h-full w-full"
></canvas>
