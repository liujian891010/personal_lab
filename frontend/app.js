const appNode = document.querySelector("#app");
const toastNode = document.querySelector("#toast");
const healthPillNode = document.querySelector("#health-pill");
const sessionSlotNode = document.querySelector("#session-slot");
const topbarNode = document.querySelector(".topbar");
const appShellNode = document.querySelector(".app-shell");
const EXTERNAL_APPKEY_LOGIN_URL = "https://sg-al-cwork-web.mediportal.com.cn/user/login/appkey";
const DEFAULT_APPKEY = "A2d5J8fCDNHT3Vbkv3dndsEzoQ3zMNsv";
const EXTERNAL_APP_CODE = "personal_lab";

const state = {
  appkey: null,
  health: null,
  currentUser: null,
  askResult: null,
  askWritebackResult: null,
  adminEvents: [],
};

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const statusToneMap = {
  success: "good",
  ok: "good",
  active: "good",
  published: "good",
  created: "good",
  open: "warn",
  needs_review: "warn",
  degraded: "bad",
  failed: "bad",
  conflicted: "bad",
  resolved: "good",
  draft: "neutral",
  done: "good",
  low: "neutral",
  medium: "warn",
  high: "bad",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function stripHtml(value) {
  return String(value ?? "").replace(/<[^>]+>/g, "");
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function toneForStatus(value) {
  return statusToneMap[String(value || "").toLowerCase()] || "neutral";
}

function badge(label, tone = "neutral") {
  return `<span class="badge ${tone}">${escapeHtml(label)}</span>`;
}

function chip(label, tone = "neutral") {
  return `<span class="chip ${tone}">${escapeHtml(label)}</span>`;
}

function linkButton(href, label) {
  return `<a class="ghost-link" href="${href}">${escapeHtml(label)}</a>`;
}

function serializeParams(params) {
  const next = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return;
    }
    const text = String(value).trim();
    if (!text) {
      return;
    }
    next.set(key, text);
  });
  return next.toString();
}

function buildHash(path, params = {}) {
  const search = serializeParams(params);
  return `#${path}${search ? `?${search}` : ""}`;
}

function isPublicApiPath(path) {
  return String(path || "").startsWith("/api/public/");
}

