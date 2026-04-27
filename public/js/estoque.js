// Módulo de estoque: campos customizados (FieldDefinition) e produtos.
// Auto-inicializa ao carregar e responde ao hash #estoque.

const toastEl = document.getElementById("toast");
function showToast(msg, type = "success") {
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.className = "toast show " + (type === "error" ? "error" : "success");
  setTimeout(() => toastEl.classList.remove("show"), 2400);
}

const money = (v) =>
  Number(v || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

async function api(path, { method = "GET", body, params } = {}) {
  const url = new URL(path, window.location.origin);
  if (params)
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });

  const opts = { method, headers: {}, credentials: "include" };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }

  const res = await fetch(url, opts);
  if (res.redirected) {
    window.location.href = res.url || "/login";
    return null;
  }
  if (res.status === 401 || res.status === 403) {
    window.location.href = "/login";
    return null;
  }

  let data = {};
  try { data = await res.json(); } catch {}

  if (!res.ok) {
    const msg = data?.error || "Erro";
    const det = data?.details
      ? (typeof data.details === "string" ? data.details : Object.values(data.details).join(" • "))
      : "";
    showToast(det ? `${msg}: ${det}` : msg, "error");
    throw new Error(msg);
  }
  return data;
}

// ============================================================
//  ESTADO
// ============================================================
let camposCache = [];   // FieldDefinition[]
let prodPage = 1, prodPer = 24, prodQ = "";

// ============================================================
//  CAMPOS CUSTOMIZADOS
// ============================================================
async function carregarCampos() {
  const data = await api("/api/field-definitions").catch(() => ({}));
  camposCache = data?.campos || [];
  renderCamposTable();
  return camposCache;
}

function renderCamposTable() {
  const tbody = document.getElementById("campoTable");
  if (!tbody) return;
  if (!camposCache.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">Nenhum campo cadastrado.</td></tr>`;
    return;
  }
  tbody.innerHTML = camposCache.map(c => `
    <tr data-id="${c.id_field}">
      <td>${c.ordem}</td>
      <td>${escapeHtml(c.label)}</td>
      <td><code>${escapeHtml(c.nome)}</code></td>
      <td>${escapeHtml(c.tipo)}</td>
      <td>${c.obrigatorio ? "Sim" : "—"}</td>
      <td>${(c.opcoes || []).map(o => escapeHtml(o)).join(", ")}</td>
      <td><button class="btn btn-sm btn-outline-secondary btn-edit-campo">Editar</button></td>
    </tr>
  `).join("");

  tbody.querySelectorAll(".btn-edit-campo").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const id = e.target.closest("tr").dataset.id;
      abrirEditCampo(id);
    });
  });
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function setupModalCampoNovo() {
  const tipo = document.getElementById("campoTipo");
  const opcoesWrap = document.getElementById("campoOpcoesWrap");
  tipo.addEventListener("change", () => {
    opcoesWrap.classList.toggle("d-none", tipo.value !== "select");
  });

  const modal = document.getElementById("modalCampo");
  modal.addEventListener("show.bs.modal", () => {
    document.getElementById("campoLabel").value = "";
    document.getElementById("campoTipo").value = "texto";
    document.getElementById("campoOpcoes").value = "";
    document.getElementById("campoObrigatorio").checked = false;
    document.getElementById("campoOrdem").value = 0;
    opcoesWrap.classList.add("d-none");
  });

  document.getElementById("btnSalvarCampo").addEventListener("click", async () => {
    const tipoVal = document.getElementById("campoTipo").value;
    const payload = {
      label: document.getElementById("campoLabel").value.trim(),
      tipo: tipoVal,
      obrigatorio: document.getElementById("campoObrigatorio").checked,
      ordem: Number(document.getElementById("campoOrdem").value || 0),
    };
    if (tipoVal === "select") {
      payload.opcoes = document.getElementById("campoOpcoes").value
        .split("\n").map(s => s.trim()).filter(Boolean);
    }
    try {
      await api("/api/field-definitions", { method: "POST", body: payload });
      showToast("Campo criado");
      bootstrap.Modal.getInstance(modal).hide();
      await carregarCampos();
    } catch {}
  });
}

