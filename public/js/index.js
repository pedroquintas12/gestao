    import { initSidebar } from "./sidebar.js";

    document.addEventListener('DOMContentLoaded', () => {
  initSidebar();

});
    let cliPage=1, cliPer=24, cliQ='';
    let veiPage=1, veiPer=24, veiQ='', veiCli=null;
    let svcPage=1, svcPer=24, svcQ='';
    let venPage=1, venPer=10, venQ='', venStatus='', venPag='';
    let cxPage=1, cxPer=24, cxDataRef=null;
    let currentVendaId = null;

    // ===== helpers =====
    const toastEl = document.getElementById('toast');
    function showToast(msg, type='success'){
      toastEl.textContent = msg;
      toastEl.className = 'toast show ' + (type==='error'?'error':'success');
      setTimeout(()=>toastEl.classList.remove('show'), 2400);
    }
    const money = (v)=> (Number(v||0)).toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});

    async function api(path, {method='GET', body, params} = {}){
      const url = new URL(path, window.location.origin);
      if(params) Object.entries(params).forEach(([k,v])=>{
        if(v!==undefined && v!==null && v!=='') url.searchParams.set(k,v)
      });
      const res = await fetch(url, {
        method,
        headers: {'Content-Type':'application/json'},
        body: body ? JSON.stringify(body) : undefined
      });
      const data = await res.json().catch(()=> ({}));
      if(!res.ok){
        const msg = data?.error || 'Erro';
        showToast(msg, 'error');
        throw new Error(msg);
      }
      return data;
    }

    function renderPagination(container, page, per_page, total, onPage){
      const total_pages = Math.max(1, Math.ceil(total / per_page));
      container.innerHTML = '';
      const ul = container;
      const add = (p, label, disabled=false, active=false)=>{
        const li = document.createElement('li');
        li.className = 'page-item ' + (disabled?'disabled ':'') + (active?'active ':'');
        const a = document.createElement('a');
        a.className = 'page-link';
        a.href = '#';
        a.textContent = label;
        a.onclick = (e)=>{e.preventDefault(); if(!disabled && !active) onPage(p)};
        li.appendChild(a);
        ul.appendChild(li);
      };
      add(page-1,'«', page<=1);
      for(let i=1; i<=total_pages; i++){
        if(i===1 || i===total_pages || Math.abs(i-page)<=2){
          add(i, String(i), false, i===page);
        }else if(Math.abs(i-page)===3){
          const li = document.createElement('li');
          li.className = 'page-item disabled';
          li.innerHTML = '<span class="page-link">…</span>';
          ul.appendChild(li);
        }
      }
      add(page+1,'»', page>=total_pages);
    }

    // ===== roteador simples =====
    const sections = {
      dashboard: document.getElementById('page-dashboard'),
      clientes:  document.getElementById('page-clientes'),
      veiculos:  document.getElementById('page-veiculos'),
      servicos:  document.getElementById('page-servicos'),
      vendas:    document.getElementById('page-vendas'),
      caixa:     document.getElementById('page-caixa'),
    };
    function showPage(hash){
      const key = (hash||'#dashboard').replace('#','');
      Object.values(sections).forEach(s=>s.classList.add('d-none'));
      (sections[key]||sections.dashboard).classList.remove('d-none');
      document.querySelectorAll('#menu .nav-link').forEach(a=>{
        a.classList.toggle('active', a.getAttribute('href') === '#'+key);
      });
      if(key==='dashboard') loadDashboard();
      if(key==='clientes')  loadClientes();
      if(key==='veiculos')  loadVeiculos();
      if(key==='servicos')  loadServicos();
      if(key==='vendas')    { loadServicosCombo(); loadVendas(); }
      if(key==='caixa')     loadCaixa();
    }
    window.addEventListener('hashchange', ()=>showPage(location.hash));
    showPage(location.hash);

    // ===== Dashboard =====
    async function loadDashboard(){
      const today = new Date().toISOString().slice(0,10);
      console.log(today)
      try{
        const cx = await api('/api/caixa', {params:{data: today}});
        document.getElementById('kpiCaixaHoje').textContent = 'R$ '+money(cx.total_valor||cx.total||0);

        const ven = await api('/api/vendas', {params:{page:1, per_page:1, status:'FINALIZADA',start_date: today}});
        document.getElementById('kpiVendasHoje').textContent = String(ven.pagination?.total || 0);

        const sv = await api('/api/servicos', {params:{page:1, per_page:1}});
        document.getElementById('kpiServicos').textContent = String(sv.pagination?.total || 0);
      }catch{}
    }

    // ===== Clientes =====
    async function loadClientes(){
      const {clientes, pagination} = await api('/api/clientes', {params:{q: cliQ, page: cliPage, per_page: cliPer}});
      const tbody = document.getElementById('cliTable');
      tbody.innerHTML = (clientes||[]).map(c=>`
        <tr>
          <td>${c.id_cliente}</td>
          <td>${c.nome||''}</td>
          <td>${c.numero||''}</td>
          <td class="actions-col">
            <button class="btn btn-sm btn-outline-secondary" onclick="openEditCliente(${c.id_cliente})">
              <i class="bi bi-pencil"></i> Editar
            </button>
          </td>
        </tr>
      `).join('');
      renderPagination(document.getElementById('cliPag'), pagination.page, pagination.per_page, pagination.total, (p)=>{cliPage=p; loadClientes();});
    }
    document.getElementById('btnCliBusca').onclick = ()=>{ cliQ = document.getElementById('cliSearch').value||''; cliPage=1; loadClientes(); };
    document.getElementById('btnSalvarCliente').onclick = async ()=>{
      try{
        const payload = { nome: cliNome.value, cpf: cliCPF.value, numero: cliTel.value };
        await api('/api/clientes', {method:'POST', body: payload});
        showToast('Cliente salvo!');
        bootstrap.Modal.getInstance(document.getElementById('modalCliente')).hide();
        loadClientes();
      }catch{}
    };

    // ===== Veículos (lista) =====
    async function loadVeiculos(){
      const params = {q: veiQ, page: veiPage, per_page: veiPer};
      if(veiCli) params.id_cliente = veiCli;
      const {veiculos, pagination} = await api('/api/veiculos', {params});
      const tbody = document.getElementById('veiTable');
      tbody.innerHTML = (veiculos||[]).map(v=>`
        <tr>
          <td>${v.id_veiculo}</td>
          <td>${v.placa}</td>
          <td>${v.id_cliente}</td>
          <td>${v.marca||''}</td>
          <td>${v.modelo||''}</td>
          <td>${v.km||''}</td>
          <td class="actions-col">
            <button class="btn btn-sm btn-outline-secondary" onclick="openEditVeiculo(${v.id_veiculo})">
              <i class="bi bi-pencil"></i> Editar
            </button>
          </td>
        </tr>
      `).join('');
      renderPagination(document.getElementById('veiPag'), pagination.page, pagination.per_page, pagination.total, (p)=>{veiPage=p; loadVeiculos();});
    }
    document.getElementById('btnVeiBusca').onclick = ()=>{
      veiQ   = document.getElementById('veiSearch').value||'';
      veiCli = document.getElementById('veiCliId').value||null;
      veiPage=1; loadVeiculos();
    };

    // ===== Veículo (modal) — busca de cliente por nome (novo veículo) =====
    let veiCliBuscaTimer = null;

    async function buscarClientesPorNome(term){
      if(!term || term.trim().length < 2) return [];
      try{
        const {clientes} = await api('/api/clientes', {params:{q: term.trim(), page:1, per_page:10}});
        return clientes||[];
      }catch{return []}
    }

    function renderSugestoesClientes(list){
      const box = document.getElementById('veiCliSug');
      if(!box) return;
      if(!list.length){
        box.style.display='none'; box.innerHTML=''; return;
      }
      box.innerHTML = list.map(c=>`
        <button type="button" class="list-group-item list-group-item-action"
                data-id="${c.id_cliente}" data-nome="${c.nome||''}">
          <div class="d-flex justify-content-between">
            <strong>${c.nome||'-'}</strong><span class="text-muted">#${c.id_cliente}</span>
          </div>
          ${c.numero ? `<small class="text-muted">• ${c.numero}</small>` : ''}
        </button>
      `).join('');
      box.style.display='block';

      box.querySelectorAll('.list-group-item').forEach(btn=>{
        btn.addEventListener('click', ()=>{
          document.getElementById('veiCliIdHidden').value = btn.dataset.id;
          document.getElementById('veiCliNome').value     = btn.dataset.nome;
          box.style.display='none';
          box.innerHTML='';
        });
      });
    }

    const veiCliNomeEl = document.getElementById('veiCliNome');
    const veiCliSugEl  = document.getElementById('veiCliSug');

    veiCliNomeEl?.addEventListener('input', ()=>{
      document.getElementById('veiCliIdHidden').value = '';
      clearTimeout(veiCliBuscaTimer);
      veiCliBuscaTimer = setTimeout(async ()=>{
        const lista = await buscarClientesPorNome(veiCliNomeEl.value);
        renderSugestoesClientes(lista);
      }, 250);
    });

    document.addEventListener('click', (e)=>{
      if(!veiCliSugEl) return;
      const dentro = e.target.closest('#veiCliSug') || e.target.closest('#veiCliNome');
      if(!dentro){ veiCliSugEl.style.display='none'; }
    });

    // Salvar veículo (novo)
    document.getElementById('btnSalvarVeiculo').onclick = async ()=>{
      try{
        const id_cliente = Number(document.getElementById('veiCliIdHidden').value || 0);
        const placa = (document.getElementById('veiPlaca').value || '').trim().toUpperCase();
        const km = Number(document.getElementById('veiKM').value || 0);
        const observacao = (document.getElementById('veiObs').value || '').trim();
        const marca = (document.getElementById('veiMarca').value || '').trim();
        const modelo = (document.getElementById('veiModel').value || '').trim();
        const cor = (document.getElementById('veiCor').value || '').trim();

        if(!id_cliente){ showToast('Selecione um cliente da lista.', 'error'); return; }
        if(!placa){ showToast('Informe a placa.', 'error'); return; }

        const payload = { id_cliente, placa, km, observacao,marca,modelo,cor };
        console.log(payload);
        await api('/api/veiculos', { method:'POST', body: payload });
        showToast('Veículo salvo!');
        bootstrap.Modal.getInstance(document.getElementById('modalVeiculo')).hide();

        document.getElementById('veiCliNome').value = '';
        document.getElementById('veiCliIdHidden').value = '';
        document.getElementById('veiPlaca').value = '';
        document.getElementById('veiKM').value = '';
        document.getElementById('veiCor').value = '';
        document.getElementById('veiModel').value = '';
        document.getElementById('veiMarca').value = '';
        document.getElementById('veiObs').value = '';

        loadVeiculos();
      }catch(e){
        console.error('Erro ao salvar veículo:', e);
        showToast('Erro ao salvar veículo','error');
      }
    };

    // ===== Serviços =====
    async function loadServicos(){
      const {servicos, pagination} = await api('/api/servicos', {params:{q: svcQ, page: svcPage, per_page: svcPer}});
      const tbody = document.getElementById('svcTable');
      tbody.innerHTML = (servicos||[]).map(s=>`
        <tr>
          <td>${s.id_servico}</td>
          <td>${s.nome}</td>
          <td>${money(s.valor)}</td>
          <td class="actions-col">
            <button class="btn btn-sm btn-outline-secondary" onclick="openEditServico(${s.id_servico})">
              <i class="bi bi-pencil"></i> Editar
            </button>
          </td>
        </tr>
      `).join('');
      renderPagination(document.getElementById('svcPag'), pagination.page, pagination.per_page, pagination.total, (p)=>{svcPage=p; loadServicos();});
    }
    document.getElementById('btnSvcBusca').onclick = ()=>{ svcQ = document.getElementById('svcSearch').value||''; svcPage=1; loadServicos(); };
    document.getElementById('btnSalvarServico').onclick = async ()=>{
      try{
        const payload = { nome: svcNome.value, valor: Number(svcValor.value||0) };
        await api('/api/servicos', {method:'POST', body: payload});
        showToast('Serviço salvo!');
        bootstrap.Modal.getInstance(document.getElementById('modalServico')).hide();
        loadServicos(); loadServicosCombo();
      }catch{}
    };
    async function loadServicosCombo(){
      try{
        const {servicos} = await api('/api/servicos', {params:{page:1, per_page:200}});
        const sel = document.getElementById('cartServico');
        sel.innerHTML = (servicos||[]).map(s=>`<option value="${s.id_servico}" data-preco="${s.valor}">${s.nome} — R$ ${money(s.valor)}</option>`).join('');
      }catch{}
    }

    // ===== Vendas / Orçamentos =====
    function statusPill(s){
      if(s==='FINALIZADA') return '<span class="badge-rounded pill-completed">FINALIZADA</span>';
      if(s==='CANCELADA')  return '<span class="badge-rounded pill-cancel">CANCELADA</span>';
      return '<span class="badge-rounded pill-processed">EM_ANDAMENTO</span>';
    }
    async function loadVendas(){
      const params = {q: venQ, status: venStatus, pagamento: venPag, page: venPage, per_page: venPer};
      const {vendas, pagination} = await api('/api/vendas', {params});
      const tbody = document.getElementById('venTable');
      tbody.innerHTML = (vendas||[]).map(v=>`
        <tr>
          <td>${v.id_venda}</td>
          <td>${v.descricao||'-'}</td>
          <td>${v.cliente?.nome ?? v.id_cliente}</td>
          <td>${v.veiculo?.placa ?? v.id_veiculo}</td>
          <td>R$ ${money(v.total)}</td>
          <td>${statusPill(v.status)}</td>
          <td><span class="badge-rounded pill-pay">${v.pagamento}</span></td>
          <td><button class="btn btn-sm btn-light card-btn" onclick="openCart(${v.id_venda})">Abrir</button></td>
        </tr>
      `).join('');
      renderPagination(document.getElementById('venPag'), pagination.page, pagination.per_page, pagination.total, (p)=>{venPage=p; loadVendas();});
    }
    document.getElementById('btnVenBusca').onclick = ()=>{
      venQ = venSearch.value||''; venStatus = venFilStatus.value||''; venPag = venFilPag.value||'';
      venPage=1; loadVendas();
    };

    // ========= Busca Cliente + Veículo (modal de venda) =========
    function debounce(fn, delay=250){ let t; return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn(...args), delay); }; }
    const elBuscaCli   = document.getElementById('venClienteBusca');
    const elResCli     = document.getElementById('venClienteResultados');
    const elCliHidden  = document.getElementById('venCli');
    const elVeiSelect  = document.getElementById('venVei');
    const elDesc       = document.getElementById('venDesc');

    document.getElementById('modalVendaNova').addEventListener('show.bs.modal', ()=>{
      elBuscaCli.value=''; elCliHidden.value=''; elResCli.style.display='none'; elResCli.innerHTML='';
      elVeiSelect.innerHTML='<option value="">Selecione o cliente primeiro…</option>'; elVeiSelect.disabled=true;
      elDesc.value='';
    });

    const buscarClientes = debounce(async (q)=>{
      q = (q||'').trim();
      if(!q || q.length < 2){ elResCli.style.display='none'; elResCli.innerHTML=''; return; }
      try{
        const {clientes} = await api('/api/clientes', {params:{q, page:1, per_page:10}});
        if(!clientes?.length){
          elResCli.innerHTML='<div class="list-group-item text-muted">Nenhum cliente encontrado</div>';
          elResCli.style.display='block'; return;
        }
        elResCli.innerHTML = clientes.map(c=>`
          <button type="button" class="list-group-item list-group-item-action"
                  data-id="${c.id_cliente}" data-nome="${c.nome}">
            <div class="d-flex justify-content-between">
              <strong>${c.nome}</strong><small class="text-muted">#${c.id_cliente}</small>
            </div>
            <small class="text-muted">${c.numero ? ' • '+c.numero : ''}</small>
          </button>
        `).join('');
        elResCli.style.display='block';
      }catch{
        elResCli.style.display='none';
      }
    }, 300);

    elBuscaCli.addEventListener('input', e => buscarClientes(e.target.value));

    elResCli.addEventListener('click', async e=>{
      const btn = e.target.closest('[data-id]');
      if(!btn) return;
      const id = Number(btn.dataset.id);
      const nome = btn.dataset.nome;
      elCliHidden.value = id;
      elBuscaCli.value = nome;
      elResCli.style.display = 'none';
      await carregarVeiculosDoCliente(id);
    });

    document.addEventListener('click', e=>{
      if(!elResCli.contains(e.target) && e.target !== elBuscaCli)
        elResCli.style.display='none';
    });

    async function carregarVeiculosDoCliente(id_cliente){
      elVeiSelect.disabled=true;
      elVeiSelect.innerHTML='<option>Carregando…</option>';
      try{
        const {veiculos} = await api('/api/veiculos', {params:{id_cliente, page:1, per_page:200}});
        if(!veiculos?.length){
          elVeiSelect.innerHTML='<option>Cliente sem veículos</option>'; return;
        }
        elVeiSelect.innerHTML = veiculos.map(v=>`
          <option value="${v.id_veiculo}">
            ${v.placa}${v.km ? ' • '+v.km+' km' : ''}${v.observacao ? ' • '+v.observacao : ''}
          </option>`).join('');
        elVeiSelect.disabled=false;
      }catch{
        elVeiSelect.innerHTML='<option>Erro ao carregar veículos</option>';
      }
    }

    document.getElementById('btnCriarVenda').onclick = async ()=>{
      try{
        const id_cliente = Number(elCliHidden.value);
        const id_veiculo = Number(elVeiSelect.value);
        const descricao  = elDesc.value || null;

        if(!id_cliente){ showToast('Selecione um cliente válido','error'); return; }
        if(!id_veiculo){ showToast('Selecione um veículo do cliente','error'); return; }

        const res = await api('/api/vendas', {method:'POST', body:{id_cliente, id_veiculo, descricao}});
        showToast('Venda criada!');
        bootstrap.Modal.getInstance(document.getElementById('modalVendaNova')).hide();
        loadVendas();
        openCart(res.venda.id_venda);
      }catch{}
    };

    // ===== Carrinho =====
    window.openCart = async (id)=>{
      currentVendaId = id;
      const res = await api(`/api/vendas/${id}`);
      document.getElementById('cartBox').classList.remove('d-none');
      document.getElementById('cartVendaId').textContent = id;
      document.getElementById('cartStatus').textContent = res.venda.status;
      document.getElementById('cartPag').textContent = res.venda.pagamento;
      document.getElementById('cartTotal').textContent = money(res.venda.total);
      const tbody = document.getElementById('cartItens');
      const itens = res.venda.itens || [];
      tbody.innerHTML = itens.map(it=>`
        <tr>
          <td>${it.descricao}</td>
          <td>R$ ${money(it.preco_unit)}</td>
          <td>${it.quantidade}</td>
          <td>R$ ${money(it.desconto)}</td>
          <td>R$ ${money(it.subtotal)}</td>
          <td><button class="btn btn-sm btn-outline-danger" onclick="remItem(${id}, ${it.id_item})">Remover</button></td>
        </tr>
      `).join('');
    };

    document.getElementById('btnAddItem').onclick = async ()=>{
      if(!currentVendaId) return;
      const id_servico = Number(document.getElementById('cartServico').value);
      const quantidade = Number(document.getElementById('cartQtd').value||1);
      const desconto   = Number(document.getElementById('cartDesc').value||0);
      try{
        const res = await api(`/api/vendas/${currentVendaId}/itens`, {method:'POST', body:{id_servico, quantidade, desconto}});
        showToast('Item adicionado');
        openCart(res.venda.id_venda);
        loadVendas();
      }catch{}
    };
    window.remItem = async (id_venda, id_item)=>{
      try{
        const res = await api(`/api/vendas/${id_venda}/itens/${id_item}`, {method:'DELETE'});
        showToast('Item removido');
        openCart(res.venda.id_venda); loadVendas();
      }catch{}
    };

    let finishing = false;
    document.getElementById('btnFinalizar').onclick = async () => {
      if (!currentVendaId || finishing) return;
      finishing = true;
      const btn = document.getElementById('btnFinalizar');
      btn.disabled = true;
      try {
        const forma_pagamento = document.getElementById('cartForma').value;
        const res = await api(`/api/vendas/${currentVendaId}/finalizar`, { method:'POST', body:{ forma_pagamento }});
        showToast('Venda finalizada!');
        openCart(res.venda.id_venda);
        loadVendas();
      } catch (e) {
        console.error(e);
        showToast('Erro ao finalizar venda', 'error');
      } finally {
        finishing = false;
        btn.disabled = false;
      }
    };

    let canceling = false;
    document.getElementById('btnCancelar').onclick = async () => {
      if (!currentVendaId || canceling) return;
      canceling = true;
      const btn = document.getElementById('btnCancelar');
      btn.disabled = true;
      try {
        const res = await api(`/api/vendas/${currentVendaId}/cancelar`, { method:'POST' });
        showToast('Venda cancelada');
        openCart(res.venda.id_venda);
        loadVendas();
      } catch (e) {
        console.error(e);
        showToast('Erro ao cancelar venda', 'error');
      } finally {
        canceling = false;
        btn.disabled = false;
      }
    };

    // ===== Caixa =====
    async function loadCaixa(){
      if(!cxDataRef){
        const today = new Date(); const y = today.toISOString().slice(0,10);
        document.getElementById('cxData').value = y; cxDataRef = y;
      }
      const {lancamentos, pagination, total_valor, total} = await api('/api/caixa', {params:{data: cxDataRef, page: cxPage, per_page: cxPer}});
      document.getElementById('cxTable').innerHTML = (lancamentos||[]).map(l=>`
        <tr>
          <td>${l.venda_id}</td>
          <td>${l.id_lcto||''}</td>
          <td>${l.descricao||''}</td>
          <td>R$ ${money(l.valor)}</td>
          <td>${l.created_at ? new Date(l.created_at).toLocaleString('pt-BR') : ''}</td>
        </tr>
      `).join('');
      document.getElementById('cxTotal').textContent = money(total_valor||total||0);
      document.getElementById('cxPeriodoLabel').textContent = cxDataRef;
      renderPagination(document.getElementById('cxPag'), pagination.page, pagination.per_page, pagination.total, (p)=>{cxPage=p; loadCaixa();});
    }
    document.getElementById('btnCxBuscar').onclick = ()=>{ cxDataRef = document.getElementById('cxData').value||null; cxPage=1; loadCaixa(); };

    // ===== ações de UI =====
    document.getElementById('btnToggleSidebar')?.addEventListener('click', ()=>{
      document.querySelector('.sidebar').classList.toggle('d-none');
    });
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el=>{
      new bootstrap.Tooltip(el);
    });

    /* ====== EDITAR CLIENTE ====== */
    window.openEditCliente = async (id)=>{
      try{
        const res = await api(`/api/clientes/${id}`);
        const c = res.cliente || res;
        document.getElementById('cliEditId').value   = c.id_cliente;
        document.getElementById('cliEditNome').value = c.nome||'';
        document.getElementById('cliEditCPF').value  = c.cpf||'';
        document.getElementById('cliEditTel').value  = c.numero||'';
        new bootstrap.Modal(document.getElementById('modalClienteEdit')).show();
      }catch(e){}
    };
    document.getElementById('btnAtualizarCliente').onclick = async ()=>{
      const id = Number(document.getElementById('cliEditId').value);
      try{
        const body = {
          nome:  document.getElementById('cliEditNome').value,
          cpf:   document.getElementById('cliEditCPF').value,
          numero:document.getElementById('cliEditTel').value
        };
        await api(`/api/clientes/${id}`, {method:'PUT', body});
        showToast('Cliente atualizado!');
        bootstrap.Modal.getInstance(document.getElementById('modalClienteEdit')).hide();
        loadClientes();
      }catch(e){}
    };

    /* ====== EDITAR VEÍCULO ====== */
    window.openEditVeiculo = async (id)=>{
      try{
        const res = await api(`/api/veiculos/${id}`);
        const v = res.veiculo || res;
        document.getElementById('veiEditId').value     = v.id_veiculo;
        document.getElementById('veiEditPlaca').value  = v.placa||'';
        document.getElementById('veiEditKM').value     = v.km||0;
        document.getElementById('veiEditObs').value    = v.observacao||'';
        document.getElementById('veiEditMarca').value    = v.observacao||'';
        document.getElementById('veiEditModel').value    = v.observacao||'';
        document.getElementById('veiEditCor').value    = v.observacao||'';
        new bootstrap.Modal(document.getElementById('modalVeiculoEdit')).show();
      }catch(e){}
    };
    document.getElementById('btnAtualizarVeiculo').onclick = async ()=>{
      const id = Number(document.getElementById('veiEditId').value);
      try{
        const body = {
          placa: (document.getElementById('veiEditPlaca').value||'').toUpperCase(),
          km: Number(document.getElementById('veiEditKM').value||0),
          observacao: document.getElementById('veiEditObs').value||'',
          marca: document.getElementById('veiEditMarca').value||'',
          modelo: document.getElementById('veiEditModel').value||'',
          cor: document.getElementById('veiEditCor').value||''
        };
        console.log(body);
        await api(`/api/veiculos/${id}`, {method:'PUT', body});
        showToast('Veículo atualizado!');
        bootstrap.Modal.getInstance(document.getElementById('modalVeiculoEdit')).hide();
        loadVeiculos();
      }catch(e){}
    };

    /* ====== EDITAR SERVIÇO ====== */
    window.openEditServico = async (id)=>{
      try{
        const res = await api(`/api/servicos/${id}`);
        const s = res.servico || res;
        document.getElementById('svcEditId').value    = s.id_servico;
        document.getElementById('svcEditNome').value  = s.nome||'';
        document.getElementById('svcEditValor').value = s.valor||0;
        new bootstrap.Modal(document.getElementById('modalServicoEdit')).show();
      }catch(e){}
    };
    document.getElementById('btnAtualizarServico').onclick = async ()=>{
      const id = Number(document.getElementById('svcEditId').value);
      try{
        const body = { nome: document.getElementById('svcEditNome').value, valor: Number(document.getElementById('svcEditValor').value||0) };
        await api(`/api/servicos/${id}`, {method:'PUT', body});
        showToast('Serviço atualizado!');
        bootstrap.Modal.getInstance(document.getElementById('modalServicoEdit')).hide();
        loadServicos(); loadServicosCombo();
      }catch(e){}
    };