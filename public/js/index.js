import { initSidebar } from "./sidebar.js";

// ==================== VARIÁVEIS DE ESTADO ====================
document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
});

let cliPage = 1,
  cliPer = 24,
  cliQ = "";
let veiPage = 1,
  veiPer = 24,
  veiQ = "",
  veiCli = null;
let svcPage = 1,
  svcPer = 24,
  svcQ = "";
let venPage = 1,
  venPer = 10,
  venQ = "",
  venStatus = "",
  venPag = "";
// NOVO: datas de filtro das vendas
let venDataIni = "",
  venDataFim = "";

let cxPage = 1,
  cxPer = 24,
  cxDataRef = null;

let currentVendaId = null; // venda atualmente aberta no modal

// refs globais do modal de edição de venda/orçamento
const vendaModalEl = document.getElementById("modalVendaEdit");
const vendaModal = vendaModalEl
  ? new bootstrap.Modal(vendaModalEl, { backdrop: "static" })
  : null;

// Campos do header do modal
const elVendaTitulo = document.getElementById("editVendaTitulo"); // "Venda #123"
const elVendaStatus = document.getElementById("editVendaStatus"); // badge status
const elVendaPagamentoBadge = document.getElementById("editVendaPagamentoBadge"); // badge pagamento
const elVendaTotal = document.getElementById("editVendaTotal"); // "R$ 100,00"

// Botões header modal
const btnVendaPDF = document.getElementById("btnVendaPDF");
const btnVendaCancelar = document.getElementById("btnVendaCancelar");
const btnVendaFecharX = document.getElementById("btnVendaFecharX");

// Seção "Dados da venda"
const elVendaDescInput = document.getElementById("editVendaDescricaoInput"); // descrição da nota / observação
const elVendaPagamentoSelect = document.getElementById("editVendaPagamentoSelect"); // select forma_pagamento (no bloco Dados da venda / orçamento)
const btnSalvarCabecalho = document.getElementById("btnSalvarCabecalho");

// Seção Itens da venda
const elBuscaServico = document.getElementById("editItemServicoBusca");
const elSugestoesServico = document.getElementById("servicoSugestoes");
const elServicoIdHidden = document.getElementById("editItemServicoId");
const elServicoPrecoHidden = document.getElementById("editItemServicoPreco");
const elServicoHintBox = document.getElementById("servicoEscolhidoHint");
const elServicoHintNome = document.getElementById("servicoEscolhidoNome");
const elServicoHintValor = document.getElementById("servicoEscolhidoValor");

const elItemQtd = document.getElementById("editItemQtd");
const elItemDescReais = document.getElementById("editItemDesc");
const btnAddItem = document.getElementById("btnItemAdd");

const itensTableBody = document.getElementById("itensTableBody"); // tbody da listagem de itens já adicionados

// Rodapé modal
const btnVendaFechar = document.getElementById("btnVendaFechar");

// ==================== HELPERS GERAIS ====================

const toastEl = document.getElementById("toast");
function showToast(msg, type = "success") {
  toastEl.textContent = msg;
  toastEl.className = "toast show " + (type === "error" ? "error" : "success");
  setTimeout(() => toastEl.classList.remove("show"), 2400);
}

const money = (v) =>
  Number(v || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

/* ============================================
   API HELPER COM CHECK DE LOGIN
   ============================================
   - Trata redirect 302
   - Trata 401/403 vindo da API
   - Evita tentar fazer .json() em HTML
   - Se descobrir que não tem sessão válida -> manda pro /login
*/
async function api(path, { method = "GET", body, params } = {}) {
  const url = new URL(path, window.location.origin);
  if (params)
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        url.searchParams.set(k, v);
      }
    });

  const options = { method, headers: {}, credentials: "include" }; // garante que cookies de sessão vão junto
  if (body) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const res = await fetch(url, options);

  // 1. redirect explícito (ex.: backend mandou 302 pra /login)
  if (res.redirected) {
    window.location.href = res.url || "/login";
    return null;
  }

  // 2. checa content-type
  const contentType = res.headers.get("Content-Type") || "";

  // 2a. PDF? devolve o Response cru
  if (contentType.includes("application/pdf")) {
    return res;
  }

  // 3. sessão inválida / proibido
  if (res.status === 401 || res.status === 403) {
    try {
      const errData = contentType.includes("application/json")
        ? await res.json()
        : await res.text();
      console.warn("Sessão inválida:", errData);
    } catch (e) {}
    window.location.href = "/login";
    return null;
  }

  // 4. servidor retornou HTML (provavelmente login)
  if (contentType.includes("text/html") || contentType.includes("text/plain")) {
    const text = await res.text();

    if (text.startsWith("<!DOCTYPE html")) {
      window.location.href = "/login";
      return null;
    }

    try {
      return JSON.parse(text);
    } catch (err) {
      console.error("Resposta inesperada da API (HTML):", text);
      showToast("Erro de autenticação", "error");
      window.location.href = "/login";
      return null;
    }
  }

  // 5. caso normal: JSON
  let data = {};
  try {
    data = await res.json();
  } catch (e) {
    data = {};
  }

  // 6. erro HTTP -> toast
  if (!res.ok) {
    const msg = data?.error || "Erro";
    showToast(msg, "error");
    throw new Error(msg);
  }

  return data;
}

