/* ═══════════════════════════════════════════════
   Mangadeck — Complete Dashboard JS
   Fixed: search relevance, thumbnail loading,
   modal, downloads, cart, queue, settings, SSE
   ═══════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ─── State ─── */
  const S = {
    tab: "home",
    searchPage: 1,
    discoverPage: 1,
    config: {},
    sse: null,
    completedTasks: new Set(),
    homeLoaded: false,
    modalManga: null,
    modalChapters: [],
    modalVolumes: {},
    modalSelectedChapters: new Set(),
    modalSelectedVolumes: new Set(),
    modalMode: "chapter",
  };

  /* ─── DOM helpers ─── */
  const $ = (sel, ctx) => (ctx || document).querySelector(sel);
  const $$ = (sel, ctx) => [...(ctx || document).querySelectorAll(sel)];

  function ce(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  function esc(str) {
    const d = document.createElement("div");
    d.textContent = str || "";
    return d.innerHTML;
  }

  /* ─── API fetch wrapper ─── */
  async function api(path, opts) {
    opts = opts || {};
    const headers = { "Content-Type": "application/json" };
    if (opts.headers) Object.assign(headers, opts.headers);
    opts.headers = headers;
    try {
      const resp = await fetch(path, opts);
      if (!resp.ok) {
        const text = await resp.text();
        try { return JSON.parse(text); } catch (e) { return { error: text }; }
      }
      return await resp.json();
    } catch (err) {
      return { error: String(err) };
    }
  }

  /* ─── Formatters ─── */
  function fmtBytes(b) {
    if (!b || b <= 0) return "0 B";
    if (b < 1024) return b + " B";
    if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
    return (b / 1048576).toFixed(1) + " MB";
  }

  function fmtTime(s) {
    if (!s || s <= 0) return "--";
    if (s < 60) return Math.round(s) + "s";
    return Math.floor(s / 60) + "m " + Math.round(s % 60) + "s";
  }

  function chStr(n) {
    if (n === undefined || n === null) return "?";
    return n === Math.floor(n) ? String(Math.floor(n)) : String(n);
  }

  /* ─── Cover proxy ─── */
  function coverUrl(url) {
    if (!url || typeof url !== "string") return "";
    // Already proxied
    if (url.startsWith("/api/proxy")) return url;
    return "/api/proxy/image?url=" + encodeURIComponent(url);
  }

  function coverImg(url, cls) {
    cls = cls || "";
    const src = coverUrl(url);
    if (!src) {
      return `<div class="${cls}" style="background:var(--bg-3);width:100%;height:100%"></div>`;
    }
    return `<img class="${cls}" src="${src}" alt="" loading="lazy"
      onerror="this.onerror=null;this.style.display='none';this.parentElement.style.background='var(--bg-3)'"
    />`;
  }

  /* ─── Debounce ─── */
  function debounce(fn, ms) {
    let timer;
    return function () {
      const args = arguments;
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  /* ─── Range parser ─── */
  function parseRange(str) {
    if (!str || !str.trim()) return null;
    const result = [];
    const parts = str.split(",");
    for (let i = 0; i < parts.length; i++) {
      const p = parts[i].trim();
      if (!p) continue;
      if (p.indexOf("-") !== -1) {
        const sides = p.split("-");
        const a = parseFloat(sides[0]);
        const b = parseFloat(sides[1]);
        if (isNaN(a) || isNaN(b)) continue;
        const lo = Math.min(a, b);
        const hi = Math.max(a, b);
        for (let n = Math.floor(lo); n <= Math.ceil(hi); n++) {
          result.push(n);
        }
      } else {
        const n = parseFloat(p);
        if (!isNaN(n)) result.push(n);
      }
    }
    return result.length > 0 ? [...new Set(result)].sort((a, b) => a - b) : null;
  }

  /* ═══════════════════════════════════
     PARTICLES
     ═══════════════════════════════════ */
  function initParticles(canvasId, count, color, maxAlpha, speed) {
    const canvas = $(canvasId);
    if (!canvas) return null;
    const parent = canvas.parentElement;
    if (!parent) return null;
    const ctx = canvas.getContext("2d");
    let w = 0;
    let h = 0;
    const particles = [];
    let running = true;

    function resize() {
      const rect = parent.getBoundingClientRect();
      w = canvas.width = Math.max(rect.width, 100);
      h = canvas.height = Math.max(rect.height, 100);
    }
    resize();
    window.addEventListener("resize", resize);

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 1.5 + 0.5,
        vx: (Math.random() - 0.5) * speed,
        vy: (Math.random() - 0.5) * speed,
        a: Math.random() * maxAlpha,
        da: (Math.random() - 0.5) * 0.004,
      });
    }

    function draw() {
      if (!running) return;
      ctx.clearRect(0, 0, w, h);
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.a += p.da;
        if (p.a > maxAlpha || p.a < 0.02) p.da *= -1;
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = color.replace("A", Math.max(0, p.a).toFixed(3));
        ctx.fill();
      }
      // Connection lines
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = color.replace("A", ((1 - dist / 100) * 0.08).toFixed(3));
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);
    return function stop() { running = false; };
  }

  /* ═══════════════════════════════════
     TOAST
     ═══════════════════════════════════ */
  function toast(msg, type) {
    type = type || "info";
    const icons = { success: "check_circle", error: "error", info: "info" };
    const container = $("#toasts");
    if (!container) return;
    const t = ce("div", "toast " + type,
      '<span class="material-icons-outlined">' + (icons[type] || "info") + "</span>" +
      "<span>" + esc(msg) + "</span>"
    );
    container.appendChild(t);
    setTimeout(function () {
      t.classList.add("removing");
      setTimeout(function () { t.remove(); }, 300);
    }, 4500);
  }

  /* ═══════════════════════════════════
     CONFETTI
     ═══════════════════════════════════ */
  function launchConfetti() {
    const canvas = $("#confetti-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const pieces = [];
    const colors = ["#4a8fe7", "#3dd68c", "#e7974a", "#e7524a", "#e7d94a", "#9c6ae7"];
    for (let i = 0; i < 160; i++) {
      pieces.push({
        x: Math.random() * canvas.width,
        y: Math.random() * -canvas.height,
        w: Math.random() * 10 + 4,
        h: Math.random() * 6 + 3,
        c: colors[Math.floor(Math.random() * colors.length)],
        vx: (Math.random() - 0.5) * 5,
        vy: Math.random() * 4 + 2,
        rot: Math.random() * 360,
        rv: (Math.random() - 0.5) * 10,
        o: 1,
      });
    }
    let frame = 0;
    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      let alive = false;
      for (let i = 0; i < pieces.length; i++) {
        const p = pieces[i];
        if (p.o <= 0) continue;
        alive = true;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rot * Math.PI) / 180);
        ctx.globalAlpha = p.o;
        ctx.fillStyle = p.c;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.06;
        p.rot += p.rv;
        if (frame > 90) p.o -= 0.012;
      }
      frame++;
      if (alive && frame < 220) {
        requestAnimationFrame(draw);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
    requestAnimationFrame(draw);
  }

  /* ═══════════════════════════════════
     SKELETON LOADERS
     ═══════════════════════════════════ */
  function skeletonGrid(container, count) {
    count = count || 12;
    container.innerHTML = "";
    for (let i = 0; i < count; i++) {
      container.appendChild(ce("div", "skeleton-card",
        '<div class="skel skel-cover"></div>' +
        '<div class="skeleton-card-body">' +
        '<div class="skel skel-line w80"></div>' +
        '<div class="skel skel-line w40"></div>' +
        "</div>"
      ));
    }
  }

  function skeletonScroll(container, count) {
    count = count || 8;
    container.innerHTML = "";
    for (let i = 0; i < count; i++) {
      container.appendChild(ce("div", "skeleton-card",
        '<div class="skel skel-cover"></div>' +
        '<div class="skeleton-card-body">' +
        '<div class="skel skel-line w80"></div>' +
        '</div>'
      ));
    }
  }

  /* ═══════════════════════════════════
     MANGA CARD
     ═══════════════════════════════════ */
  function mangaCard(manga) {
    const card = ce("div", "manga-card");
    const srcList = manga.sources || [manga.source || ""];
    const coverSrc = coverUrl(manga.cover_url);
    const statusChip = manga.status === "ongoing"
      ? '<span class="chip chip-green">ongoing</span>'
      : manga.status === "completed"
        ? '<span class="chip chip-orange">completed</span>'
        : "";

    card.innerHTML =
      '<div class="manga-card-cover-wrap">' +
        (coverSrc
          ? '<img class="manga-card-cover" src="' + coverSrc + '" alt="" loading="lazy" ' +
            'onerror="this.onerror=null;this.style.display=\'none\';this.parentElement.style.background=\'var(--bg-3)\'" />'
          : '<div class="manga-card-cover" style="background:var(--bg-3)"></div>') +
        '<div class="manga-card-overlay"></div>' +
        '<div class="manga-card-actions">' +
          '<button class="card-action-btn btn-cart" title="Add to cart">' +
            '<span class="material-icons-outlined">add_shopping_cart</span></button>' +
          '<button class="card-action-btn btn-quick-dl" title="Download">' +
            '<span class="material-icons-outlined">download</span></button>' +
        '</div>' +
      '</div>' +
      '<div class="manga-card-body">' +
        '<div class="manga-card-title">' + esc(manga.title) + '</div>' +
        '<div class="manga-card-meta">' +
          '<span class="chip chip-accent">' + (manga.type || "manga") + '</span>' +
          statusChip +
        '</div>' +
      '</div>';

    card.addEventListener("click", function (e) {
      if (e.target.closest(".card-action-btn")) return;
      openModal(manga);
    });

    var cartBtn = card.querySelector(".btn-cart");
    if (cartBtn) {
      cartBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        addToCart(manga);
      });
    }

    var dlBtn = card.querySelector(".btn-quick-dl");
    if (dlBtn) {
      dlBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        quickDownload(manga);
      });
    }

    return card;
  }

  /* ═══════════════════════════════════
     TAB NAVIGATION
     ═══════════════════════════════════ */
  function initTabs() {
    $$(".nav-item").forEach(function (n) {
      n.addEventListener("click", function () {
        switchTab(n.dataset.tab);
      });
    });
    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-goto]");
      if (btn) switchTab(btn.dataset.goto);
    });
  }

  function switchTab(tab) {
    S.tab = tab;
    $$(".nav-item").forEach(function (n) {
      n.classList.toggle("active", n.dataset.tab === tab);
    });
    $$(".tab-panel").forEach(function (p) {
      p.classList.toggle("active", p.id === "tab-" + tab);
    });
    var sidebar = $("#sidebar");
    if (sidebar) sidebar.classList.remove("open");

    switch (tab) {
      case "home": loadHome(); break;
      case "discover": loadDiscover(); break;
      case "search": break; // don't auto-search
      case "downloads": refreshDownloads(); break;
      case "cart": refreshCart(); break;
      case "queue": refreshQueue(); break;
      case "sources": loadSources(); break;
      case "logs": loadLogs(); break;
      case "settings": loadSettings(); break;
    }
  }

  /* ═══════════════════════════════════
     HOME PAGE
     ═══════════════════════════════════ */
  async function loadHome() {
    if (S.homeLoaded) return;
    S.homeLoaded = true;

    var scroll = $("#home-trending");
    if (scroll) skeletonScroll(scroll, 8);

    try {
      var data = await api("/api/trending?lang=en&page=1");
      if (scroll) {
        scroll.innerHTML = "";
        if (data.results && data.results.length > 0) {
          var items = data.results.slice(0, 15);
          for (var i = 0; i < items.length; i++) {
            scroll.appendChild(mangaCard(items[i]));
          }
        } else {
          scroll.innerHTML = '<p style="color:var(--text-3);padding:20px;font-size:.85rem">No trending data available</p>';
        }
      }
    } catch (e) {
      if (scroll) scroll.innerHTML = '<p style="color:var(--text-3);padding:20px;font-size:.85rem">Could not load trending</p>';
    }

    updateHomeStats();
  }

  async function updateHomeStats() {
    try {
      var sys = await api("/api/system");
      if (sys.error) return;
      var dl = sys.download_stats || {};
      var q = sys.queue_stats || {};
      var fmtEl = $("#home-format");
      if (fmtEl) fmtEl.textContent = (S.config.default_format || "cbz").toUpperCase();
      var dlEl = $("#home-download-count");
      if (dlEl) dlEl.textContent = String((dl.complete || 0) + (dl.active || 0));
      var cartEl = $("#home-cart-count");
      if (cartEl) cartEl.textContent = String(q.cart_count || 0);
    } catch (e) { /* ignore */ }
  }

  /* ═══════════════════════════════════
     DISCOVER / TRENDING
     ═══════════════════════════════════ */
  async function loadDiscover() {
    var grid = $("#discover-grid");
    if (!grid) return;
    skeletonGrid(grid);

    var langSel = $("#discover-lang");
    var lang = langSel ? langSel.value : "en";

    try {
      var data = await api("/api/trending?lang=" + encodeURIComponent(lang) + "&page=" + S.discoverPage);
      grid.innerHTML = "";
      if (data.results && data.results.length > 0) {
        for (var i = 0; i < data.results.length; i++) {
          grid.appendChild(mangaCard(data.results[i]));
        }
      } else {
        grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1">' +
          '<span class="material-icons-outlined">explore_off</span>' +
          '<p>No trending manga found</p></div>';
      }
    } catch (e) {
      grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1">' +
        '<span class="material-icons-outlined">error</span>' +
        '<p>Failed to load trending</p></div>';
    }
  }

  /* ═══════════════════════════════════
     SEARCH — FIXED
     ═══════════════════════════════════ */
  async function doSearch(queryOverride) {
    var searchInput = $("#search-input");
    var query = queryOverride || (searchInput ? searchInput.value.trim() : "");
    if (!query) return;

    // Sync the input value
    if (searchInput) searchInput.value = query;

    var grid = $("#search-results");
    var empty = $("#search-empty");
    if (!grid) return;

    if (empty) empty.classList.add("hidden");
    skeletonGrid(grid);

    var langSel = $("#search-lang");
    var lang = langSel ? langSel.value : "en";

    // Build URL with properly encoded query
    var url = "/api/search?q=" + encodeURIComponent(query) +
              "&lang=" + encodeURIComponent(lang) +
              "&page=" + S.searchPage;

    try {
      var data = await api(url);

      grid.innerHTML = "";

      if (data.error) {
        toast("Search error: " + data.error, "error");
        if (empty) {
          empty.classList.remove("hidden");
          var emptyP = empty.querySelector("p");
          if (emptyP) emptyP.textContent = "Search failed. Try again.";
        }
        return;
      }

      if (!data.results || data.results.length === 0) {
        if (empty) {
          empty.classList.remove("hidden");
          var emptyP2 = empty.querySelector("p");
          if (emptyP2) emptyP2.textContent = 'No results for "' + query + '"';
        }
        return;
      }

      for (var i = 0; i < data.results.length; i++) {
        grid.appendChild(mangaCard(data.results[i]));
      }

      toast("Found " + data.count + " results for \"" + query + "\"", "info");
    } catch (e) {
      grid.innerHTML = "";
      toast("Search failed: " + String(e), "error");
    }
  }

  /* ═══════════════════════════════════
     MANGA DETAIL MODAL — FULL
     ═══════════════════════════════════ */
  async function openModal(manga) {
    var modal = $("#manga-modal");
    var body = $("#modal-body");
    if (!modal || !body) return;

    modal.classList.remove("hidden");

    S.modalManga = manga;
    S.modalChapters = [];
    S.modalVolumes = {};
    S.modalSelectedChapters = new Set();
    S.modalSelectedVolumes = new Set();
    S.modalMode = "chapter";

    // Loading skeleton
    body.innerHTML =
      '<div style="display:flex;gap:24px">' +
        '<div class="skel" style="width:180px;height:260px;border-radius:12px;flex-shrink:0"></div>' +
        '<div style="flex:1">' +
          '<div class="skel skel-line w80"></div>' +
          '<div class="skel skel-line w60"></div>' +
          '<div class="skel skel-line w40"></div>' +
          '<div class="skel skel-line w80" style="margin-top:20px"></div>' +
        '</div>' +
      '</div>';

    try {
      var source = manga.source || "";
      var detailUrl = "/api/manga/" + encodeURIComponent(manga.id);
      if (source) detailUrl += "?source=" + encodeURIComponent(source);

      var detail = await api(detailUrl);

      if (!detail || detail.error) {
        body.innerHTML = '<p style="color:var(--text-2)">Failed to load manga details.</p>';
        return;
      }

      // Merge data
      S.modalManga = Object.assign({}, manga, detail);
      var m = S.modalManga;

      var coverSrc = coverUrl(m.cover_url || manga.cover_url);
      var chCount = (m.chapters ? m.chapters.length : 0) || m.chapter_count || 0;
      var dir = m.reading_direction || "rtl";
      var lang = S.config.language || "en";
      var sourceIds = JSON.stringify(m.source_ids || manga.source_ids || {});
      var titleEnc = encodeURIComponent(m.title || "");

      // Start async loads
      var chaptersUrl = "/api/manga/" + encodeURIComponent(manga.id) + "/chapters" +
        "?lang=" + encodeURIComponent(lang) +
        "&aggregate=true" +
        "&title=" + titleEnc +
        "&source_ids=" + encodeURIComponent(sourceIds);

      var volumesUrl = "/api/manga/" + encodeURIComponent(manga.id) + "/volumes" +
        "?lang=" + encodeURIComponent(lang) +
        "&title=" + titleEnc +
        "&source_ids=" + encodeURIComponent(sourceIds);

      var chaptersPromise = api(chaptersUrl);
      var volumesPromise = api(volumesUrl);

      // Build sources display
      var sourcesArr = m.sources || [m.source || ""];
      var sourcesHtml = "";
      for (var si = 0; si < sourcesArr.length; si++) {
        if (sourcesArr[si]) sourcesHtml += '<span class="chip">' + esc(sourcesArr[si]) + '</span>';
      }

      var authorsHtml = "";
      if (m.authors && m.authors.length > 0) {
        authorsHtml = '<p style="color:var(--text-2);font-size:.8rem;margin-top:4px">' +
          esc(m.authors.join(", ")) + '</p>';
      }

      // Build modal HTML
      body.innerHTML =
        '<div class="detail-top">' +
          (coverSrc
            ? '<img class="detail-cover" src="' + coverSrc + '" alt="" ' +
              'onerror="this.onerror=null;this.style.background=\'var(--bg-3)\';this.src=\'\'" />'
            : '<div class="detail-cover" style="background:var(--bg-3)"></div>') +
          '<div class="detail-info">' +
            '<h2 class="detail-title">' + esc(m.title) + '</h2>' +
            '<div class="detail-meta">' +
              '<span class="chip chip-accent">' + esc(m.type || "manga") + '</span>' +
              '<span class="chip">' + esc(m.status || "unknown") + '</span>' +
              '<span class="chip" id="modal-ch-total">' + chCount + ' ch.</span>' +
              '<span class="chip">' + esc(dir) + '</span>' +
              sourcesHtml +
            '</div>' +
            authorsHtml +
            '<p class="detail-desc">' + esc((m.description || "").substring(0, 300)) + '</p>' +

            '<!-- Quick download bar -->' +
            '<div class="quick-dl-bar">' +
              '<div class="quick-dl-row">' +
                '<div class="field-group">' +
                  '<label class="field-label">Format</label>' +
                  '<select id="modal-format" class="field-select field-sm">' +
                    '<option value="cbz">CBZ</option>' +
                    '<option value="epub">EPUB</option>' +
                    '<option value="pdf">PDF</option>' +
                    '<option value="images">Images</option>' +
                  '</select>' +
                '</div>' +
                '<div class="field-group">' +
                  '<label class="field-label">Chapters</label>' +
                  '<input id="modal-ch-input" type="text" class="field-input field-sm range-input" placeholder="e.g. 1-50, 100-200" autocomplete="off"/>' +
                '</div>' +
                '<div class="field-group">' +
                  '<label class="field-label">Volumes</label>' +
                  '<input id="modal-vol-input" type="text" class="field-input field-sm range-input" placeholder="e.g. 1-10" autocomplete="off"/>' +
                '</div>' +
              '</div>' +
              '<div class="quick-dl-hint" id="modal-range-hint">' +
                'Leave blank to download all. Accepts: 1-50 | 1,3,5 | 1-10,20-30' +
              '</div>' +
              '<div class="quick-dl-actions">' +
                '<button id="modal-download-range" class="btn btn-primary">' +
                  '<span class="material-icons-outlined">download</span> Download' +
                '</button>' +
                '<button id="modal-add-cart-range" class="btn btn-outline">' +
                  '<span class="material-icons-outlined">add_shopping_cart</span> Add to cart' +
                '</button>' +
              '</div>' +
            '</div>' +

            '<!-- Browse toggle -->' +
            '<div class="browse-toggle">' +
              '<span class="browse-toggle-label">Browse and select:</span>' +
              '<button id="modal-mode-chapter" class="btn btn-sm btn-primary">' +
                '<span class="material-icons-outlined">format_list_numbered</span> Chapters</button>' +
              '<button id="modal-mode-volume" class="btn btn-sm btn-outline">' +
                '<span class="material-icons-outlined">library_books</span> Volumes</button>' +
              '<button id="modal-select-all" class="btn btn-outline btn-sm">' +
                '<span class="material-icons-outlined">select_all</span> All</button>' +
              '<button id="modal-select-none" class="btn btn-outline btn-sm">' +
                '<span class="material-icons-outlined">deselect</span> None</button>' +
            '</div>' +

            '<div id="modal-selection-info" class="modal-selection-info"></div>' +

            '<div class="detail-actions" id="modal-browse-actions" style="display:none">' +
              '<button id="modal-download-sel" class="btn btn-primary">' +
                '<span class="material-icons-outlined">download</span> Download selected</button>' +
            '</div>' +

          '</div>' +
        '</div>' +

        '<!-- Chapter/volume browser -->' +
        '<div id="modal-browser-header" class="browser-header">' +
          '<h4 class="detail-section-title" style="margin:0;border:none;padding:0;flex:1">' +
            '<span id="modal-browser-title">Chapters</span>' +
            '<span id="modal-browser-loading" class="browser-loading">loading from all sources...</span>' +
          '</h4>' +
        '</div>' +
        '<div id="modal-browser" class="chapter-list" style="max-height:400px">' +
          '<div class="browser-spinner">' +
            '<span class="material-icons-outlined spinning">sync</span>' +
            '<p>Loading chapters from all sources...</p>' +
          '</div>' +
        '</div>';

      // Set default format
      var fmtSel = $("#modal-format");
      if (fmtSel && S.config.default_format) {
        fmtSel.value = S.config.default_format;
      }

      // Wire range hint
      var chInput = $("#modal-ch-input");
      var volInput = $("#modal-vol-input");
      var hintEl = $("#modal-range-hint");

      function updateHint() {
        if (!hintEl || !chInput || !volInput) return;
        var chText = chInput.value.trim();
        var volText = volInput.value.trim();

        if (!chText && !volText) {
          hintEl.textContent = "Leave blank to download all. Accepts: 1-50 | 1,3,5 | 1-10,20-30";
          hintEl.className = "quick-dl-hint";
          return;
        }

        var parts = [];
        if (chText) {
          var parsed = parseRange(chText);
          if (parsed) {
            parts.push(parsed.length + " chapter(s): " + chStr(parsed[0]) + "-" + chStr(parsed[parsed.length - 1]));
          } else {
            hintEl.textContent = "Invalid chapter range";
            hintEl.className = "quick-dl-hint hint-error";
            return;
          }
        }
        if (volText) {
          var parsed2 = parseRange(volText);
          if (parsed2) {
            parts.push(parsed2.length + " volume(s)");
          } else {
            hintEl.textContent = "Invalid volume range";
            hintEl.className = "quick-dl-hint hint-error";
            return;
          }
        }
        hintEl.textContent = parts.join(" + ");
        hintEl.className = "quick-dl-hint hint-active";
      }

      if (chInput) chInput.addEventListener("input", updateHint);
      if (volInput) volInput.addEventListener("input", updateHint);

      // Wire download/cart buttons
      var dlRangeBtn = $("#modal-download-range");
      if (dlRangeBtn) {
        dlRangeBtn.addEventListener("click", function () {
          var chR = chInput ? parseRange(chInput.value) : null;
          var volR = volInput ? parseRange(volInput.value) : null;
          downloadWithRange(S.modalManga, chR, volR);
        });
      }

      var cartRangeBtn = $("#modal-add-cart-range");
      if (cartRangeBtn) {
        cartRangeBtn.addEventListener("click", function () {
          var chR = chInput ? parseRange(chInput.value) : null;
          var volR = volInput ? parseRange(volInput.value) : null;
          addToCartWithRange(S.modalManga, chR, volR);
          modal.classList.add("hidden");
        });
      }

      // Wire browse mode
      var modeChBtn = $("#modal-mode-chapter");
      var modeVolBtn = $("#modal-mode-volume");
      var selectAllBtn = $("#modal-select-all");
      var selectNoneBtn = $("#modal-select-none");
      var dlSelBtn = $("#modal-download-sel");

      if (modeChBtn) modeChBtn.addEventListener("click", function () { setModalMode("chapter"); });
      if (modeVolBtn) modeVolBtn.addEventListener("click", function () { setModalMode("volume"); });
      if (selectAllBtn) selectAllBtn.addEventListener("click", selectAll);
      if (selectNoneBtn) selectNoneBtn.addEventListener("click", selectNone);
      if (dlSelBtn) dlSelBtn.addEventListener("click", downloadSelected);

      // Load aggregated chapters
      try {
        var chData = await chaptersPromise;
        if (chData && !chData.error) {
          S.modalChapters = chData.chapters || [];
          var totalEl = $("#modal-ch-total");
          if (totalEl) totalEl.textContent = S.modalChapters.length + " ch.";
          var loadEl = $("#modal-browser-loading");
          if (loadEl) {
            var srcCount = chData.source_map ? Object.keys(chData.source_map).length : 1;
            loadEl.textContent = S.modalChapters.length + " from " + srcCount + " source(s)";
            loadEl.classList.add("loaded");
          }
          // Update placeholder
          if (chInput && S.modalChapters.length > 0) {
            var first = S.modalChapters[0].chapter_number;
            var last = S.modalChapters[S.modalChapters.length - 1].chapter_number;
            chInput.placeholder = chStr(first) + "-" + chStr(last) + " (" + S.modalChapters.length + " available)";
          }
        } else {
          S.modalChapters = detail.chapters || [];
        }
      } catch (e) {
        S.modalChapters = detail.chapters || [];
        var loadEl2 = $("#modal-browser-loading");
        if (loadEl2) {
          loadEl2.textContent = "primary source only";
          loadEl2.classList.add("warn");
        }
      }

      // Load volumes
      try {
        var volData = await volumesPromise;
        if (volData && !volData.error) {
          S.modalVolumes = volData.volumes || {};
        } else {
          buildVolumesFromChapters();
        }
      } catch (e) {
        buildVolumesFromChapters();
      }

      // Update volume placeholder
      if (volInput) {
        var volKeys = Object.keys(S.modalVolumes).filter(function (k) { return k !== "none"; });
        volKeys.sort(function (a, b) { return parseFloat(a) - parseFloat(b); });
        if (volKeys.length > 0) {
          volInput.placeholder = volKeys[0] + "-" + volKeys[volKeys.length - 1] + " (" + volKeys.length + " volumes)";
        }
      }

      renderBrowser();

    } catch (e) {
      body.innerHTML = '<p style="color:var(--text-2)">Error loading: ' + esc(String(e)) + '</p>';
    }
  }

  function buildVolumesFromChapters() {
    S.modalVolumes = {};
    for (var i = 0; i < S.modalChapters.length; i++) {
      var ch = S.modalChapters[i];
      var v = ch.volume_number;
      var key;
      if (v != null && v !== undefined) {
        key = v === Math.floor(v) ? String(Math.floor(v)) : String(v);
      } else {
        key = "none";
      }
      if (!S.modalVolumes[key]) S.modalVolumes[key] = [];
      S.modalVolumes[key].push(ch);
    }
  }

  /* ─── Modal mode switching ─── */
  function setModalMode(mode) {
    S.modalMode = mode;
    S.modalSelectedChapters.clear();
    S.modalSelectedVolumes.clear();

    var chBtn = $("#modal-mode-chapter");
    var volBtn = $("#modal-mode-volume");
    if (chBtn) chBtn.className = mode === "chapter" ? "btn btn-primary btn-sm" : "btn btn-outline btn-sm";
    if (volBtn) volBtn.className = mode === "volume" ? "btn btn-primary btn-sm" : "btn btn-outline btn-sm";

    var titleEl = $("#modal-browser-title");
    if (titleEl) titleEl.textContent = mode === "chapter" ? "Chapters" : "Volumes";

    var browseActions = $("#modal-browse-actions");
    if (browseActions) browseActions.style.display = "flex";

    renderBrowser();
    updateSelectionInfo();
  }

  /* ─── Browser rendering ─── */
  function renderBrowser() {
    var container = $("#modal-browser");
    if (!container) return;
    container.innerHTML = "";

    if (S.modalMode === "chapter") {
      renderChapterBrowser(container);
    } else {
      renderVolumeBrowser(container);
    }
  }

  function renderChapterBrowser(container) {
    if (!S.modalChapters.length) {
      container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-3)">No chapters found</div>';
      return;
    }

    for (var i = 0; i < S.modalChapters.length; i++) {
      var ch = S.modalChapters[i];
      var num = ch.chapter_number;
      var ns = chStr(num);
      var selected = S.modalSelectedChapters.has(num);

      var row = ce("div", "chapter-row" + (selected ? " ch-selected" : ""),
        '<label class="ch-check-wrap">' +
          '<input type="checkbox" class="ch-check" data-num="' + num + '"' + (selected ? " checked" : "") + '/>' +
        '</label>' +
        '<span class="chapter-num">Ch. ' + ns + '</span>' +
        '<span class="chapter-title">' + esc(ch.title || "") + '</span>' +
        '<span class="chapter-source">' + esc(ch.source || "") + '</span>'
      );

      (function (row, num) {
        var cb = row.querySelector(".ch-check");
        cb.addEventListener("change", function () {
          if (cb.checked) {
            S.modalSelectedChapters.add(num);
            row.classList.add("ch-selected");
          } else {
            S.modalSelectedChapters.delete(num);
            row.classList.remove("ch-selected");
          }
          updateSelectionInfo();
        });
        row.addEventListener("click", function (e) {
          if (e.target.tagName === "INPUT") return;
          cb.checked = !cb.checked;
          cb.dispatchEvent(new Event("change"));
        });
      })(row, num);

      container.appendChild(row);
    }
  }

  function renderVolumeBrowser(container) {
    var keys = Object.keys(S.modalVolumes);
    keys.sort(function (a, b) {
      if (a === "none") return 1;
      if (b === "none") return -1;
      return parseFloat(a) - parseFloat(b);
    });

    if (!keys.length) {
      container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-3)">No volume data</div>';
      return;
    }

    for (var k = 0; k < keys.length; k++) {
      var key = keys[k];
      var chs = S.modalVolumes[key] || [];
      var label = key === "none" ? "No volume" : "Volume " + key;
      var selected = S.modalSelectedVolumes.has(key);
      var rangeText = chs.length > 0
        ? "Ch. " + chStr(chs[0].chapter_number) + " - " + chStr(chs[chs.length - 1].chapter_number)
        : "";

      var chRows = "";
      for (var ci = 0; ci < chs.length; ci++) {
        chRows +=
          '<div class="vol-ch-row">' +
            '<span class="chapter-num">Ch. ' + chStr(chs[ci].chapter_number) + '</span>' +
            '<span class="chapter-title">' + esc(chs[ci].title || "") + '</span>' +
            '<span class="chapter-source">' + esc(chs[ci].source || "") + '</span>' +
          '</div>';
      }

      var card = ce("div", "volume-card" + (selected ? " vol-selected" : ""),
        '<div class="vol-header">' +
          '<label class="ch-check-wrap">' +
            '<input type="checkbox" class="vol-check" data-vol="' + esc(key) + '"' + (selected ? " checked" : "") + '/>' +
          '</label>' +
          '<div class="vol-info">' +
            '<span class="vol-label">' + esc(label) + '</span>' +
            '<span class="vol-range">' + rangeText + '</span>' +
          '</div>' +
          '<span class="vol-count">' + chs.length + ' ch.</span>' +
          '<button class="vol-expand-btn"><span class="material-icons-outlined">expand_more</span></button>' +
        '</div>' +
        '<div class="vol-chapters hidden">' + chRows + '</div>'
      );

      (function (card, key) {
        var cb = card.querySelector(".vol-check");
        cb.addEventListener("change", function () {
          if (cb.checked) {
            S.modalSelectedVolumes.add(key);
            card.classList.add("vol-selected");
          } else {
            S.modalSelectedVolumes.delete(key);
            card.classList.remove("vol-selected");
          }
          updateSelectionInfo();
        });

        var header = card.querySelector(".vol-header");
        header.addEventListener("click", function (e) {
          if (e.target.tagName === "INPUT" || e.target.closest(".vol-expand-btn")) return;
          cb.checked = !cb.checked;
          cb.dispatchEvent(new Event("change"));
        });

        var expandBtn = card.querySelector(".vol-expand-btn");
        var chapDiv = card.querySelector(".vol-chapters");
        expandBtn.addEventListener("click", function (e) {
          e.stopPropagation();
          chapDiv.classList.toggle("hidden");
          var icon = expandBtn.querySelector(".material-icons-outlined");
          icon.textContent = chapDiv.classList.contains("hidden") ? "expand_more" : "expand_less";
        });
      })(card, key);

      container.appendChild(card);
    }
  }

  /* ─── Selection helpers ─── */
  function selectAll() {
    if (S.modalMode === "chapter") {
      S.modalSelectedChapters.clear();
      for (var i = 0; i < S.modalChapters.length; i++) {
        S.modalSelectedChapters.add(S.modalChapters[i].chapter_number);
      }
      $$(".ch-check").forEach(function (cb) {
        cb.checked = true;
        var row = cb.closest(".chapter-row");
        if (row) row.classList.add("ch-selected");
      });
    } else {
      S.modalSelectedVolumes.clear();
      Object.keys(S.modalVolumes).forEach(function (k) { S.modalSelectedVolumes.add(k); });
      $$(".vol-check").forEach(function (cb) {
        cb.checked = true;
        var card = cb.closest(".volume-card");
        if (card) card.classList.add("vol-selected");
      });
    }
    updateSelectionInfo();
  }

  function selectNone() {
    S.modalSelectedChapters.clear();
    S.modalSelectedVolumes.clear();
    $$(".ch-check, .vol-check").forEach(function (cb) { cb.checked = false; });
    $$(".ch-selected").forEach(function (el) { el.classList.remove("ch-selected"); });
    $$(".vol-selected").forEach(function (el) { el.classList.remove("vol-selected"); });
    updateSelectionInfo();
  }

  function updateSelectionInfo() {
    var el = $("#modal-selection-info");
    if (!el) return;
    if (S.modalMode === "chapter") {
      var count = S.modalSelectedChapters.size;
      if (count === 0) {
        el.textContent = "";
      } else {
        var nums = Array.from(S.modalSelectedChapters).sort(function (a, b) { return a - b; });
        el.textContent = count + " selected: " + chStr(nums[0]) + " - " + chStr(nums[nums.length - 1]);
      }
    } else {
      var count2 = S.modalSelectedVolumes.size;
      if (count2 === 0) {
        el.textContent = "";
      } else {
        el.textContent = count2 + " volume(s) selected";
      }
    }
  }

  /* ─── Download with ranges ─── */
  function volRangeToChapters(volRange) {
    if (!volRange) return null;
    var result = [];
    for (var i = 0; i < volRange.length; i++) {
      var key = String(volRange[i] === Math.floor(volRange[i]) ? Math.floor(volRange[i]) : volRange[i]);
      var chs = S.modalVolumes[key] || [];
      for (var j = 0; j < chs.length; j++) {
        result.push(chs[j].chapter_number);
      }
    }
    result.sort(function (a, b) { return a - b; });
    return result.length > 0 ? result : null;
  }

  async function downloadWithRange(manga, chapterRange, volumeRange) {
    if (!manga) return;
    var fmt = "cbz";
    var fmtSel = $("#modal-format");
    if (fmtSel) fmt = fmtSel.value;
    if (!fmt) fmt = S.config.default_format || "cbz";

    var finalRange = chapterRange;
    if (volumeRange && !chapterRange) {
      finalRange = volRangeToChapters(volumeRange);
    }

    try {
      var d = await api("/api/download", {
        method: "POST",
        body: JSON.stringify({
          manga_id: manga.id,
          title: manga.title,
          source: manga.source,
          source_ids: manga.source_ids || {},
          format: fmt,
          chapter_range: finalRange,
          volume_range: null,
          language: S.config.language || "en",
          reading_direction: manga.reading_direction,
        }),
      });
      if (d.task_id) {
        var lbl = finalRange ? finalRange.length + " chapter(s)" : "all";
        toast("Downloading " + lbl + ": " + manga.title, "success");
        switchTab("downloads");
        $("#manga-modal").classList.add("hidden");
      } else {
        toast("Failed: " + (d.error || "Unknown error"), "error");
      }
    } catch (e) {
      toast("Download failed", "error");
    }
  }

  async function addToCartWithRange(manga, chapterRange, volumeRange) {
    if (!manga) return;
    var finalRange = chapterRange;
    if (volumeRange && !chapterRange) {
      finalRange = volRangeToChapters(volumeRange);
    }
    var fmt = "cbz";
    var fmtSel = $("#modal-format");
    if (fmtSel) fmt = fmtSel.value;

    try {
      await api("/api/cart/add", {
        method: "POST",
        body: JSON.stringify({
          manga_id: manga.id,
          title: manga.title,
          source: manga.source,
          source_ids: manga.source_ids || {},
          cover_url: manga.cover_url || "",
          format: fmt,
          chapter_range: finalRange,
          language: S.config.language || "en",
          reading_direction: manga.reading_direction,
        }),
      });
      var lbl = finalRange ? finalRange.length + " ch." : "all";
      toast("Cart: " + manga.title + " (" + lbl + ")", "success");
      updateCartBadge();
    } catch (e) {
      toast("Failed to add to cart", "error");
    }
  }

  function downloadSelected() {
    var chRange = null;
    if (S.modalMode === "chapter" && S.modalSelectedChapters.size > 0) {
      chRange = Array.from(S.modalSelectedChapters).sort(function (a, b) { return a - b; });
    } else if (S.modalMode === "volume" && S.modalSelectedVolumes.size > 0) {
      chRange = [];
      S.modalSelectedVolumes.forEach(function (volKey) {
        var chs = S.modalVolumes[volKey] || [];
        for (var i = 0; i < chs.length; i++) chRange.push(chs[i].chapter_number);
      });
      chRange.sort(function (a, b) { return a - b; });
      if (!chRange.length) chRange = null;
    }
    downloadWithRange(S.modalManga, chRange, null);
  }

  async function quickDownload(manga) {
    try {
      var d = await api("/api/download", {
        method: "POST",
        body: JSON.stringify({
          manga_id: manga.id,
          title: manga.title,
          source: manga.source,
          source_ids: manga.source_ids || {},
          format: S.config.default_format || "cbz",
          language: S.config.language || "en",
          reading_direction: manga.reading_direction,
        }),
      });
      if (d.task_id) toast("Downloading: " + manga.title, "success");
      else toast("Failed: " + (d.error || ""), "error");
    } catch (e) {
      toast("Download failed", "error");
    }
  }

  /* ═══════════════════════════════════
     CART
     ═══════════════════════════════════ */
  async function addToCart(manga) {
    try {
      await api("/api/cart/add", {
        method: "POST",
        body: JSON.stringify({
          manga_id: manga.id,
          title: manga.title,
          source: manga.source,
          source_ids: manga.source_ids || {},
          cover_url: manga.cover_url || "",
          format: S.config.default_format || "cbz",
          language: S.config.language || "en",
          reading_direction: manga.reading_direction,
        }),
      });
      toast("Added: " + manga.title, "success");
      updateCartBadge();
    } catch (e) {
      toast("Failed to add to cart", "error");
    }
  }

  async function updateCartBadge() {
    try {
      var d = await api("/api/cart");
      if (d.error) return;
      var count = d.count || 0;
      var badge = $("#cart-badge");
      if (badge) {
        if (count > 0) { badge.textContent = String(count); badge.classList.remove("hidden"); }
        else badge.classList.add("hidden");
      }
      var sc = $("#stat-cart");
      if (sc) sc.textContent = String(count);
      var hc = $("#home-cart-count");
      if (hc) hc.textContent = String(count);
    } catch (e) { /* ignore */ }
  }

  async function refreshCart() {
    var list = $("#cart-list");
    var empty = $("#cart-empty");
    var countEl = $("#cart-count");
    if (!list) return;

    try {
      var d = await api("/api/cart");
      if (d.error) return;
      if (countEl) countEl.textContent = (d.count || 0) + " items";

      if (!d.items || d.items.length === 0) {
        list.innerHTML = "";
        if (empty) empty.classList.remove("hidden");
        return;
      }
      if (empty) empty.classList.add("hidden");
      list.innerHTML = "";

      for (var i = 0; i < d.items.length; i++) {
        var item = d.items[i];
        var cover = coverUrl(item.cover_url);
        var row = ce("div", "cart-item",
          (cover
            ? '<img class="cart-cover" src="' + cover + '" alt="" onerror="this.onerror=null;this.src=\'\';this.style.background=\'var(--bg-3)\'" />'
            : '<div class="cart-cover" style="background:var(--bg-3)"></div>') +
          '<div class="cart-info">' +
            '<div class="cart-title">' + esc(item.title) + '</div>' +
            '<div class="cart-details">' + esc(item.output_format || "cbz") + ' | ' + esc(item.source) + '</div>' +
          '</div>' +
          '<button class="cart-remove" data-id="' + esc(item.id) + '">' +
            '<span class="material-icons-outlined">close</span>' +
          '</button>'
        );
        (function (itemId) {
          var removeBtn = row.querySelector(".cart-remove");
          if (removeBtn) {
            removeBtn.addEventListener("click", async function () {
              await api("/api/cart/" + encodeURIComponent(itemId), { method: "DELETE" });
              refreshCart();
              updateCartBadge();
            });
          }
        })(item.id);
        list.appendChild(row);
      }
    } catch (e) { /* ignore */ }
  }

  /* ═══════════════════════════════════
     QUEUE
     ═══════════════════════════════════ */
  async function refreshQueue() {
    var list = $("#queue-list");
    var empty = $("#queue-empty");
    var statsEl = $("#queue-stats");
    if (!list) return;

    try {
      var d = await api("/api/queue");
      if (d.error) return;

      if (statsEl) {
        statsEl.innerHTML =
          '<span class="stat-chip">Queued: ' + (d.count || 0) + '</span>' +
          '<span class="stat-chip">Processing: ' + (d.processing ? "yes" : "no") + '</span>' +
          '<span class="stat-chip">Done: ' + ((d.stats && d.stats.completed) || 0) + '</span>';
      }

      if (!d.items || d.items.length === 0) {
        list.innerHTML = "";
        if (empty) empty.classList.remove("hidden");
        return;
      }
      if (empty) empty.classList.add("hidden");
      list.innerHTML = "";

      for (var i = 0; i < d.items.length; i++) {
        var item = d.items[i];
        list.appendChild(ce("div", "queue-item",
          '<span class="material-icons-outlined" style="color:var(--text-3)">drag_indicator</span>' +
          '<div class="cart-info">' +
            '<div class="cart-title">' + esc(item.title) + '</div>' +
            '<div class="cart-details">' + esc(item.output_format || "cbz") + ' | ' + esc(item.source) + '</div>' +
          '</div>' +
          '<span class="dl-status ' + esc(item.status) + '">' + esc(item.status) + '</span>'
        ));
      }
    } catch (e) { /* ignore */ }
  }

  /* ═══════════════════════════════════
     DOWNLOADS
     ═══════════════════════════════════ */
  async function refreshDownloads() {
    try {
      var d = await api("/api/downloads");
      if (d.error) return;
      renderDownloads(d.tasks || [], d.stats || {});
    } catch (e) { /* ignore */ }
  }

  function renderDownloads(tasks, stats) {
    var list = $("#downloads-list");
    var empty = $("#downloads-empty");
    var statsRow = $("#download-stats");
    if (!list) return;

    if (statsRow) {
      statsRow.innerHTML =
        '<span class="stat-chip">Active: ' + (stats.active || 0) + '</span>' +
        '<span class="stat-chip">Complete: ' + (stats.complete || 0) + '</span>' +
        '<span class="stat-chip">Error: ' + (stats.error || 0) + '</span>' +
        '<span class="stat-chip">' + fmtBytes(stats.total_bytes_downloaded || 0) + '</span>';
    }

    var statActive = $("#stat-active");
    if (statActive) statActive.textContent = String((stats.active || 0) + (stats.converting || 0));

    if (!tasks || tasks.length === 0) {
      list.innerHTML = "";
      if (empty) empty.classList.remove("hidden");
      return;
    }
    if (empty) empty.classList.add("hidden");
    list.innerHTML = "";

    for (var i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      var cancelHtml = "";
      if (t.status === "downloading" || t.status === "pending") {
        cancelHtml = '<button class="btn btn-outline btn-sm btn-danger cancel-btn" data-id="' + esc(t.task_id) + '">' +
          '<span class="material-icons-outlined">close</span></button>';
      }

      var errorHtml = "";
      if (t.error_message) {
        errorHtml = '<p style="color:var(--red);font-size:.7rem;margin-top:6px;font-family:var(--font-mono)">' +
          esc(t.error_message) + '</p>';
      }

      var item = ce("div", "download-item",
        '<div class="dl-header">' +
          '<span class="dl-title">' + esc(t.title) + '</span>' +
          '<span class="dl-status ' + esc(t.status) + '">' + esc(t.status) + '</span>' +
          cancelHtml +
        '</div>' +
        '<div class="dl-progress-bar">' +
          '<div class="dl-progress-fill" style="width:' + (t.progress_percent || 0) + '%"></div>' +
        '</div>' +
        '<div class="dl-stats">' +
          '<span><span class="material-icons-outlined">speed</span>' + fmtBytes(t.speed_bps || 0) + '/s</span>' +
          '<span><span class="material-icons-outlined">layers</span>' + (t.completed_items || 0) + '/' + (t.total_items || 0) + '</span>' +
          '<span><span class="material-icons-outlined">timer</span>ETA ' + fmtTime(t.eta_seconds) + '</span>' +
          '<span><span class="material-icons-outlined">data_usage</span>' + fmtBytes(t.bytes_downloaded || 0) + '</span>' +
          (t.current_chapter ? '<span>' + esc(t.current_chapter) + ' (' + (t.current_page || 0) + '/' + (t.total_pages || 0) + ')</span>' : '') +
        '</div>' +
        errorHtml
      );

      var cancelBtn = item.querySelector(".cancel-btn");
      if (cancelBtn) {
        (function (taskId) {
          cancelBtn.addEventListener("click", async function () {
            await api("/api/download/" + encodeURIComponent(taskId) + "/cancel", { method: "POST" });
          });
        })(t.task_id);
      }

      list.appendChild(item);

      // Confetti on completion
      if (t.status === "complete" && !S.completedTasks.has(t.task_id)) {
        S.completedTasks.add(t.task_id);
        launchConfetti();
        toast("Complete: " + t.title, "success");
      }
    }
  }

  /* ═══════════════════════════════════
     SOURCES
     ═══════════════════════════════════ */
  async function loadSources() {
    var grid = $("#sources-grid");
    if (!grid) return;

    try {
      var d = await api("/api/sources");
      if (d.error) { grid.innerHTML = '<p style="color:var(--text-3);padding:20px">Failed to load sources</p>'; return; }
      grid.innerHTML = "";
      var sources = d.sources || [];
      for (var i = 0; i < sources.length; i++) {
        var src = sources[i];
        var statusCls = "unknown";
        if (src.available === true) statusCls = "online";
        else if (src.available === false) statusCls = "offline";

        var types = [];
        if (src.supports_manga) types.push("manga");
        if (src.supports_manhwa) types.push("manhwa");
        if (src.supports_manhua) types.push("manhua");

        var tagsHtml = "";
        for (var j = 0; j < types.length; j++) {
          tagsHtml += '<span class="chip">' + types[j] + '</span>';
        }

        grid.appendChild(ce("div", "source-card",
          '<div class="source-header">' +
            '<span class="source-name">' + esc(src.name) + '</span>' +
            '<span class="source-status ' + statusCls + '"></span>' +
          '</div>' +
          '<div class="source-tags">' +
            tagsHtml +
            '<span class="chip">' + src.rate_limit + 's</span>' +
            (src.enabled ? '<span class="chip chip-green">on</span>' : '<span class="chip">off</span>') +
          '</div>'
        ));
      }
    } catch (e) {
      grid.innerHTML = '<p style="color:var(--text-3);padding:20px">Failed</p>';
    }
  }

  /* ═══════════════════════════════════
     LOGS
     ═══════════════════════════════════ */
  async function loadLogs() {
    var container = $("#logs-container");
    var statsRow = $("#log-stats");
    if (!container) return;

    var levelSel = $("#log-level-filter");
    var searchInput = $("#log-search");
    var level = levelSel ? levelSel.value : "";
    var search = searchInput ? searchInput.value : "";

    try {
      var url = "/api/logs?limit=200" +
        "&level=" + encodeURIComponent(level) +
        "&search=" + encodeURIComponent(search);
      var d = await api(url);
      if (d.error) return;

      var logs = d.logs || {};
      var entries = logs.entries || [];
      var stats = d.stats || {};

      if (statsRow) {
        var counts = stats.counts || {};
        statsRow.innerHTML =
          '<span class="stat-chip">Total: ' + (stats.total || 0) + '</span>' +
          '<span class="stat-chip" style="color:var(--accent)">Info: ' + (counts.info || 0) + '</span>' +
          '<span class="stat-chip" style="color:var(--orange)">Warn: ' + (counts.warning || 0) + '</span>' +
          '<span class="stat-chip" style="color:var(--red)">Error: ' + (counts.error || 0) + '</span>';
      }

      container.innerHTML = "";
      for (var i = 0; i < entries.length; i++) {
        var e = entries[i];
        var ts = e.timestamp || "";
        var timeStr = "";
        if (ts.indexOf("T") !== -1) {
          timeStr = ts.split("T")[1].substring(0, 8);
        }
        container.appendChild(ce("div", "log-entry",
          '<span class="log-time">' + timeStr + '</span>' +
          '<span class="log-level ' + esc(e.level) + '">' + esc(e.level) + '</span>' +
          '<span class="log-msg">' + esc(e.message) + '</span>'
        ));
      }
    } catch (e) {
      container.innerHTML = '<p style="padding:16px;color:var(--text-3)">Failed to load logs</p>';
    }
  }

  /* ═══════════════════════════════════
     SETTINGS
     ═══════════════════════════════════ */
  var SETTINGS_MAP = {
    "cfg-output-dir": "output_dir",
    "cfg-default-format": "default_format",
    "cfg-language": "language",
    "cfg-reading-direction": "reading_direction",
    "cfg-max-downloads": "max_concurrent_downloads",
    "cfg-max-images": "max_concurrent_images",
    "cfg-bandwidth": "bandwidth_limit_kbps",
    "cfg-rate-limit": "rate_limit_delay",
    "cfg-crop-threshold": "crop_threshold",
    "cfg-crop-min-ratio": "crop_min_ratio",
    "cfg-jpeg-quality": "jpeg_quality",
    "cfg-epub-width": "epub_page_width",
    "cfg-epub-height": "epub_page_height",
    "cfg-discord-webhook": "discord_webhook_url",
    "cfg-telegram-token": "telegram_bot_token",
    "cfg-telegram-chat": "telegram_chat_id",
    "cfg-theme": "theme",
  };

  var SETTINGS_CHECKS = {
    "cfg-auto-crop": "auto_crop",
    "cfg-epub-apple": "epub_apple_books_compat",
    "cfg-epub-cover": "epub_generate_cover",
    "cfg-epub-vertical": "epub_vertical_mode",
    "cfg-notify": "notify_on_complete",
    "cfg-notify-desktop": "notify_desktop",
    "cfg-high-contrast": "high_contrast",
    "cfg-minimal": "minimal_mode",
  };

  var INT_KEYS = [
    "max_concurrent_downloads", "max_concurrent_images", "bandwidth_limit_kbps",
    "crop_threshold", "jpeg_quality", "epub_page_width", "epub_page_height",
  ];
  var FLOAT_KEYS = ["rate_limit_delay", "crop_min_ratio"];

  async function loadSettings() {
    try {
      var d = await api("/api/config");
      if (d.error) return;
      S.config = d;

      for (var id in SETTINGS_MAP) {
        var key = SETTINGS_MAP[id];
        var el = $("#" + id);
        if (el && S.config[key] !== undefined) {
          el.value = S.config[key] != null ? String(S.config[key]) : "";
        }
      }
      for (var id2 in SETTINGS_CHECKS) {
        var key2 = SETTINGS_CHECKS[id2];
        var el2 = $("#" + id2);
        if (el2) el2.checked = !!S.config[key2];
      }

      applyTheme();
    } catch (e) { /* ignore */ }
  }

  async function saveSettings() {
    var updates = {};

    for (var id in SETTINGS_MAP) {
      var key = SETTINGS_MAP[id];
      var el = $("#" + id);
      if (!el) continue;
      var val = el.value;
      if (INT_KEYS.indexOf(key) !== -1) {
        updates[key] = parseInt(val) || 0;
      } else if (FLOAT_KEYS.indexOf(key) !== -1) {
        updates[key] = parseFloat(val) || 0;
      } else {
        updates[key] = val;
      }
    }

    for (var id2 in SETTINGS_CHECKS) {
      var key2 = SETTINGS_CHECKS[id2];
      var el2 = $("#" + id2);
      if (el2) updates[key2] = el2.checked;
    }

    try {
      await api("/api/config", { method: "POST", body: JSON.stringify(updates) });
      Object.assign(S.config, updates);
      applyTheme();
      toast("Settings saved", "success");
    } catch (e) {
      toast("Failed to save settings", "error");
    }
  }

  function applyTheme() {
    document.documentElement.setAttribute("data-theme", S.config.theme || "dark");
    if (S.config.high_contrast) {
      document.documentElement.setAttribute("data-contrast", "high");
    } else {
      document.documentElement.removeAttribute("data-contrast");
    }
    document.body.classList.toggle("minimal", !!S.config.minimal_mode);
  }

  /* ═══════════════════════════════════
     SSE — Live updates
     ═══════════════════════════════════ */
  function initSSE() {
    if (S.sse) {
      try { S.sse.close(); } catch (e) { /* ignore */ }
    }
    try {
      S.sse = new EventSource("/api/events");
      S.sse.onmessage = function (ev) {
        try {
          var d = JSON.parse(ev.data);
          if (S.tab === "downloads") {
            renderDownloads(d.tasks || [], {});
          }
          var active = 0;
          var tasks = d.tasks || [];
          for (var i = 0; i < tasks.length; i++) {
            if (tasks[i].status === "downloading" || tasks[i].status === "converting") active++;
          }
          var el = $("#stat-active");
          if (el) el.textContent = String(active);
        } catch (e) { /* ignore parse errors */ }
      };
      S.sse.onerror = function () {
        setTimeout(initSSE, 5000);
      };
    } catch (e) {
      setTimeout(initSSE, 5000);
    }
  }

  /* ═══════════════════════════════════
     INIT
     ═══════════════════════════════════ */
  function init() {
    // Intro particles
    initParticles("#splash-particles", 60, "rgba(74,143,231,A)", 0.4, 0.25);

    // Settle intro letters
    setTimeout(function () {
      var letters = document.getElementById("intro-letters");
      if (letters) letters.classList.add("settled");
    }, 2200);

    // Hide splash
    setTimeout(function () {
      var splash = document.getElementById("splash");
      if (splash) splash.classList.add("hidden");
    }, 4200);

    // Hero particles
    setTimeout(function () {
      initParticles("#hero-particles", 40, "rgba(74,143,231,A)", 0.35, 0.2);
    }, 4400);

    // Tabs
    initTabs();

    // Mobile nav
    var mobileNav = $("#mobile-nav");
    if (mobileNav) {
      mobileNav.addEventListener("click", function () {
        var sidebar = $("#sidebar");
        if (sidebar) sidebar.classList.toggle("open");
      });
    }

    // Search
    var searchBtn = $("#search-btn");
    if (searchBtn) searchBtn.addEventListener("click", function () { doSearch(); });

    var searchInput = $("#search-input");
    if (searchInput) {
      searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") doSearch();
      });
    }

    // Home search
    var homeSearch = $("#home-search-input");
    if (homeSearch) {
      homeSearch.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          var q = homeSearch.value.trim();
          if (q) {
            switchTab("search");
            setTimeout(function () { doSearch(q); }, 150);
          }
        }
      });
    }

    // Discover
    var discoverRefresh = $("#discover-refresh");
    if (discoverRefresh) discoverRefresh.addEventListener("click", loadDiscover);
    var discoverLang = $("#discover-lang");
    if (discoverLang) discoverLang.addEventListener("change", loadDiscover);

    // Downloads
    var clearDl = $("#clear-downloads");
    if (clearDl) {
      clearDl.addEventListener("click", async function () {
        await api("/api/downloads/clear", { method: "POST" });
        refreshDownloads();
      });
    }

    // Cart
    var cartClear = $("#cart-clear");
    if (cartClear) {
      cartClear.addEventListener("click", async function () {
        await api("/api/cart/clear", { method: "POST" });
        refreshCart();
        updateCartBadge();
      });
    }
    var cartDlAll = $("#cart-download-all");
    if (cartDlAll) {
      cartDlAll.addEventListener("click", async function () {
        try {
          var d = await api("/api/queue/start", {
            method: "POST",
            body: JSON.stringify({ enqueue_cart: true }),
          });
          toast("Queue started with " + (d.enqueued || 0) + " items", "success");
          switchTab("downloads");
          updateCartBadge();
        } catch (e) {
          toast("Failed to start queue", "error");
        }
      });
    }

    // Queue
    var queueStart = $("#queue-start");
    if (queueStart) {
      queueStart.addEventListener("click", async function () {
        await api("/api/queue/start", { method: "POST", body: JSON.stringify({ enqueue_cart: false }) });
        refreshQueue();
        toast("Queue started", "info");
      });
    }
    var queueStop = $("#queue-stop");
    if (queueStop) {
      queueStop.addEventListener("click", async function () {
        await api("/api/queue/stop", { method: "POST" });
        refreshQueue();
        toast("Queue stopped", "info");
      });
    }
    var queueClear = $("#queue-clear");
    if (queueClear) {
      queueClear.addEventListener("click", async function () {
        await api("/api/queue/clear", { method: "POST" });
        refreshQueue();
      });
    }

    // Sources
    var checkSources = $("#check-sources");
    if (checkSources) {
      checkSources.addEventListener("click", async function () {
        toast("Checking sources...", "info");
        await api("/api/sources/check");
        loadSources();
        toast("Source check complete", "success");
      });
    }

    // Logs
    var logLevel = $("#log-level-filter");
    if (logLevel) logLevel.addEventListener("change", loadLogs);
    var logSearch = $("#log-search");
    if (logSearch) logSearch.addEventListener("input", debounce(loadLogs, 400));
    var clearLogs = $("#clear-logs");
    if (clearLogs) {
      clearLogs.addEventListener("click", async function () {
        await api("/api/logs/clear", { method: "POST" });
        loadLogs();
      });
    }

    // Settings
    var saveBtn = $("#save-settings");
    if (saveBtn) saveBtn.addEventListener("click", saveSettings);

    var resetBtn = $("#reset-settings");
    if (resetBtn) {
      resetBtn.addEventListener("click", async function () {
        await api("/api/config/reset", { method: "POST" });
        loadSettings();
        toast("Settings reset to defaults", "info");
      });
    }

    var exportBtn = $("#export-config");
    if (exportBtn) {
      exportBtn.addEventListener("click", function () {
        window.open("/api/config/export", "_blank");
      });
    }

    var importBtn = $("#import-config");
    if (importBtn) {
      importBtn.addEventListener("change", async function (e) {
        var file = e.target.files[0];
        if (!file) return;
        var text = await file.text();
        var result = await api("/api/config/import", {
          method: "POST",
          body: text,
          headers: { "Content-Type": "application/json" },
        });
        if (result.imported) {
          toast("Config imported", "success");
          loadSettings();
        } else {
          toast("Invalid config file", "error");
        }
      });
    }

    // Notification tests
    var testDiscord = $("#test-discord");
    if (testDiscord) {
      testDiscord.addEventListener("click", async function () {
        var urlInput = $("#cfg-discord-webhook");
        var url = urlInput ? urlInput.value : "";
        var r = await api("/api/notifications/test", {
          method: "POST",
          body: JSON.stringify({ channel: "discord", webhook_url: url }),
        });
        toast(r.discord ? "Discord OK" : "Discord failed", r.discord ? "success" : "error");
      });
    }

    var testTelegram = $("#test-telegram");
    if (testTelegram) {
      testTelegram.addEventListener("click", async function () {
        var tokenInput = $("#cfg-telegram-token");
        var chatInput = $("#cfg-telegram-chat");
        var r = await api("/api/notifications/test", {
          method: "POST",
          body: JSON.stringify({
            channel: "telegram",
            bot_token: tokenInput ? tokenInput.value : "",
            chat_id: chatInput ? chatInput.value : "",
          }),
        });
        toast(r.telegram ? "Telegram OK" : "Telegram failed", r.telegram ? "success" : "error");
      });
    }

    // Modal close handlers
    var modalClose = $(".modal-close");
    if (modalClose) {
      modalClose.addEventListener("click", function () {
        $("#manga-modal").classList.add("hidden");
      });
    }
    var modalBackdrop = $(".modal-backdrop");
    if (modalBackdrop) {
      modalBackdrop.addEventListener("click", function () {
        $("#manga-modal").classList.add("hidden");
      });
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        var modal = $("#manga-modal");
        if (modal) modal.classList.add("hidden");
      }
    });

    // Initial data load
    loadSettings().then(function () {
      loadHome();
      updateCartBadge();
    });

    // SSE
    initSSE();

    // Show search empty state
    var searchEmpty = $("#search-empty");
    var searchIn = $("#search-input");
    if (searchEmpty && searchIn && !searchIn.value) {
      searchEmpty.classList.remove("hidden");
    }
  }

  // Boot
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();