async function copyTextToClipboard(value) {
  const text = String(value ?? "");
  if (!text) {
    throw new Error("Nothing to copy.");
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  window.prompt("Copy this link", text);
}

function getRoute() {
  const rawHash = location.hash.replace(/^#/, "") || "/reports";
  const [pathPart, searchPart = ""] = rawHash.split("?");
  const parts = pathPart.split("/").filter(Boolean).map((part) => decodeURIComponent(part));
  return {
    section: parts[0] || "reports",
    detail: parts[1] || null,
    params: new URLSearchParams(searchPart),
  };
}

function setActiveNav(section) {
  document.querySelectorAll(".main-nav a").forEach((anchor) => {
    anchor.classList.toggle("active", anchor.dataset.section === section);
  });
}

function showToast(message, tone = "neutral") {
  toastNode.textContent = message;
  toastNode.className = `toast ${tone}`;
  toastNode.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toastNode.hidden = true;
  }, 3200);
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: {
      Accept: "application/json",
      ...(state.appkey && path.startsWith("/api/") ? { "X-Appkey": state.appkey } : {}),
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch (error) {
      void error;
    }
    const apiError = new ApiError(detail, response.status);
    if (response.status === 401 && path !== "/api/auth/me" && path !== "/api/auth/login" && !isPublicApiPath(path)) {
      await handleUnauthorized(detail);
    }
    throw apiError;
  }

  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

function apiGet(path) {
  return apiRequest(path);
}

function apiPost(path, payload) {
  return apiRequest(path, { method: "POST", body: JSON.stringify(payload) });
}

async function apiRequestText(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: {
      Accept: "text/plain, application/json",
      ...(state.appkey && path.startsWith("/api/") ? { "X-Appkey": state.appkey } : {}),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch (error) {
      void error;
    }
    const apiError = new ApiError(detail, response.status);
    if (response.status === 401 && !isPublicApiPath(path)) {
      await handleUnauthorized(detail);
    }
    throw apiError;
  }

  return response.text();
}

async function apiPostForm(path, formData) {
  const response = await fetch(path, {
    credentials: "same-origin",
    method: "POST",
    body: formData,
    headers: {
      Accept: "application/json",
      ...(state.appkey && path.startsWith("/api/") ? { "X-Appkey": state.appkey } : {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch (error) {
      void error;
    }
    const apiError = new ApiError(detail, response.status);
    if (response.status === 401 && !isPublicApiPath(path)) {
      await handleUnauthorized(detail);
    }
    throw apiError;
  }

  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

function stripFrontmatter(content) {
  const text = String(content ?? "");
  if (!text.startsWith("---\n")) {
    return text;
  }
  const end = text.indexOf("\n---\n", 4);
  if (end === -1) {
    return text;
  }
  return text.slice(end + 5).trim();
}

function renderInlineMarkdown(text) {
  const placeholders = [];
  const stash = (html) => {
    const token = `__MD_TOKEN_${placeholders.length}__`;
    placeholders.push(html);
    return token;
  };

  let rendered = escapeHtml(String(text ?? ""));

  rendered = rendered.replace(/`([^`]+)`/g, (_, code) => stash(`<code>${escapeHtml(code)}</code>`));
  rendered = rendered.replace(
    /!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]+)")?\)/g,
    (_, alt, src, title) =>
      stash(
        `<img src="${escapeHtml(src)}" alt="${escapeHtml(alt)}"${title ? ` title="${escapeHtml(title)}"` : ""} />`
      )
  );
  rendered = rendered.replace(
    /\[([^\]]+)\]\(([^)\s]+)(?:\s+"([^"]+)")?\)/g,
    (_, label, href, title) =>
      stash(
        `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer"${title ? ` title="${escapeHtml(title)}"` : ""}>${escapeHtml(label)}</a>`
      )
  );
  rendered = rendered.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  rendered = rendered.replace(/(^|[^\*])\*([^*]+)\*(?!\*)/g, "$1<em>$2</em>");
  rendered = rendered.replace(/~~([^~]+)~~/g, "<del>$1</del>");

  placeholders.forEach((html, index) => {
    rendered = rendered.replace(`__MD_TOKEN_${index}__`, html);
  });

  return rendered;
}

function isTableRow(line) {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|");
}

function isTableDivider(line) {
  return /^\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?$/.test(line.trim());
}

function splitTableCells(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function renderMarkdownLite(markdown) {
  const source = String(markdown ?? "").replace(/\r\n/g, "\n");
  const lines = source.split("\n");
  let html = "";
  let listType = null;
  let inCode = false;
  let codeBuffer = [];
  let paragraphBuffer = [];
  let blockquoteBuffer = [];

  const flushParagraph = () => {
    if (!paragraphBuffer.length) {
      return;
    }
    html += `<p>${renderInlineMarkdown(paragraphBuffer.join(" "))}</p>`;
    paragraphBuffer = [];
  };

  const closeCode = () => {
    if (inCode) {
      html += `<pre><code>${escapeHtml(codeBuffer.join("\n"))}</code></pre>`;
      inCode = false;
      codeBuffer = [];
    }
  };

  const closeList = () => {
    if (!listType) {
      return;
    }
    html += listType === "ol" ? "</ol>" : "</ul>";
    listType = null;
  };

  const flushBlockquote = () => {
    if (!blockquoteBuffer.length) {
      return;
    }
    html += `<blockquote>${blockquoteBuffer.map((line) => `<p>${renderInlineMarkdown(line)}</p>`).join("")}</blockquote>`;
    blockquoteBuffer = [];
  };

  const flushAll = () => {
    flushParagraph();
    flushBlockquote();
    closeList();
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();

    if (line.startsWith("```")) {
      flushAll();
      if (inCode) {
        closeCode();
      } else {
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      codeBuffer.push(line);
      continue;
    }

    if (!trimmed) {
      flushAll();
      continue;
    }

    if (isTableRow(line) && index + 1 < lines.length && isTableDivider(lines[index + 1])) {
      flushAll();
      const headerCells = splitTableCells(line);
      index += 2;
      const bodyRows = [];
      while (index < lines.length && isTableRow(lines[index])) {
        bodyRows.push(splitTableCells(lines[index]));
        index += 1;
      }
      index -= 1;
      html += `
        <table class="markdown-table">
          <thead><tr>${headerCells.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("")}</tr></thead>
          <tbody>
            ${bodyRows.map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`).join("")}
          </tbody>
        </table>
      `;
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      flushAll();
      const level = Math.min(headingMatch[1].length, 6);
      html += `<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`;
      continue;
    }

    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      flushAll();
      html += "<hr />";
      continue;
    }

    if (trimmed.startsWith("> ")) {
      flushParagraph();
      closeList();
      blockquoteBuffer.push(trimmed.slice(2).trim());
      continue;
    }

    const orderedMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (orderedMatch) {
      flushParagraph();
      flushBlockquote();
      if (listType !== "ol") {
        closeList();
        html += "<ol>";
        listType = "ol";
      }
      html += `<li>${renderInlineMarkdown(orderedMatch[2])}</li>`;
      continue;
    }

    const unorderedMatch = trimmed.match(/^[-*+]\s+(.+)$/);
    if (unorderedMatch) {
      flushParagraph();
      flushBlockquote();
      if (listType !== "ul") {
        closeList();
        html += "<ul>";
        listType = "ul";
      }
      html += `<li>${renderInlineMarkdown(unorderedMatch[1])}</li>`;
      continue;
    }

    flushBlockquote();
    closeList();
    paragraphBuffer.push(trimmed);
  }

  flushAll();
  closeCode();
  return html || "<p class=\"subtle\">No content.</p>";
}

function renderLoading() {
  appNode.innerHTML = `
    <section class="loading">
      <div class="skeleton"></div>
      <div class="skeleton"></div>
      <div class="skeleton"></div>
    </section>
  `;
}

function renderError(error) {
  appNode.innerHTML = `
    <section class="empty-state">
      <p class="eyebrow">Request Failed</p>
      <h2 class="page-title">页面加载失败</h2>
      <p class="page-copy">${escapeHtml(error.message || String(error))}</p>
      <button class="button" id="retry-button" type="button">重新加载</button>
    </section>
  `;
  document.querySelector("#retry-button")?.addEventListener("click", () => renderRoute());
}

function isUnauthorizedError(error) {
  return error instanceof ApiError && error.status === 401;
}

function renderSessionChrome() {
  if (!sessionSlotNode) {
    return;
  }
  const navNode = document.querySelector(".main-nav");
  navNode?.classList.toggle("disabled", !state.currentUser);
  if (!state.currentUser) {
    sessionSlotNode.innerHTML = `
      <div class="session-pill signed-out">
        <span class="session-state-dot" aria-hidden="true"></span>
        <div class="session-meta">
          <strong>已退出</strong>
          <span>输入 APPKEY 后重新进入工作区</span>
        </div>
      </div>
    `;
    return;
  }
  sessionSlotNode.innerHTML = `
    <div class="session-pill">
      <span class="session-state-dot active" aria-hidden="true"></span>
      <div class="session-meta">
        <strong>${escapeHtml(state.currentUser.user_name)}</strong>
        <span>工作区：${escapeHtml(state.currentUser.workspace_name)}</span>
      </div>
      <button class="ghost-button" id="logout-button" type="button">退出</button>
    </div>
  `;
  document.querySelector("#logout-button")?.addEventListener("click", async () => {
    clearClientAuthState();
    state.currentUser = null;
    renderSessionChrome();
    renderLoginView();
  });
}

function setTopbarVisible(visible) {
  if (!topbarNode) {
    return;
  }
  topbarNode.hidden = !visible;
}

function setLayoutMode(mode) {
  const isAuthMode = mode === "auth";
  const isReaderMode = mode === "reader";
  document.body.classList.toggle("auth-mode", isAuthMode);
  document.body.classList.toggle("reader-mode", isReaderMode);
  appShellNode?.classList.toggle("auth-mode", isAuthMode);
  appShellNode?.classList.toggle("reader-mode", isReaderMode);
  if (topbarNode) {
    topbarNode.hidden = isAuthMode || isReaderMode;
  }
}

function renderLoginView(message = "") {
  setTopbarVisible(false);
  setLayoutMode("auth");
  setActiveNav("");
  appNode.innerHTML = `
    <section class="login-shell">
      <form class="login-card" id="login-form">
        <p class="eyebrow">Authentication</p>
        <h2 class="page-title">APPKEY 登录</h2>
        <p class="login-note">输入 APPKEY 后，系统会通过后端直接调用外部登录接口，建立当前用户和工作区会话。</p>
        <label class="field">
          <span class="field-label">APPKEY</span>
          <input name="appkey" type="password" autocomplete="off" placeholder="请输入 APPKEY" />
        </label>
        ${message ? `<p class="subtle">${escapeHtml(message)}</p>` : ""}
        <div class="button-row">
          <button class="button" type="submit">登录</button>
        </div>
      </form>
    </section>
  `;
  const appkeyInputNode = document.querySelector('#login-form input[name="appkey"]');
  if (appkeyInputNode && !appkeyInputNode.value) {
    appkeyInputNode.value = DEFAULT_APPKEY;
  }
  document.querySelector("#login-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const appkey = String(form.get("appkey") || "").trim();
    if (!appkey) {
      showToast("请输入 APPKEY。", "bad");
      return;
    }
    try {
      const payload = await loginWithExternalAppkey(appkey);
      state.appkey = appkey;
      state.currentUser = payload;
      persistClientAuthState();
      try {
        state.currentUser = await apiGet("/api/auth/me");
      } catch (error) {
        clearClientAuthState();
        throw error;
      }
      persistClientAuthState();
      renderSessionChrome();
      await refreshHealth();
      if (!location.hash) {
        location.hash = buildHash("/reports");
      }
      showToast("登录成功。", "good");
      await renderRoute();
    } catch (error) {
      if (!isUnauthorizedError(error)) {
        renderLoginView(error.message || "登录失败。");
      }
    }
  });
}

async function handleUnauthorized(message = "登录已失效，请重新登录。") {
  clearClientAuthState();
  state.appkey = null;
  state.currentUser = null;
  renderSessionChrome();
  renderLoginView(message);
}

function persistClientAuthState() {
  if (state.appkey) {
    sessionStorage.setItem("appkey", state.appkey);
  } else {
    sessionStorage.removeItem("appkey");
  }
  if (state.currentUser) {
    sessionStorage.setItem("currentUser", JSON.stringify(state.currentUser));
  } else {
    sessionStorage.removeItem("currentUser");
  }
}

function clearClientAuthState() {
  sessionStorage.removeItem("appkey");
  sessionStorage.removeItem("currentUser");
}

function restoreClientAuthState() {
  const storedAppkey = sessionStorage.getItem("appkey");
  const storedUser = sessionStorage.getItem("currentUser");
  state.appkey = storedAppkey || null;
  if (!storedUser) {
    state.currentUser = null;
    return;
  }
  try {
    state.currentUser = JSON.parse(storedUser);
  } catch (error) {
    void error;
    clearClientAuthState();
    state.appkey = null;
    state.currentUser = null;
  }
}

function pickFirstString(payload, keys) {
  for (const key of keys) {
    const value = payload?.[key];
    if (value === undefined || value === null) {
      continue;
    }
    const text = String(value).trim();
    if (text) {
      return text;
    }
  }
  return null;
}

function normalizeExternalAuthPayload(payload) {
  const candidate =
    (payload && typeof payload.data === "object" && payload.data) ||
    (payload && typeof payload.result === "object" && payload.result) ||
    (payload && typeof payload.user === "object" && payload.user) ||
    (payload && typeof payload.payload === "object" && payload.payload) ||
    payload;
  if (!candidate || typeof candidate !== "object") {
    throw new Error("登录失败：外部接口返回格式异常。");
  }
  const userId = pickFirstString(candidate, ["user_id", "userId", "userid", "uid", "id"]);
  if (!userId) {
    throw new Error("登录失败：外部接口未返回 user_id。");
  }
  const userName =
    pickFirstString(candidate, ["user_name", "userName", "username", "name", "nickname", "displayName", "realName"]) || userId;
  const workspaceId =
    pickFirstString(candidate, ["workspace_id", "workspaceId", "workspaceid", "tenant_id", "tenantId", "tenantid", "org_id", "orgId", "orgid", "space_id", "spaceId", "spaceid"]) ||
    userId;
  const workspaceName =
    pickFirstString(candidate, ["workspace_name", "workspaceName", "workspacename", "tenant_name", "tenantName", "tenantname", "org_name", "orgName", "orgname", "space_name", "spaceName", "spacename"]) ||
    userName;
  const rawRoles = Array.isArray(candidate.roles) ? candidate.roles : [];
  const roles = rawRoles.length ? rawRoles.map((item) => String(item).trim()).filter(Boolean) : ["user"];
  const appkeyStatus = pickFirstString(candidate, ["appkey_status", "appkeyStatus", "status"]) || "active";
  return {
    user_id: userId,
    user_name: userName,
    workspace_id: workspaceId,
    workspace_name: workspaceName,
    roles,
    appkey_status: appkeyStatus,
  };
}

async function loginWithExternalAppkey(appkey) {
  const search = new URLSearchParams({ appKey: appkey, appCode: EXTERNAL_APP_CODE });
  let response;
  try {
    response = await fetch(`${EXTERNAL_APPKEY_LOGIN_URL}?${search.toString()}`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
  } catch (error) {
    throw new Error(`外部登录接口调用失败：${error.message || "network error"}`);
  }
  let payload = null;
  try {
    payload = await response.json();
  } catch (error) {
    throw new Error("外部登录接口返回了无效的 JSON。");
  }
  if (!response.ok) {
    const detail =
      (payload && (payload.message || payload.msg || payload.error || payload.detail)) ||
      `${response.status} ${response.statusText}`;
    throw new Error(`外部登录失败：${detail}`);
  }
  return normalizeExternalAuthPayload(payload);
}

function renderPagination({ path, page, pageSize, total, params }) {
  if (!total || total <= pageSize) {
    return "";
  }
  const maxPage = Math.max(1, Math.ceil(total / pageSize));
  return `
    <div class="pagination">
      <a class="ghost-link" href="${buildHash(path, { ...params, page: Math.max(1, page - 1) })}">上一页</a>
      <span class="subtle">第 ${page} / ${maxPage} 页，共 ${total} 条</span>
      <a class="ghost-link" href="${buildHash(path, { ...params, page: Math.min(maxPage, page + 1) })}">下一页</a>
    </div>
  `;
}

function renderPageShell({ eyebrow, title, copy, toolbar = "", body }) {
  return `
    <section>
      <header class="page-header">
        <div>
          <p class="eyebrow">${escapeHtml(eyebrow)}</p>
          <h2 class="page-title">${escapeHtml(title)}</h2>
          <p class="page-copy">${escapeHtml(copy)}</p>
        </div>
      </header>
      ${toolbar}
      ${body}
    </section>
  `;
}

function promptForFolderSelection(folders, currentFolderId = null) {
  const options = ["(Unfiled)", ...folders.map((folder) => folder.folder_name)];
  const currentIndex = currentFolderId ? folders.findIndex((folder) => folder.folder_id === currentFolderId) + 1 : 0;
  const choice = window.prompt(
    `Move report to:\n${options.map((option, index) => `${index}: ${option}`).join("\n")}\n\nEnter index:`,
    String(Math.max(currentIndex, 0))
  );
  if (choice === null) {
    return undefined;
  }
  const selectedIndex = Number(choice);
  if (Number.isNaN(selectedIndex) || selectedIndex < 0 || selectedIndex >= options.length) {
    throw new Error("Invalid folder index.");
  }
  return selectedIndex === 0 ? null : folders[selectedIndex - 1].folder_id;
}

async function moveReportToFolder(reportId, folderId, successMessage = "Report moved.") {
  await apiPost(`/api/reports/${encodeURIComponent(reportId)}/move-folder`, { folder_id: folderId });
  showToast(successMessage, "good");
}

function _bindFolderNavEvents(folders, currentFolderId, unfiled, filterParams) {
  // new folder
  document.querySelector("#new-folder-btn")?.addEventListener("click", async () => {
    const name = window.prompt("文件夹名称：");
    if (!name?.trim()) return;
    try {
      await apiPost("/api/report-folders", { folder_name: name.trim() });
      showToast("文件夹已创建", "good");
      renderRoute();
    } catch (err) {
      showToast(err.message, "bad");
    }
  });

  // rename
  document.querySelectorAll("[data-rename-folder]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const fid = btn.dataset.renameFolder;
      const newName = window.prompt("新名称：", btn.dataset.folderName);
      if (!newName?.trim()) return;
      try {
        await apiRequest(`/api/report-folders/${encodeURIComponent(fid)}`, {
          method: "PATCH",
          body: JSON.stringify({ folder_name: newName.trim() }),
        });
        showToast("已重命名", "good");
        renderRoute();
      } catch (err) {
        showToast(err.message, "bad");
      }
    });
  });

  // delete
  document.querySelectorAll("[data-delete-folder]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const fid = btn.dataset.deleteFolder;
      if (!window.confirm(`确认删除文件夹"${btn.dataset.folderName}"？文件夹必须为空。`)) return;
      try {
        await apiRequest(`/api/report-folders/${encodeURIComponent(fid)}`, { method: "DELETE" });
        showToast("文件夹已删除", "good");
        location.hash = buildHash("/reports", filterParams);
        renderRoute();
      } catch (err) {
        showToast(err.message, "bad");
      }
    });
  });

  // move report
  document.querySelectorAll("[data-move-report]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const reportId = btn.dataset.moveReport;
      try {
        const targetFolderId = promptForFolderSelection(folders, btn.dataset.currentFolderId || null);
        if (targetFolderId === undefined) return;
        await moveReportToFolder(reportId, targetFolderId, "已移动到目标文件夹");
        renderRoute();
      } catch (err) {
        showToast(err.message, "bad");
      }
      return;
    });
  });

  // drag-and-drop: report cards as drag sources
  document.querySelectorAll("article.card[data-report-id]").forEach((card) => {
    card.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", card.dataset.reportId);
      e.dataTransfer.effectAllowed = "move";
      card.classList.add("dragging");
    });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
  });

  // drag-and-drop: folder nav items as drop targets
  document.querySelectorAll(".folder-nav-item[data-folder-id]").forEach((li) => {
    li.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      li.classList.add("drop-target");
    });
    li.addEventListener("dragleave", () => li.classList.remove("drop-target"));
    li.addEventListener("drop", async (e) => {
      e.preventDefault();
      li.classList.remove("drop-target");
      const reportId = e.dataTransfer.getData("text/plain");
      if (!reportId) return;
      const targetFolderId = li.dataset.dropFolderId || li.dataset.folderId || null;
      try {
        await moveReportToFolder(reportId, targetFolderId, targetFolderId ? "已归档到文件夹" : "已移回 Unfiled");
        renderRoute();
      } catch (err) {
        showToast(err.message, "bad");
      }
      return;
    });
  });
}

function bindHashForm(formSelector, path) {
  const form = document.querySelector(formSelector);
  if (!form) {
    return;
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const next = {};
    data.forEach((value, key) => {
      next[key] = value;
    });
    next.page = 1;
    location.hash = buildHash(path, next);
  });
  form.querySelector("[data-reset]")?.addEventListener("click", () => {
    location.hash = buildHash(path);
  });
}

async function refreshHealth() {
  try {
    state.health = await apiGet("/api/health");
    const tone = toneForStatus(state.health.status);
    healthPillNode.className = `health-pill ${tone}`;
    healthPillNode.textContent = `${state.health.status.toUpperCase()} · ${state.health.version}`;
  } catch (error) {
    healthPillNode.className = "health-pill error";
    healthPillNode.textContent = "API Error";
  }
}

async function renderReportsView(route) {
  if (route.detail) {
    await renderReportDetail(route.detail);
    return;
  }

  const q = route.params.get("q") || "";
  const page = Number(route.params.get("page") || "1");
  const tag = route.params.get("tag") || "";
  const sourceDomain = route.params.get("source_domain") || "";
  const status = route.params.get("status") || "";
  const skillName = route.params.get("skill_name") || "";
  const folderId = route.params.get("folder_id") || "";
  const unfiled = route.params.get("unfiled") === "true";

  const [listData, tagsData, domainsData, foldersData] = await Promise.all([
    q
      ? apiGet(`/api/search?${serializeParams({ q, tag, source_domain: sourceDomain, status, skill_name: skillName, limit: 24 })}`)
      : apiGet(`/api/reports?${serializeParams({ page, page_size: 18, tag, source_domain: sourceDomain, status, skill_name: skillName, folder_id: folderId || undefined, unfiled: unfiled || undefined })}`),
    apiGet("/api/tags"),
    apiGet("/api/domains"),
    apiGet("/api/report-folders"),
  ]);

  const folders = foldersData.items || [];

  const folderNav = `
    <nav class="folder-nav panel">
      <div class="folder-nav-header">
        <span class="field-label">文件夹</span>
        <button class="ghost-button" id="new-folder-btn" type="button">+ 新建</button>
      </div>
      <ul class="folder-nav-list">
        <li class="${!folderId && !unfiled ? "active" : ""}">
          <a href="${buildHash("/reports", { tag, source_domain: sourceDomain, status, skill_name: skillName })}">All Reports</a>
        </li>
        <li class="folder-nav-item ${unfiled ? "active" : ""}" data-folder-id="">
          <a href="${buildHash("/reports", { unfiled: "true", tag, source_domain: sourceDomain, status, skill_name: skillName })}">Unfiled</a>
        </li>
        ${folders.map((f) => `
          <li class="folder-nav-item ${folderId === f.folder_id ? "active" : ""}" data-folder-id="${escapeHtml(f.folder_id)}">
            <a href="${buildHash("/reports", { folder_id: f.folder_id, tag, source_domain: sourceDomain, status, skill_name: skillName })}">${escapeHtml(f.folder_name)}</a>
            <span class="folder-count subtle">${f.report_count}</span>
            <span class="folder-actions">
              <button class="icon-btn" data-rename-folder="${escapeHtml(f.folder_id)}" data-folder-name="${escapeHtml(f.folder_name)}" title="重命名">✎</button>
              <button class="icon-btn" data-delete-folder="${escapeHtml(f.folder_id)}" data-folder-name="${escapeHtml(f.folder_name)}" title="删除">✕</button>
            </span>
          </li>
        `).join("")}
      </ul>
    </nav>
  `;

  const items = listData.items || [];
  const cards = items.length
    ? items
        .map((item) => {
          const itemTags = item.tags || [];
          const summary = q ? stripHtml(item.snippet || item.summary || "") : item.summary;
          const folderBadge = item.folder_name_ref
            ? `<span class="chip neutral" title="文件夹">${escapeHtml(item.folder_name_ref)}</span>`
            : "";
          return `
            <article class="card" draggable="true" data-report-id="${escapeHtml(item.report_id)}">
              <div class="meta-row">
                ${badge(item.status || "published", toneForStatus(item.status))}
                ${badge(item.source_domain || "unknown")}
                ${badge(item.skill_name || item.source_type || "report")}
                ${folderBadge}
              </div>
              <h3><a href="${buildHash(`/reports/${encodeURIComponent(item.report_id)}`)}">${escapeHtml(item.title)}</a></h3>
              <p class="text-block">${escapeHtml(summary || "No summary.")}</p>
              <div class="chip-row">${itemTags.map((value) => chip(value)).join("")}</div>
              <div class="inline-list subtle">
                <span>${escapeHtml(item.report_id)}</span>
                <span>${escapeHtml(formatDateTime(item.generated_at))}</span>
              </div>
              <div class="button-row">
                <button class="ghost-button" data-move-report="${escapeHtml(item.report_id)}" data-current-folder-id="${escapeHtml(item.folder_id_ref || "")}" data-report-title="${escapeHtml(item.title)}">移动到文件夹</button>
              </div>
            </article>
          `;
        })
        .join("")
    : `
      <section class="empty-state">
        <p class="eyebrow">Reports</p>
        <h3>没有命中结果</h3>
        <p class="page-copy">调整搜索词或过滤条件后再试。</p>
      </section>
    `;

  const toolbar = `
    <form class="toolbar panel" id="report-filters">
      <label class="field">
        <span class="field-label">关键词</span>
        <input name="q" value="${escapeHtml(q)}" placeholder="搜索报告标题或正文" />
      </label>
      <label class="field">
        <span class="field-label">Tag</span>
        <input list="tag-options" name="tag" value="${escapeHtml(tag)}" placeholder="例如 validation" />
        <datalist id="tag-options">
          ${(tagsData.items || [])
            .slice(0, 20)
            .map((item) => `<option value="${escapeHtml(item.tag || "")}"></option>`)
            .join("")}
        </datalist>
      </label>
      <label class="field">
        <span class="field-label">Domain</span>
        <input list="domain-options" name="source_domain" value="${escapeHtml(sourceDomain)}" placeholder="例如 example.com" />
        <datalist id="domain-options">
          ${(domainsData.items || [])
            .slice(0, 20)
            .map((item) => `<option value="${escapeHtml(item.source_domain || "")}"></option>`)
            .join("")}
        </datalist>
      </label>
      <label class="field">
        <span class="field-label">Status</span>
        <select name="status">
          <option value="">All</option>
          <option value="published" ${status === "published" ? "selected" : ""}>published</option>
          <option value="draft" ${status === "draft" ? "selected" : ""}>draft</option>
        </select>
      </label>
      <label class="field">
        <span class="field-label">Skill</span>
        <input name="skill_name" value="${escapeHtml(skillName)}" placeholder="例如 openclaw" />
      </label>
      <div class="button-row">
        <button class="button" type="submit">应用过滤</button>
        <button class="ghost-button" type="button" data-reset>清空</button>
      </div>
    </form>
  `;

  const body = `
    <div class="reports-workspace">
      ${folderNav}
      <div class="reports-main">
        <section class="card-grid">${cards}</section>
        ${q ? "" : renderPagination({ path: "/reports", page, pageSize: 18, total: listData.total || 0, params: { tag, source_domain: sourceDomain, status, skill_name: skillName, folder_id: folderId || undefined, unfiled: unfiled || undefined } })}
      </div>
    </div>
  `;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Reports",
    title: q ? "报告搜索" : "报告中心",
    copy: q ? `当前按关键词"${q}"检索报告。` : "查看 Skill 产出的报告、过滤来源，并进入原文详情。",
    toolbar,
    body,
  });

  bindHashForm("#report-filters", "/reports");
  _bindFolderNavEvents(folders, folderId, unfiled, { tag, source_domain: sourceDomain, status, skill_name: skillName });
}

async function renderUploadsView(route) {
  if (route.detail) {
    await renderUploadDetail(route.detail);
    return;
  }

  const page = Number(route.params.get("page") || "1");
  const status = route.params.get("status") || "";
  const stage = route.params.get("stage") || "";
  const q = route.params.get("q") || "";

  const [data, foldersData] = await Promise.all([
    apiGet(`/api/uploads?${serializeParams({ page, page_size: 18, status, stage, q })}`),
    apiGet("/api/report-folders"),
  ]);
  const folders = foldersData.items || [];

  const cards = (data.items || []).length
    ? data.items
        .map(
          (item) => `
            <article class="card">
              <div class="meta-row">
                ${badge(item.upload_status, toneForStatus(item.upload_status))}
                ${badge(item.processing_stage, toneForStatus(item.processing_stage))}
                ${badge(item.file_ext)}
              </div>
              <h3><a href="${buildHash(`/uploads/${encodeURIComponent(item.upload_id)}`)}">${escapeHtml(item.title || item.original_filename)}</a></h3>
              <div class="inline-list subtle">
                <span>${escapeHtml(item.original_filename)}</span>
                <span>${escapeHtml(item.upload_id)}</span>
              </div>
              <div class="inline-list subtle">
                <span>${escapeHtml(String(item.file_size_bytes))} bytes</span>
                <span>${escapeHtml(formatDateTime(item.updated_at))}</span>
              </div>
              ${
                item.report_id_ref
                  ? `<div class="button-row">${linkButton(buildHash(`/reports/${encodeURIComponent(item.report_id_ref)}`), "Open Report")}</div>`
                  : ""
              }
            </article>
          `
        )
        .join("")
    : `
      <section class="empty-state">
        <p class="eyebrow">Uploads</p>
        <h3>还没有上传任务</h3>
        <p class="page-copy">先上传一个文件，或者调整筛选条件后再看。</p>
      </section>
    `;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Uploads",
    title: "Upload Center",
    copy: "接收本地文件，跟踪处理状态，并把结果推进到标准报告链路。",
    toolbar: `
      <section class="panel" style="margin-bottom: 18px;">
        <form id="upload-form" class="upload-form-shell">
          <label class="upload-picker" for="upload-file-input">
            <span class="upload-picker-eyebrow">File Intake</span>
            <strong class="upload-picker-title">选择一个文件开始上传</strong>
            <span class="upload-picker-copy">支持 txt、md、html、pdf、docx。上传后会进入抽取、报告生成和入库链路。</span>
            <span class="upload-picker-button">Select Files</span>
            <span class="upload-picked-name" id="upload-picked-name">No files selected</span>
            <input id="upload-file-input" name="file" type="file" multiple required />
          </label>
          <div class="upload-form-grid">
          <label class="field">
            <span class="field-label">Title</span>
            <input name="title" placeholder="可选，默认用文件名" />
          </label>
          <label class="field">
            <span class="field-label">Compile Mode</span>
            <select name="compile_mode">
              <option value="">none</option>
              <option value="propose">propose</option>
              <option value="apply_safe">apply_safe</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">Auto Process</span>
            <select name="auto_process">
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">Auto Compile</span>
            <select name="auto_compile">
              <option value="false">false</option>
              <option value="true">true</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">目标文件夹</span>
            <select name="folder_id">
              <option value="">-- 不归档 (Unfiled) --</option>
              ${folders.map((f) => `<option value="${escapeHtml(f.folder_id)}">${escapeHtml(f.folder_name)}</option>`).join("")}
            </select>
          </label>
          </div>
          <div class="upload-form-actions">
            <div class="upload-form-hint">建议默认使用 \`Auto Process = true\`，需要更保守时再关闭自动处理。</div>
            <div class="button-row">
              <button class="button" type="submit">Upload File</button>
            </div>
          </div>
        </form>
      </section>
      <form class="toolbar panel" id="upload-filters">
        <label class="field">
          <span class="field-label">Keyword</span>
          <input name="q" value="${escapeHtml(q)}" placeholder="文件名 / 标题 / source_ref" />
        </label>
        <label class="field">
          <span class="field-label">Status</span>
          <select name="status">
            <option value="">All</option>
            ${["uploaded", "queued", "processing", "completed", "failed", "needs_review"]
              .map((value) => `<option value="${value}" ${status === value ? "selected" : ""}>${value}</option>`)
              .join("")}
          </select>
        </label>
        <label class="field">
          <span class="field-label">Stage</span>
          <select name="stage">
            <option value="">All</option>
            ${["received", "stored", "extracting", "normalizing", "summarizing", "report_generating", "syncing", "compiling", "done", "error"]
              .map((value) => `<option value="${value}" ${stage === value ? "selected" : ""}>${value}</option>`)
              .join("")}
          </select>
        </label>
        <div class="button-row">
          <button class="button" type="submit">Apply</button>
          <button class="ghost-button" type="button" data-reset>Reset</button>
        </div>
      </form>
    `,
    body: `
      <section class="card-grid">${cards}</section>
      ${renderPagination({ path: "/uploads", page, pageSize: 18, total: data.total || 0, params: { status, stage, q } })}
    `,
  });

  bindHashForm("#upload-filters", "/uploads");

  const uploadInput = document.querySelector("#upload-file-input");
  const uploadPickedName = document.querySelector("#upload-picked-name");
  uploadInput?.addEventListener("change", () => {
    const files = Array.from(uploadInput.files || []);
    if (!uploadPickedName) {
      return;
    }
    if (!files.length) {
      uploadPickedName.textContent = "No files selected";
      uploadPickedName.classList.remove("has-file");
      return;
    }
    const label =
      files.length === 1
        ? `${files[0].name} | ${files[0].size} bytes`
        : `${files.length} files selected | ${files.slice(0, 3).map((file) => file.name).join(", ")}${files.length > 3 ? ", ..." : ""}`;
    uploadPickedName.textContent = label;
    uploadPickedName.classList.add("has-file");
  });

  document.querySelector("#upload-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const files = Array.from(uploadInput?.files || []);
    if (!files.length) {
      showToast("请选择要上传的文件。", "bad");
      return;
    }

    const title = String(form.querySelector('[name="title"]')?.value || "").trim();
    const compileMode = String(form.querySelector('[name="compile_mode"]')?.value || "").trim();
    const autoProcess = String(form.querySelector('[name="auto_process"]')?.value || "true");
    const autoCompile = String(form.querySelector('[name="auto_compile"]')?.value || "false");
    const folderIdVal = String(form.querySelector('[name="folder_id"]')?.value || "").trim();
    const submitButton = form.querySelector('button[type="submit"]');
    const previousButtonText = submitButton?.textContent || "Upload Files";

    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = files.length > 1 ? `Uploading ${files.length} files...` : "Uploading...";
      }

      const successes = [];
      const failures = [];

      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        if (title) {
          formData.append("title", files.length > 1 ? `${title} - ${file.name}` : title);
        }
        if (compileMode) {
          formData.append("compile_mode", compileMode);
        }
        formData.append("auto_process", autoProcess);
        formData.append("auto_compile", autoCompile);
        if (folderIdVal) {
          formData.append("folder_id", folderIdVal);
        }

        try {
          const result = await apiPostForm("/api/uploads", formData);
          successes.push(result);
        } catch (error) {
          failures.push(`${file.name}: ${error.message || "upload failed"}`);
        }
      }

      if (!successes.length) {
        throw new Error(failures[0] || "上传失败。");
      }

      form.reset();
      if (uploadPickedName) {
        uploadPickedName.textContent = "No files selected";
        uploadPickedName.classList.remove("has-file");
      }

      if (failures.length) {
        showToast(`Created ${successes.length} upload job(s), ${failures.length} failed.`, "warn");
      } else {
        showToast(
          successes.length === 1 ? "Upload job created." : `Created ${successes.length} upload jobs.`,
          "good"
        );
      }

      const latestUpload = successes[successes.length - 1];
      location.hash = buildHash(`/uploads/${encodeURIComponent(latestUpload.upload_id)}`);
    } catch (error) {
      showToast(error.message || "Upload failed.", "bad");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = previousButtonText;
      }
    }
  });
}