// cria badge bonita
function badge(texto, classe = "") {
  return `<span class="badge-rounded ${classe}">${texto}</span>`;
}

// fácil debounce
function debounce(fn, delay = 250) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}

// ==================== PAGINAÇÃO ====================
function renderPagination(container, page, per_page, total, onPage) {
  const total_pages = Math.max(1, Math.ceil(total / per_page));
  container.innerHTML = "";
  const ul = container;

  const add = (p, label, disabled = false, active = false) => {
    const li = document.createElement("li");
    li.className =
      "page-item " + (disabled ? "disabled " : "") + (active ? "active " : "");
    const a = document.createElement("a");
    a.className = "page-link";
    a.href = "#";
    a.textContent = label;
    a.onclick = (e) => {
      e.preventDefault();
      if (!disabled && !active) onPage(p);
    };
    li.appendChild(a);
    ul.appendChild(li);
  };

  add(page - 1, "«", page <= 1);
  for (let i = 1; i <= total_pages; i++) {
    if (i === 1 || i === total_pages || Math.abs(i - page) <= 2) {
      add(i, String(i), false, i === page);
    } else if (Math.abs(i - page) === 3) {
      const li = document.createElement("li");
      li.className = "page-item disabled";
      li.innerHTML = '<span class="page-link">…</span>';
      ul.appendChild(li);
    }
  }
  add(page + 1, "»", page >= total_pages);
}

// ==================== ROTEADOR DAS PÁGINAS (dashboard/clientes/etc) ====================
const sections = {
  dashboard: document.getElementById("page-dashboard"),
  clientes: document.getElementById("page-clientes"),
  veiculos: document.getElementById("page-veiculos"),
  servicos: document.getElementById("page-servicos"),
  vendas: document.getElementById("page-vendas"),
  caixa: document.getElementById("page-caixa"),
};

function showPage(hash) {
  const key = (hash || "#dashboard").replace("#", "");
  Object.values(sections).forEach((s) => s.classList.add("d-none"));
  (sections[key] || sections.dashboard).classList.remove("d-none");

  // ATUALIZADO: se seu menu está dentro de #sidebar
  document.querySelectorAll("#sidebar .nav-link").forEach((a) => {
    a.classList.toggle("active", a.getAttribute("href") === "#" + key);
  });

  if (key === "dashboard") loadDashboard();
  if (key === "clientes") loadClientes();
  if (key === "veiculos") loadVeiculos();
  if (key === "servicos") loadServicos();
  if (key === "vendas") {
    loadVendas();
  }
  if (key === "caixa") loadCaixa();
}

window.addEventListener("hashchange", () => showPage(location.hash));
showPage(location.hash);

// ==================== DASHBOARD ====================
async function loadDashboard() {
  // monta data local (sem UTC bug)
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0"); // meses começam em 0
  const dd = String(now.getDate()).padStart(2, "0");
  const hojeLocal = `${yyyy}-${mm}-${dd}`; // ex "2025-10-27"

  try {
    // 1. Caixa de hoje
    const cx = await api("/api/caixa", { params: { data: hojeLocal } });
    if (!cx) return;
    document.getElementById("kpiCaixaHoje").textContent =
      "R$ " + money(cx.total_valor || cx.total || 0);

    // aqui você pode querer mudar pra data_ini/data_fim também
    const ven = await api("/api/vendas", {
      params: {
        page: 1,
        per_page: 1,
        status: "FINALIZADA",
        data_ini: hojeLocal,
        data_fim: hojeLocal,
      },
    });
    if (!ven) return;
    document.getElementById("kpiVendasHoje").textContent = String(
      ven.pagination?.total || 0
    );

    const sv = await api("/api/servicos", {
      params: { page: 1, per_page: 1 },
    });
    if (!sv) return;
    document.getElementById("kpiServicos").textContent = String(
      sv.pagination?.total || 0
    );
  } catch {}
}

// ==================== CLIENTES ====================
async function loadClientes() {
  const resp = await api("/api/clientes", {
    params: { q: cliQ, page: cliPage, per_page: cliPer },
  });
  if (!resp) return;
  const { clientes, pagination } = resp;

  const tbody = document.getElementById("cliTable");
  tbody.innerHTML = (clientes || [])
    .map(
      (c) => `
    <tr>
      <td>${c.id_cliente}</td>
      <td>${c.nome || ""}</td>
      <td>${c.numero || ""}</td>
      <td class="actions-col">
        <button class="btn btn-sm btn-outline-secondary" onclick="openEditCliente(${c.id_cliente})">
          <i class="bi bi-pencil"></i> Editar
        </button>
      </td>
    </tr>
  `
    )
    .join("");

  renderPagination(
    document.getElementById("cliPag"),
    pagination.page,
    pagination.per_page,
    pagination.total,
    (p) => {
      cliPage = p;
      loadClientes();
    }
  );
}
document.getElementById("btnCliBusca").onclick = () => {
  cliQ = document.getElementById("cliSearch").value || "";
  cliPage = 1;
  loadClientes();
};
document.getElementById("btnSalvarCliente").onclick = async () => {
  try {
    const payload = {
      nome: cliNome.value,
      cpf: cliCPF.value,
      numero: cliTel.value,
    };
    const ok = await api("/api/clientes", { method: "POST", body: payload });

    if (!ok) return;
    showToast("Cliente salvo!");
    bootstrap.Modal.getInstance(
      document.getElementById("modalCliente")
    ).hide();
    loadClientes();
  } catch (e) {
    showToast(e.message, "error");
  }
};

