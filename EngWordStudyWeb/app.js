'use strict';

/* ---------- 상수 ---------- */

const STORAGE_KEY = 'vocabCards.v1';
const BACKUP_KEY = 'vocabCards.v1.backup';
const TERM_MAX_LEN = 100;
const MEANING_MAX_LEN = 200;
const CURRENT_VERSION = 2;

/* ---------- 상태 ---------- */

let appState = null;
let storageAvailable = true;
let isFlipped = false;
let isAnimating = false;
let loopToastTimer = null;

// 현재 필터 기준으로 학습 순환에 포함되는 단어 id 목록의 스냅샷.
// "다음"/"이전"/필터 변경/섞기/추가/삭제 시점에만 다시 계산한다(암기 완료
// 토글 직후에는 다시 계산하지 않아, 방금 완료 처리한 카드가 바로 사라지지
// 않게 한다).
let activeQueue = [];

// 단어 관리 화면에서 현재 인라인 수정 중인 단어의 id (수정 중이 아니면 null)
let editingWordId = null;

/* ---------- 유틸 ---------- */

function createId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function nowIso() {
  return new Date().toISOString();
}

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function isQuotaExceededError(error) {
  return (
    error instanceof DOMException &&
    (error.code === 22 ||
      error.code === 1014 ||
      error.name === 'QuotaExceededError' ||
      error.name === 'NS_ERROR_DOM_QUOTA_REACHED')
  );
}

