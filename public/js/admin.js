   import { initSidebar } from "./sidebar.js";
   

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();

});
   // ===== helpers =====
    const toastEl = document.getElementById('toast');
    const showToast = (msg, type='success')=>{
      toastEl.textContent = msg;
      toastEl.className = 'toast show ' + (type==='error'?'error':'success');
      setTimeout(()=>toastEl.classList.remove('show'), 2200);
    };
    const money = (v)=> (Number(v||0)).toLocaleString('pt-BR',{minimumFractionDigits:2, maximumFractionDigits:2});
    async function api(path, {method='GET', body, params} = {}){
      const url = new URL(path, window.location.origin);
      if(params) Object.entries(params).forEach(([k,v])=>{ if(v!==undefined && v!==null && v!=='') url.searchParams.set(k,v) });
      const res = await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: body ? JSON.stringify(body) : undefined });
      const data = await res.json().catch(()=> ({}));
      if(!res.ok){ const msg = data?.error || 'Erro'; showToast(msg,'error'); throw new Error(msg); }
      return data;
    }
    function badgeStatus(s){
      if(s==='FINALIZADA') return '<span class="badge-rounded pill-completed">FINALIZADA</span>';
      if(s==='CANCELADA')  return '<span class="badge-rounded pill-cancel">CANCELADA</span>';
      return '<span class="badge-rounded pill-processed">EM_ANDAMENTO</span>';
    }
    function formatDateTime(ts){
      if(!ts) return '';
      try{ return new Date(ts).toLocaleString('pt-BR'); }catch{ return ''; }
    }
    document.getElementById('btnToggleSidebar')?.addEventListener('click', ()=>{
      document.querySelector('.sidebar').classList.toggle('d-none');
    });
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el=> new bootstrap.Tooltip(el));

    // ===== estado dos relatórios =====
    let repStart = null, repEnd = null;
    let repPage = 1, repPer = 12, repStatus = '', repPagamento = '';
    let chartTop = null;
    let cacheVendasExibidas = [];

    // datas padrão: últimos 30 dias
    function setDefaultDates(){
      const end = new Date();
      const start = new Date(); start.setDate(end.getDate()-30);
      const toISO = d => d.toISOString().slice(0,10);
      document.getElementById('repStart').value = toISO(start);
      document.getElementById('repEnd').value   = toISO(end);
      repStart = toISO(start); repEnd = toISO(end);
    }
    setDefaultDates();

    // atalhos de período
    document.querySelectorAll('[data-range]').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const kind = btn.getAttribute('data-range');
        const now = new Date(); const toISO = d => d.toISOString().slice(0,10);
        if(kind==='today'){
          document.getElementById('repStart').value = toISO(now);
          document.getElementById('repEnd').value   = toISO(now);
        }else if(kind==='7' || kind==='30'){
          const start = new Date(); start.setDate(now.getDate()-Number(kind));
          document.getElementById('repStart').value = toISO(start);
          document.getElementById('repEnd').value   = toISO(now);
        }else if(kind==='month'){
          const first = new Date(now.getFullYear(), now.getMonth(), 1);
          const last  = new Date(now.getFullYear(), now.getMonth()+1, 0);
          document.getElementById('repStart').value = toISO(first);
          document.getElementById('repEnd').value   = toISO(last);
        }
        aplicarPeriodo();
      });
    });

    document.getElementById('btnRepAplicar').onclick = aplicarPeriodo;
    function aplicarPeriodo(){
      repStart = document.getElementById('repStart').value || null;
      repEnd   = document.getElementById('repEnd').value   || null;
      repPage  = 1;
      carregarRelatorio();
    }

    // ========= Núcleo sem endpoints extras =========
    // 1) Pagina /api/vendas até trazer tudo do período
    async function fetchTodasVendasPeriodo({start, end, status, pagamento}){
      let page = 1, per = 100;
      let total = 0, acumulado = [];
      while(true){
        const {vendas = [], pagination = {}} = await api('/api/vendas', {
          params: { page, per_page: per, start_date: start, end_date: end, status, pagamento }
        });
        acumulado = acumulado.concat(vendas);
        total = pagination.total ?? acumulado.length;
        const totalPages = Math.max(1, Math.ceil(total / per));
        if(page >= totalPages || vendas.length === 0) break;
        page++;
      }
      return acumulado;
    }

    // 2) Busca itens de cada venda em lotes (para Top Serviços)
    async function fetchItensDasVendas(ids, batchSize = 6){
      const itensPorVenda = new Map();
      for(let i = 0; i < ids.length; i += batchSize){
        const slice = ids.slice(i, i+batchSize);
        const reqs = slice.map(id => api(`/api/vendas/${id}`));
        const resps = await Promise.allSettled(reqs);
        resps.forEach((r, idx)=>{
          const id = slice[idx];
          if(r.status === 'fulfilled'){
            const itens = r.value?.venda?.itens || [];
            itensPorVenda.set(id, itens);
          }else{
            itensPorVenda.set(id, []);
          }
        });
      }
      return itensPorVenda;
    }

    // 3) Monta Top Serviços a partir dos itens
    function agregarTopServicos(itensPorVenda){
      const mapa = new Map(); // chave: nome/descricao || id_servico
      itensPorVenda.forEach((itens)=>{
        (itens||[]).forEach(it=>{
          const key = it.id_servico ?? it.descricao ?? '—';
          const nome = it.descricao ?? `Serviço #${it.id_servico ?? '-'}`;
          const qtd = Number(it.quantidade || 1);
          const total = Number(it.subtotal ?? (Number(it.preco_unit||0) * qtd - Number(it.desconto||0)));
          if(!mapa.has(key)){
            mapa.set(key, { nome, quantidade: 0, total: 0 });
          }
          const acc = mapa.get(key);
          acc.quantidade += qtd;
          acc.total += total;
        });
      });
      return Array.from(mapa.values()).sort((a,b)=> b.quantidade - a.quantidade);
    }

    // 4) Render Top Serviços (tabela + gráfico)
    function renderTopServicos(rows){
      const info = document.getElementById('topServInfo');
      info.textContent = rows.length ? `Top ${Math.min(rows.length, 10)} no período` : 'Sem dados no período';
      const top10 = rows.slice(0,10);

      const tbody = document.getElementById('tblTopServicos');
      tbody.innerHTML = top10.map(r=>`
        <tr>
          <td>${r.nome}</td>
          <td class="text-end">${r.quantidade}</td>
          <td class="text-end">${money(r.total)}</td>
        </tr>
      `).join('');

      const labels = top10.map(r => r.nome);
      const dataQtd = top10.map(r => r.quantidade);

      const ctx = document.getElementById('chartTopServicos');
      if(chartTop){ chartTop.destroy(); }
      chartTop = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Quantidade vendida', data: dataQtd }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: { ticks: { autoSkip:true, maxRotation:0 } }, y: { beginAtZero:true, ticks:{ precision:0 } } }
        }
      });
    }

    // 5) Render histórico com paginação client-side (sobre a lista total carregada)
    let cacheTodasVendas = []; // todas do período (para paginar e exportar)
    function renderHistorico(page = 1){
      const per = repPer;
      const startIdx = (page-1)*per;
      const pageRows = cacheTodasVendas.slice(startIdx, startIdx+per);
      cacheVendasExibidas = pageRows;

      const tbody = document.getElementById('tblRepVendas');
      tbody.innerHTML = pageRows.map(v=>`
        <tr>
          <td>${v.id_venda}</td>
          <td>${v.descricao ?? '-'}</td>
          <td>${v.cliente?.nome ?? v.id_cliente ?? '-'}</td>
          <td>${v.veiculo?.placa ?? v.id_veiculo ?? '-'}</td>
          <td class="text-end">R$ ${money(v.total)}</td>
          <td>${badgeStatus(v.status)}</td>
          <td><span class="badge-rounded pill-pay">${v.pagamento}</span></td>
          <td>${formatDateTime(v.created_at)}</td>
        </tr>
      `).join('');

      // paginação
      const total = cacheTodasVendas.length;
      const total_pages = Math.max(1, Math.ceil(total / per));
      const container = document.getElementById('repPaginate');
      container.innerHTML = '';
      const add = (p, label, disabled=false, active=false)=>{
        const li = document.createElement('li');
        li.className = 'page-item ' + (disabled?'disabled ':'') + (active?'active ':'');
        const a = document.createElement('a');
        a.className = 'page-link'; a.href = '#'; a.textContent = label;
        a.onclick = (e)=>{e.preventDefault(); if(!disabled && !active){ repPage=p; renderHistorico(repPage); }};
        li.appendChild(a); container.appendChild(li);
      };
      add(page-1,'«', page<=1);
      for(let i=1;i<=total_pages;i++){
        if(i===1 || i===total_pages || Math.abs(i-page)<=2){ add(i,String(i),false,i===page); }
        else if(Math.abs(i-page)===3){ const li=document.createElement('li'); li.className='page-item disabled'; li.innerHTML='<span class="page-link">…</span>'; container.appendChild(li); }
      }
      add(page+1,'»', page>=total_pages);
    }

    // 6) Carregamento geral do relatório
    async function carregarRelatorio(){
      try{
        repStatus    = document.getElementById('repStatus').value || '';
        repPagamento = document.getElementById('repPag').value || '';

        // a) traz TODAS as vendas do período (com filtros)
        const vendas = await fetchTodasVendasPeriodo({
          start: repStart, end: repEnd, status: repStatus, pagamento: repPagamento
        });
        cacheTodasVendas = vendas;

        // KPIs
        const totalVendas = vendas.length;
        const faturamento = vendas.reduce((s,v)=> s + Number(v.total||0), 0);
        const ticketMedio = totalVendas ? (faturamento / totalVendas) : 0;
        document.getElementById('kpiRepVendas').textContent = String(totalVendas);
        document.getElementById('kpiRepFaturamento').textContent = 'R$ ' + money(faturamento);
        document.getElementById('kpiRepTicket').textContent = 'R$ ' + money(ticketMedio);

        // b) busca itens de cada venda (para Top Serviços)
        const ids = vendas.map(v => v.id_venda).filter(Boolean);
        const itensMap = await fetchItensDasVendas(ids);  // lotes para evitar travar
        const top = agregarTopServicos(itensMap);
        renderTopServicos(top);

        // c) histórico paginado client-side
        repPage = 1;
        renderHistorico(repPage);
      }catch(e){
        console.error(e);
        showToast('Não foi possível carregar o relatório','error');
      }
    }

    // filtros do histórico (força recarregar tudo — mantém consistência com Top Serviços)
    document.getElementById('btnRepFiltrar').onclick = carregarRelatorio;

    // export CSV (linhas exibidas)
    document.getElementById('btnRepCSV').onclick = ()=>{
      if(!cacheVendasExibidas.length){ showToast('Nada para exportar','error'); return; }
      const headers = ['id_venda','descricao','cliente','veiculo','total','status','pagamento','created_at'];
      const rows = cacheVendasExibidas.map(v=>[
        v.id_venda,
        (v.descricao ?? '').toString().replace(/"/g,'""'),
        (v.cliente?.nome ?? v.id_cliente ?? '').toString().replace(/"/g,'""'),
        (v.veiculo?.placa ?? v.id_veiculo ?? '').toString().replace(/"/g,'""'),
        Number(v.total||0).toFixed(2),
        v.status ?? '',
        v.pagamento ?? '',
        v.created_at ?? ''
      ]);
      const csv = [headers.join(','), ...rows.map(r=>r.map(c=>`"${c}"`).join(','))].join('\n');
      const blob = new Blob([csv],{type:'text/csv;charset=utf-8;'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `vendas_${repStart||'ini'}_${repEnd||'fim'}.csv`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    };

    // carregar ao entrar
    carregarRelatorio();