// editar cliente
window.openEditCliente = async (id) => {
  try {
    const res = await api(`/api/clientes/${id}`);
    if (!res) return;
    const c = res.cliente || res;

    document.getElementById("cliEditId").value = c.id_cliente;
    document.getElementById("cliEditNome").value = c.nome || "";
    document.getElementById("cliEditCPF").value = c.cpf || "";
    document.getElementById("cliEditTel").value = c.numero || "";

    new bootstrap.Modal(
      document.getElementById("modalClienteEdit")
    ).show();
  } catch (e) {}
};
document.getElementById("btnAtualizarCliente").onclick = async () => {
  const id = Number(document.getElementById("cliEditId").value);
  try {
    const body = {
      nome: document.getElementById("cliEditNome").value,
      cpf: document.getElementById("cliEditCPF").value,
      numero: document.getElementById("cliEditTel").value,
    };
    const ok = await api(`/api/clientes/${id}`, { method: "PUT", body });
    if (!ok) return;
    showToast("Cliente atualizado!");
    bootstrap.Modal.getInstance(
      document.getElementById("modalClienteEdit")
    ).hide();
    loadClientes();
  } catch (e) {}
};

// ==================== VEÍCULOS ====================
async function loadVeiculos() {
  const params = { q: veiQ, page: veiPage, per_page: veiPer };
  if (veiCli) params.id_cliente = veiCli;

  const resp = await api("/api/veiculos", { params });
  if (!resp) return;
  const { veiculos, pagination } = resp;

  const tbody = document.getElementById("veiTable");
  tbody.innerHTML = (veiculos || [])
    .map(
      (v) => `
    <tr>
      <td>${v.id_veiculo}</td>
      <td>${v.placa}</td>
      <td>${v.id_cliente}</td>
      <td>${v.marca || ""}</td>
      <td>${v.modelo || ""}</td>
      <td>${v.km || ""}</td>
      <td class="actions-col">
        <button class="btn btn-sm btn-outline-secondary" onclick="openEditVeiculo(${v.id_veiculo})">
          <i class="bi bi-pencil"></i> Editar
        </button>
      </td>
    </tr>
  `
    )
    .join("");

  renderPagination(
    document.getElementById("veiPag"),
    pagination.page,
    pagination.per_page,
    pagination.total,
    (p) => {
      veiPage = p;
      loadVeiculos();
    }
  );
}
document.getElementById("btnVeiBusca").onclick = () => {
  veiQ = document.getElementById("veiSearch").value || "";
  veiCli = document.getElementById("veiCliId").value || null;
  veiPage = 1;
  loadVeiculos();
};

// autocomplete cliente dentro do modalVeiculo (novo veículo)
let veiCliBuscaTimer = null;

async function buscarClientesPorNome(term) {
  if (!term || term.trim().length < 2) return [];
  try {
    const resp = await api("/api/clientes", {
      params: { q: term.trim(), page: 1, per_page: 10 },
    });
    if (!resp) return [];
    const { clientes } = resp;
    return clientes || [];
  } catch {
    return [];
  }
}

function renderSugestoesClientes(list) {
  const box = document.getElementById("veiCliSug");
  if (!box) return;
  if (!list.length) {
    box.style.display = "none";
    box.innerHTML = "";
    return;
  }
  box.innerHTML = list
    .map(
      (c) => `
    <button type="button" class="list-group-item list-group-item-action"
            data-id="${c.id_cliente}" data-nome="${c.nome || ""}">
      <div class="d-flex justify-content-between">
        <strong>${c.nome || "-"}</strong>
        <span class="text-muted">#${c.id_cliente}</span>
      </div>
      ${c.numero ? `<small class="text-muted">• ${c.numero}</small>` : ""}
    </button>
  `
    )
    .join("");
  box.style.display = "block";

  box.querySelectorAll(".list-group-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("veiCliIdHidden").value = btn.dataset.id;
      document.getElementById("veiCliNome").value = btn.dataset.nome;
      box.style.display = "none";
      box.innerHTML = "";
    });
  });
}

const veiCliNomeEl = document.getElementById("veiCliNome");
const veiCliSugEl = document.getElementById("veiCliSug");

veiCliNomeEl?.addEventListener("input", () => {
  document.getElementById("veiCliIdHidden").value = "";
  clearTimeout(veiCliBuscaTimer);
  veiCliBuscaTimer = setTimeout(async () => {
    const lista = await buscarClientesPorNome(veiCliNomeEl.value);
    renderSugestoesClientes(lista);
  }, 250);
});

document.addEventListener("click", (e) => {
  if (!veiCliSugEl) return;
  const dentro =
    e.target.closest("#veiCliSug") || e.target.closest("#veiCliNome");
  if (!dentro) {
    veiCliSugEl.style.display = "none";
  }
});