async function renderUploadDetail(uploadId) {
  const data = await apiGet(`/api/uploads/${encodeURIComponent(uploadId)}`);
  const [rawText, reportPreview] = await Promise.all([
    data.raw_preview_available
      ? apiRequestText(`/api/uploads/${encodeURIComponent(uploadId)}/raw`).catch(() => "")
      : Promise.resolve(""),
    apiRequestText(`/api/uploads/${encodeURIComponent(uploadId)}/report-preview`).catch(() => ""),
  ]);

  const artifacts = (data.artifacts || []).length
    ? data.artifacts
        .map(
          (item) => `
            <div class="meta-block">
              <div class="inline-kv">
                <strong>${escapeHtml(item.artifact_kind)}</strong>
                <code>${escapeHtml(item.file_path)}</code>
              </div>
            </div>
          `
        )
        .join("")
    : `<p class="subtle">No artifacts yet.</p>`;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Uploads / Detail",
    title: data.title || data.original_filename,
    copy: data.source_ref,
    body: `
      <div class="button-row" style="margin-bottom: 16px;">
        ${linkButton(buildHash("/uploads"), "返回 Upload 列表")}
        ${data.report_id_ref ? linkButton(buildHash(`/reports/${encodeURIComponent(data.report_id_ref)}`), "Open Report") : ""}
        ${data.upload_status !== "completed" ? `<button class="button" id="process-upload" type="button">Process</button>` : ""}
        ${["failed", "needs_review"].includes(data.upload_status) ? `<button class="ghost-button" id="retry-upload" type="button">Retry</button>` : ""}
      </div>
      <section class="detail-grid">
        <article class="detail-shell">
          <div class="meta-row">
            ${badge(data.upload_status, toneForStatus(data.upload_status))}
            ${badge(data.processing_stage, toneForStatus(data.processing_stage))}
            ${badge(data.file_ext)}
          </div>
          <div class="report-info-grid" style="margin-top: 12px;">
            <div class="meta-block meta-block-compact report-info-card">
              <div class="inline-kv inline-kv-compact">
                <strong>Upload ID</strong>
                <code>${escapeHtml(data.upload_id)}</code>
              </div>
            </div>
            <div class="meta-block meta-block-compact report-info-card">
              <div class="inline-kv inline-kv-compact">
                <strong>File Size</strong>
                <span>${escapeHtml(String(data.file_size_bytes))} bytes</span>
              </div>
            </div>
            <div class="meta-block meta-block-compact report-info-card">
              <div class="inline-kv inline-kv-compact">
                <strong>Created</strong>
                <span>${escapeHtml(formatDateTime(data.created_at))}</span>
              </div>
            </div>
            <div class="meta-block meta-block-compact report-info-card">
              <div class="inline-kv inline-kv-compact">
                <strong>Updated</strong>
                <span>${escapeHtml(formatDateTime(data.updated_at))}</span>
              </div>
            </div>
            <div class="meta-block meta-block-compact report-info-card report-info-card-wide">
              <div class="inline-kv inline-kv-compact">
                <strong>Storage Path</strong>
                <code>${escapeHtml(data.storage_path)}</code>
              </div>
            </div>
          </div>
          ${
            data.error_message
              ? `<div class="meta-block" style="margin-top: 14px;"><div class="inline-kv"><strong>Error</strong><span>${escapeHtml(data.error_code || "error")} | ${escapeHtml(data.error_message)}</span></div></div>`
              : ""
          }
          <section style="margin-top: 18px;">
            <h3>Raw Preview</h3>
            <pre class="document-raw"><code>${escapeHtml(rawText || "No raw preview yet.")}</code></pre>
          </section>
          <section style="margin-top: 18px;">
            <h3>Report Preview</h3>
            <pre class="document-raw"><code>${escapeHtml(reportPreview || "No report preview yet.")}</code></pre>
          </section>
        </article>
        <aside class="detail-stack">
          <section class="detail-shell">
            <h3>Processing</h3>
            <div class="detail-stack">
              <div class="meta-block"><div class="inline-kv"><strong>Source Type</strong><span>${escapeHtml(data.source_type)}</span></div></div>
              <div class="meta-block"><div class="inline-kv"><strong>Folder</strong><span>${escapeHtml(data.folder_name_ref || "Unfiled")}</span></div></div>
              <div class="meta-block"><div class="inline-kv"><strong>Auto Process</strong><span>${escapeHtml(String(data.auto_process))}</span></div></div>
              <div class="meta-block"><div class="inline-kv"><strong>Auto Compile</strong><span>${escapeHtml(String(data.auto_compile))}</span></div></div>
              <div class="meta-block"><div class="inline-kv"><strong>Compile Mode</strong><span>${escapeHtml(data.compile_mode || "-")}</span></div></div>
              <div class="meta-block"><div class="inline-kv"><strong>Report</strong><span>${data.report_id_ref ? `<a href="${buildHash(`/reports/${encodeURIComponent(data.report_id_ref)}`)}">${escapeHtml(data.report_id_ref)}</a>` : "-"}</span></div></div>
            </div>
          </section>
          <section class="detail-shell">
            <h3>Artifacts</h3>
            <div class="detail-stack">${artifacts}</div>
          </section>
        </aside>
      </section>
    `,
  });

  document.querySelector("#process-upload")?.addEventListener("click", async () => {
    try {
      await apiPost(`/api/uploads/${encodeURIComponent(uploadId)}/process`, {});
      showToast("Upload processing completed.", "good");
      await renderUploadDetail(uploadId);
    } catch (error) {
      showToast(error.message || "Process failed.", "bad");
    }
  });

  document.querySelector("#retry-upload")?.addEventListener("click", async () => {
    try {
      await apiPost(`/api/uploads/${encodeURIComponent(uploadId)}/retry`, {});
      showToast("Upload retry completed.", "good");
      await renderUploadDetail(uploadId);
    } catch (error) {
      showToast(error.message || "Retry failed.", "bad");
    }
  });
}

