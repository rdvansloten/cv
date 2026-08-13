/* CV renderer
 * Loads content.md, splits YAML frontmatter from markdown body,
 * routes H2 sections to sidebar or main column, and wraps each
 * H3 entry in a .entry block for clean print page breaks.
 */

const SIDEBAR_SECTIONS = new Set([
  'Introduction',
  'Certifications',
  'Languages',
  'Hobbies',
  'Office / Creative Tools',
  'Technical Tools',
]);

/* Sidebar sections rendered as <details> so they can collapse at narrow
   widths. Intro is intentionally absent — it always stays visible. */
const COLLAPSIBLE_SIDEBAR_SECTIONS = new Set([
  'Certifications',
  'Languages',
  'Hobbies',
  'Office / Creative Tools',
  'Technical Tools',
]);

const NARROW_VIEWPORT = '(max-width: 700px)';

/* Contact icon box, in px. Sized a touch larger than the sidebar text so the
   icons read clearly next to it, both on screen and in the PDF. */
const ICON_SIZE = 17.5;

const ICONS = {
  location: `<svg viewBox="0 0 24 24" width="${ICON_SIZE}" height="${ICON_SIZE}" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
  phone: `<svg viewBox="0 0 24 24" width="${ICON_SIZE}" height="${ICON_SIZE}" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>`,
  email: `<svg viewBox="0 0 24 24" width="${ICON_SIZE}" height="${ICON_SIZE}" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>`,
  github: `<svg viewBox="0 0 24 24" width="${ICON_SIZE}" height="${ICON_SIZE}" fill="currentColor"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.09 3.29 9.4 7.86 10.93.58.1.79-.25.79-.56 0-.28-.01-1.02-.02-2-3.2.7-3.88-1.54-3.88-1.54-.52-1.33-1.27-1.68-1.27-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.68 1.24 3.34.95.1-.74.4-1.24.73-1.52-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.18 1.18.92-.26 1.91-.39 2.9-.39s1.98.13 2.9.39c2.21-1.49 3.18-1.18 3.18-1.18.62 1.58.23 2.75.11 3.04.74.81 1.18 1.84 1.18 3.1 0 4.42-2.69 5.4-5.25 5.68.41.36.78 1.06.78 2.13 0 1.54-.01 2.78-.01 3.16 0 .31.21.67.8.55C20.21 21.4 23.5 17.09 23.5 12 23.5 5.65 18.35.5 12 .5z"/></svg>`,
};

function parseFrontmatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!m) return { data: {}, body: text };
  return { data: jsyaml.load(m[1]) || {}, body: m[2] };
}