function formatDateYYYYMMDD(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}${m}${d}`;
}

/* ---------- 데이터 모델 ---------- */

function createSampleWords() {
  const samples = [
    ['abundant', '풍부한'],
    ['consequence', '결과'],
    ['diligent', '근면한'],
    ['enhance', '향상시키다'],
    ['fundamental', '근본적인'],
    ['gradually', '점차적으로'],
    ['inevitable', '피할 수 없는'],
    ['justify', '정당화하다'],
    ['notion', '개념'],
    ['overcome', '극복하다'],
  ];
  const ts = nowIso();
  return samples.map(([term, meaning]) => ({
    id: createId(),
    term,
    meaning,
    memorized: false,
    createdAt: ts,
    updatedAt: ts,
  }));
}

function createDefaultState() {
  const words = createSampleWords();
  return {
    version: CURRENT_VERSION,
    words,
    filter: 'unmemorized',
    currentWordId: words.length > 0 ? words[0].id : null,
    order: null,
  };
}

function isValidWord(word) {
  return (
    word &&
    typeof word === 'object' &&
    typeof word.id === 'string' &&
    typeof word.term === 'string' &&
    typeof word.meaning === 'string' &&
    typeof word.memorized === 'boolean'
  );
}

// 버전과 무관하게 공통으로 요구되는 최소 구조. 여기 통과한 데이터만 migrateState로 넘긴다.
function isValidBaseState(state) {
  return (
    state &&
    typeof state === 'object' &&
    typeof state.version === 'number' &&
    Array.isArray(state.words) &&
    state.words.every(isValidWord) &&
    (state.filter === 'all' || state.filter === 'unmemorized') &&
    (state.currentWordId === null || typeof state.currentWordId === 'string')
  );
}

// 과거 버전의 저장 데이터를 현재 구조(CURRENT_VERSION)로 단계적으로 변환한다.
function migrateState(state) {
  let migrated = state;

  if (migrated.version === 1) {
    migrated = { ...migrated, version: 2, order: null };
  }

  // order 필드가 아예 없는 경우(수동 편집된 파일 등)를 대비한 방어적 보정
  if (migrated.order === undefined) {
    migrated = { ...migrated, order: null };
  }

  return migrated;
}

// 마이그레이션까지 끝난 뒤, 현재 버전 구조로 정확히 맞는지 검증한다.
function isValidCurrentState(state) {
  return (
    isValidBaseState(state) &&
    state.version === CURRENT_VERSION &&
    (state.order === null ||
      (Array.isArray(state.order) && state.order.every((id) => typeof id === 'string')))
  );
}

/* ---------- 저장/복원 ---------- */

function checkStorageAvailable() {
  try {
    const testKey = '__vocabCards_test__';
    window.localStorage.setItem(testKey, '1');
    window.localStorage.removeItem(testKey);
    return true;
  } catch (e) {
    return false;
  }
}

function saveState(state) {
  if (!storageAvailable) {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    if (isQuotaExceededError(e)) {
      showBanner('저장 공간이 부족해 저장하지 못했어요');
      return;
    }
    storageAvailable = false;
    showBanner('이 브라우저에서는 저장되지 않아요');
  }
}

function loadState() {
  if (!storageAvailable) {
    return createDefaultState();
  }

  let raw = null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch (e) {
    storageAvailable = false;
    return createDefaultState();
  }

  if (raw === null) {
    const state = createDefaultState();
    saveState(state);
    return state;
  }

  try {
    const parsed = JSON.parse(raw);
    if (!isValidBaseState(parsed)) {
      throw new Error('저장된 데이터 구조가 올바르지 않습니다.');
    }
    const migrated = migrateState(parsed);
    if (!isValidCurrentState(migrated)) {
      throw new Error('저장된 데이터를 최신 구조로 변환할 수 없습니다.');
    }
    if (migrated.version !== parsed.version) {
      // 마이그레이션이 실제로 일어났다면 변환된 구조를 바로 저장해둔다
      saveState(migrated);
    }
    return migrated;
  } catch (e) {
    try {
      window.localStorage.setItem(BACKUP_KEY, raw);
    } catch (backupError) {
      /* 백업 저장에 실패해도 샘플 데이터로는 계속 진행한다 */
    }
    showBanner('저장된 데이터를 읽을 수 없어 샘플 단어로 다시 시작합니다.');
    const state = createDefaultState();
    saveState(state);
    return state;
  }
}

/* ---------- 학습 대상 큐(순서 + 필터 적용) ---------- */

// order가 지정되어 있으면 그 순서로, order에 없는 단어(새로 추가된 단어 등)는
// 끝에 자연스럽게 덧붙인다. order가 없으면 원래 추가 순서를 그대로 쓴다.
function getWordsInOrder() {
  if (!appState.order) {
    return appState.words;
  }
  const byId = new Map(appState.words.map((word) => [word.id, word]));
  const seen = new Set();
  const ordered = [];
  appState.order.forEach((id) => {
    const word = byId.get(id);
    if (word && !seen.has(id)) {
      ordered.push(word);
      seen.add(id);
    }
  });
  appState.words.forEach((word) => {
    if (!seen.has(word.id)) {
      ordered.push(word);
    }
  });
  return ordered;
}

function computeFilteredWords() {
  const source = getWordsInOrder();
  if (appState.filter === 'unmemorized') {
    return source.filter((word) => !word.memorized);
  }
  return source.slice();
}

function rebuildQueue() {
  activeQueue = computeFilteredWords().map((word) => word.id);
}

function ensureCurrentInQueue() {
  if (activeQueue.length === 0) {
    appState.currentWordId = null;
    return;
  }
  if (!activeQueue.includes(appState.currentWordId)) {
    appState.currentWordId = activeQueue[0];
  }
}

// 새 단어를 words(그리고 order가 설정돼 있다면 order 끝)에 추가한다.
function pushWords(newWords) {
  appState.words.push(...newWords);
  if (appState.order !== null) {
    appState.order.push(...newWords.map((word) => word.id));
  }
}

function removeWordFromOrder(id) {
  if (appState.order !== null) {
    appState.order = appState.order.filter((wordId) => wordId !== id);
  }
}

/* ---------- 상태 조회 ---------- */

function getCurrentWord() {
  if (!appState.currentWordId) {
    return null;
  }
  return appState.words.find((word) => word.id === appState.currentWordId) || null;
}

/* ---------- DOM 참조 ---------- */

const el = {};

function cacheElements() {
  el.banner = document.getElementById('app-banner');
  el.manageBtn = document.getElementById('manage-btn');
  el.backBtn = document.getElementById('back-btn');

  el.progressSection = document.getElementById('progress-section');
  el.progressText = document.getElementById('progress-text');
  el.progressBarFill = document.getElementById('progress-bar-fill');
  el.progressBar = document.querySelector('.progress-bar');
  el.filterAllBtn = document.getElementById('filter-all-btn');
  el.filterUnmemorizedBtn = document.getElementById('filter-unmemorized-btn');
  el.shuffleBtn = document.getElementById('shuffle-btn');
  el.clearOrderBtn = document.getElementById('clear-order-btn');

  el.emptyState = document.getElementById('empty-state');
  el.emptyAddBtn = document.getElementById('empty-add-btn');
  el.allDoneState = document.getElementById('all-done-state');
  el.showAllBtn = document.getElementById('show-all-btn');
  el.resetMemorizedBtnAllDone = document.getElementById('reset-memorized-btn-alldone');

  el.cardArea = document.getElementById('card-area');
  el.flashCard = document.getElementById('flash-card');
  el.badgeDone = document.getElementById('badge-done');
  el.term = el.flashCard.querySelector('.term');
  el.meaning = el.flashCard.querySelector('.meaning');
  el.termSmall = el.flashCard.querySelector('.term-small');
  el.srAnnounce = document.getElementById('sr-announce');
  el.positionIndicator = document.getElementById('position-indicator');
  el.loopToast = document.getElementById('loop-toast');
  el.shortcutHint = document.getElementById('shortcut-hint');
  el.toggleMemorizedBtn = document.getElementById('toggle-memorized-btn');
  el.prevBtn = document.getElementById('prev-btn');
  el.nextBtn = document.getElementById('next-btn');
  el.studyScreen = document.getElementById('study-screen');
  el.manageScreen = document.getElementById('manage-screen');
  el.addForm = document.getElementById('add-form');
  el.termInput = document.getElementById('term-input');
  el.meaningInput = document.getElementById('meaning-input');
  el.addBtn = document.getElementById('add-btn');
  el.formHint = document.getElementById('form-hint');

  el.bulkInput = document.getElementById('bulk-input');
  el.bulkAddBtn = document.getElementById('bulk-add-btn');
  el.bulkResult = document.getElementById('bulk-result');

  el.exportBtn = document.getElementById('export-btn');
  el.importBtn = document.getElementById('import-btn');
  el.importFileInput = document.getElementById('import-file-input');

  el.wordCountLabel = document.getElementById('word-count-label');
  el.wordList = document.getElementById('word-list');
  el.resetMemorizedBtn = document.getElementById('reset-memorized-btn');
}

/* ---------- 렌더링 ---------- */

function showBanner(message) {
  el.banner.textContent = message;
  el.banner.hidden = false;
}

function setCardFlipped(flipped, options) {
  const animate = options && options.animate === false ? false : true;
  if (!animate) {
    el.flashCard.classList.add('no-anim');
  }
  isFlipped = flipped;
  el.flashCard.classList.toggle('flipped', flipped);
  el.flashCard.setAttribute('aria-pressed', String(flipped));
  if (!animate) {
    void el.flashCard.offsetWidth;
    requestAnimationFrame(() => {
      el.flashCard.classList.remove('no-anim');
    });
  }
}

function announceCardFace() {
  const word = getCurrentWord();
  if (!word) {
    el.srAnnounce.textContent = '';
    return;
  }
  el.srAnnounce.textContent = isFlipped ? `뜻: ${word.meaning}` : `영단어: ${word.term}`;
}

function renderPosition() {
  if (appState.currentWordId === null || activeQueue.length === 0) {
    el.positionIndicator.textContent = '';
    return;
  }
  const idx = activeQueue.indexOf(appState.currentWordId);
  const shown = idx === -1 ? 1 : idx + 1;
  el.positionIndicator.textContent = `${shown} / ${activeQueue.length}`;
}

function renderProgress() {
  const total = appState.words.length;
  const completed = appState.words.filter((word) => word.memorized).length;
  el.progressText.textContent = `완료 ${completed} / 전체 ${total}`;
  const pct = total === 0 ? 0 : Math.round((completed / total) * 100);
  el.progressBarFill.style.width = `${pct}%`;
  if (el.progressBar) {
    el.progressBar.setAttribute('aria-valuenow', String(pct));
  }
}

function renderFilterControls() {
  const isAll = appState.filter === 'all';
  el.filterAllBtn.classList.toggle('active', isAll);
  el.filterAllBtn.setAttribute('aria-pressed', String(isAll));
  el.filterUnmemorizedBtn.classList.toggle('active', !isAll);
  el.filterUnmemorizedBtn.setAttribute('aria-pressed', String(!isAll));
}

function renderCard() {
  const totalWords = appState.words.length;

  if (totalWords === 0) {
    el.progressSection.hidden = true;
    el.emptyState.hidden = false;
    el.allDoneState.hidden = true;
    el.cardArea.hidden = true;
    el.toggleMemorizedBtn.disabled = true;
    el.prevBtn.disabled = true;
    el.nextBtn.disabled = true;
    el.positionIndicator.textContent = '';
    el.srAnnounce.textContent = '';
    return;
  }

  el.progressSection.hidden = false;

  if (activeQueue.length === 0) {
    // 필터가 "미완료만"이고 모든 단어를 암기 완료한 상태
    el.emptyState.hidden = true;
    el.allDoneState.hidden = false;
    el.cardArea.hidden = true;
    el.toggleMemorizedBtn.disabled = true;
    el.prevBtn.disabled = true;
    el.nextBtn.disabled = true;
    el.positionIndicator.textContent = '';
    el.srAnnounce.textContent = '';
    return;
  }

  el.emptyState.hidden = true;
  el.allDoneState.hidden = true;
  el.cardArea.hidden = false;
  el.toggleMemorizedBtn.disabled = false;
  el.prevBtn.disabled = false;
  el.nextBtn.disabled = false;

  const word = getCurrentWord();
  el.term.textContent = word.term;
  el.meaning.textContent = word.meaning;
  el.termSmall.textContent = word.term;
  el.badgeDone.hidden = !word.memorized;

  el.flashCard.classList.toggle('flipped', isFlipped);
  el.flashCard.setAttribute('aria-pressed', String(isFlipped));

  el.toggleMemorizedBtn.setAttribute('aria-pressed', String(word.memorized));
  el.toggleMemorizedBtn.classList.toggle('active', word.memorized);

  renderPosition();
  announceCardFace();
}

function createWordViewRow(word) {
  const li = document.createElement('li');
  li.className = 'word-item';
  li.dataset.id = word.id;

  const main = document.createElement('div');
  main.className = 'word-item-main';

  const termSpan = document.createElement('span');
  termSpan.className = 'word-item-term';
  termSpan.textContent = word.term;

  const meaningSpan = document.createElement('span');
  meaningSpan.className = 'word-item-meaning';
  meaningSpan.textContent = word.meaning;

  const statusSpan = document.createElement('span');
  statusSpan.className = 'word-item-status';
  statusSpan.textContent = word.memorized ? '완료' : '학습 중';

  main.append(termSpan, meaningSpan, statusSpan);

  const actions = document.createElement('div');
  actions.className = 'word-item-actions';

  const editBtn = document.createElement('button');
  editBtn.type = 'button';
  editBtn.className = 'btn btn-small btn-secondary edit-btn';
  editBtn.textContent = '수정';

  const deleteBtn = document.createElement('button');
  deleteBtn.type = 'button';
  deleteBtn.className = 'btn btn-small btn-danger delete-btn';
  deleteBtn.textContent = '삭제';

  actions.append(editBtn, deleteBtn);
  li.append(main, actions);
  return li;
}

function createWordEditRow(word) {
  const li = document.createElement('li');
  li.className = 'word-item word-item-editing';
  li.dataset.id = word.id;

  const form = document.createElement('form');
  form.className = 'edit-form';
  form.noValidate = true;

  const row = document.createElement('div');
  row.className = 'edit-form-row';

  const termInput = document.createElement('input');
  termInput.type = 'text';
  termInput.className = 'edit-term-input';
  termInput.maxLength = TERM_MAX_LEN;
  termInput.value = word.term;
  termInput.setAttribute('aria-label', '영단어 수정');

  const meaningInput = document.createElement('input');
  meaningInput.type = 'text';
  meaningInput.className = 'edit-meaning-input';
  meaningInput.maxLength = MEANING_MAX_LEN;
  meaningInput.value = word.meaning;
  meaningInput.setAttribute('aria-label', '뜻 수정');

  row.append(termInput, meaningInput);

  const actions = document.createElement('div');
  actions.className = 'edit-form-actions';

  const saveBtn = document.createElement('button');
  saveBtn.type = 'submit';
  saveBtn.className = 'btn btn-small btn-primary';
  saveBtn.textContent = '저장';

  const cancelBtn = document.createElement('button');
  cancelBtn.type = 'button';
  cancelBtn.className = 'btn btn-small btn-secondary cancel-edit-btn';
  cancelBtn.textContent = '취소';

  actions.append(saveBtn, cancelBtn);

  const hint = document.createElement('p');
  hint.className = 'hint edit-hint';
  hint.setAttribute('role', 'alert');
  hint.textContent = '영단어와 뜻을 모두 입력해 주세요';
  hint.hidden = true;

  form.append(row, actions, hint);
  li.append(form);
  return li;
}

function renderWordList() {
  el.wordList.innerHTML = '';
  el.wordCountLabel.textContent = `전체 ${appState.words.length}개`;

  if (appState.words.length === 0) {
    const li = document.createElement('li');
    li.className = 'word-list-empty';
    li.textContent = '등록된 단어가 없습니다.';
    el.wordList.appendChild(li);
    return;
  }

  // 최신 추가 순으로 표시 (원본 배열의 순서는 바꾸지 않는다)
  const sorted = appState.words.slice().reverse();

  sorted.forEach((word) => {
    const row = word.id === editingWordId ? createWordEditRow(word) : createWordViewRow(word);
    el.wordList.appendChild(row);
  });

  if (editingWordId !== null) {
    const input = el.wordList.querySelector(`[data-id="${CSS.escape(editingWordId)}"] .edit-term-input`);
    if (input) {
      input.focus();
    }
  }
}

function updateAddButtonState() {
  const valid = el.termInput.value.trim().length > 0 && el.meaningInput.value.trim().length > 0;
  el.addBtn.disabled = !valid;
}

function showScreen(screen) {
  el.studyScreen.hidden = screen !== 'study';
  el.manageScreen.hidden = screen !== 'manage';
  if (screen === 'manage') {
    renderWordList();
    updateAddButtonState();
  }
}

/* ---------- 동작: 카드 학습 ---------- */

function flipCard() {
  if (isAnimating || !getCurrentWord()) {
    return;
  }

  const reduceMotion = prefersReducedMotion();
  setCardFlipped(!isFlipped, { animate: !reduceMotion });
  announceCardFace();

  if (!reduceMotion) {
    isAnimating = true;
    window.setTimeout(() => {
      isAnimating = false;
    }, 450);
  }
}

function showLoopToast() {
  el.loopToast.hidden = false;
  window.clearTimeout(loopToastTimer);
  loopToastTimer = window.setTimeout(() => {
    el.loopToast.hidden = true;
  }, 1600);
}

function goNext() {
  if (activeQueue.length === 0) {
    return;
  }

  const staleQueue = activeQueue;
  const idx = staleQueue.indexOf(appState.currentWordId);
  const safeIdx = idx === -1 ? 0 : idx;
  const candidateId = staleQueue[(safeIdx + 1) % staleQueue.length];
  const wrapped = staleQueue.length > 1 && (safeIdx + 1) % staleQueue.length === 0;

  // 방금 암기 완료 처리된 카드가 있다면 여기서 비로소 순환에서 제외된다.
  rebuildQueue();

  if (activeQueue.length === 0) {
    appState.currentWordId = null;
  } else if (activeQueue.includes(candidateId)) {
    appState.currentWordId = candidateId;
  } else {
    appState.currentWordId = activeQueue[0];
  }

  setCardFlipped(false, { animate: false });
  renderCard();
  saveState(appState);

  if (appState.currentWordId !== null && wrapped) {
    showLoopToast();
  }
}

function goPrev() {
  if (activeQueue.length === 0) {
    return;
  }

  const staleQueue = activeQueue;
  const idx = staleQueue.indexOf(appState.currentWordId);
  const safeIdx = idx === -1 ? 0 : idx;
  const candidateId = staleQueue[(safeIdx - 1 + staleQueue.length) % staleQueue.length];

  rebuildQueue();

  if (activeQueue.length === 0) {
    appState.currentWordId = null;
  } else if (activeQueue.includes(candidateId)) {
    appState.currentWordId = candidateId;
  } else {
    appState.currentWordId = activeQueue[activeQueue.length - 1];
  }

  setCardFlipped(false, { animate: false });
  renderCard();
  saveState(appState);
}

function toggleMemorized() {
  const word = getCurrentWord();
  if (!word) {
    return;
  }
  word.memorized = !word.memorized;
  word.updatedAt = nowIso();
  saveState(appState);
  // activeQueue는 일부러 다시 계산하지 않는다: "다음"/"이전"을 누르기
  // 전까지는 카드와 진행 위치가 그대로 유지되어야 한다.
  renderProgress();
  renderCard();
}

/* ---------- 동작: 필터·순서 ---------- */

function setFilter(filter) {
  if (appState.filter === filter) {
    return;
  }
  appState.filter = filter;
  rebuildQueue();
  ensureCurrentInQueue();
  setCardFlipped(false, { animate: false });
  renderFilterControls();
  renderCard();
  saveState(appState);
}

function shuffleOrder() {
  const ids = appState.words.map((word) => word.id);
  for (let i = ids.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [ids[i], ids[j]] = [ids[j], ids[i]];
  }
  appState.order = ids;
  rebuildQueue();
  ensureCurrentInQueue();
  setCardFlipped(false, { animate: false });
  renderCard();
  saveState(appState);
}

function clearOrder() {
  if (appState.order === null) {
    return;
  }
  appState.order = null;
  rebuildQueue();
  ensureCurrentInQueue();
  setCardFlipped(false, { animate: false });
  renderCard();
  saveState(appState);
}

/* ---------- 동작: 암기 완료 모두 초기화 ---------- */

function resetAllMemorized() {
  const confirmed = window.confirm('모든 단어의 암기 완료 상태를 초기화할까요?');
  if (!confirmed) {
    return;
  }
  const ts = nowIso();
  appState.words.forEach((word) => {
    if (word.memorized) {
      word.memorized = false;
      word.updatedAt = ts;
    }
  });
  rebuildQueue();
  ensureCurrentInQueue();
  setCardFlipped(false, { animate: false });
  saveState(appState);
  renderProgress();
  renderWordList();
  renderCard();
}

/* ---------- 동작: 단어 추가/수정/삭제 ---------- */

function createAndAddWord(term, meaning) {
  const ts = nowIso();
  const word = {
    id: createId(),
    term,
    meaning,
    memorized: false,
    createdAt: ts,
    updatedAt: ts,
  };

  pushWords([word]);
  rebuildQueue();
  ensureCurrentInQueue();

  saveState(appState);
  renderProgress();
  renderWordList();
  renderCard();
}

function onAddSubmit(event) {
  event.preventDefault();

  const term = el.termInput.value.trim().slice(0, TERM_MAX_LEN);
  const meaning = el.meaningInput.value.trim().slice(0, MEANING_MAX_LEN);

  if (!term || !meaning) {
    el.formHint.hidden = false;
    return;
  }
  el.formHint.hidden = true;

  const isDuplicate = appState.words.some(
    (word) => word.term.trim().toLowerCase() === term.toLowerCase()
  );
  if (isDuplicate) {
    const proceed = window.confirm('이미 있는 단어예요. 그래도 추가할까요?');
    if (!proceed) {
      return;
    }
  }

  createAndAddWord(term, meaning);

  el.addForm.reset();
  updateAddButtonState();
  el.termInput.focus();
}

function updateWord(id, rawTerm, rawMeaning) {
  const term = rawTerm.trim().slice(0, TERM_MAX_LEN);
  const meaning = rawMeaning.trim().slice(0, MEANING_MAX_LEN);
  if (!term || !meaning) {
    return false;
  }
  const word = appState.words.find((w) => w.id === id);
  if (!word) {
    return false;
  }
  word.term = term;
  word.meaning = meaning;
  word.updatedAt = nowIso();
  saveState(appState);
  renderProgress();
  renderCard();
  return true;
}

function deleteWord(id) {
  const oldQueue = activeQueue.slice();
  const idx = appState.words.findIndex((w) => w.id === id);
  if (idx === -1) {
    return;
  }

  appState.words.splice(idx, 1);
  removeWordFromOrder(id);
  if (editingWordId === id) {
    editingWordId = null;
  }

  rebuildQueue();

  if (appState.currentWordId === id) {
    const oldIdx = oldQueue.indexOf(id);
    let resolved = false;
    if (oldIdx !== -1 && oldQueue.length > 1) {
      const candidateId = oldQueue[(oldIdx + 1) % oldQueue.length];
      if (candidateId !== id && activeQueue.includes(candidateId)) {
        appState.currentWordId = candidateId;
        resolved = true;
      }
    }
    if (!resolved) {
      ensureCurrentInQueue();
    }
  } else {
    ensureCurrentInQueue();
  }

  setCardFlipped(false, { animate: false });
  saveState(appState);
  renderProgress();
  renderWordList();
  renderCard();
}

/* ---------- 단어 목록 이벤트(수정/삭제) ---------- */

function onWordListClick(event) {
  const editBtn = event.target.closest('.edit-btn');
  if (editBtn) {
    const li = editBtn.closest('[data-id]');
    editingWordId = li.dataset.id;
    renderWordList();
    return;
  }

  const cancelBtn = event.target.closest('.cancel-edit-btn');
  if (cancelBtn) {
    editingWordId = null;
    renderWordList();
    return;
  }

  const deleteBtn = event.target.closest('.delete-btn');
  if (deleteBtn) {
    const li = deleteBtn.closest('[data-id]');
    const id = li.dataset.id;
    const word = appState.words.find((w) => w.id === id);
    if (!word) {
      return;
    }
    const confirmed = window.confirm(`"${word.term}" 단어를 삭제할까요?`);
    if (!confirmed) {
      return;
    }
    deleteWord(id);
  }
}

function onWordListSubmit(event) {
  const form = event.target.closest('.edit-form');
  if (!form) {
    return;
  }
  event.preventDefault();

  const li = form.closest('[data-id]');
  const id = li.dataset.id;
  const termInput = form.querySelector('.edit-term-input');
  const meaningInput = form.querySelector('.edit-meaning-input');

  const ok = updateWord(id, termInput.value, meaningInput.value);
  if (!ok) {
    form.querySelector('.edit-hint').hidden = false;
    return;
  }

  editingWordId = null;
  renderWordList();
}

/* ---------- 동작: 일괄 추가 ---------- */

// 한 줄을 "영단어\t뜻"(우선) 또는 "영단어,뜻" 형식으로 해석한다.
// 뜻에 쉼표가 포함될 수 있으므로 첫 번째 구분자 이후는 모두 뜻으로 취급한다.
function parseBulkLine(line) {
  const trimmedLine = line.replace(/\r$/, '');
  if (trimmedLine.trim() === '') {
    return { blank: true };
  }

  let rawTerm;
  let rawMeaning;
  const tabIdx = trimmedLine.indexOf('\t');
  if (tabIdx !== -1) {
    rawTerm = trimmedLine.slice(0, tabIdx);
    rawMeaning = trimmedLine.slice(tabIdx + 1);
  } else {
    const commaIdx = trimmedLine.indexOf(',');
    if (commaIdx === -1) {
      return { invalid: true };
    }
    rawTerm = trimmedLine.slice(0, commaIdx);
    rawMeaning = trimmedLine.slice(commaIdx + 1);
  }

  const term = rawTerm.trim().slice(0, TERM_MAX_LEN);
  const meaning = rawMeaning.trim().slice(0, MEANING_MAX_LEN);
  if (!term || !meaning) {
    return { invalid: true };
  }
  return { term, meaning };
}

function onBulkAddClick() {
  const lines = el.bulkInput.value.split(/\r?\n/);
  const existingTermsLower = new Set(appState.words.map((word) => word.term.trim().toLowerCase()));

  let invalidCount = 0;
  let duplicateCount = 0;
  const newWords = [];
  const ts = nowIso();

  lines.forEach((line) => {
    const parsed = parseBulkLine(line);
    if (parsed.blank) {
      return;
    }
    if (parsed.invalid) {
      invalidCount++;
      return;
    }
    const key = parsed.term.toLowerCase();
    if (existingTermsLower.has(key)) {
      duplicateCount++;
      return;
    }
    existingTermsLower.add(key);
    newWords.push({
      id: createId(),
      term: parsed.term,
      meaning: parsed.meaning,
      memorized: false,
      createdAt: ts,
      updatedAt: ts,
    });
  });

  if (newWords.length > 0) {
    pushWords(newWords);
    rebuildQueue();
    ensureCurrentInQueue();
    saveState(appState);
    renderProgress();
    renderWordList();
    renderCard();
  }

  const skippedCount = invalidCount + duplicateCount;
  el.bulkResult.textContent = `${newWords.length}개 추가, ${skippedCount}개 건너뜀 (중복 ${duplicateCount}개)`;
  el.bulkResult.hidden = false;
  el.bulkInput.value = '';
}

/* ---------- 동작: JSON 내보내기/가져오기 ---------- */

function exportData() {
  const filename = `vocab-cards-${formatDateYYYYMMDD(new Date())}.json`;
  const json = JSON.stringify(appState, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function onImportFileChange(event) {
  const input = event.target;
  const file = input.files && input.files[0];
  input.value = ''; // 같은 파일을 다시 선택할 수 있도록 초기화

  if (!file) {
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    let parsed;
    try {
      parsed = JSON.parse(String(reader.result));
    } catch (e) {
      window.alert('올바른 JSON 파일이 아니에요.');
      return;
    }

    if (!isValidBaseState(parsed)) {
      window.alert('파일 구조가 올바르지 않아요.');
      return;
    }
    const migrated = migrateState(parsed);
    if (!isValidCurrentState(migrated)) {
      window.alert('파일 구조가 올바르지 않아요.');
      return;
    }

    const confirmed = window.confirm('현재 데이터를 덮어쓸까요?');
    if (!confirmed) {
      return;
    }

    appState = migrated;
    editingWordId = null;
    rebuildQueue();
    ensureCurrentInQueue();
    setCardFlipped(false, { animate: false });
    saveState(appState);
    renderFilterControls();
    renderProgress();
    renderWordList();
    renderCard();
  };
  reader.onerror = () => {
    window.alert('파일을 읽는 중 문제가 발생했어요.');
  };
  reader.readAsText(file);
}

/* ---------- 키보드 단축키 (학습 화면에서만) ---------- */

function onGlobalKeyDown(event) {
  if (el.studyScreen.hidden) {
    return;
  }
  if (event.ctrlKey || event.metaKey || event.altKey) {
    return;
  }

  const target = event.target;
  const tag = target && target.tagName ? target.tagName.toLowerCase() : '';
  const isTyping = tag === 'input' || tag === 'textarea' || (target && target.isContentEditable);
  if (isTyping) {
    return;
  }

  if (event.key === ' ' || event.key === 'Spacebar') {
    if (tag === 'button') {
      // 포커스된 버튼 자체의 기본 Space 동작(그 버튼 클릭)에 맡긴다
      return;
    }
    event.preventDefault();
    flipCard();
    return;
  }

  if (event.key === 'ArrowRight') {
    event.preventDefault();
    goNext();
    return;
  }

  if (event.key === 'ArrowLeft') {
    event.preventDefault();
    goPrev();
    return;
  }

  if (event.key === 'm' || event.key === 'M') {
    event.preventDefault();
    toggleMemorized();
  }
}

/* ---------- 여러 탭 동기화 ---------- */

function onStorageEvent(event) {
  if (event.key !== STORAGE_KEY || event.newValue === null) {
    return;
  }

  let parsed;
  try {
    parsed = JSON.parse(event.newValue);
  } catch (e) {
    return;
  }
  if (!isValidBaseState(parsed)) {
    return;
  }
  const migrated = migrateState(parsed);
  if (!isValidCurrentState(migrated)) {
    return;
  }

  appState = migrated;
  if (editingWordId !== null && !appState.words.some((w) => w.id === editingWordId)) {
    editingWordId = null;
  }

  rebuildQueue();
  ensureCurrentInQueue();
  setCardFlipped(false, { animate: false });
  renderFilterControls();
  renderProgress();
  renderCard();
  if (!el.manageScreen.hidden) {
    renderWordList();
  }
}

/* ---------- PWA: 서비스 워커 등록 ---------- */

function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) {
    return;
  }
  if (window.location.protocol === 'file:') {
    return; // 로컬 파일로 열었을 때는 등록을 건너뛴다
  }
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./service-worker.js').catch(() => {
      /* 서비스 워커 등록 실패는 핵심 기능에 영향을 주지 않으므로 조용히 무시한다 */
    });
  });
}

/* ---------- 이벤트 바인딩 ---------- */

function attachEventListeners() {
  el.flashCard.addEventListener('click', flipCard);
  el.prevBtn.addEventListener('click', goPrev);
  el.nextBtn.addEventListener('click', goNext);
  el.toggleMemorizedBtn.addEventListener('click', toggleMemorized);

  el.manageBtn.addEventListener('click', () => showScreen('manage'));
  el.backBtn.addEventListener('click', () => showScreen('study'));
  el.emptyAddBtn.addEventListener('click', () => showScreen('manage'));
  el.showAllBtn.addEventListener('click', () => setFilter('all'));
  el.resetMemorizedBtnAllDone.addEventListener('click', resetAllMemorized);

  el.filterAllBtn.addEventListener('click', () => setFilter('all'));
  el.filterUnmemorizedBtn.addEventListener('click', () => setFilter('unmemorized'));
  el.shuffleBtn.addEventListener('click', shuffleOrder);
  el.clearOrderBtn.addEventListener('click', clearOrder);

  el.addForm.addEventListener('submit', onAddSubmit);
  el.termInput.addEventListener('input', () => {
    updateAddButtonState();
    el.formHint.hidden = true;
  });
  el.meaningInput.addEventListener('input', () => {
    updateAddButtonState();
    el.formHint.hidden = true;
  });

  el.wordList.addEventListener('click', onWordListClick);
  el.wordList.addEventListener('submit', onWordListSubmit);

  el.bulkAddBtn.addEventListener('click', onBulkAddClick);

  el.exportBtn.addEventListener('click', exportData);
  el.importBtn.addEventListener('click', () => el.importFileInput.click());
  el.importFileInput.addEventListener('change', onImportFileChange);

  el.resetMemorizedBtn.addEventListener('click', resetAllMemorized);

  document.addEventListener('keydown', onGlobalKeyDown);
  window.addEventListener('storage', onStorageEvent);
}

/* ---------- 초기화 ---------- */

function init() {
  cacheElements();

  storageAvailable = checkStorageAvailable();
  if (!storageAvailable) {
    showBanner('이 브라우저에서는 저장되지 않아요');
  }

  appState = loadState();

  rebuildQueue();
  ensureCurrentInQueue();

  setCardFlipped(false, { animate: false });
  renderFilterControls();
  renderProgress();
  renderCard();
  renderWordList();
  updateAddButtonState();

  attachEventListeners();
  registerServiceWorker();
}

document.addEventListener('DOMContentLoaded', init);