async function renderReportDetail(reportId) {
  const [data, foldersData] = await Promise.all([
    apiGet(`/api/reports/${encodeURIComponent(reportId)}`),
    apiGet("/api/report-folders"),
  ]);
  const folders = foldersData.items || [];
  const content = renderMarkdownLite(stripFrontmatter(data.content));
  const links = data.links?.length
    ? data.links
        .map(
          (item) => `
            <div class="meta-block">
              <div class="inline-kv">
                <strong>${escapeHtml(item.link_type)}</strong>
                <a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url)}</a>
              </div>
            </div>
          `
        )
        .join("")
    : `<p class="subtle">No extracted links.</p>`;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Reports / Detail",
    title: data.title,
    copy: data.summary,
    body: `
      <div class="button-row" style="margin-bottom: 16px;">
        ${linkButton(buildHash("/reports"), "返回报告列表")}
        <a class="soft-button" href="${escapeHtml(data.source_url || data.source_ref)}" target="_blank" rel="noreferrer">打开来源</a>
        <a class="ghost-button" href="${buildHash(`/report-only/${encodeURIComponent(data.report_id)}`)}">仅详情页</a>
      </div>
      <section class="detail-grid">
        <article class="detail-shell">
          <div class="markdown-body">${content}</div>
        </article>
        <aside class="detail-stack">
          <section class="detail-shell detail-meta report-detail-meta">
            <div class="meta-row">
              ${badge(data.status, toneForStatus(data.status))}
              ${badge(data.source_domain)}
              ${badge(data.skill_name)}
            </div>
            <div class="report-info-grid">
              <div class="meta-block meta-block-compact report-info-card">
                <div class="inline-kv inline-kv-compact">
                  <strong>Report ID</strong>
                  <code>${escapeHtml(data.report_id)}</code>
                </div>
              </div>
              <div class="meta-block meta-block-compact report-info-card">
                <div class="inline-kv inline-kv-compact">
                  <strong>Generated At</strong>
                  <span>${escapeHtml(formatDateTime(data.generated_at))}</span>
                </div>
              </div>
              <div class="meta-block meta-block-compact report-info-card">
                <div class="inline-kv inline-kv-compact">
                  <strong>Updated At</strong>
                  <span>${escapeHtml(formatDateTime(data.updated_at))}</span>
                </div>
              </div>
              <div class="meta-block meta-block-compact report-info-card report-info-card-wide">
                <div class="inline-kv inline-kv-compact">
                  <strong>Source Ref</strong>
                  <code>${escapeHtml(data.source_ref)}</code>
                </div>
              </div>
            </div>
            <div class="report-tag-panel">
              <p class="field-label">Tags</p>
              <div class="chip-row report-tag-row">${(data.tags || []).map((value) => chip(value)).join("")}</div>
            </div>
          </section>
          <section class="detail-shell">
            <h3>Extracted Links</h3>
            <div class="detail-stack">${links}</div>
          </section>
        </aside>
      </section>
    `,
  });

  document
    .querySelector(".report-detail-meta .report-info-grid")
    ?.insertAdjacentHTML(
      "beforeend",
      `
        <div class="meta-block meta-block-compact report-info-card report-info-card-wide">
          <div class="inline-kv inline-kv-compact">
            <strong>Folder</strong>
            <span>${escapeHtml(data.folder_name_ref || "Unfiled")}</span>
          </div>
        </div>
      `
    );

  document
    .querySelector('.button-row[style="margin-bottom: 16px;"]')
    ?.insertAdjacentHTML("beforeend", '<button class="ghost-button" id="move-report-detail" type="button">移动到文件夹</button>');

  document
    .querySelector('.button-row[style="margin-bottom: 16px;"]')
    ?.insertAdjacentHTML("beforeend", '<button class="ghost-button" id="delete-report-detail" type="button">Delete Report</button>');

  document
    .querySelector('.button-row[style="margin-bottom: 16px;"]')
    ?.insertAdjacentHTML("beforeend", '<button class="ghost-button" id="share-report-detail" type="button">Copy Share Link</button>');

  document.querySelector("#move-report-detail")?.addEventListener("click", async () => {
    try {
      const targetFolderId = promptForFolderSelection(folders, data.folder_id_ref || null);
      if (targetFolderId === undefined) return;
      await moveReportToFolder(reportId, targetFolderId, "已更新报告归档");
      await renderReportDetail(reportId);
    } catch (error) {
      showToast(error.message || "Move failed.", "bad");
    }
  });
  document.querySelector("#delete-report-detail")?.addEventListener("click", async () => {
    const confirmed = window.confirm(
      `Confirm delete "${data.title}"? The report will disappear immediately and files will be purged after 7 days.`
    );
    if (!confirmed) return;
    try {
      await apiRequest(`/api/reports/${encodeURIComponent(reportId)}`, { method: "DELETE" });
      showToast("Report deleted.", "good");
      location.hash = buildHash("/reports");
    } catch (error) {
      showToast(error.message || "Delete failed.", "bad");
    }
  });
  document.querySelector("#share-report-detail")?.addEventListener("click", async () => {
    try {
      const result = await apiPost(`/api/reports/${encodeURIComponent(reportId)}/share`, {});
      await copyTextToClipboard(result.share_url);
      showToast("Share link copied.", "good");
    } catch (error) {
      showToast(error.message || "Share link creation failed.", "bad");
    }
  });
}

