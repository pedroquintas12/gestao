export async function initSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;

  // 1) Busca do usuário (tolerante a 204/HTML)
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
      <a class="nav-link" href="/admin" data-role="admin" data-bs-toggle="tooltip" data-bs-placement="right" title="Administração">
        <i class="bi bi-gear"></i><span class="label">Administração</span>
      </a>
    </li>
  ` : "";

  // 2) Menu — links apontam para "/" (SPA com hash) e "/admin" (rota real)
  sidebar.innerHTML = `
    <ul class="nav flex-column" id="menu">
      <li class="nav-item">
        <a class="nav-link" href="/#dashboard" data-section="dashboard" data-bs-toggle="tooltip" data-bs-placement="right" title="Dashboard">
          <i class="bi bi-speedometer2"></i><span class="label">Dashboard</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="/#clientes" data-section="clientes" data-bs-toggle="tooltip" data-bs-placement="right" title="Clientes">
          <i class="bi bi-people"></i><span class="label">Clientes</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="/#veiculos" data-section="veiculos" data-bs-toggle="tooltip" data-bs-placement="right" title="Veículos">
          <i class="bi bi-truck"></i><span class="label">Veículos</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="/#servicos" data-section="servicos" data-bs-toggle="tooltip" data-bs-placement="right" title="Serviços">
          <i class="bi bi-wrench-adjustable-circle"></i><span class="label">Serviços</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="/#vendas" data-section="vendas" data-bs-toggle="tooltip" data-bs-placement="right" title="Vendas / Orçamentos">
          <i class="bi bi-bag-check"></i><span class="label">Vendas / Orçamentos</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="/#caixa" data-section="caixa" data-bs-toggle="tooltip" data-bs-placement="right" title="Caixa do dia">
          <i class="bi bi-cash-coin"></i><span class="label">Caixa do dia</span>
        </a>
      </li>
      ${adminItem}
    </ul>
  `;

  // 3) Tooltips
  if (window.bootstrap?.Tooltip) {
    sidebar.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
  }

  // 4) Ativação visual
  function setActive() {
    // limpa
    sidebar.querySelectorAll('#menu .nav-link').forEach(a => a.classList.remove('active'));

    if (location.pathname === '/admin') {
      // ativa admin quando na rota real
      sidebar.querySelector('#menu .nav-link[data-role="admin"]')?.classList.add('active');
      return;
    }

    // estamos em "/" → usa hash (#dashboard como padrão)
    const section = (location.hash || '#dashboard').replace('#', '');
    const link = sidebar.querySelector(`#menu .nav-link[data-section="${section}"]`);
    (link || sidebar.querySelector('#menu .nav-link[data-section="dashboard"]'))?.classList.add('active');
  }

  setActive();
  // hash muda dentro de "/"
  window.addEventListener('hashchange', setActive);
  // navegação entre "/" e "/admin"
  window.addEventListener('popstate', setActive);
}