// salvar veículo novo
document.getElementById("btnSalvarVeiculo").onclick = async () => {
  try {
    const id_cliente = Number(
      document.getElementById("veiCliIdHidden").value || 0
    );
    const placa = (document.getElementById("veiPlaca").value || "")
      .trim()
      .toUpperCase();
    const km = Number(document.getElementById("veiKM").value || 0);
    const observacao = (document.getElementById("veiObs").value || "").trim();
    const marca = (document.getElementById("veiMarca").value || "").trim();
    const modelo = (document.getElementById("veiModel").value || "").trim();
    const cor = (document.getElementById("veiCor").value || "").trim();

    if (!id_cliente) {
      showToast("Selecione um cliente da lista.", "error");
      return;
    }
    if (!placa) {
      showToast("Informe a placa.", "error");
      return;
    }

    const payload = {
      id_cliente,
      placa,
      km,
      observacao,
      marca,
      modelo,
      cor,
    };
    const ok = await api("/api/veiculos", { method: "POST", body: payload });
    if (!ok) return;
    showToast("Veículo salvo!");
    bootstrap.Modal.getInstance(
      document.getElementById("modalVeiculo")
    ).hide();

    // limpa form
    document.getElementById("veiCliNome").value = "";
    document.getElementById("veiCliIdHidden").value = "";
    document.getElementById("veiPlaca").value = "";
    document.getElementById("veiKM").value = "";
    document.getElementById("veiCor").value = "";
    document.getElementById("veiModel").value = "";
    document.getElementById("veiMarca").value = "";
    document.getElementById("veiObs").value = "";

    loadVeiculos();
  } catch (e) {
    console.error("Erro ao salvar veículo:", e);
    showToast("Erro ao salvar veículo", "error");
  }
};

// editar veículo existente
window.openEditVeiculo = async (id) => {
  try {
    const res = await api(`/api/veiculos/${id}`);
    if (!res) return;
    const v = res.veiculo || res;

    document.getElementById("veiEditId").value = v.id_veiculo;
    document.getElementById("veiEditPlaca").value = v.placa || "";
    document.getElementById("veiEditKM").value = v.km || 0;
    document.getElementById("veiEditObs").value = v.observacao || "";
    document.getElementById("veiEditMarca").value = v.marca || "";
    document.getElementById("veiEditModel").value = v.modelo || "";
    document.getElementById("veiEditCor").value = v.cor || "";

    new bootstrap.Modal(
      document.getElementById("modalVeiculoEdit")
    ).show();
  } catch (e) {}
};

document.getElementById("btnAtualizarVeiculo").onclick = async () => {
  const id = Number(document.getElementById("veiEditId").value);
  try {
    const body = {
      placa: (document.getElementById("veiEditPlaca").value || "").toUpperCase(),
      km: Number(document.getElementById("veiEditKM").value || 0),
      observacao: document.getElementById("veiEditObs").value || "",
      marca: document.getElementById("veiEditMarca").value || "",
      modelo: document.getElementById("veiEditModel").value || "",
      cor: document.getElementById("veiEditCor").value || "",
    };
    const ok = await api(`/api/veiculos/${id}`, { method: "PUT", body });
    if (!ok) return;
    showToast("Veículo atualizado!");
    bootstrap.Modal.getInstance(
      document.getElementById("modalVeiculoEdit")
    ).hide();
    loadVeiculos();
  } catch (e) {}
};

// ==================== SERVIÇOS ====================
async function loadServicos() {
  const resp = await api("/api/servicos", {
    params: { q: svcQ, page: svcPage, per_page: svcPer },
  });
  if (!resp) return;
  const { servicos, pagination } = resp;

  const tbody = document.getElementById("svcTable");
  tbody.innerHTML = (servicos || [])
    .map(
      (s) => `
    <tr>
      <td>${s.id_servico}</td>
      <td>${s.nome}</td>
      <td>${money(s.valor)}</td>
      <td class="actions-col">
        <button class="btn btn-sm btn-outline-secondary" onclick="openEditServico(${s.id_servico})">
          <i class="bi bi-pencil"></i> Editar
        </button>
      </td>
    </tr>`
    )
    .join("");

  renderPagination(
    document.getElementById("svcPag"),
    pagination.page,
    pagination.per_page,
    pagination.total,
    (p) => {
      svcPage = p;
      loadServicos();
    }
  );
}
document.getElementById("btnSvcBusca").onclick = () => {
  svcQ = document.getElementById("svcSearch").value || "";
  svcPage = 1;
  loadServicos();
};
document.getElementById("btnSalvarServico").onclick = async () => {
  try {
    const payload = {
      nome: svcNome.value,
      valor: Number(svcValor.value || 0),
    };
    const ok = await api("/api/servicos", { method: "POST", body: payload });
    if (!ok) return;
    showToast("Serviço salvo!");
    bootstrap.Modal.getInstance(
      document.getElementById("modalServico")
    ).hide();
    loadServicos();
  } catch {}
};