async function renderReportOnlyDetail(reportId, shareToken = "") {
  const detailPath = shareToken
    ? `/api/public/reports/${encodeURIComponent(reportId)}?${serializeParams({ share_token: shareToken })}`
    : `/api/reports/${encodeURIComponent(reportId)}`;
  const data = await apiGet(detailPath);
  const content = renderMarkdownLite(stripFrontmatter(data.content));
  const fullViewAction = state.currentUser
    ? `<a class="ghost-button" href="${buildHash(`/reports/${encodeURIComponent(data.report_id)}`)}">ç€¹å±¾æš£éšåº¡å½´ç‘™å——æµ˜</a>`
    : "";

  appNode.innerHTML = `
    <section class="report-reader-shell">
      <header class="detail-shell report-reader-header">
        <div class="report-reader-heading">
          <p class="eyebrow">Report Detail</p>
          <h1 class="page-title">${escapeHtml(data.title)}</h1>
          <p class="page-copy">${escapeHtml(data.summary)}</p>
        </div>
        <div class="report-reader-actions">
          <a class="soft-button" href="${escapeHtml(data.source_url || data.source_ref)}" target="_blank" rel="noreferrer">打开来源</a>
          <a class="ghost-button" href="${buildHash(`/reports/${encodeURIComponent(data.report_id)}`)}">完整后台视图</a>
        </div>
        <div class="meta-row">
          ${badge(data.status, toneForStatus(data.status))}
          ${badge(data.source_domain)}
          ${badge(data.skill_name)}
        </div>
        <div class="chip-row">${(data.tags || []).map((value) => chip(value)).join("")}</div>
        <div class="report-reader-meta">
          <div class="meta-block meta-block-compact report-info-card">
            <div class="inline-kv inline-kv-compact">
              <strong>Report ID</strong>
              <code>${escapeHtml(data.report_id)}</code>
            </div>
          </div>
          <div class="meta-block meta-block-compact report-info-card">
            <div class="inline-kv inline-kv-compact">
              <strong>Generated At</strong>
              <span>${escapeHtml(formatDateTime(data.generated_at))}</span>
            </div>
          </div>
          <div class="meta-block meta-block-compact report-info-card">
            <div class="inline-kv inline-kv-compact">
              <strong>Updated At</strong>
              <span>${escapeHtml(formatDateTime(data.updated_at))}</span>
            </div>
          </div>
          <div class="meta-block meta-block-compact report-info-card report-info-card-wide">
            <div class="inline-kv inline-kv-compact">
              <strong>Source Ref</strong>
              <code>${escapeHtml(data.source_ref)}</code>
            </div>
          </div>
        </div>
      </header>
      <article class="detail-shell report-reader-content">
        <div class="markdown-body">${content}</div>
      </article>
    </section>
  `;
  if (!state.currentUser) {
    document.querySelector(".report-reader-actions .ghost-button")?.remove();
  }
}

