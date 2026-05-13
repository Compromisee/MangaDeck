(function () {
  "use strict";

  /* ═══ PARTICLES ═══ */
  function initHeroParticles() {
    var canvas = document.getElementById("hero-canvas");
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var w, h;
    var particles = [];
    var mouse = { x: -1000, y: -1000 };

    function resize() {
      w = canvas.width = canvas.parentElement.offsetWidth;
      h = canvas.height = canvas.parentElement.offsetHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    canvas.addEventListener("mousemove", function (e) {
      var rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    });
    canvas.addEventListener("mouseleave", function () {
      mouse.x = -1000; mouse.y = -1000;
    });

    for (var i = 0; i < 70; i++) {
      particles.push({
        x: Math.random() * 1400,
        y: Math.random() * 900,
        r: Math.random() * 1.5 + .5,
        vx: (Math.random() - .5) * .3,
        vy: (Math.random() - .5) * .3,
        a: Math.random() * .5,
        da: (Math.random() - .5) * .003,
      });
    }

    (function draw() {
      ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < particles.length; i++) {
        var p = particles[i];
        // Mouse repulsion
        var dx = p.x - mouse.x;
        var dy = p.y - mouse.y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120 && dist > 0) {
          p.x += dx / dist * 1.5;
          p.y += dy / dist * 1.5;
        }
        p.x += p.vx; p.y += p.vy; p.a += p.da;
        if (p.a > .5 || p.a < .02) p.da *= -1;
        if (p.x < 0) p.x = w; if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(74,143,231," + Math.max(0, p.a).toFixed(3) + ")";
        ctx.fill();
      }
      for (var i = 0; i < particles.length; i++) {
        for (var j = i + 1; j < particles.length; j++) {
          var dx2 = particles[i].x - particles[j].x;
          var dy2 = particles[i].y - particles[j].y;
          var d2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);
          if (d2 < 110) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = "rgba(74,143,231," + ((1 - d2 / 110) * .08).toFixed(3) + ")";
            ctx.lineWidth = .5;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(draw);
    })();
  }

  /* ═══ PARALLAX ═══ */
  function initParallax() {
    var els = document.querySelectorAll("[data-parallax]");
    window.addEventListener("scroll", function () {
      var scrollY = window.pageYOffset;
      for (var i = 0; i < els.length; i++) {
        var speed = parseFloat(els[i].getAttribute("data-parallax")) || .3;
        els[i].style.transform = "translateY(" + (scrollY * speed * -.3) + "px)";
      }
    });
  }

  /* ═══ NAV SCROLL ═══ */
  function initNav() {
    var nav = document.getElementById("nav");
    var toggle = document.getElementById("nav-toggle");
    var links = document.querySelector(".nav-links");

    window.addEventListener("scroll", function () {
      if (window.pageYOffset > 60) nav.classList.add("scrolled");
      else nav.classList.remove("scrolled");
    });

    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });

    var navAnchors = document.querySelectorAll(".nav-links a[href^='#']");
    for (var i = 0; i < navAnchors.length; i++) {
      navAnchors[i].addEventListener("click", function () {
        links.classList.remove("open");
      });
    }
  }

  /* ═══ SCROLL REVEAL ═══ */
  function initReveal() {
    var items = document.querySelectorAll("[data-reveal]");
    function check() {
      for (var i = 0; i < items.length; i++) {
        var rect = items[i].getBoundingClientRect();
        var delay = parseInt(items[i].getAttribute("data-delay")) || 0;
        if (rect.top < window.innerHeight * .88) {
          (function (el, d) {
            setTimeout(function () { el.classList.add("visible"); }, d * 100);
          })(items[i], delay);
        }
      }
    }
    check();
    window.addEventListener("scroll", check);
  }

  /* ═══ COUNT UP ═══ */
  function initCountUp() {
    var nums = document.querySelectorAll("[data-count]");
    var counted = false;
    function check() {
      if (counted) return;
      for (var i = 0; i < nums.length; i++) {
        var rect = nums[i].getBoundingClientRect();
        if (rect.top < window.innerHeight * .8) {
          counted = true;
          doCount();
          return;
        }
      }
    }
    function doCount() {
      for (var i = 0; i < nums.length; i++) {
        (function (el) {
          var target = parseInt(el.getAttribute("data-count"));
          var current = 0;
          var step = Math.max(1, Math.floor(target / 40));
          var interval = setInterval(function () {
            current += step;
            if (current >= target) { current = target; clearInterval(interval); }
            el.textContent = current;
          }, 30);
        })(nums[i]);
      }
    }
    check();
    window.addEventListener("scroll", check);
  }

  /* ═══ TERMINAL ANIMATION ═══ */
  function initTerminal() {
    var container = document.getElementById("terminal-lines");
    var cursor = document.getElementById("terminal-cursor");
    if (!container) return;

    var lines = [
      { type: "prompt", text: "$ python main.py --mode cli --search \"One Piece\"", delay: 800 },
      { type: "output", text: "", delay: 200 },
      { type: "dim", text: "  Searching across 7 sources...", delay: 600 },
      { type: "output", text: "", delay: 400 },
      { type: "accent", text: "  Found 5 results:", delay: 300 },
      { type: "output", text: "  [1] One Piece (mangadex, manganato, mangakakalot) - 1076 chapters", delay: 100 },
      { type: "output", text: "  [2] One Piece Colored (mangadex, manganato) - 1076 chapters", delay: 80 },
      { type: "output", text: "  [3] One Piece Digital Colored (mangakatana) - 1055 chapters", delay: 80 },
      { type: "output", text: "  [4] One Piece Party (mangadex) - 42 chapters", delay: 80 },
      { type: "output", text: "  [5] One Piece: Strong World (mangahere) - 2 chapters", delay: 80 },
      { type: "output", text: "", delay: 600 },
      { type: "prompt", text: "$ python main.py --mode cli --download mdx_a1c7c817 --format epub --chapters 1-100", delay: 1200 },
      { type: "output", text: "", delay: 300 },
      { type: "dim", text: "  [Aggregator] mangadex: added 100 chapters", delay: 400 },
      { type: "dim", text: "  [Aggregator] One Piece: 100 chapters (ch.1-100) from mangadex", delay: 200 },
      { type: "output", text: "", delay: 300 },
      { type: "accent", text: "  [Download] Starting: One Piece", delay: 200 },
      { type: "output", text: "  [Download] One Piece: 100 chapters to download", delay: 100 },
      { type: "dim", text: "  [Download] One Piece Ch.1 from mangadex", delay: 80 },
      { type: "dim", text: "  [Download] One Piece Ch.2 from mangadex", delay: 60 },
      { type: "dim", text: "  [Download] One Piece Ch.3 from mangadex", delay: 60 },
      { type: "dim", text: "  ...", delay: 200 },
      { type: "dim", text: "  [Download] One Piece Ch.100 from mangadex", delay: 60 },
      { type: "output", text: "", delay: 300 },
      { type: "accent", text: "  [Download] Converting One Piece to epub", delay: 400 },
      { type: "success", text: "  [Download] Complete: One Piece -> ~/Mangadeck/One Piece/One Piece.epub", delay: 300 },
      { type: "output", text: "", delay: 200 },
      { type: "success", text: "  Done. 100 chapters downloaded in 47s.", delay: 0 },
    ];

    var started = false;

    function startTyping() {
      if (started) return;
      started = true;
      var lineIndex = 0;
      var totalDelay = 0;

      function addLine(i) {
        if (i >= lines.length) return;
        var line = lines[i];
        totalDelay += line.delay;

        setTimeout(function () {
          var div = document.createElement("div");

          if (line.type === "prompt") {
            // Typing animation for prompts
            var textContent = line.text;
            var promptSpan = document.createElement("span");
            promptSpan.className = "t-prompt";
            promptSpan.textContent = "$ ";
            div.appendChild(promptSpan);
            var cmdSpan = document.createElement("span");
            cmdSpan.className = "t-cmd";
            div.appendChild(cmdSpan);
            container.appendChild(div);

            // Type out command
            var cmdText = textContent.substring(2); // Remove "$ "
            var charIdx = 0;
            var typeInterval = setInterval(function () {
              if (charIdx < cmdText.length) {
                cmdSpan.textContent += cmdText[charIdx];
                charIdx++;
                scrollTerminal();
              } else {
                clearInterval(typeInterval);
              }
            }, 18);
          } else {
            div.className = "t-" + line.type;
            div.textContent = line.text;
            container.appendChild(div);
          }

          scrollTerminal();
          addLine(i + 1);
        }, totalDelay);
      }

      addLine(0);
    }

    function scrollTerminal() {
      var body = document.getElementById("terminal-body");
      if (body) body.scrollTop = body.scrollHeight;
    }

    // Start when terminal is visible
    function checkVisible() {
      var wrap = document.querySelector(".terminal-wrap");
      if (!wrap) return;
      var rect = wrap.getBoundingClientRect();
      if (rect.top < window.innerHeight * .75) {
        startTyping();
        window.removeEventListener("scroll", checkVisible);
      }
    }
    checkVisible();
    window.addEventListener("scroll", checkVisible);
  }

  /* ═══ SMOOTH ANCHOR ═══ */
  function initSmoothScroll() {
    var links = document.querySelectorAll('a[href^="#"]');
    for (var i = 0; i < links.length; i++) {
      links[i].addEventListener("click", function (e) {
        var href = this.getAttribute("href");
        if (href === "#") return;
        var target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          var top = target.getBoundingClientRect().top + window.pageYOffset - 60;
          window.scrollTo({ top: top, behavior: "smooth" });
        }
      });
    }
  }

  /* ═══ INIT ═══ */
  function init() {
    initHeroParticles();
    initParallax();
    initNav();
    initReveal();
    initCountUp();
    initTerminal();
    initSmoothScroll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
