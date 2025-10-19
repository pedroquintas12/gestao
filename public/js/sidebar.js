export async function initSidebar(){
    const sidebar =  document.getElementById("sidebar");
    if(!sidebar) return;

    let user = null;
    try {
        const resp = await fetch("/me", { credentials: "include" });
        user = await resp.json();
        console.log(user)
    } catch (err) {
        console.error("Erro ao buscar usuário logado", err);
    }

    sidebar.innerHTML= `
    <ul class="nav flex-column" id="menu">
        <li class="nav-item">
          <a class="nav-link active" href="#dashboard" data-bs-toggle="tooltip" data-bs-placement="right" title="Dashboard">
            <i class="bi bi-speedometer2"></i><span class="label">Dashboard</span>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#clientes" data-bs-toggle="tooltip" data-bs-placement="right" title="Clientes">
            <i class="bi bi-people"></i><span class="label">Clientes</span>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#veiculos" data-bs-toggle="tooltip" data-bs-placement="right" title="Veículos">
            <i class="bi bi-truck"></i><span class="label">Veículos</span>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#servicos" data-bs-toggle="tooltip" data-bs-placement="right" title="Serviços">
            <i class="bi bi-wrench-adjustable-circle"></i><span class="label">Serviços</span>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#vendas" data-bs-toggle="tooltip" data-bs-placement="right" title="Vendas / Orçamentos">
            <i class="bi bi-bag-check"></i><span class="label">Vendas / Orçamentos</span>
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#caixa" data-bs-toggle="tooltip" data-bs-placement="right" title="Caixa do dia">
            <i class="bi bi-cash-coin"></i><span class="label">Caixa do dia</span>
          </a>
        </li>
      </ul>
      
      `
      if (user.is_admin){
        sidebar.innerHTML =
        `
        <li class="nav-item">
          <a class="nav-link" href="/admin" data-bs-toggle="tooltip" data-bs-placement="right" title="Administração">
            <i class="bi bi-cash-coin"></i><span class="label">Administração</span>
          </a>
        </li>
        `
      }



}