async function renderWikiView(route) {
  if (route.detail) {
    await renderWikiDetail(route.detail);
    return;
  }

  const q = route.params.get("q") || "";
  const tag = route.params.get("tag") || "";
  const pageType = route.params.get("page_type") || "";
  const status = route.params.get("status") || "";
  const page = Number(route.params.get("page") || "1");
  const data = await apiGet(
    `/api/wiki/pages?${serializeParams({ q, tag, page_type: pageType, status, page, page_size: 18 })}`
  );

  const cards = (data.items || []).length
    ? data.items
        .map(
          (item) => `
            <article class="card">
              <div class="meta-row">
                ${badge(item.page_type)}
                ${badge(item.status, toneForStatus(item.status))}
                ${badge(`${item.source_report_count} source`)}
              </div>
              <h3><a href="${buildHash(`/wiki/${encodeURIComponent(item.slug)}`)}">${escapeHtml(item.title)}</a></h3>
              <p class="text-block">${escapeHtml(item.summary || "No summary.")}</p>
              <div class="chip-row">${(item.tags || []).map((value) => chip(value)).join("")}</div>
              <div class="inline-list subtle">
                <span>${escapeHtml(item.page_id)}</span>
                <span>${escapeHtml(formatDateTime(item.updated_at))}</span>
              </div>
            </article>
          `
        )
        .join("")
    : `
      <section class="empty-state">
        <p class="eyebrow">Wiki</p>
        <h3>没有命中 Wiki 页面</h3>
        <p class="page-copy">当前条件下没有知识页。</p>
      </section>
    `;

  const toolbar = `
    <form class="toolbar panel" id="wiki-filters">
      <label class="field">
        <span class="field-label">关键词</span>
        <input name="q" value="${escapeHtml(q)}" placeholder="搜索标题、摘要、正文" />
      </label>
      <label class="field">
        <span class="field-label">Tag</span>
        <input name="tag" value="${escapeHtml(tag)}" placeholder="例如 agentic-workflow" />
      </label>
      <label class="field">
        <span class="field-label">Page Type</span>
        <select name="page_type">
          <option value="">All</option>
          ${["entity", "concept", "topic", "question", "timeline"]
            .map((value) => `<option value="${value}" ${pageType === value ? "selected" : ""}>${value}</option>`)
            .join("")}
        </select>
      </label>
      <label class="field">
        <span class="field-label">Status</span>
        <select name="status">
          <option value="">All</option>
          ${["active", "needs_review", "draft", "conflicted", "deprecated"]
            .map((value) => `<option value="${value}" ${status === value ? "selected" : ""}>${value}</option>`)
            .join("")}
        </select>
      </label>
      <div class="button-row">
        <button class="button" type="submit">筛选页面</button>
        <button class="ghost-button" type="button" data-reset>清空</button>
      </div>
    </form>
  `;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Wiki",
    title: "知识页索引",
    copy: "按 slug 进入详情页，查看证据报告、关联页面和原始 Markdown 内容。",
    toolbar,
    body: `
      <section class="card-grid">${cards}</section>
      ${renderPagination({ path: "/wiki", page, pageSize: 18, total: data.total || 0, params: { q, tag, page_type: pageType, status } })}
    `,
  });

  bindHashForm("#wiki-filters", "/wiki");
}

async function renderWikiDetail(slug) {
  const data = await apiGet(`/api/wiki/by-slug/${encodeURIComponent(slug)}`);
  const sourceReports = (data.source_reports || []).length
    ? data.source_reports
        .map(
          (item) => `
            <div class="meta-block">
              <div class="inline-kv">
                <strong>${escapeHtml(item.evidence_role)}</strong>
                <a href="${buildHash(`/reports/${encodeURIComponent(item.report_id)}`)}">${escapeHtml(item.title)}</a>
                <span class="subtle">${escapeHtml(item.report_id)} · ${escapeHtml(formatDateTime(item.generated_at))}</span>
              </div>
            </div>
          `
        )
        .join("")
    : `<p class="subtle">No linked reports.</p>`;

  const relatedPages = (data.related_pages || []).length
    ? data.related_pages
        .map(
          (item) => `
            <div class="meta-block">
              <div class="inline-kv">
                <strong>${escapeHtml(item.link_type)}</strong>
                <a href="${buildHash(`/wiki/${encodeURIComponent(item.slug)}`)}">${escapeHtml(item.title)}</a>
                <span class="subtle">${escapeHtml(item.page_type)} · ${escapeHtml(item.page_id)}</span>
              </div>
            </div>
          `
        )
        .join("")
    : `<p class="subtle">No related pages.</p>`;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Wiki / Detail",
    title: data.title,
    copy: data.summary || "Knowledge page detail",
    body: `
      <div class="button-row" style="margin-bottom: 16px;">
        ${linkButton(buildHash("/wiki"), "返回知识页列表")}
      </div>
      <section class="detail-grid">
        <article class="detail-shell">
          <div class="meta-row">
            ${badge(data.page_type)}
            ${badge(data.status, toneForStatus(data.status))}
            ${data.confidence ? badge(`confidence ${data.confidence}`) : ""}
          </div>
          <div class="chip-row" style="margin-top: 8px;">${(data.tags || []).map((value) => chip(value)).join("")}</div>
          <div class="markdown-body" style="margin-top: 18px;">${renderMarkdownLite(stripFrontmatter(data.content))}</div>
        </article>
        <aside class="detail-stack">
          <section class="detail-shell detail-meta">
            <div class="meta-block"><div class="inline-kv"><strong>Page ID</strong><code>${escapeHtml(data.page_id)}</code></div></div>
            <div class="meta-block"><div class="inline-kv"><strong>Slug</strong><code>${escapeHtml(data.slug)}</code></div></div>
            <div class="meta-block"><div class="inline-kv"><strong>Updated At</strong><span>${escapeHtml(formatDateTime(data.updated_at))}</span></div></div>
            <div class="meta-block"><div class="inline-kv"><strong>File Path</strong><code>${escapeHtml(data.file_path)}</code></div></div>
          </section>
          <section class="detail-shell">
            <h3>Source Reports</h3>
            <div class="detail-stack">${sourceReports}</div>
          </section>
          <section class="detail-shell">
            <h3>Related Pages</h3>
            <div class="detail-stack">${relatedPages}</div>
          </section>
        </aside>
      </section>
    `,
  });
}