window.openEditServico = async (id) => {
  try {
    const res = await api(`/api/servicos/${id}`);
    if (!res) return;
    const s = res.servico || res;
    document.getElementById("svcEditId").value = s.id_servico;
    document.getElementById("svcEditNome").value = s.nome || "";
    document.getElementById("svcEditValor").value = s.valor || 0;
    new bootstrap.Modal(
      document.getElementById("modalServicoEdit")
    ).show();
  } catch (e) {}
};
document.getElementById("btnAtualizarServico").onclick = async () => {
  const id = Number(document.getElementById("svcEditId").value);
  try {
    const body = {
      nome: document.getElementById("svcEditNome").value,
      valor: Number(document.getElementById("svcEditValor").value || 0),
    };
    const ok = await api(`/api/servicos/${id}`, { method: "PUT", body });
    if (!ok) return;
    showToast("Serviço atualizado!");
    bootstrap.Modal.getInstance(
      document.getElementById("modalServicoEdit")
    ).hide();
    loadServicos();
  } catch (e) {}
};

// ==================== VENDAS / ORÇAMENTOS ====================

function statusPill(s) {
  if (s === "FINALIZADA")
    return '<span class="badge-rounded pill-done">FINALIZADA</span>';
  if (s === "CANCELADA")
    return '<span class="badge-rounded pill-cancel">CANCELADA</span>';
  return '<span class="badge-rounded pill-open">EM_ANDAMENTO</span>';
}

async function loadVendas() {
  const params = {
    q: venQ,
    status: venStatus,
    pagamento: venPag,
    // NOVO: filtros de data indo pro backend
    data_ini: venDataIni || undefined,
    data_fim: venDataFim || undefined,
    page: venPage,
    per_page: venPer,
  };
  const resp = await api("/api/vendas", { params });
  if (!resp) return;
  const { vendas, pagination } = resp;

  const tbody = document.getElementById("venTable");
  tbody.innerHTML = (vendas || [])
    .map(
      (v) => `
    <tr>
      <td>${v.id_venda}</td>
      <td>${v.descricao || "-"}</td>
      <td>${v.cliente?.nome ?? v.id_cliente}</td>
      <td>${v.veiculo?.placa ?? v.id_veiculo}</td>
      <td>R$ ${money(v.total)}</td>
      <td>${statusPill(v.status)}</td>
      <td><span class="badge-rounded pill-pay">${v.pagamento}</span></td>
      <td>
        <button class="btn btn-sm btn-light card-btn" onclick="openVendaModal(${v.id_venda})">
          Abrir
        </button>
      </td>
    </tr>
  `
    )
    .join("");

  renderPagination(
    document.getElementById("venPag"),
    pagination.page,
    pagination.per_page,
    pagination.total,
    (p) => {
      venPage = p;
      loadVendas();
    }
  );
}

document.getElementById("btnVenBusca").onclick = () => {
  venQ = venSearch.value || "";
  venStatus = venFilStatus.value || "";
  venPag = venFilPag.value || "";

  // NOVO: ler os inputs <input type="date" id="venDataIni" ...> e <input type="date" id="venDataFim" ...>
  venDataIni = (document.getElementById("venDataIni")?.value || "").trim();
  venDataFim = (document.getElementById("venDataFim")?.value || "").trim();

  venPage = 1;
  loadVendas();
};

// criação de nova venda
const elBuscaCli = document.getElementById("venClienteBusca");
const elResCli = document.getElementById("venClienteResultados");
const elCliHidden = document.getElementById("venCli");
const elVeiSelect = document.getElementById("venVei");
const elDesc = document.getElementById("venDesc");

document
  .getElementById("modalVendaNova")
  .addEventListener("show.bs.modal", () => {
    elBuscaCli.value = "";
    elCliHidden.value = "";
    elResCli.style.display = "none";
    elResCli.innerHTML = "";
    elVeiSelect.innerHTML =
      '<option value="">Selecione o cliente primeiro…</option>';
    elVeiSelect.disabled = true;
    elDesc.value = "";
  });

const buscarClientesVenda = debounce(async (q) => {
  q = (q || "").trim();
  if (!q || q.length < 2) {
    elResCli.style.display = "none";
    elResCli.innerHTML = "";
    return;
  }
  try {
    const resp = await api("/api/clientes", {
      params: { q, page: 1, per_page: 10 },
    });
    if (!resp) return;
    const { clientes } = resp;

    if (!clientes?.length) {
      elResCli.innerHTML =
        '<div class="list-group-item text-muted">Nenhum cliente encontrado</div>';
      elResCli.style.display = "block";
      return;
    }
    elResCli.innerHTML = clientes
      .map(
        (c) => `
      <button type="button" class="list-group-item list-group-item-action"
              data-id="${c.id_cliente}" data-nome="${c.nome}">
        <div class="d-flex justify-content-between">
          <strong>${c.nome}</strong>
          <small class="text-muted">#${c.id_cliente}</small>
        </div>
        <small class="text-muted">${c.numero ? " • " + c.numero : ""}</small>
      </button>
    `
      )
      .join("");
    elResCli.style.display = "block";
  } catch {
    elResCli.style.display = "none";
  }
}, 300);

elBuscaCli.addEventListener("input", (e) => buscarClientesVenda(e.target.value));

elResCli.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-id]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const nome = btn.dataset.nome;
  elCliHidden.value = id;
  elBuscaCli.value = nome;
  elResCli.style.display = "none";
  await carregarVeiculosDoClienteVenda(id);
});