function splitSections(md) {
  const lines = md.split('\n');
  const sections = [];
  let current = null;
  for (const line of lines) {
    const h2 = line.match(/^##\s+(.+?)\s*$/);
    if (h2) {
      if (current) sections.push(current);
      current = { title: h2[1].trim(), body: '' };
    } else if (current) {
      current.body += line + '\n';
    }
  }
  if (current) sections.push(current);
  return sections;
}

function el(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstChild;
}

function renderPhoto(data, root) {
  const img = root.querySelector('.photo-img');
  if (!img) return;
  // Candidate portrait sources, tried in order. An explicit `photo:` in the
  // frontmatter wins; otherwise just drop a file named photo.<ext> into
  // assets/ and it shows up automatically — no config needed. The .photo
  // container already clips it to a circle.
  const exts = ['jpg', 'jpeg', 'png', 'webp', 'avif'];
  const candidates = [data.photo, ...exts.map(e => `assets/photo.${e}`)]
    .filter(Boolean);

  // Probe each candidate in turn — only set src on the real <img> once one
  // loads, so a missing file leaves the CSS silhouette visible instead of
  // showing a broken-image icon.
  (function tryNext(i) {
    if (i >= candidates.length) return;
    const probe = new Image();
    probe.onload = () => { img.src = candidates[i]; };
    probe.onerror = () => tryNext(i + 1);
    probe.src = candidates[i];
  })(0);
}

function renderMasthead(data, slot) {
  slot.innerHTML = `
    <h1>${data.name || ''}</h1>
    <div class="subtitle">${data.title || ''}</div>
  `;
}

function renderContact(data, slot) {
  const items = [
    { icon: 'location', text: data.location },
    { icon: 'phone', text: data.phone, href: data.phone ? 'tel:' + data.phone.replace(/\s+/g, '') : null },
    { icon: 'email', text: data.email, href: data.email ? 'mailto:' + data.email : null },
    { icon: 'github', text: data.github, href: data.github ? 'https://' + data.github.replace(/^https?:\/\//, '') : null },
  ].filter(i => i.text);

  slot.innerHTML = items
    .map(i => {
      const inner = `${ICONS[i.icon] || ''}<span>${i.text}</span>`;
      return i.href
        ? `<a class="contact-item" href="${i.href}">${inner}</a>`
        : `<div class="contact-item">${inner}</div>`;
    })
    .join('');
}

function renderSidebarSection(section, parent) {
  const slug = slugify(section.title);
  const collapsible = COLLAPSIBLE_SIDEBAR_SECTIONS.has(section.title);
  const wrap = document.createElement(collapsible ? 'details' : 'section');
  wrap.className = 'sidebar-section ' + slug + (collapsible ? ' collapsible' : '');

  if (collapsible) {
    wrap.innerHTML =
      `<summary><h2>${section.title}</h2></summary>` +
      `<div class="sidebar-section-body">${marked.parse(section.body)}</div>`;
  } else {
    wrap.innerHTML = `<h2>${section.title}</h2>${marked.parse(section.body)}`;
  }

  // Languages: split "Name — Level" into two columns
  if (slug === 'languages') {
    wrap.querySelectorAll('li').forEach(li => {
      const txt = li.textContent;
      const m = txt.split(/\s+[—–-]\s+/);
      if (m.length === 2) {
        li.innerHTML = `<span class="lang-name">${m[0]}</span><span class="lang-level">${m[1]}</span>`;
      }
    });
  }

  parent.appendChild(wrap);
}

/**
 * Open/close the collapsible sidebar sections based on viewport width:
 *   - narrow: closed (collapsed)
 *   - wide:   forced open (CSS hides the chevron + disables interaction)
 * Also forces them open before printing so the PDF never hides content.
 */
function setupSidebarCollapse() {
  const sections = document.querySelectorAll('details.sidebar-section.collapsible');
  if (!sections.length) return;
  const mq = window.matchMedia(NARROW_VIEWPORT);

  const sync = () => {
    sections.forEach(d => { d.open = !mq.matches; });
  };
  sync();
  mq.addEventListener('change', sync);
  window.addEventListener('beforeprint', () => {
    sections.forEach(d => { d.open = true; });
  });
}

function renderMainSection(section, parent) {
  const slug = slugify(section.title);
  const wrap = document.createElement('section');
  wrap.className = 'main-section ' + slug;
  wrap.innerHTML = `<h2>${section.title}</h2>${marked.parse(section.body)}`;

  // Technical Skills: H3s become a 2-column grid of skill groups
  if (slug === 'technical-skills') {
    const grid = document.createElement('div');
    grid.className = 'skills-grid';
    const h3s = Array.from(wrap.querySelectorAll('h3'));
    for (const h3 of h3s) {
      const group = document.createElement('div');
      group.className = 'skill-group';
      let node = h3;
      while (node && !(node !== h3 && node.tagName === 'H3')) {
        const next = node.nextSibling;
        group.appendChild(node);
        node = next;
      }
      grid.appendChild(group);
    }
    wrap.appendChild(grid);
  } else if (slug === 'professional-experience' || slug === 'education') {
    // Wrap each H3 + following siblings in .entry
    wrapEntries(wrap);
  }

  parent.appendChild(wrap);
}

/**
 * Find H3 elements inside `container` and group each H3 with its
 * following siblings (until the next H3) under a new wrapper div.
 */
function wrapEntries(container) {
  const h3s = Array.from(container.querySelectorAll('h3'));
  for (const h3 of h3s) {
    const entry = document.createElement('div');
    entry.className = 'entry';
    h3.parentNode.insertBefore(entry, h3);
    let node = h3;
    while (node && !(node !== h3 && node.tagName === 'H3')) {
      const next = node.nextSibling;
      entry.appendChild(node);
      node = next;
    }
    // The first <p> after H3 (if it contains only italic content) is the meta line
    const firstP = entry.querySelector('h3 + p');
    if (firstP && firstP.children.length === 1 && firstP.firstElementChild.tagName === 'EM') {
      const meta = document.createElement('div');
      meta.className = 'entry-meta';
      meta.textContent = firstP.firstElementChild.textContent;
      firstP.replaceWith(meta);
    }
  }
}

function slugify(s) {
  return s.toLowerCase()
    .replace(/[\/]/g, '-')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

/**
 * Optional style overrides from frontmatter.
 *   style:
 *     main-text: 10pt           (body text in the white main column)
 *     sidebar-text: 9pt         (body text in the blue sidebar)
 *     main-heading: 12pt        (## headings in the main column)
 *     sidebar-heading: 11pt     (## headings in the sidebar)
 *     name-color: "#173e5e"     (the H1 name)
 *     icon-color: "#ffffff"     (the contact icons)
 *     marker-color: "#ffffff"   (◊ and » list markers, both columns)
 */
const STYLE_MAP = {
  'main-text':       ['--font-size-main'],
  'sidebar-text':    ['--font-size-sidebar'],
  'main-heading':    ['--font-size-main-h'],
  'sidebar-heading': ['--font-size-sidebar-h'],
  'name-color':      ['--color-name'],
  'icon-color':      ['--color-icon'],
  'marker-color':    ['--color-marker-sidebar', '--color-marker-main'],
};

const SAFE_VALUE = /^[#\w.()%,\s/-]+$/;

function applyStyle(style) {
  if (!style || typeof style !== 'object') return;
  for (const [key, raw] of Object.entries(style)) {
    const targets = STYLE_MAP[key];
    if (!targets) {
      console.warn(`Unknown style key: ${key}`);
      continue;
    }
    const value = String(raw).trim();
    if (!SAFE_VALUE.test(value)) {
      console.warn(`Ignoring style.${key}: contains disallowed characters`);
      continue;
    }
    for (const v of targets) {
      document.documentElement.style.setProperty(v, value);
    }
  }
}

async function init() {
  try {
    const res = await fetch('content.md', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`Failed to load content.md: ${res.status}`);
    const md = await res.text();
    const { data, body } = parseFrontmatter(md);
    const cv = document.getElementById('cv');

    applyStyle(data.style);
    renderPhoto(data, cv);
    renderMasthead(data, cv.querySelector('[data-slot="masthead"]'));
    renderContact(data, cv.querySelector('[data-slot="contact"]'));

    const sidebarSlot = cv.querySelector('[data-slot="sidebar"]');
    const mainSlot = cv.querySelector('[data-slot="main"]');

    const sections = splitSections(body);
    for (const sec of sections) {
      if (SIDEBAR_SECTIONS.has(sec.title)) {
        renderSidebarSection(sec, sidebarSlot);
      } else {
        renderMainSection(sec, mainSlot);
      }
    }

    setupSidebarCollapse();
    document.title = `CV — ${data.name || 'Resume'}`;
    cv.removeAttribute('aria-busy');
  } catch (err) {
    console.error(err);
    document.getElementById('cv').innerHTML =
      `<div style="padding:24px;color:#900">Could not load content.md — ${err.message}</div>`;
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
