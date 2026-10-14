/**
 * 工作台交互组件库（wb-ui）。
 * 实现「高级交互设计」10 种模式中的纯 UI 部分：
 *  1 弹窗主题切换  2 拖拽排序  3 批量勾选(错峰)  4 滑块惯性吸附
 *  5 文本展开      7 开关联动 ripple
 * （6 步骤条、8 卡片弧线删除、9 堆叠滚动、10 标签展开由样式 + assistant.js 调用本库完成）
 * 所有组件只做本地视图层交互，不触达后端、不改动状态语义。
 */

const store = {
  get(key, fallback) { try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* 隐私模式等场景忽略 */ } },
};

/* ---------- 主题（模式 1 的底层） ---------- */
const THEME_KEY = 'wb.theme';
const MEDIA = window.matchMedia('(prefers-color-scheme: dark)');
let themeMode = store.get(THEME_KEY, 'system'); // light | dark | system

function applyTheme(mode, { animate = false } = {}) {
  themeMode = mode;
  store.set(THEME_KEY, mode);
  const resolved = mode === 'system' ? (MEDIA.matches ? 'dark' : 'light') : mode;
  if (animate) {
    document.documentElement.classList.add('theme-anim');
    setTimeout(() => document.documentElement.classList.remove('theme-anim'), 500);
  }
  document.documentElement.dataset.theme = resolved;
}
function currentThemeMode() { return themeMode; }
MEDIA.addEventListener('change', () => { if (themeMode === 'system') applyTheme('system'); });

/* ---------- Toast ---------- */
function toast(textValue, kind = 'status', { duration = 3200 } = {}) {
  let host = document.querySelector('.wb-toasts');
  if (!host) { host = document.createElement('div'); host.className = 'wb-toasts'; document.body.append(host); }
  const node = document.createElement('div');
  node.className = 'wb-toast'; node.dataset.kind = kind; node.textContent = textValue;
  host.append(node);
  setTimeout(() => { node.dataset.leave = 'true'; setTimeout(() => node.remove(), 320); }, duration);
  return node;
}

/* ---------- 弹窗（模式 1：Modal Theme Transition） ---------- */
function modal({ title }) {
  const backdrop = document.createElement('div');
  backdrop.className = 'wb-modal-backdrop'; backdrop.dataset.open = 'false';
  const box = document.createElement('div'); box.className = 'wb-modal'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true');
  const head = document.createElement('div'); head.className = 'wb-modal-head';
  const h3 = document.createElement('h3'); h3.textContent = title;
  const close = document.createElement('button'); close.className = 'wb-btn wb-btn--ghost wb-icon-btn'; close.type = 'button';
  close.setAttribute('aria-label', '关闭'); close.textContent = '×';
  head.append(h3, close);
  const body = document.createElement('div'); body.className = 'wb-modal-body';
  box.append(head, body); backdrop.append(box); document.body.append(backdrop);
  requestAnimationFrame(() => { backdrop.dataset.open = 'true'; });

  let lastFocus = document.activeElement;
  function onKey(event) { if (event.key === 'Escape') closeDialog(); }
  function closeDialog() {
    backdrop.dataset.open = 'false';
    document.removeEventListener('keydown', onKey);
    setTimeout(() => { backdrop.remove(); lastFocus?.focus?.(); }, 300);
  }
  close.addEventListener('click', closeDialog);
  backdrop.addEventListener('pointerdown', event => { if (event.target === backdrop) closeDialog(); });
  document.addEventListener('keydown', onKey);
  return { body, close: closeDialog };
}