document.addEventListener("click", (e) => {
  if (!elResCli.contains(e.target) && e.target !== elBuscaCli)
    elResCli.style.display = "none";
});

async function carregarVeiculosDoClienteVenda(id_cliente) {
  elVeiSelect.disabled = true;
  elVeiSelect.innerHTML = "<option>Carregando…</option>";
  try {
    const resp = await api("/api/veiculos", {
      params: { id_cliente, page: 1, per_page: 200 },
    });
    if (!resp) {
      return;
    }
    const { veiculos } = resp;

    if (!veiculos?.length) {
      elVeiSelect.innerHTML = "<option>Cliente sem veículos</option>";
      return;
    }
    elVeiSelect.innerHTML = veiculos
      .map(
        (v) => `
      <option value="${v.id_veiculo}">
        ${v.placa}${
          v.km ? " • " + v.km + " km" : ""
        }${v.observacao ? " • " + v.observacao : ""}
      </option>`
      )
      .join("");
    elVeiSelect.disabled = false;
  } catch {
    elVeiSelect.innerHTML = "<option>Erro ao carregar veículos</option>";
  }
}

document.getElementById("btnCriarVenda").onclick = async () => {
  try {
    const id_cliente = Number(elCliHidden.value);
    const id_veiculo = Number(elVeiSelect.value);
    const descricao = elDesc.value || null;

    if (!id_cliente) {
      showToast("Selecione um cliente válido", "error");
      return;
    }
    if (!id_veiculo) {
      showToast("Selecione um veículo do cliente", "error");
      return;
    }

    const res = await api("/api/vendas", {
      method: "POST",
      body: { id_cliente, id_veiculo, descricao },
    });
    if (!res) return;

    showToast("Venda criada!");
    bootstrap.Modal.getInstance(
      document.getElementById("modalVendaNova")
    ).hide();
    loadVendas();
    openVendaModal(res.venda.id_venda);
  } catch {}
};

// ==================== MODAL DE EDIÇÃO DA VENDA ====================

// Abre modal e popula tudo
window.openVendaModal = async (id) => {
  currentVendaId = id;
  const data = await api(`/api/vendas/${id}`); // espera { venda: {...} }
  if (!data) return;
  const v = data.venda || data;

  // header
  if (elVendaTitulo)
    elVendaTitulo.textContent = `Venda #${v.id_venda || id}`;
  if (elVendaTotal)
    elVendaTotal.textContent = `R$ ${money(v.total)}`;

  if (elVendaStatus) {
    if (v.status === "FINALIZADA") {
      elVendaStatus.className = "status-chip chip-done";
      elVendaStatus.textContent = "FINALIZADA";
    } else if (v.status === "CANCELADA") {
      elVendaStatus.className = "status-chip chip-cancel";
      elVendaStatus.textContent = "CANCELADA";
    } else {
      elVendaStatus.className = "status-chip chip-open";
      elVendaStatus.textContent = "EM_ANDAMENTO";
    }
  }

  if (elVendaPagamentoBadge) {
    elVendaPagamentoBadge.textContent = v.pagamento || "-";
  }

  // dados da venda (descrição e forma de pagamento p/ edição simples)
  if (elVendaDescInput) {
    elVendaDescInput.value = v.descricao || "";
  }
  if (elVendaPagamentoSelect) {
    elVendaPagamentoSelect.value = v.pagamento || "NÃO_PAGO";
  }

  // 🔥 NOVO: refletir a forma de pagamento atual também no select de finalização
  const cartFormaSelect = document.getElementById("cartForma");
  if (cartFormaSelect) {
    const formaAtual =
      v.pagamento && v.pagamento !== "NÃO_PAGO" ? v.pagamento : "PIX";
    cartFormaSelect.value = formaAtual;
  }

  // zera seleção de serviço novo
  resetServicoBusca();

  // tabela de itens
  renderItensTabela(v.itens || []);

  // mostra modal
  vendaModal?.show();
};

// Render da tabela de itens já existentes
function renderItensTabela(itens) {
  if (!itensTableBody) return;
  itensTableBody.innerHTML = (itens || [])
    .map(
      (it) => `
    <tr>
      <td>${it.descricao}</td>
      <td>R$ ${money(it.preco_unit)}</td>
      <td>${it.quantidade}</td>
      <td>R$ ${money(it.desconto)}</td>
      <td>R$ ${money(it.subtotal)}</td>
      <td style="text-align:right;">
        <button class="btn btn-sm btn-outline-danger" onclick="remItem(${currentVendaId}, ${it.id_item})">
          Remover
        </button>
      </td>
    </tr>
  `
    )
    .join("");
}

// ========== salvar cabeçalho venda (descrição & forma_pagamento) ==========
btnSalvarCabecalho?.addEventListener("click", async () => {
  if (!currentVendaId) return;
  try {
    const body = {
      descricao: elVendaDescInput?.value || "",
      pagamento: elVendaPagamentoSelect?.value || undefined,
    };
    const res = await api(`/api/vendas/${currentVendaId}`, {
      method: "PUT",
      body,
    });
    if (!res) return;
    showToast("Dados atualizados!");
    await openVendaModal(res.venda?.id_venda || currentVendaId);
    loadVendas();
  } catch (e) {
    console.error(e);
    showToast("Erro ao salvar alterações", "error");
  }
});