function setupModalCampoEdit() {
  const tipo = document.getElementById("campoEditTipo");
  const opcoesWrap = document.getElementById("campoEditOpcoesWrap");
  tipo.addEventListener("change", () => {
    opcoesWrap.classList.toggle("d-none", tipo.value !== "select");
  });

  document.getElementById("btnAtualizarCampo").addEventListener("click", async () => {
    const id = document.getElementById("campoEditId").value;
    const tipoVal = document.getElementById("campoEditTipo").value;
    const payload = {
      label: document.getElementById("campoEditLabel").value.trim(),
      tipo: tipoVal,
      obrigatorio: document.getElementById("campoEditObrigatorio").checked,
      ordem: Number(document.getElementById("campoEditOrdem").value || 0),
    };
    if (tipoVal === "select") {
      payload.opcoes = document.getElementById("campoEditOpcoes").value
        .split("\n").map(s => s.trim()).filter(Boolean);
    } else {
      payload.opcoes = [];
    }
    try {
      await api(`/api/field-definitions/${id}`, { method: "PATCH", body: payload });
      showToast("Campo atualizado");
      bootstrap.Modal.getInstance(document.getElementById("modalCampoEdit")).hide();
      await carregarCampos();
    } catch {}
  });

  document.getElementById("btnExcluirCampo").addEventListener("click", async () => {
    const id = document.getElementById("campoEditId").value;
    if (!confirm("Excluir esse campo? Produtos antigos mantêm o valor mas ele não será mais editável.")) return;
    try {
      await api(`/api/field-definitions/${id}`, { method: "DELETE" });
      showToast("Campo excluído");
      bootstrap.Modal.getInstance(document.getElementById("modalCampoEdit")).hide();
      await carregarCampos();
    } catch {}
  });
}

function abrirEditCampo(id) {
  const c = camposCache.find(c => String(c.id_field) === String(id));
  if (!c) return;
  document.getElementById("campoEditId").value = c.id_field;
  document.getElementById("campoEditLabel").value = c.label;
  document.getElementById("campoEditTipo").value = c.tipo;
  document.getElementById("campoEditObrigatorio").checked = !!c.obrigatorio;
  document.getElementById("campoEditOrdem").value = c.ordem;
  document.getElementById("campoEditOpcoes").value = (c.opcoes || []).join("\n");
  document.getElementById("campoEditOpcoesWrap").classList.toggle("d-none", c.tipo !== "select");
  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalCampoEdit")).show();
}

// ============================================================
//  PRODUTOS
// ============================================================
function inputForCampo(c, valor, prefix = "") {
  const id = `${prefix}extra_${c.nome}`;
  const required = c.obrigatorio ? "required" : "";
  const v = valor ?? "";
  let inner = "";
  switch (c.tipo) {
    case "numero":
      inner = `<input type="number" step="any" class="form-control" id="${id}" data-extra="${c.nome}" data-tipo="${c.tipo}" value="${escapeHtml(v)}" ${required}>`;
      break;
    case "data":
      inner = `<input type="date" class="form-control" id="${id}" data-extra="${c.nome}" data-tipo="${c.tipo}" value="${escapeHtml(v)}" ${required}>`;
      break;
    case "booleano":
      inner = `
        <select class="form-select" id="${id}" data-extra="${c.nome}" data-tipo="${c.tipo}">
          <option value="">—</option>
          <option value="true" ${v === true || v === "true" ? "selected" : ""}>Sim</option>
          <option value="false" ${v === false || v === "false" ? "selected" : ""}>Não</option>
        </select>`;
      break;
    case "select":
      inner = `<select class="form-select" id="${id}" data-extra="${c.nome}" data-tipo="${c.tipo}" ${required}>
        <option value="">—</option>
        ${(c.opcoes || []).map(o => `<option value="${escapeHtml(o)}" ${o === v ? "selected" : ""}>${escapeHtml(o)}</option>`).join("")}
      </select>`;
      break;
    default: // texto
      inner = `<input type="text" class="form-control" id="${id}" data-extra="${c.nome}" data-tipo="${c.tipo}" value="${escapeHtml(v)}" ${required}>`;
  }
  const obrig = c.obrigatorio ? ' <span class="text-danger">*</span>' : "";
  return `<div class="col-12 col-md-6">
    <label class="form-label" for="${id}">${escapeHtml(c.label)}${obrig}</label>
    ${inner}
  </div>`;
}

