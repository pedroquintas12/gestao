  import { initSidebar } from "./sidebar.js";

  // ======== Error boundary global ========
  window.addEventListener('error', (e) => {
    console.error('WindowError:', e?.error || e?.message || e);
    showToast('Ocorreu um erro inesperado.', 'error');
  });
  window.addEventListener('unhandledrejection', (e) => {
    console.error('UnhandledRejection:', e?.reason || e);
    showToast('Falha em operação assíncrona.', 'error');
  });

  document.addEventListener('DOMContentLoaded', () => {
    try {
      initSidebar?.();
    } catch (e) {
      console.error('initSidebar failed:', e);
      showToast('Falha ao inicializar a sidebar', 'error');
    }
    safeInit();
  });

  // ===== helpers =====
  const getEl = (id) => document.getElementById(id);
  const exists = (el) => !!el;

  const toastEl = getEl('toast');
  const showToast = (msg, type = 'success') => {
    if (!exists(toastEl)) {
      // fallback mínimo
      if (type === 'error') alert(msg);
      else console.log('Toast:', msg);
      return;
    }
    toastEl.textContent = (msg ?? '').toString();
    toastEl.className = 'toast show ' + (type === 'error' ? 'error' : 'success');
    setTimeout(() => toastEl.classList.remove('show'), 2200);
  };

  const money = (v) => {
    const n = Number(v);
    return Number.isFinite(n)
      ? n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : '0,00';
  };

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  function errToMsg(err) {
    if (!err) return 'Erro';
    if (typeof err === 'string') return err;
    if (err?.message) return err.message;
    try { return JSON.stringify(err); } catch { return 'Erro'; }
  }

  // fetch com timeout, parse seguro e retries opcionais
  async function api(path, { method = 'GET', body, params, timeout = 12000, retries = 0 } = {}) {
    const url = new URL(path, window.location.origin);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
      });
    }

    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(new DOMException('Timeout', 'AbortError')), timeout);

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal
      });

      const ct = res.headers.get('content-type') || '';
      let data = null;
      if (res.status === 204) {
        data = null;
      } else if (ct.includes('application/json')) {
        data = await res.json().catch(() => ({}));
      } else {
        const text = await res.text().catch(() => '');
        data = { raw: text };
      }

      if (!res.ok) {
        const msg = (data && (data.error || data.message || data.detail)) || `${res.status} ${res.statusText}`;
        showToast(msg, 'error');
        throw new Error(msg);
      }
      return data ?? {};
    } catch (e) {
      if (retries > 0) {
        console.warn('API retrying:', url.toString(), 'retries left:', retries, e);
        await sleep(400);
        return api(path, { method, body, params, timeout, retries: retries - 1 });
      }
      const msg = /AbortError/.test(String(e?.name || e)) ? 'Tempo de resposta excedido' : errToMsg(e);
      showToast(msg, 'error');
      throw e;
    } finally {
      clearTimeout(t);
    }
  }

  function badgeStatus(s) {
    if (s === 'FINALIZADA') return '<span class="badge-rounded pill-completed">FINALIZADA</span>';
    if (s === 'CANCELADA') return '<span class="badge-rounded pill-cancel">CANCELADA</span>';
    return '<span class="badge-rounded pill-processed">EM_ANDAMENTO</span>';
  }

  function formatDateTime(ts) {
    if (!ts) return '';
    try {
      const d = new Date(ts);
      if (isNaN(+d)) return '';
      return d.toLocaleString('pt-BR');
    } catch {
      return '';
    }
  }

  function safeInit() {
    // Botão da sidebar
    try {
      getEl('btnToggleSidebar')?.addEventListener('click', () => {
        document.querySelector('.sidebar')?.classList?.toggle('d-none');
      });
    } catch (e) {
      console.warn('toggle sidebar failed:', e);
    }

    // Tooltips (só se Bootstrap existir)
    try {
      if (window.bootstrap?.Tooltip) {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
      }
    } catch (e) {
      console.warn('bootstrap Tooltip init failed:', e);
    }

    // Set datas padrão
    try { setDefaultDates(); } catch (e) { console.warn('setDefaultDates failed:', e); }

    // Listeners com guards
    getEl('btnRepAplicar') && (getEl('btnRepAplicar').onclick = aplicarPeriodo);
    getEl('btnRepFiltrar') && (getEl('btnRepFiltrar').onclick = carregarRelatorio);
    getEl('btnRepCSV') && (getEl('btnRepCSV').onclick = exportCSV);

    // Carrega ao entrar
    carregarRelatorio().catch(e => console.error('carregarRelatorio onload:', e));
  }

  // ===== estado dos relatórios =====
  let repStart = null, repEnd = null;
  let repPage = 1, repPer = 12, repStatus = '', repPagamento = '';
  let chartTop = null;
  let cacheVendasExibidas = [];
  let cacheTodasVendas = []; // todas do período

  // datas padrão: últimos 30 dias
  function setDefaultDates() {
    const startEl = getEl('repStart');
    const endEl = getEl('repEnd');
    if (!exists(startEl) || !exists(endEl)) return;

    const end = new Date();
    const start = new Date(); start.setDate(end.getDate() - 30);

    // toISO (YYYY-MM-DD) no fuso local
    const toISOdate = (d) => {
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const da = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${da}`;
    };

    startEl.value = toISOdate(start);
    endEl.value = toISOdate(end);
    repStart = startEl.value;
    repEnd = endEl.value;
  }

  // atalhos de período
  document.querySelectorAll('[data-range]').forEach(btn => {
    btn.addEventListener('click', () => {
      try {
        const kind = btn.getAttribute('data-range');
        const now = new Date();
        const toISOdate = (d) => {
          const y = d.getFullYear();
          const m = String(d.getMonth() + 1).padStart(2, '0');
          const da = String(d.getDate()).padStart(2, '0');
          return `${y}-${m}-${da}`;
        };
        if (kind === 'today') {
          getEl('repStart').value = toISOdate(now);
          getEl('repEnd').value = toISOdate(now);
        } else if (kind === '7' || kind === '30') {
          const start = new Date(); start.setDate(now.getDate() - Number(kind));
          getEl('repStart').value = toISOdate(start);
          getEl('repEnd').value = toISOdate(now);
        } else if (kind === 'month') {
          const first = new Date(now.getFullYear(), now.getMonth(), 1);
          const last = new Date(now.getFullYear(), now.getMonth() + 1, 0);
          getEl('repStart').value = toISOdate(first);
          getEl('repEnd').value = toISOdate(last);
        }
        aplicarPeriodo();
      } catch (e) {
        console.error('data-range click failed:', e);
        showToast('Falha ao aplicar período', 'error');
      }
    });
  });

  function aplicarPeriodo() {
    try {
      repStart = getEl('repStart')?.value || null;
      repEnd = getEl('repEnd')?.value || null;
      // validação simples de formato YYYY-MM-DD
      const re = /^\d{4}-\d{2}-\d{2}$/;
      if (repStart && !re.test(repStart)) throw new Error('Data inicial inválida');
      if (repEnd && !re.test(repEnd)) throw new Error('Data final inválida');
      repPage = 1;
      carregarRelatorio();
    } catch (e) {
      console.error('aplicarPeriodo:', e);
      showToast(errToMsg(e), 'error');
    }
  }

  // ========= Núcleo sem endpoints extras =========
  // 1) Pagina /api/vendas até trazer tudo do período
  async function fetchTodasVendasPeriodo({ start, end, status, pagamento }) {
    let page = 1, per = 100;
    let total = 0, acumulado = [];
    let loopGuard = 0, MAX_LOOPS = 200; // proteção contra paginação quebrada

    while (true) {
      if (loopGuard++ > MAX_LOOPS) {
        console.warn('Loop pagination guard reached');
        break;
      }

      if (!status){
        status = "FINALIZADA";
      }

      const payload = await api('/api/vendas', {
        params: { page, per_page: per, start_date: start, end_date: end, status, pagamento},
        retries: 1
      }).catch(e => {
        console.error('fetchTodasVendasPeriodo page failed:', e);
        return null;
      });

      if (!payload) break;

      const vendas = Array.isArray(payload.vendas) ? payload.vendas : [];
      const pagination = payload.pagination || {};
      acumulado = acumulado.concat(vendas);

      total = Number.isFinite(pagination.total) ? pagination.total : acumulado.length;
      const totalPages = Math.max(1, Math.ceil(total / per));

      if (page >= totalPages || vendas.length === 0) break;
      page++;
    }
    return acumulado;
  }

  // 2) Busca itens de cada venda em lotes (para Top Serviços) — com retry leve
  async function fetchItensDasVendas(ids, batchSize = 6) {
    const itensPorVenda = new Map();
    if (!Array.isArray(ids) || ids.length === 0) return itensPorVenda;

    for (let i = 0; i < ids.length; i += batchSize) {
      const slice = ids.slice(i, i + batchSize);
      const reqs = slice.map(id => api(`/api/vendas/${id}`, { retries: 1 }).catch(e => e));
      const resps = await Promise.allSettled(reqs);

      resps.forEach((r, idx) => {
        const id = slice[idx];
        if (r.status === 'fulfilled' && r.value && !(r.value instanceof Error)) {
          // tenta v.venda.itens -> v.itens -> []
          const v = r.value;
          const itens = v?.venda?.itens || v?.itens || [];
          itensPorVenda.set(id, Array.isArray(itens) ? itens : []);
        } else {
          console.warn('fetchItens falhou para id', id, r);
          itensPorVenda.set(id, []);
        }
      });
    }
    return itensPorVenda;
  }

  // 3) Monta Top Serviços a partir dos itens
  function agregarTopServicos(itensPorVenda) {
    const mapa = new Map(); // chave: nome/descricao || id_servico
    try {
      itensPorVenda.forEach((itens) => {
        (itens || []).forEach(it => {
          const key = it.id_servico ?? it.descricao ?? '—';
          const nome = it.descricao ?? `Serviço #${it.id_servico ?? '-'}`;
          const qtd = Number(it.quantidade || 1);
          const preco = Number(it.preco_unit || 0);
          const desc = Number(it.desconto || 0);
          const subtotal = Number.isFinite(Number(it.subtotal)) ? Number(it.subtotal) : (preco * qtd - desc);
          if (!mapa.has(key)) {
            mapa.set(key, { nome, quantidade: 0, total: 0 });
          }
          const acc = mapa.get(key);
          acc.quantidade += (Number.isFinite(qtd) ? qtd : 0);
          acc.total += (Number.isFinite(subtotal) ? subtotal : 0);
        });
      });
    } catch (e) {
      console.error('agregarTopServicos:', e);
      showToast('Falha ao agregar serviços', 'error');
    }
    return Array.from(mapa.values()).sort((a, b) => b.quantidade - a.quantidade);
  }

  // 4) Render Top Serviços (tabela + gráfico)
  function renderTopServicos(rows) {
    try {
      const info = getEl('topServInfo');
      if (info) info.textContent = rows.length ? `Top ${Math.min(rows.length, 10)} no período` : 'Sem dados no período';

      const top10 = rows.slice(0, 10);
      const tbody = getEl('tblTopServicos');
      if (tbody) {
        tbody.innerHTML = top10.map(r => `
          <tr>
            <td>${r.nome}</td>
            <td class="text-end">${r.quantidade}</td>
            <td class="text-end">${money(r.total)}</td>
          </tr>
        `).join('');
      }

      const ctx = getEl('chartTopServicos');
      if (!ctx || !window.Chart) {
        if (!window.Chart) console.warn('Chart.js não carregado');
        return;
      }

      const labels = top10.map(r => r.nome);
      const dataQtd = top10.map(r => r.quantidade);
      if (chartTop) { try { chartTop.destroy(); } catch {} }

      chartTop = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Quantidade vendida', data: dataQtd }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: { ticks: { autoSkip: true, maxRotation: 0 } }, y: { beginAtZero: true, ticks: { precision: 0 } } }
        }
      });
    } catch (e) {
      console.error('renderTopServicos:', e);
      showToast('Falha ao renderizar Top Serviços', 'error');
    }
  }

  // 5) Render histórico com paginação client-side
  function getCreatedAtSafe(v) {
    // tenta created_at, cai para create_at (typo)
    return v.created_at ?? v.create_at ?? v.createdAt ?? null;
  }

  function renderHistorico(page = 1) {
    try {
      const per = repPer;
      const startIdx = (page - 1) * per;
      const pageRows = cacheTodasVendas.slice(startIdx, startIdx + per);
      cacheVendasExibidas = pageRows;

      const tbody = getEl('tblRepVendas');
      if (tbody) {
        tbody.innerHTML = pageRows.map(v => `
          <tr>
            <td>${v.id_venda ?? '-'}</td>
            <td>${(v.descricao ?? '-')}</td>
            <td>${(v.cliente?.nome ?? v.id_cliente ?? '-')}</td>
            <td>${(v.veiculo?.placa ?? v.id_veiculo ?? '-')}</td>
            <td class="text-end">R$ ${money(v.total)}</td>
            <td>${badgeStatus(v.status)}</td>
            <td><span class="badge-rounded pill-pay">${v.pagamento ?? '-'}</span></td>
            <td>${formatDateTime(getCreatedAtSafe(v))}</td>
          </tr>
        `).join('');
      }

      // paginação
      const total = cacheTodasVendas.length;
      const total_pages = Math.max(1, Math.ceil(total / per));
      const container = getEl('repPaginate');
      if (!container) return;
      container.innerHTML = '';
      const add = (p, label, disabled = false, active = false) => {
        const li = document.createElement('li');
        li.className = 'page-item ' + (disabled ? 'disabled ' : '') + (active ? 'active ' : '');
        const a = document.createElement('a');
        a.className = 'page-link'; a.href = '#'; a.textContent = label;
        a.onclick = (e) => { e.preventDefault(); if (!disabled && !active) { repPage = p; renderHistorico(repPage); } };
        li.appendChild(a); container.appendChild(li);
      };
      add(page - 1, '«', page <= 1);
      for (let i = 1; i <= total_pages; i++) {
        if (i === 1 || i === total_pages || Math.abs(i - page) <= 2) { add(i, String(i), false, i === page); }
        else if (Math.abs(i - page) === 3) { const li = document.createElement('li'); li.className = 'page-item disabled'; li.innerHTML = '<span class="page-link">…</span>'; container.appendChild(li); }
      }
      add(page + 1, '»', page >= total_pages);
    } catch (e) {
      console.error('renderHistorico:', e);
      showToast('Falha ao renderizar histórico', 'error');
    }
  }

  // 6) Carregamento geral do relatório
  async function carregarRelatorio() {
    try {
      repStatus = getEl('repStatus')?.value || '';
      repPagamento = getEl('repPag')?.value || '';

      // a) traz TODAS as vendas do período (com filtros)
      const vendas = await fetchTodasVendasPeriodo({
        start: repStart, end: repEnd, status: repStatus, pagamento: repPagamento
      });
      cacheTodasVendas = Array.isArray(vendas) ? vendas : [];

      // KPIs (com guardas)
      const totalVendas = cacheTodasVendas.length;
      const faturamento = cacheTodasVendas.reduce((s, v) => s + (Number.isFinite(Number(v.total)) ? Number(v.total) : 0), 0);
      const ticketMedio = totalVendas ? (faturamento / totalVendas) : 0;

      if (getEl('kpiRepVendas')) getEl('kpiRepVendas').textContent = String(totalVendas);
      if (getEl('kpiRepFaturamento')) getEl('kpiRepFaturamento').textContent = 'R$ ' + money(faturamento);
      if (getEl('kpiRepTicket')) getEl('kpiRepTicket').textContent = 'R$ ' + money(ticketMedio);

      // b) busca itens de cada venda (para Top Serviços)
      const ids = cacheTodasVendas.map(v => v.id_venda).filter(Boolean);
      const itensMap = await fetchItensDasVendas(ids).catch(e => {
        console.error('fetchItensDasVendas:', e);
        return new Map();
      });
      const top = agregarTopServicos(itensMap);
      renderTopServicos(top);

      // c) histórico paginado client-side
      repPage = 1;
      renderHistorico(repPage);
    } catch (e) {
      console.error('carregarRelatorio:', e);
      showToast('Não foi possível carregar o relatório', 'error');
      // fallback de KPIs
      if (getEl('kpiRepVendas')) getEl('kpiRepVendas').textContent = '0';
      if (getEl('kpiRepFaturamento')) getEl('kpiRepFaturamento').textContent = 'R$ 0,00';
      if (getEl('kpiRepTicket')) getEl('kpiRepTicket').textContent = 'R$ 0,00';
    }
  }

  // export CSV (linhas exibidas)
  function exportCSV() {
    try {
      if (!cacheVendasExibidas.length) { showToast('Nada para exportar', 'error'); return; }
      const headers = ['id_venda', 'descricao', 'cliente', 'veiculo', 'total', 'status', 'pagamento', 'created_at'];
      const rows = cacheVendasExibidas.map(v => [
        v.id_venda ?? '',
        (v.descricao ?? '').toString().replace(/"/g, '""'),
        (v.cliente?.nome ?? v.id_cliente ?? '').toString().replace(/"/g, '""'),
        (v.veiculo?.placa ?? v.id_veiculo ?? '').toString().replace(/"/g, '""'),
        Number(v.total || 0).toFixed(2),
        v.status ?? '',
        v.pagamento ?? '',
        getCreatedAtSafe(v) ?? ''
      ]);
      const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n');
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `vendas_${repStart || 'ini'}_${repEnd || 'fim'}.csv`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('exportCSV:', e);
      showToast('Falha ao exportar CSV', 'error');
    }
  }