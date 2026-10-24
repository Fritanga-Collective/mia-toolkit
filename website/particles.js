/* MIA Tools — institutional pages: particle motion over the illustrations.
 * Decorative progressive enhancement. The still image is always there; this
 * adds a <canvas> on top of any <picture data-particles="<scene>">.
 *  - Does nothing with prefers-reduced-motion, without canvas, or without JS.
 *  - Runs only while the picture is on screen and the tab is visible.
 *  - Scene coordinates are fractions of the 16:9 source image; they are
 *    mapped through the img's object-fit: cover crop and object-position,
 *    so the same scene lines up in the 16:9 hero and the 21:9 card crop.
 * First-party, no dependencies, nothing sent anywhere.
 */
(function () {
  "use strict";
  var IW = 16, IH = 9;                       // source aspect (1600x900)
  var reduce = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)");
  if (!window.requestAnimationFrame || (reduce && reduce.matches)) return;

  var rand = function (a, b) { return a + Math.random() * (b - a); };
  var lerp = function (a, b, t) { return a + (b - a) * t; };
  var smooth = function (e0, e1, x) {
    var t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0)));
    return t * t * (3 - 2 * t);
  };

  // Polyline helpers for the network scene: points in source fractions.
  function path(pts) {
    var len = [0], total = 0, i;
    for (i = 1; i < pts.length; i++) {
      total += Math.hypot(pts[i][0] - pts[i - 1][0],
                          (pts[i][1] - pts[i - 1][1]) * IH / IW);
      len.push(total);
    }
    return { pts: pts, len: len, total: total };
  }
  function along(p, u) {
    var d = u * p.total, i = 1;
    while (i < p.len.length - 1 && p.len[i] < d) i++;
    var seg = (d - p.len[i - 1]) / ((p.len[i] - p.len[i - 1]) || 1);
    return [lerp(p.pts[i - 1][0], p.pts[i][0], seg),
            lerp(p.pts[i - 1][1], p.pts[i][1], seg)];
  }

  /* Scene 1: discs dissolve into a twisting stream that enters the USB
   * (img/inst/disc-to-usb-real). */
  var stream = {
    density: 0.5,                            // particles per CSS px of width
    max: 420,
    discs: [0.12, 0.34, 0.24, 0.76],         // x0, x1, y0, y1 of the stack
    usb: [0.755, 0.5],
    spawn: function (p) {
      p.dust = Math.random() < 0.18;
      p.sx = rand(this.discs[0], this.discs[1]);
      p.sy = rand(this.discs[2], this.discs[3]);
      p.u = 0;
      p.v = p.dust ? rand(0.05, 0.12) : rand(0.09, 0.16);   // per second
      p.phase = Math.random() < 0.5 ? 0 : Math.PI;           // two strands
      p.j = rand(-1, 1);
      p.size = rand(1.4, 3);
      p.dx = rand(-0.06, -0.02); p.dy = rand(-0.05, 0.05);
    },
    draw: function (ctx, p, t, map, px) {
      var x, y, a, depth = 1, k;
      if (p.dust) {                          // specks drifting off the discs
        x = p.sx + p.dx * p.u * 3; y = p.sy + p.dy * p.u * 3;
        a = 0.8 * smooth(0, 0.15, p.u) * (1 - smooth(0.6, 1, p.u));
        ctx.fillStyle = "rgba(150,235,245," + a.toFixed(3) + ")";
      } else {
        var u = p.u, amp = lerp(0.19, 0.03, smooth(0, 0.95, u));
        var th = p.phase + u * Math.PI * 3.2 - t * 0.9;
        var hx = lerp(0.3, this.usb[0], u);
        var hy = this.usb[1] + amp * Math.sin(th) + p.j * amp * 0.35;
        depth = 0.65 + 0.35 * Math.cos(th);
        k = smooth(0, 0.3, u);               // leave the disc, join the helix
        x = lerp(p.sx, hx, k); y = lerp(p.sy, hy, k);
        a = depth * smooth(0, 0.08, u) * (1 - smooth(0.9, 1, u));
        ctx.fillStyle = "rgba(" + Math.round(lerp(130, 45, u)) + "," +
          Math.round(lerp(230, 110, u)) + ",255," + a.toFixed(3) + ")";
      }
      var c = map(x, y), s = p.size * depth * px;
      ctx.fillRect(c[0] - s / 2, c[1] - s / 2, s, s);
    },
    after: function (ctx, t, map, px) {      // the USB breathes
      var c = map(0.82, 0.5), r = 70 * px;
      var g = ctx.createRadialGradient(c[0], c[1], 0, c[0], c[1], r);
      g.addColorStop(0, "rgba(70,140,255," +
        (0.16 + 0.08 * Math.sin(t * 2.2)).toFixed(3) + ")");
      g.addColorStop(1, "rgba(70,140,255,0)");
      ctx.fillStyle = g; ctx.fillRect(c[0] - r, c[1] - r, 2 * r, 2 * r);
    }
  };

  /* Scene 2: pulses travel the circuit lines into the hub, then up the beam
   * to the PACS server (img/inst/network-to-pacs-beam). */
  // Traced from the artwork's circuit lines (box → hub), then the beam.
  var HUB = [0.59, 0.455];
  var feeds = [
    [[0.449, 0.256], [0.489, 0.291], [0.494, 0.444], [0.519, 0.476],
     [0.578, 0.472]],
    [[0.274, 0.358], [0.359, 0.437], [0.425, 0.437], [0.488, 0.494],
     [0.578, 0.472]],
    [[0.27, 0.576], [0.353, 0.496], [0.55, 0.492], [0.578, 0.476]],
    [[0.406, 0.578], [0.463, 0.522], [0.519, 0.522], [0.578, 0.478]],
    [[0.45, 0.798], [0.501, 0.751], [0.501, 0.522], [0.538, 0.5],
     [0.578, 0.478]],
    [[0.5625, 0.824], [0.621, 0.767], [0.621, 0.683], [0.536, 0.6],
     [0.536, 0.522], [0.578, 0.48]],
    [[0.7175, 0.642], [0.669, 0.597], [0.609, 0.597], [0.566, 0.561],
     [0.566, 0.5], [0.581, 0.48]]
  ].map(path);
  var beam = path([[0.6, 0.45], [0.709, 0.353]]);
  var network = {
    density: 0.035,
    max: 28,
    hubHit: 0,
    spawn: function (p, fresh) {
      p.beam = false;
      p.path = feeds[Math.floor(Math.random() * feeds.length)];
      p.u = fresh ? Math.random() : 0;
      p.v = rand(0.18, 0.3);
    },
    step: function (p, t) {                   // reached the hub: go up the beam
      if (p.u < 1) return false;
      if (p.beam) return true;               // respawn
      this.hubHit = t;
      p.beam = true; p.path = beam; p.u = 0; p.v = 0.9;
      return false;
    },
    draw: function (ctx, p, t, map, px) {
      var head = map.apply(null, along(p.path, p.u));
      var tail = map.apply(null, along(p.path, Math.max(0, p.u - 0.12)));
      var g = ctx.createLinearGradient(tail[0], tail[1], head[0], head[1]);
      var col = p.beam ? "200,240,255" : "110,220,255";
      g.addColorStop(0, "rgba(" + col + ",0)");
      g.addColorStop(1, "rgba(" + col + ",0.9)");
      ctx.strokeStyle = g; ctx.lineWidth = (p.beam ? 2 : 1.5) * px;
      ctx.beginPath(); ctx.moveTo(tail[0], tail[1]);
      ctx.lineTo(head[0], head[1]); ctx.stroke();
      ctx.fillStyle = "rgba(" + col + ",1)";
      ctx.beginPath(); ctx.arc(head[0], head[1], 1.6 * px, 0, 6.2832);
      ctx.fill();
    },
    after: function (ctx, t, map, px) {      // hub flashes on each arrival
      var c = map(HUB[0], HUB[1]), r = 40 * px;
      var a = 0.12 + 0.35 * Math.max(0, 1 - (t - this.hubHit) * 3);
      var g = ctx.createRadialGradient(c[0], c[1], 0, c[0], c[1], r);
      g.addColorStop(0, "rgba(120,220,255," + a.toFixed(3) + ")");
      g.addColorStop(1, "rgba(120,220,255,0)");
      ctx.fillStyle = g; ctx.fillRect(c[0] - r, c[1] - r, 2 * r, 2 * r);
    }
  };

  var SCENES = { stream: stream, network: network };

  function attach(pic) {
    var base = SCENES[pic.getAttribute("data-particles")];
    var img = pic.querySelector("img");
    var canvas = document.createElement("canvas");
    var ctx = canvas.getContext && canvas.getContext("2d");
    if (!base || !img || !ctx) return;
    var scene = Object.create(base);         // per-instance state (hubHit)
    canvas.className = "i-particles";
    canvas.setAttribute("aria-hidden", "true");
    pic.appendChild(canvas);

    var W = 0, H = 0, dpr = 1, ox = 0, oy = 0, sc = 1, parts = [];
    var raf = 0, last = 0, visible = false, off = false;
    var map = function (x, y) { return [ox + x * IW * sc, oy + y * IH * sc]; };

    function size() {
      var r = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = Math.round(r.width * dpr); H = Math.round(r.height * dpr);
      if (!W || !H) return;
      canvas.width = W; canvas.height = H;
      // object-fit: cover + object-position, in device pixels.
      var pos = (getComputedStyle(img).objectPosition || "50% 50%").split(" ");
      var fx = parseFloat(pos[0]) / 100, fy = parseFloat(pos[1] || pos[0]) / 100;
      sc = Math.max(W / IW, H / IH);
      ox = (W - IW * sc) * (isNaN(fx) ? 0.5 : fx);
      oy = (H - IH * sc) * (isNaN(fy) ? 0.5 : fy);
      var n = Math.min(scene.max, Math.round(r.width * scene.density));
      while (parts.length < n) {
        var p = {}; scene.spawn(p, true); p.u = Math.random(); parts.push(p);
      }
      parts.length = n;
    }

    function frame(now) {
      var t = now / 1000, dt = Math.min(0.05, last ? t - last : 0);
      last = t;
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        p.u += p.v * dt;
        if (scene.step ? scene.step(p, t) : p.u >= 1) scene.spawn(p, false);
        scene.draw(ctx, p, t, map, dpr);
      }
      if (scene.after) scene.after(ctx, t, map, dpr);
      ctx.globalCompositeOperation = "source-over";
      raf = requestAnimationFrame(frame);
    }
    function start() {
      if (raf || off || !visible || document.hidden) return;
      last = 0; raf = requestAnimationFrame(frame);
    }
    function stop() {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
    }

    size();
    if (window.ResizeObserver) new ResizeObserver(size).observe(canvas);
    else window.addEventListener("resize", size);
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stop(); else start();
    });
    if (reduce && reduce.addEventListener) {
      reduce.addEventListener("change", function () {
        if (reduce.matches) { off = true; stop(); canvas.remove(); }
      });
    }
    if (window.IntersectionObserver) {
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
        if (visible) start(); else stop();
      }).observe(pic);
    } else { visible = true; start(); }
  }

  Array.prototype.forEach.call(
    document.querySelectorAll("picture[data-particles]"), attach);
})();
