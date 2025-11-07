export async function initSidebar() {
  const sidebarNav = document.getElementById("sidebar");
  if (!sidebarNav) return;

  const aside = sidebarNav.closest("aside.sidebar");
  const version = aside?.dataset.version || "0.0.0";
  aside?.classList.remove("d-none"); // limpa possível resquício

  // Busca usuário
  let user = null;
  try {
    const resp = await fetch("/me", { credentials: "include" });
    if (resp.ok) {
      const text = await resp.text();
      user = text ? JSON.parse(text) : null;
    }
  } catch (err) {
    console.error("Erro ao buscar usuário logado:", err);
  }

  const adminItem = (user && user.is_admin) ? `
    <li class="nav-item">
      <a class="nav-link" href="/admin" data-role="admin"
         data-bs-toggle="tooltip" data-bs-placement="right"
         title="Administração" aria-label="Administração">
        <i class="bi bi-gear"></i><span class="label">Administração</span>
      </a>
    </li>
  ` : "";

  // Menu com labels (serão ocultos quando colapsar)
  sidebarNav.innerHTML = `
    <ul id="menu" class="list-unstyled m-0 p-0">
      <li><a href="/#dashboard" class="nav-link active" data-section="dashboard"
             data-bs-toggle="tooltip" data-bs-placement="right"
             title="Dashboard" aria-label="Dashboard">
             <i class="bi bi-speedometer2"></i><span class="label">Dashboard</span></a></li>

      <li><a href="/#clientes" class="nav-link" data-section="clientes"
             data-bs-toggle="tooltip" data-bs-placement="right"
             title="Clientes" aria-label="Clientes">
             <i class="bi bi-people"></i><span class="label">Clientes</span></a></li>

      <li><a href="/#veiculos" class="nav-link" data-section="veiculos"
             data-bs-toggle="tooltip" data-bs-placement="right"
             title="Veículos" aria-label="Veículos">
             <i class="bi bi-car-front"></i><span class="label">Veículos</span></a></li>

      <li><a href="/#servicos" class="nav-link" data-section="servicos"
             data-bs-toggle="tooltip" data-bs-placement="right"
             title="Serviços" aria-label="Serviços">
             <i class="bi bi-wrench-adjustable"></i><span class="label">Serviços</span></a></li>

      <li><a href="/#vendas" class="nav-link" data-section="vendas"
             data-bs-toggle="tooltip" data-bs-placement="right"
             title="Vendas / Orçamentos" aria-label="Vendas / Orçamentos">
             <i class="bi bi-receipt"></i><span class="label">Vendas / Orçamentos</span></a></li>

      <li><a href="/#caixa" class="nav-link" data-section="caixa"
             data-bs-toggle="tooltip" data-bs-placement="right"
             title="Caixa do dia" aria-label="Caixa do dia">
             <i class="bi bi-cash-coin"></i><span class="label">Caixa do dia</span></a></li>

      ${adminItem}

      <li class="mt-3 border-top pt-3">
        <a href="/logout" class="nav-link text-danger"
           data-bs-toggle="tooltip" data-bs-placement="right"
           title="Sair" aria-label="Sair">
           <i class="bi bi-box-arrow-right"></i><span class="label">Sair</span></a>
      </li>
    </ul>
  `;

  // Versão no footer
  const sbVersion = document.getElementById("sbVersion");
  if (sbVersion) sbVersion.textContent = `v${version}`;

  // ===== Tooltips: só quando colapsada =====
  const mq = window.matchMedia("(max-width: 992px)");

  function isExpanded() {
    // Desktop expandida: sem .collapsed
    // Mobile expandida: com .force-expanded
    return (!mq.matches && !aside.classList.contains("collapsed")) ||
           ( mq.matches &&  aside.classList.contains("force-expanded"));
  }

  function enableTooltips() {
    if (!window.bootstrap?.Tooltip) return;
    sidebarNav.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
      bootstrap.Tooltip.getOrCreateInstance(el, { container: 'body' });
    });
  }

  function disableTooltips() {
    if (!window.bootstrap?.Tooltip) return;
    sidebarNav.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
      const inst = bootstrap.Tooltip.getInstance(el);
      if (inst) inst.dispose();
    });
  }

  function refreshTooltipsByState() {
    if (isExpanded()) {
      disableTooltips(); // expandida = sem tooltip
    } else {
      enableTooltips();  // colapsada = com tooltip
    }
  }

  // Active state
  function setActive() {
    sidebarNav.querySelectorAll('#menu .nav-link').forEach(a => a.classList.remove('active'));
    if (location.pathname === '/admin') {
      sidebarNav.querySelector('#menu .nav-link[data-role="admin"]')?.classList.add('active');
      return;
    }
    const section = (location.hash || '#dashboard').replace('#', '');
    const link = sidebarNav.querySelector(`#menu .nav-link[data-section="${section}"]`);
    (link || sidebarNav.querySelector('#menu .nav-link[data-section="dashboard"]'))?.classList.add('active');
  }
  setActive();
  window.addEventListener('hashchange', setActive);
  window.addEventListener('popstate', setActive);

  // ===== Toggle que diferencia desktop x mobile =====
  const toggleBtn = document.getElementById("btnToggleSidebar");

  function applySavedState() {
    try {
      const desk = localStorage.getItem("sb_collapsed_desktop");
      const mob  = localStorage.getItem("sb_expanded_mobile");

      if (!mq.matches) {
        // desktop
        aside.classList.toggle("collapsed", desk === "1");
        aside.classList.remove("force-expanded"); // só mobile usa isso
        aside?.classList.remove("d-none");
      } else {
        // mobile
        aside.classList.toggle("force-expanded", mob === "1");
        aside?.classList.remove("d-none");
      }
    } catch {}
    refreshTooltipsByState();
  }

  applySavedState();

  if (toggleBtn && aside) {
    // previne handler antigo
    toggleBtn.onclick = null;
    toggleBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopImmediatePropagation();

      if (mq.matches) {
        // MOBILE: alterna "force-expanded"
        const willExpand = !aside.classList.contains("force-expanded");
        aside.classList.toggle("force-expanded", willExpand);
        aside?.classList.remove("d-none");
        try { localStorage.setItem("sb_expanded_mobile", willExpand ? "1" : "0"); } catch {}
      } else {
        // DESKTOP: alterna "collapsed"
        const willCollapse = !aside.classList.contains("collapsed");
        aside.classList.toggle("collapsed", willCollapse);
        aside?.classList.remove("d-none");
        try { localStorage.setItem("sb_collapsed_desktop", willCollapse ? "1" : "0"); } catch {}
      }

      // atualiza tooltips conforme novo estado
      refreshTooltipsByState();
    }, { capture: true });

    // Reaplica estados ao mudar largura (evita “sumir”)
    mq.addEventListener?.("change", applySavedState);
    window.addEventListener("resize", applySavedState);
  }
}