/* 主题选择弹窗：切换时带全站过渡动画（模式 1 本体）。 */
function openSettingsModal({ onDensityChange } = {}) {
  const dialog = modal({ title: '工作台设置' });

  const themeBlock = document.createElement('div');
  const themeTitle = document.createElement('p');
  themeTitle.textContent = '主题';
  themeTitle.style.cssText = 'margin:0 0 .5rem;font-size:.84rem;font-weight:600';
  const options = document.createElement('div'); options.className = 'wb-theme-options';
  const picks = [['light', '浅色'], ['dark', '深色'], ['system', '跟随系统']];
  const buttons = new Map();
  function syncPressed() { for (const [mode, btn] of buttons) btn.setAttribute('aria-pressed', String(currentThemeMode() === mode)); }
  for (const [mode, label] of picks) {
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'wb-theme-option'; btn.dataset.themePick = mode;
    const preview = document.createElement('div'); preview.className = 'wb-theme-preview';
    const name = document.createElement('span'); name.textContent = label;
    btn.append(preview, name);
    btn.addEventListener('click', () => { applyTheme(mode, { animate: true }); syncPressed(); toast('主题已切换：' + label, 'ok'); });
    buttons.set(mode, btn); options.append(btn);
  }
  syncPressed();
  themeBlock.append(themeTitle, options);

  /* 密度滑块：3 档（紧凑/标准/舒适）速度感知吸附（模式 4）。 */
  const densityBlock = document.createElement('div');
  const densityTitle = document.createElement('p');
  densityTitle.textContent = '信息密度';
  densityTitle.style.cssText = 'margin:0 0 .55rem;font-size:.84rem;font-weight:600';
  const DENSITY = [{ key: 'compact', label: '紧凑', value: 0, css: .82 }, { key: 'normal', label: '标准', value: 50, css: 1 }, { key: 'relaxed', label: '舒适', value: 100, css: 1.22 }];
  const current = Math.round(parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--density')) || 1) * 50;
  let densityIndex = Math.max(0, DENSITY.findIndex(d => d.value >= current - 25));
  const sliderRow = document.createElement('div'); sliderRow.className = 'wb-slider-row';
  const slider = document.createElement('input');
  slider.type = 'range'; slider.min = '0'; slider.max = '100'; slider.step = '1'; slider.value = DENSITY[densityIndex].value;
  slider.className = 'wb-slider'; slider.setAttribute('aria-label', '信息密度');
  const labels = document.createElement('div'); labels.className = 'wb-slider-labels';
  const labelSpans = DENSITY.map(d => { const s = document.createElement('span'); s.textContent = d.label; return s; });
  labels.append(...labelSpans);
  function paintFill() {
    slider.style.setProperty('--fill', slider.value + '%');
    labelSpans.forEach((s, i) => s.dataset.active = String(i === densityIndex));
  }
  function commitIndex(i, { snap = true } = {}) {
    densityIndex = Math.min(DENSITY.length - 1, Math.max(0, i));
    const target = DENSITY[densityIndex];
    if (snap) slider.value = target.value; // 吸附：直接落到档位
    paintFill();
    document.documentElement.style.setProperty('--density', String(target.css));
    store.set('wb.density', target.key);
    onDensityChange?.(target);
  }
  slider.addEventListener('input', () => {
    const v = Number(slider.value);
    densityIndex = v < 25 ? 0 : v < 75 ? 1 : 2;
    paintFill();
    document.documentElement.style.setProperty('--density', String(DENSITY[densityIndex].css)); // 拖动时实时预览
  });
  /* 惯性：记录最近指针速度，释放时速度足够则顺势滑过一档。 */
  let lastX = 0, lastT = 0, velocity = 0;
  slider.addEventListener('pointerdown', event => { lastX = event.clientX; lastT = performance.now(); velocity = 0; });
  slider.addEventListener('pointermove', event => {
    if (event.buttons === 0 && event.pointerType !== 'touch') return;
    const now = performance.now(); const dt = now - lastT;
    if (dt > 0) { velocity = ((event.clientX - lastX) / dt) * 1000; lastX = event.clientX; lastT = now; }
  });
  slider.addEventListener('pointerup', () => {
    const FLICK = 380; // px/s 以上视为甩动
    let next = densityIndex;
    if (velocity > FLICK) next = densityIndex + 1;
    else if (velocity < -FLICK) next = densityIndex - 1;
    else next = Number(slider.value) < 25 ? 0 : Number(slider.value) < 75 ? 1 : 2;
    commitIndex(next);
    velocity = 0;
  });
  slider.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight') commitIndex(densityIndex + 1);
    if (event.key === 'ArrowLeft') commitIndex(densityIndex - 1);
  });
  commitIndex(densityIndex, { snap: false });
  densityBlock.append(densityTitle, sliderRow, labels);
  sliderRow.append(slider);

  dialog.body.append(themeBlock, densityBlock);
  return dialog;
}