async function renderAskView() {
  const askResult = state.askResult;
  const askWritebackResult = state.askWritebackResult;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Query",
    title: "Ask the Knowledge Base",
    copy: "先消耗 Wiki 层，再回退到 Report 层。高价值问答可以回写为 question 页面或 review task。",
    body: `
      <section class="split-grid">
        <div class="panel">
          <form id="ask-form" class="form-grid">
            <label class="field">
              <span class="field-label">Question</span>
              <textarea name="question" placeholder="例如：openclaw 的报告如何沉淀成 Wiki？">${escapeHtml(askResult?.question || "")}</textarea>
            </label>
            <div class="form-grid two">
              <label class="field">
                <span class="field-label">Writeback Strategy</span>
                <select name="writeback">
                  <option value="suggest">suggest</option>
                  <option value="always">always</option>
                  <option value="never">never</option>
                </select>
              </label>
              <div class="field">
                <span class="field-label">Action</span>
                <div class="button-row">
                  <button class="button" type="submit">Run Query</button>
                </div>
              </div>
            </div>
          </form>
        </div>
        <aside class="panel">
          <h3>Usage Notes</h3>
          <div class="detail-stack">
            <div class="meta-block"><div class="inline-kv"><strong>Priority</strong><span>Wiki pages are ranked ahead of reports.</span></div></div>
            <div class="meta-block"><div class="inline-kv"><strong>Writeback</strong><span>Use <code>question_page</code> for stable FAQ, or <code>task</code> when human review is safer.</span></div></div>
            <div class="meta-block"><div class="inline-kv"><strong>Evidence</strong><span>Returned sources are persisted in <code>question_runs</code> and <code>question_run_sources</code>.</span></div></div>
          </div>
        </aside>
      </section>
      ${
        askResult
          ? `
            <section class="split-grid" style="margin-top: 18px;">
              <article class="detail-shell">
                <div class="meta-row">
                  ${badge(`run ${askResult.run_id}`)}
                  ${badge(`writeback ${askResult.should_writeback ? "suggested" : "not suggested"}`, askResult.should_writeback ? "warn" : "neutral")}
                </div>
                <div class="markdown-body" style="margin-top: 18px;">${renderMarkdownLite(askResult.answer)}</div>
                <div class="button-row" style="margin-top: 18px;">
                  <button class="button" id="writeback-page" type="button">回写 Question Page</button>
                  <button class="ghost-button" id="writeback-task" type="button">生成 Review Task</button>
                </div>
                ${
                  askWritebackResult
                    ? `<div class="meta-block" style="margin-top: 18px;"><div class="inline-kv"><strong>Writeback Result</strong><span>${escapeHtml(askWritebackResult.message)}${askWritebackResult.page_id ? ` · ${escapeHtml(askWritebackResult.page_id)}` : ""}${askWritebackResult.task_id ? ` · task ${escapeHtml(askWritebackResult.task_id)}` : ""}</span></div></div>`
                    : ""
                }
              </article>
              <aside class="detail-stack">
                <section class="detail-shell">
                  <h3>Wiki Evidence</h3>
                  <div class="detail-stack">
                    ${
                      (askResult.source_wiki_pages || []).length
                        ? askResult.source_wiki_pages
                            .map(
                              (item) => `
                                <div class="meta-block">
                                  <div class="inline-kv">
                                    <strong>${escapeHtml(item.page_type)}</strong>
                                    <a href="${buildHash(`/wiki/${encodeURIComponent(item.slug)}`)}">${escapeHtml(item.title)}</a>
                                    <span class="subtle">${escapeHtml(item.page_id)} · score ${escapeHtml(item.score)}</span>
                                  </div>
                                </div>
                              `
                            )
                            .join("")
                        : `<p class="subtle">No wiki evidence.</p>`
                    }
                  </div>
                </section>
                <section class="detail-shell">
                  <h3>Report Evidence</h3>
                  <div class="detail-stack">
                    ${
                      (askResult.source_reports || []).length
                        ? askResult.source_reports
                            .map(
                              (item) => `
                                <div class="meta-block">
                                  <div class="inline-kv">
                                    <strong>${escapeHtml(item.source_domain)}</strong>
                                    <a href="${buildHash(`/reports/${encodeURIComponent(item.report_id)}`)}">${escapeHtml(item.title)}</a>
                                    <span class="subtle">${escapeHtml(item.report_id)} · ${escapeHtml(formatDateTime(item.generated_at))}</span>
                                  </div>
                                </div>
                              `
                            )
                            .join("")
                        : `<p class="subtle">No report evidence.</p>`
                    }
                  </div>
                </section>
              </aside>
            </section>
          `
          : ""
      }
    `,
  });

  document.querySelector("#ask-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const question = String(data.get("question") || "").trim();
    const writeback = String(data.get("writeback") || "suggest");
    if (!question) {
      showToast("请输入问题。", "bad");
      return;
    }
    try {
      state.askWritebackResult = null;
      state.askResult = await apiPost("/api/query/ask", { question, writeback });
      showToast("问答完成。", "good");
      renderAskView();
    } catch (error) {
      showToast(error.message || "问答失败。", "bad");
    }
  });

  document.querySelector("#writeback-page")?.addEventListener("click", async () => {
    if (!state.askResult) {
      return;
    }
    try {
      state.askWritebackResult = await apiPost("/api/query/writeback", {
        run_id: state.askResult.run_id,
        kind: "question_page",
      });
      showToast("已回写 question page。", "good");
      renderAskView();
    } catch (error) {
      showToast(error.message || "回写失败。", "bad");
    }
  });

  document.querySelector("#writeback-task")?.addEventListener("click", async () => {
    if (!state.askResult) {
      return;
    }
    try {
      state.askWritebackResult = await apiPost("/api/query/writeback", {
        run_id: state.askResult.run_id,
        kind: "task",
      });
      showToast("已生成 review task。", "good");
      renderAskView();
    } catch (error) {
      showToast(error.message || "创建任务失败。", "bad");
    }
  });
}

async function renderTasksView(route) {
  const status = route.params.get("status") || "open";
  const taskType = route.params.get("task_type") || "";
  const targetKind = route.params.get("target_kind") || "";
  const page = Number(route.params.get("page") || "1");

  const data = await apiGet(
    `/api/wiki/tasks?${serializeParams({ status, task_type: taskType, target_kind: targetKind, page, page_size: 20 })}`
  );

  const rows = (data.items || []).length
    ? data.items
        .map(
          (item) => `
            <tr>
              <td>${badge(item.task_type)}</td>
              <td><strong>${escapeHtml(item.title)}</strong><br /><span class="subtle">${escapeHtml(item.description || "")}</span></td>
              <td>${escapeHtml(item.target_kind)}${item.target_id ? `<br /><code>${escapeHtml(item.target_id)}</code>` : ""}</td>
              <td>${badge(item.priority, toneForStatus(item.priority))}</td>
              <td>${badge(item.status, toneForStatus(item.status))}</td>
              <td>${escapeHtml(formatDateTime(item.updated_at))}</td>
            </tr>
          `
        )
        .join("")
    : `<tr><td colspan="6" class="subtle">No tasks found.</td></tr>`;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Governance",
    title: "治理任务",
    copy: "汇总 compile、writeback、fill-gap、conflict resolution 等待办。",
    toolbar: `
      <form class="toolbar panel" id="task-filters">
        <label class="field">
          <span class="field-label">Status</span>
          <select name="status">
            <option value="">All</option>
            ${["open", "in_progress", "done"].map((value) => `<option value="${value}" ${status === value ? "selected" : ""}>${value}</option>`).join("")}
          </select>
        </label>
        <label class="field">
          <span class="field-label">Task Type</span>
          <input name="task_type" value="${escapeHtml(taskType)}" placeholder="例如 fill_gap" />
        </label>
        <label class="field">
          <span class="field-label">Target Kind</span>
          <input name="target_kind" value="${escapeHtml(targetKind)}" placeholder="例如 report" />
        </label>
        <div class="button-row">
          <button class="button" type="submit">更新列表</button>
          <button class="ghost-button" type="button" data-reset>清空</button>
        </div>
      </form>
    `,
    body: `
      <section class="table-shell">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Title</th>
              <th>Target</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
        ${renderPagination({ path: "/tasks", page, pageSize: 20, total: data.total || 0, params: { status, task_type: taskType, target_kind: targetKind } })}
      </section>
    `,
  });

  bindHashForm("#task-filters", "/tasks");
}