// ========== cancelar venda ==========
btnVendaCancelar?.addEventListener("click", async () => {
  if (!currentVendaId) return;
  if (!confirm("Tem certeza que deseja cancelar esta venda?")) return;
  try {
    const res = await api(`/api/vendas/${currentVendaId}/cancelar`, {
      method: "POST",
    });
    if (!res) return;
    showToast("Venda cancelada.");
    await openVendaModal(res.venda?.id_venda || currentVendaId);
    loadVendas();
  } catch (e) {
    console.error(e);
    showToast("Erro ao cancelar venda", "error");
  }
});

// ========== baixar PDF ==========
btnVendaPDF?.addEventListener("click", async () => {
  if (!currentVendaId) {
    showToast("Nenhuma venda selecionada", "error");
    return;
  }
  try {
    const res = await fetch(`/api/vendas/${currentVendaId}/orcamento/pdf`, {
      method: "GET",
      credentials: "include",
    });
    if (res.redirected) {
      window.location.href = res.url || "/login";
      return;
    }
    if (!res.ok) {
      // tentar ler o corpo como json pra mostrar mensagem bonitinha
      let msgErro = `Erro ${res.status}`;

      try {
        const data = await res.json(); // {error, cause, ...}
        if (data?.error) {
          msgErro = data.error;
          if (data.cause) {
            msgErro += ` (${data.cause})`;
          }
        }
      } catch (e) {
        // se não é JSON (por ex. 500 HTML), fallback
        msgErro = res.statusText || msgErro;
      }

      showToast(msgErro, "error");
      return;
    }
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = `orcamento_${String(currentVendaId).padStart(4, "0")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(blobUrl);
    showToast("PDF gerado!");
  } catch (e) {
    console.error(e);
    showToast("Erro ao baixar PDF", "error");
  }
});

// ========== fechar modal ==========
btnVendaFecharX?.addEventListener("click", () => {
  vendaModal?.hide();
});
btnVendaFechar?.addEventListener("click", () => {
  vendaModal?.hide();
});

// ==================== AUTOCOMPLETE DE SERVIÇOS NO MODAL ====================

async function buscarServicosRemoto(q) {
  if (!q || q.trim().length < 2) return [];
  try {
    const resp = await api("/api/servicos", {
      params: { q: q.trim(), page: 1, per_page: 10 },
    });
    if (!resp) return [];
    const { servicos } = resp;
    return servicos || [];
  } catch {
    return [];
  }
}

function resetServicoBusca() {
  if (elServicoIdHidden) elServicoIdHidden.value = "";
  if (elServicoPrecoHidden) elServicoPrecoHidden.value = "";
  if (elServicoHintBox) elServicoHintBox.classList.add("d-none");
  if (elBuscaServico) elBuscaServico.value = "";
  if (elSugestoesServico) {
    elSugestoesServico.style.display = "none";
    elSugestoesServico.innerHTML = "";
  }
  if (elItemQtd) elItemQtd.value = 1;
  if (elItemDescReais) elItemDescReais.value = 0;
}

function renderSugestoesServicos(lista) {
  if (!elSugestoesServico) return;
  if (!lista.length) {
    elSugestoesServico.style.display = "none";
    elSugestoesServico.innerHTML = "";
    return;
  }

  elSugestoesServico.innerHTML = lista
    .map(
      (s) => `
    <button type="button"
            class="autocomplete-item"
            data-id="${s.id_servico}"
            data-nome="${s.nome}"
            data-preco="${s.valor}">
      <div class="autocomplete-item-main">
        <span>${s.nome}</span>
        <span>R$ ${money(s.valor)}</span>
      </div>
      <div class="autocomplete-item-extra">
        <span>ID #${s.id_servico}</span>
      </div>
    </button>
  `
    )
    .join("");

  elSugestoesServico.style.display = "block";

  elSugestoesServico
    .querySelectorAll(".autocomplete-item")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.id;
        const nome = btn.dataset.nome;
        const preco = btn.dataset.preco;

        if (elServicoIdHidden) elServicoIdHidden.value = id;
        if (elServicoPrecoHidden) elServicoPrecoHidden.value = preco;

        if (elServicoHintNome) elServicoHintNome.textContent = nome;
        if (elServicoHintValor) elServicoHintValor.textContent = money(preco);
        if (elServicoHintBox) elServicoHintBox.classList.remove("d-none");

        if (elBuscaServico) elBuscaServico.value = nome;
        elSugestoesServico.style.display = "none";
        elSugestoesServico.innerHTML = "";
      });
    });
}

const buscarServicosDebounced = debounce(async (texto) => {
  // quando o usuário digita de novo, limpamos a seleção anterior
  if (elServicoIdHidden) elServicoIdHidden.value = "";
  if (elServicoPrecoHidden) elServicoPrecoHidden.value = "";
  if (elServicoHintBox) elServicoHintBox.classList.add("d-none");

  const lista = await buscarServicosRemoto(texto);
  renderSugestoesServicos(lista);
}, 300);

elBuscaServico?.addEventListener("input", (e) => {
  const q = e.target.value || "";
  if (q.length < 2) {
    elSugestoesServico.style.display = "none";
    elSugestoesServico.innerHTML = "";
    return;
  }
  buscarServicosDebounced(q);
});

document.addEventListener("click", (ev) => {
  if (
    !ev.target.closest("#servicoSugestoes") &&
    !ev.target.closest("#editItemServicoBusca")
  ) {
    if (elSugestoesServico) elSugestoesServico.style.display = "none";
  }
});

// ========== adicionar item ==========
btnAddItem?.addEventListener("click", async () => {
  if (!currentVendaId) return;

  const id_servico = Number(elServicoIdHidden?.value || 0);
  const quantidade = Number(elItemQtd?.value || 1);
  const desconto = Number(elItemDescReais?.value || 0);

  if (!id_servico) {
    showToast("Selecione um serviço válido", "error");
    elBuscaServico?.focus();
    return;
  }
  if (quantidade <= 0) {
    showToast("Quantidade inválida", "error");
    return;
  }

  try {
    const res = await api(`/api/vendas/${currentVendaId}/itens`, {
      method: "POST",
      body: { id_servico, quantidade, desconto },
    });
    if (!res) return;
    showToast("Item adicionado");
    await openVendaModal(res.venda.id_venda);
    loadVendas();
  } catch (e) {
    console.error(e);
    showToast("Erro ao adicionar item", "error");
  }
});

// ========== remover item ==========
window.remItem = async (id_venda, id_item) => {
  try {
    const res = await api(`/api/vendas/${id_venda}/itens/${id_item}`, {
      method: "DELETE",
    });
    if (!res) return;
    showToast("Item removido");
    await openVendaModal(res.venda.id_venda);
    loadVendas();
  } catch (e) {}
};

// ==================== FINALIZAR VENDA ====================

const btnFinalizarEl = document.getElementById("btnFinalizar");

btnFinalizarEl?.addEventListener("click", async () => {
  if (!currentVendaId) {
    showToast("Nenhuma venda aberta.", "error");
    return;
  }

  // pega o select fresh do DOM AGORA
  const cartFormaSelect = document.getElementById("cartForma");
  const forma_pag = cartFormaSelect ? cartFormaSelect.value : "";

  if (!forma_pag) {
    showToast("Selecione a forma de pagamento.", "error");
    return;
  }

  // trava botão
  btnFinalizarEl.disabled = true;
  btnFinalizarEl.classList.add("disabled");
  btnFinalizarEl.innerHTML = `
    <i class="bi bi-hourglass-split"></i>
    <span>Finalizando...</span>
  `;

  try {
    const res = await api(`/api/vendas/${currentVendaId}/finalizar`, {
      method: "POST",
      body: {
        forma_pagamento: forma_pag, // manda forma de pagamento escolhida
      },
    });
    console.log(forma_pag);
    if (!res) return;

    showToast("Venda finalizada!");

    await openVendaModal(res.venda?.id_venda || currentVendaId);

    loadVendas();


  } catch (err) {
    console.error("Erro ao finalizar venda:", err);
    showToast(err, "error");
  } finally {
    // destrava botão
    btnFinalizarEl.disabled = false;
    btnFinalizarEl.classList.remove("disabled");
    btnFinalizarEl.innerHTML = `
      <i class="bi bi-check2-circle"></i>
      <span>Finalizar</span>
    `;
  }
});

// ==================== CAIXA ====================
async function loadCaixa() {
  if (!cxDataRef) {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0"); // meses começam em 0
    const dd = String(today.getDate()).padStart(2, "0");

    const yLocal = `${yyyy}-${mm}-${dd}`; // ex: "2025-10-27"

    document.getElementById("cxData").value = yLocal;
    cxDataRef = yLocal;
  }

  const resp = await api("/api/caixa", {
    params: { data: cxDataRef, page: cxPage, per_page: cxPer },
  });
  console.log("Caixa response:", cxDataRef, resp);
  if (!resp) return;

  const { lancamentos, pagination, total_valor, total } = resp;

  document.getElementById("cxTable").innerHTML = (lancamentos || [])
    .map(
      (l) => `
    <tr>
      <td>${l.venda_id}</td>
      <td>${l.id_lcto || ""}</td>
      <td>${l.descricao || ""}</td>
      <td>R$ ${money(l.valor)}</td>
      <td>${
        l.created_at
          ? new Date(l.created_at).toLocaleString("pt-BR")
          : ""
      }</td>
    </tr>
  `
    )
    .join("");

  document.getElementById("cxTotal").textContent = money(
    total_valor || total || 0
  );
  document.getElementById("cxPeriodoLabel").textContent = cxDataRef;

  renderPagination(
    document.getElementById("cxPag"),
    pagination.page,
    pagination.per_page,
    pagination.total,
    (p) => {
      cxPage = p;
      loadCaixa();
    }
  );
}
document.getElementById("btnCxBuscar").onclick = () => {
  cxDataRef = document.getElementById("cxData").value || null;
  cxPage = 1;
  loadCaixa();
};

// ==================== UI GLOBAL ====================
document
  .getElementById("btnToggleSidebar")
  ?.addEventListener("click", () => {
    document.querySelector(".sidebar").classList.toggle("d-none");
  });

document
  .querySelectorAll('[data-bs-toggle="tooltip"]')
  .forEach((el) => {
    new bootstrap.Tooltip(el);
  });