/* ---------- Ripple 联动（模式 7） ---------- */
function rippleTo(target, { flash = true } = {}) {
  if (!target) return;
  target.classList.add('wb-ripple-target');
  const ping = document.createElement('span'); ping.className = 'wb-ripple-ping';
  target.append(ping);
  setTimeout(() => ping.remove(), 950);
  if (flash) { target.classList.remove('wb-flash'); void target.offsetWidth; target.classList.add('wb-flash'); setTimeout(() => target.classList.remove('wb-flash'), 850); }
}

/* ---------- 文本展开（模式 5） ---------- */
function clampText(textValue, { lines = 3 } = {}) {
  const wrap = document.createElement('div'); wrap.className = 'wb-clamp';
  const inner = document.createElement('div'); inner.className = 'wb-clamp-inner'; inner.style.webkitLineClamp = String(lines);
  inner.textContent = textValue;
  const btn = document.createElement('button'); btn.type = 'button'; btn.className = 'wb-disclose-btn'; btn.hidden = true;
  btn.textContent = '展开全文';
  btn.addEventListener('click', () => {
    const collapsed = inner.style.webkitLineClamp !== 'unset';
    inner.style.webkitLineClamp = collapsed ? 'unset' : String(lines);
    btn.textContent = collapsed ? '收起' : '展开全文';
  });
  wrap.append(inner, btn);
  requestAnimationFrame(() => { if (inner.scrollHeight > inner.clientHeight + 4) btn.hidden = false; });
  return wrap;
}

/* ---------- 拖拽排序（模式 2） ---------- */
function makeSortable(container, { storageKey, onReorder } = {}) {
  const order = store.get(storageKey, []);
  const panels = [...container.children];
  const byId = new Map(panels.map(p => [p.dataset.panelId, p]));
  const arranged = order.map(id => byId.get(id)).filter(Boolean).filter(p => p.dataset.draggable === 'true');
  const rest = panels.filter(p => !arranged.includes(p));
  for (const node of [...arranged, ...rest]) container.append(node);

  let dragging = null;
  container.addEventListener('pointerdown', event => {
    const handle = event.target.closest('.wb-drag');
    if (!handle) return;
    const panel = handle.closest('.wb-panel');
    dragging = panel; dragging.dataset.dragging = 'true';
    handle.setPointerCapture(event.pointerId);
    event.preventDefault();
  });
  container.addEventListener('pointermove', event => {
    if (!dragging) return;
    const target = event.target.closest?.('.wb-panel[data-draggable="true"]');
    for (const p of container.querySelectorAll('[data-drop-target]')) p.removeAttribute('data-drop-target');
    if (target && target !== dragging) target.dataset.dropTarget = 'true';
  });
  const finishDrag = () => {
    if (!dragging) return;
    const dropTarget = container.querySelector('[data-drop-target]');
    if (dropTarget) {
      const rect = dropTarget.getBoundingClientRect();
      container.insertBefore(dragging, event.clientY < rect.top + rect.height / 2 ? dropTarget : dropTarget.nextSibling);
    }
    dragging.removeAttribute('data-dragging');
    dragging.dataset.justDropped = 'true';
    setTimeout(() => dragging?.removeAttribute('data-just-dropped'), 500);
    const ids = [...container.children].map(p => p.dataset.panelId);
    store.set(storageKey, ids);
    dragging = null;
    onReorder?.(ids);
  };
  container.addEventListener('pointerup', finishDrag);
  container.addEventListener('pointercancel', finishDrag);
  return { getOrder: () => [...container.children].map(p => p.dataset.panelId) };
}