async function renderConflictsView(route) {
  const status = route.params.get("status") || "open";
  const severity = route.params.get("severity") || "";
  const page = Number(route.params.get("page") || "1");
  const data = await apiGet(
    `/api/wiki/conflicts?${serializeParams({ status, severity, page, page_size: 20 })}`
  );

  const rows = (data.items || []).length
    ? data.items
        .map(
          (item) => `
            <tr>
              <td>${badge(item.severity, toneForStatus(item.severity))}</td>
              <td><strong>${escapeHtml(item.topic_key)}</strong><br /><span class="subtle">${escapeHtml(item.page_id_ref || "-")}</span></td>
              <td>${escapeHtml(item.old_claim)}</td>
              <td>${escapeHtml(item.new_claim)}</td>
              <td>${badge(item.status, toneForStatus(item.status))}</td>
              <td>${escapeHtml(formatDateTime(item.created_at))}</td>
            </tr>
          `
        )
        .join("")
    : `<tr><td colspan="6" class="subtle">No conflicts found.</td></tr>`;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Governance",
    title: "冲突中心",
    copy: "追踪 page type 冲突、未解析关系和其他待裁决项。",
    toolbar: `
      <form class="toolbar panel" id="conflict-filters">
        <label class="field">
          <span class="field-label">Status</span>
          <select name="status">
            <option value="">All</option>
            ${["open", "in_progress", "resolved"].map((value) => `<option value="${value}" ${status === value ? "selected" : ""}>${value}</option>`).join("")}
          </select>
        </label>
        <label class="field">
          <span class="field-label">Severity</span>
          <select name="severity">
            <option value="">All</option>
            ${["low", "medium", "high"].map((value) => `<option value="${value}" ${severity === value ? "selected" : ""}>${value}</option>`).join("")}
          </select>
        </label>
        <div class="button-row">
          <button class="button" type="submit">更新列表</button>
          <button class="ghost-button" type="button" data-reset>清空</button>
        </div>
      </form>
    `,
    body: `
      <section class="table-shell">
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Topic</th>
              <th>Old Claim</th>
              <th>New Claim</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
        ${renderPagination({ path: "/conflicts", page, pageSize: 20, total: data.total || 0, params: { status, severity } })}
      </section>
    `,
  });

  bindHashForm("#conflict-filters", "/conflicts");
}

async function renderAdminView() {
  const health = state.health || (await apiGet("/api/health"));
  const latestSync = health.latest_sync;
  const events = state.adminEvents.length
    ? state.adminEvents
        .map(
          (item) => `
            <article class="card">
              <div class="meta-row">
                ${badge(item.label, item.tone)}
                ${badge(formatDateTime(item.createdAt))}
              </div>
              <h3>${escapeHtml(item.title)}</h3>
              <pre class="document-raw"><code>${escapeHtml(JSON.stringify(item.payload, null, 2))}</code></pre>
            </article>
          `
        )
        .join("")
    : `<section class="empty-state"><p class="eyebrow">Admin Log</p><h3>还没有运行记录</h3><p class="page-copy">执行 sync、compile 或 lint 后，结果会出现在这里。</p></section>`;

  appNode.innerHTML = renderPageShell({
    eyebrow: "Operations",
    title: "管理面板",
    copy: "同源触发 sync / compile / lint，并查看最新服务状态与操作日志。",
    body: `
      <section class="stats-grid" style="margin-bottom: 18px;">
        <article class="card">
          <p class="eyebrow">Service</p>
          <h3>${escapeHtml(health.service)}</h3>
          <div class="meta-row">${badge(health.status, toneForStatus(health.status))}${badge(health.version)}</div>
        </article>
        <article class="card">
          <p class="eyebrow">Database</p>
          <h3>${health.database_ready ? "Ready" : "Not Ready"}</h3>
          <p class="subtle">${escapeHtml(health.database_path)}</p>
        </article>
        <article class="card">
          <p class="eyebrow">Latest Sync</p>
          <h3>${latestSync ? escapeHtml(latestSync.status) : "No Run"}</h3>
          <p class="subtle">${latestSync ? escapeHtml(formatDateTime(latestSync.finished_at || latestSync.started_at)) : "尚未执行同步"}</p>
        </article>
      </section>

      <section class="split-grid">
        <div class="detail-stack">
          <section class="panel">
            <h3>Sync</h3>
            <form id="sync-form" class="form-grid two">
              <label class="field">
                <span class="field-label">Mode</span>
                <select name="mode">
                  <option value="incremental">incremental</option>
                  <option value="full">full</option>
                </select>
              </label>
              <div class="field">
                <span class="field-label">Action</span>
                <div class="button-row"><button class="button" type="submit">Run Sync</button></div>
              </div>
            </form>
          </section>

          <section class="panel">
            <h3>Compile</h3>
            <form id="compile-form" class="form-grid two">
              <label class="field">
                <span class="field-label">Mode</span>
                <select name="mode">
                  <option value="propose">propose</option>
                  <option value="apply_safe">apply_safe</option>
                </select>
              </label>
              <label class="field">
                <span class="field-label">Report ID</span>
                <input name="report_id" placeholder="留空表示消费 compile_page 待办" />
              </label>
              <div class="button-row">
                <button class="button" type="submit">Run Compile</button>
              </div>
            </form>
          </section>

          <section class="panel">
            <h3>Lint</h3>
            <form id="lint-form" class="form-grid two">
              <label class="field">
                <span class="field-label">Mode</span>
                <select name="mode">
                  <option value="light">light</option>
                  <option value="full">full</option>
                </select>
              </label>
              <div class="button-row">
                <button class="button" type="submit">Run Lint</button>
              </div>
            </form>
          </section>
        </div>

        <aside class="detail-stack">
          <section class="panel">
            <h3>openclaw Skill 对接</h3>
            <div class="detail-stack">
              <div class="meta-block"><div class="inline-kv"><strong>Step 1</strong><span>Skill 把抓取原始内容放入 <code>raw/</code>，把总结报告放入 <code>reports/</code>。</span></div></div>
              <div class="meta-block"><div class="inline-kv"><strong>Step 2</strong><span>触发 <code>POST /api/sync</code>，让报告进入索引和 SQLite。</span></div></div>
              <div class="meta-block"><div class="inline-kv"><strong>Step 3</strong><span>按需要执行 <code>POST /api/wiki/compile</code>，建议默认走 <code>propose</code> 或低风险的 <code>apply_safe</code>。</span></div></div>
              <div class="meta-block"><div class="inline-kv"><strong>Step 4</strong><span>前端在 <code>/app/</code> 查看 Wiki、问答结果、治理任务与冲突。</span></div></div>
            </div>
          </section>
        </aside>
      </section>

      <section style="margin-top: 18px;" class="card-grid">${events}</section>
    `,
  });

  document.querySelector("#sync-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAdminAction("Sync", "/api/sync", { mode: String(form.get("mode") || "incremental") });
  });

  document.querySelector("#compile-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAdminAction("Compile", "/api/wiki/compile", {
      mode: String(form.get("mode") || "propose"),
      report_id: String(form.get("report_id") || "").trim() || null,
    });
  });

  document.querySelector("#lint-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAdminAction("Lint", "/api/wiki/lint", { mode: String(form.get("mode") || "light") });
  });
}

async function runAdminAction(title, path, payload) {
  try {
    const result = await apiPost(path, payload);
    state.adminEvents.unshift({
      title,
      label: "success",
      tone: "good",
      createdAt: new Date().toISOString(),
      payload: result,
    });
    state.adminEvents = state.adminEvents.slice(0, 8);
    await refreshHealth();
    showToast(`${title} completed.`, "good");
    renderAdminView();
  } catch (error) {
    state.adminEvents.unshift({
      title,
      label: "failed",
      tone: "bad",
      createdAt: new Date().toISOString(),
      payload: { error: error.message || "request failed" },
    });
    state.adminEvents = state.adminEvents.slice(0, 8);
    showToast(error.message || `${title} failed.`, "bad");
    renderAdminView();
  }
}

async function renderNotFound() {
  appNode.innerHTML = `
    <section class="empty-state">
      <p class="eyebrow">Route</p>
      <h2 class="page-title">页面不存在</h2>
      <p class="page-copy">当前路由未实现，请从导航栏切换到已支持页面。</p>
      ${linkButton(buildHash("/reports"), "返回 Reports")}
    </section>
  `;
}

async function renderRoute() {
  const route = getRoute();
  const shareToken = route.section === "report-only" ? String(route.params.get("share_token") || "").trim() : "";
  const isPublicReportOnly = route.section === "report-only" && Boolean(shareToken);
  if (!state.currentUser && !isPublicReportOnly) {
    renderLoginView();
    return;
  }
  const isReportOnlyRoute = route.section === "report-only";
  setTopbarVisible(!isReportOnlyRoute);
  setLayoutMode(isReportOnlyRoute ? "reader" : "app");
  const navSection = ["uploads", "reports", "wiki", "ask", "tasks", "conflicts", "admin"].includes(route.section)
    ? route.section
    : "reports";
  setActiveNav(isReportOnlyRoute ? "" : navSection);
  renderLoading();

  try {
    switch (route.section) {
      case "report-only":
        await renderReportOnlyDetail(route.detail, shareToken);
        break;
      case "uploads":
        await renderUploadsView(route);
        break;
      case "reports":
        await renderReportsView(route);
        break;
      case "wiki":
        await renderWikiView(route);
        break;
      case "ask":
        await renderAskView(route);
        break;
      case "tasks":
        await renderTasksView(route);
        break;
      case "conflicts":
        await renderConflictsView(route);
        break;
      case "admin":
        await renderAdminView(route);
        break;
      default:
        await renderNotFound();
        break;
    }
  } catch (error) {
    if (isUnauthorizedError(error)) {
      return;
    }
    renderError(error);
  }
}

if (!location.hash) {
  location.hash = buildHash("/reports");
}

window.addEventListener("hashchange", () => {
  renderRoute();
});

window.addEventListener("DOMContentLoaded", async () => {
  restoreClientAuthState();
  renderSessionChrome();
  await refreshHealth();
  const route = getRoute();
  const isPublicReportOnly = route.section === "report-only" && Boolean(String(route.params.get("share_token") || "").trim());
  if (isPublicReportOnly) {
    if (!state.appkey) {
      state.currentUser = null;
      renderSessionChrome();
    }
    await renderRoute();
    return;
  }
  if (!state.appkey) {
    renderLoginView();
    return;
  }
  try {
    state.currentUser = await apiGet("/api/auth/me");
    persistClientAuthState();
    renderSessionChrome();
    await renderRoute();
  } catch (error) {
    if (isUnauthorizedError(error)) {
      renderLoginView();
      return;
    }
    renderError(error);
  }
});