function renderExtrasForm(container, valoresAtuais = {}) {
  if (!camposCache.length) {
    container.innerHTML = `<div class="col-12 text-muted small">Nenhum campo customizado definido. Cadastre na aba "Campos customizados".</div>`;
    return;
  }
  container.innerHTML = camposCache.map(c => inputForCampo(c, valoresAtuais[c.nome])).join("");
}

function coletarExtras(container) {
  const extras = {};
  container.querySelectorAll("[data-extra]").forEach(el => {
    const nome = el.dataset.extra;
    const tipo = el.dataset.tipo;
    let v = el.value;
    if (v === "" || v === null || v === undefined) return;
    if (tipo === "numero") v = Number(v);
    if (tipo === "booleano") v = (v === "true");
    extras[nome] = v;
  });
  return extras;
}

async function carregarProdutos() {
  const data = await api("/api/produtos", {
    params: { q: prodQ, page: prodPage, per_page: prodPer }
  }).catch(() => ({}));

  const tbody = document.getElementById("prodTable");
  const lista = data?.produtos || [];
  if (!lista.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Nenhum produto.</td></tr>`;
  } else {
    tbody.innerHTML = lista.map(p => {
      const extrasResumo = Object.entries(p.extras || {})
        .slice(0, 3)
        .map(([k, v]) => `<span class="badge text-bg-light me-1">${escapeHtml(k)}: ${escapeHtml(String(v))}</span>`)
        .join("");
      return `<tr data-id="${p.id_produto}">
        <td>${p.id_produto}</td>
        <td>${escapeHtml(p.nome)}</td>
        <td>R$ ${money(p.preco)}</td>
        <td>${p.quantidade}</td>
        <td>${extrasResumo || '<span class="text-muted small">—</span>'}</td>
        <td>
          <button class="btn btn-sm btn-outline-secondary btn-edit-prod">Editar</button>
          <button class="btn btn-sm btn-outline-primary btn-ajustar-prod">±</button>
        </td>
      </tr>`;
    }).join("");
    tbody.querySelectorAll(".btn-edit-prod").forEach(btn => {
      btn.addEventListener("click", (e) => abrirEditProduto(e.target.closest("tr").dataset.id));
    });
    tbody.querySelectorAll(".btn-ajustar-prod").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const id = e.target.closest("tr").dataset.id;
        const raw = prompt("Ajustar quantidade (digite +N ou -N):");
        if (!raw) return;
        const delta = Number(raw.trim());
        if (!Number.isFinite(delta)) return showToast("Valor inválido", "error");
        try {
          await api(`/api/produtos/${id}/ajustar`, { method: "POST", body: { delta } });
          showToast("Quantidade ajustada");
          carregarProdutos();
        } catch {}
      });
    });
  }
  renderProdPagination(data?.pagination);
}

function renderProdPagination(pag) {
  const container = document.getElementById("prodPag");
  if (!container) return;
  container.innerHTML = "";
  if (!pag) return;
  const total_pages = pag.total_pages || 1;
  const add = (p, label, disabled = false, active = false) => {
    const li = document.createElement("li");
    li.className = "page-item " + (disabled ? "disabled " : "") + (active ? "active " : "");
    const a = document.createElement("a");
    a.className = "page-link";
    a.href = "#";
    a.textContent = label;
    a.onclick = (e) => {
      e.preventDefault();
      if (!disabled && !active) { prodPage = p; carregarProdutos(); }
    };
    li.appendChild(a);
    container.appendChild(li);
  };
  add(pag.page - 1, "«", !pag.has_prev);
  for (let i = 1; i <= total_pages; i++) {
    if (i === 1 || i === total_pages || Math.abs(i - pag.page) <= 2) {
      add(i, String(i), false, i === pag.page);
    }
  }
  add(pag.page + 1, "»", !pag.has_next);
}

function setupModalProdutoNovo() {
  const modal = document.getElementById("modalProduto");
  modal.addEventListener("show.bs.modal", () => {
    document.getElementById("prodNome").value = "";
    document.getElementById("prodPreco").value = "0";
    document.getElementById("prodQtd").value = "0";
    renderExtrasForm(document.getElementById("prodExtrasForm"));
  });

  document.getElementById("btnSalvarProduto").addEventListener("click", async () => {
    const payload = {
      nome: document.getElementById("prodNome").value.trim(),
      preco: Number(document.getElementById("prodPreco").value || 0),
      quantidade: Number(document.getElementById("prodQtd").value || 0),
      extras: coletarExtras(document.getElementById("prodExtrasForm")),
    };
    try {
      await api("/api/produtos", { method: "POST", body: payload });
      showToast("Produto criado");
      bootstrap.Modal.getInstance(modal).hide();
      await carregarProdutos();
    } catch {}
  });
}

function setupModalProdutoEdit() {
  document.getElementById("btnAtualizarProduto").addEventListener("click", async () => {
    const id = document.getElementById("prodEditId").value;
    const payload = {
      nome: document.getElementById("prodEditNome").value.trim(),
      preco: Number(document.getElementById("prodEditPreco").value || 0),
      quantidade: Number(document.getElementById("prodEditQtd").value || 0),
      extras: coletarExtras(document.getElementById("prodEditExtrasForm")),
    };
    try {
      await api(`/api/produtos/${id}`, { method: "PATCH", body: payload });
      showToast("Produto atualizado");
      bootstrap.Modal.getInstance(document.getElementById("modalProdutoEdit")).hide();
      await carregarProdutos();
    } catch {}
  });

  document.getElementById("btnExcluirProduto").addEventListener("click", async () => {
    const id = document.getElementById("prodEditId").value;
    if (!confirm("Excluir esse produto?")) return;
    try {
      await api(`/api/produtos/${id}`, { method: "DELETE" });
      showToast("Produto excluído");
      bootstrap.Modal.getInstance(document.getElementById("modalProdutoEdit")).hide();
      await carregarProdutos();
    } catch {}
  });
}

async function abrirEditProduto(id) {
  const data = await api(`/api/produtos/${id}`).catch(() => null);
  if (!data?.produto) return;
  const p = data.produto;
  document.getElementById("prodEditId").value = p.id_produto;
  document.getElementById("prodEditNome").value = p.nome;
  document.getElementById("prodEditPreco").value = p.preco;
  document.getElementById("prodEditQtd").value = p.quantidade;
  renderExtrasForm(document.getElementById("prodEditExtrasForm"), p.extras || {});
  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalProdutoEdit")).show();
}

// ============================================================
//  ROTEAMENTO + INIT
// ============================================================
let inited = false;
async function ativarSecao() {
  if (!inited) {
    setupModalCampoNovo();
    setupModalCampoEdit();
    setupModalProdutoNovo();
    setupModalProdutoEdit();
    document.getElementById("btnProdBuscar")?.addEventListener("click", () => {
      prodQ = document.getElementById("prodSearch").value.trim();
      prodPage = 1;
      carregarProdutos();
    });
    document.getElementById("prodSearch")?.addEventListener("keypress", (e) => {
      if (e.key === "Enter") document.getElementById("btnProdBuscar").click();
    });
    inited = true;
  }
  // sempre recarrega ao abrir
  await carregarCampos();
  await carregarProdutos();
}

function init() {
  const section = document.getElementById("page-estoque");
  if (!section) return;

  // o roteador do index.js já tira a d-none. Só precisamos disparar o load
  // quando o hash for #estoque.
  function onHash() {
    if ((location.hash || "#dashboard").replace("#", "") === "estoque") {
      ativarSecao();
    }
  }
  window.addEventListener("hashchange", onHash);
  onHash(); // caso a página abra direto em #estoque
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