/* ---------- 历史卡片视图：标签筛选（10）+ 批量勾选（3）+ 弧线删除（8） ---------- */
function createHistoryView({ onOpen }) {
  const root = document.createElement('div');
  const tags = document.createElement('div'); tags.className = 'wb-tags';
  const stack = document.createElement('div'); stack.className = 'wb-stack';
  const bulkBar = document.createElement('div'); bulkBar.className = 'wb-bulkbar'; bulkBar.hidden = true;
  root.append(tags, bulkBar, stack);

  const state = { items: [], hidden: new Set(), selected: new Set(), filter: null, expandedTags: false };
  const isShown = item => (!state.filter || item.overall_status === state.filter) && !state.hidden.has(item.investigation_id);

  function renderTags() {
    tags.replaceChildren();
    const counts = new Map();
    for (const item of state.items) counts.set(item.overall_status, (counts.get(item.overall_status) || 0) + 1);
    const entries = [...counts.entries()].sort((a, b) => b[1] - a[1]);
    const LIMIT = 4;
    const visible = state.expandedTags ? entries : entries.slice(0, LIMIT);

    const all = tagButton('全部', state.items.length, state.filter === null);
    all.addEventListener('click', () => { state.filter = null; render(); });
    tags.append(all);
    for (const [status, count] of visible) {
      const btn = tagButton(String(status), count, state.filter === status);
      btn.addEventListener('click', () => { state.filter = state.filter === status ? null : status; render(); });
      tags.append(btn);
    }
    if (entries.length > LIMIT) { // 模式 10：折叠 +N，点击展开
      const more = document.createElement('button');
      more.type = 'button'; more.className = 'wb-tag wb-tag--more';
      more.textContent = state.expandedTags ? '收起标签' : `+${entries.length - LIMIT}`;
      more.addEventListener('click', () => { state.expandedTags = !state.expandedTags; renderTags(); });
      tags.append(more);
    }
  }
  function tagButton(label, count, pressed) {
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'wb-tag'; btn.setAttribute('aria-pressed', String(pressed));
    const text = document.createElement('span'); text.textContent = label;
    const num = document.createElement('span'); num.className = 'wb-tag-count'; num.textContent = String(count);
    btn.append(text, num);
    return btn;
  }

  function renderBulk() {
    bulkBar.replaceChildren();
    const count = state.selected.size;
    bulkBar.hidden = count === 0;
    if (!count) return;
    const info = document.createElement('span'); info.textContent = `已选 ${count} 项`;
    const selectVisible = document.createElement('button'); selectVisible.type = 'button'; selectVisible.className = 'wb-mini-btn'; selectVisible.textContent = '全选'; selectVisible.title = '勾选当前筛选下全部记录（仅本地视图）';
    selectVisible.addEventListener('click', () => {
      let delay = 0;
      for (const card of stack.querySelectorAll('.wb-card')) {
        const id = card.dataset.id;
        if (state.selected.has(id)) continue;
        const box = card.querySelector('.wb-check');
        box.checked = true; box.dataset.stagger = ''; box.style.animationDelay = `${delay}ms`; // 模式 3：错峰勾选
        setTimeout(() => box.removeAttribute('data-stagger'), 400 + delay);
        state.selected.add(id); delay += 60;
      }
      renderBulk();
    });
    const copyIds = document.createElement('button'); copyIds.type = 'button'; copyIds.className = 'wb-mini-btn'; copyIds.textContent = '复制 ID'; copyIds.title = '复制所选调查 ID（本地操作，不改后端）';
    copyIds.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText([...state.selected].join('\n')); toast(`已复制 ${state.selected.size} 个调查 ID`, 'ok'); }
      catch { toast('剪贴板不可用，请手动复制', 'bad'); }
    });
    const clear = document.createElement('button'); clear.type = 'button'; clear.className = 'wb-mini-btn'; clear.textContent = '取消';
    clear.addEventListener('click', () => { state.selected.clear(); render(); });
    bulkBar.append(info, selectVisible, copyIds, clear);
  }

  function renderCards() {
    stack.replaceChildren();
    const shown = state.items.filter(isShown);
    if (!shown.length) {
      const empty = document.createElement('div'); empty.className = 'wb-empty-card';
      empty.textContent = state.items.length ? '当前筛选无可见记录（仅本地视图）。' : 'Empty';
      stack.append(empty); return;
    }
    for (const item of shown) {
      const card = document.createElement('article');
      card.className = 'wb-card'; card.dataset.id = item.investigation_id;
      card.dataset.selected = String(state.selected.has(item.investigation_id));
      const top = document.createElement('div'); top.className = 'wb-card-top';
      const check = document.createElement('input'); check.type = 'checkbox'; check.className = 'wb-check';
      check.checked = state.selected.has(item.investigation_id);
      check.setAttribute('aria-label', '选择该记录');
      check.addEventListener('change', () => {
        if (check.checked) { state.selected.add(item.investigation_id); check.dataset.stagger = ''; setTimeout(() => check.removeAttribute('data-stagger'), 400); }
        else state.selected.delete(item.investigation_id);
        card.dataset.selected = String(check.checked);
        renderBulk();
      });
      const pill = document.createElement('span'); pill.className = 'wb-status-pill'; pill.dataset.tone = toneFor(String(item.overall_status));
      pill.textContent = String(item.overall_status ?? '未提供 / UNKNOWN');
      const actions = document.createElement('div'); actions.className = 'wb-card-actions';
      const open = document.createElement('button'); open.type = 'button'; open.className = 'wb-mini-btn'; open.textContent = '读取';
      open.addEventListener('click', () => onOpen(item));
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'wb-mini-btn wb-mini-btn--danger'; remove.textContent = '移出视图';
      remove.title = '仅从本页列表隐藏，不改动后端记录';
      remove.addEventListener('click', () => { // 模式 8：弧线飞出
        card.dataset.flying = 'true';
        setTimeout(() => { state.hidden.add(item.investigation_id); state.selected.delete(item.investigation_id); render(); }, 540);
      });
      actions.append(open, remove);
      top.append(check, pill, actions);

      const q = document.createElement('p'); q.className = 'wb-card-q'; q.textContent = String(item.original_question || '').slice(0, 90);
      const meta = document.createElement('div'); meta.className = 'wb-card-meta';
      const metaBits = [item.current_stage, String(item.investigation_id || '').slice(0, 8) + '…', String(item.updated_at || '').replace('T', ' ').slice(0, 16)];
      if (item.error_code) metaBits.unshift(item.error_code);
      for (const v of metaBits) { const s = document.createElement('span'); s.textContent = String(v ?? '—'); meta.append(s); }
      card.append(top, q, meta);
      stack.append(card);
    }
  }
  function render() { renderTags(); renderCards(); renderBulk(); }
  return {
    root,
    setItems(items) { state.items = Array.isArray(items) ? items : []; state.hidden.clear(); render(); },
    refresh: render,
  };
}

function toneFor(status) {
  if (status === 'RUNNING') return 'running';
  if (status === 'SUCCEEDED') return 'ok';
  if (status === 'SUCCEEDED_WITH_WARNINGS' || status === 'INCOMPLETE') return 'warn';
  if (status === 'FAILED') return 'bad';
  if (status === 'REVIEW_REQUIRED') return 'review';
  return ''; // CANCELLED / 未知枚举：中性展示
}

export { applyTheme, currentThemeMode, openSettingsModal, rippleTo, clampText, makeSortable, createHistoryView, toneFor, toast, store };
