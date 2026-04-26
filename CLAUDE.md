# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

App Flask de gestão (atualmente modelado para lava-jato) empacotado como instalador Windows. Stack: Flask 3 + Flask-SQLAlchemy + SQLite + Flask-Bcrypt + sessões. Distribuição: Inno Setup empacota o app, um `gui.exe` (launcher Tk com auto-update) e um instalador offline do Python 3.12.

## Comandos

### Desenvolvimento (Linux/Windows)
```bash
# venv + deps
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# rodar (sobe Flask em :5000 e abre o browser)
python main.py
```
No Windows há também `gestor.bat` (faz `git pull`, atualiza deps e roda `main.py`, com logs em `%LOCALAPPDATA%\Gestao\logs\app_console.log`).

### Testes
```bash
# todos
pytest

# um arquivo
pytest test/test_venda.py

# um teste
pytest test/test_venda.py::test_fluxo_venda_com_item_e_finalizacao_gera_caixa
```
`test/pytest.ini` define `testpaths = test`. A fixture `app` em [test/conftest.py](test/conftest.py) cria um SQLite temporário por teste e dropa as tabelas no teardown — chamando `create_app()` real.

### Build do instalador
```powershell
# local (Windows + Inno Setup 6 + Python 3.12)
.\build_local.ps1
```
Requer `installer/binaries/python-3.12.6-amd64.exe` baixado manualmente. CI: push de tag `V*` (ou `workflow_dispatch`) dispara [.github/workflows/release.yml](.github/workflows/release.yml) que gera [config/version.py](config/version.py), builda `gui.exe` via PyInstaller, compila o `.iss`, anexa ao GitHub Release e **commita `latest.json` direto no `main`**.

## Arquitetura

### Camadas (request → response)
```
routes/        Blueprint, mapeia HTTP → método do controller (com @login_required)
controller/    Parsing de request, paginação, monta resposta via helper
service/       Regra de negócio, transações, queries
model/         SQLAlchemy models (db.Model + TimestampMixin)
helpers/       service_result_to_response (padroniza retorno), UTC helpers
utils/         api_error, orcamentoUtil
```
Convenção dos controllers: classes com métodos sem `self` chamados como `ClasseController.metodo` (ver [controller/clienteController.py](controller/clienteController.py)). Controllers retornam via [helpers/service_resulte_helper.py](helpers/service_resulte_helper.py:19), que aceita: model com `to_dict()`, dict de erro com `{"error", "status"}`, tupla `(body, status)` ou `Response`.

Erros: serviços devolvem `{"error": "...", "status": 4xx}` (não levantam exceção). Handlers globais em [app/erros.py](app/erros.py).

### Bootstrap
[app/__init__.py:12](app/__init__.py#L12) `create_app()`:
1. Carrega config via [config/__init__.py](config/__init__.py) (`load_env_and_config`).
2. `db.init_app(app)`, registra todos os blueprints, **chama `db.create_all()` a cada start** (sem Alembic/migrations — mudanças destrutivas em modelos exigem dropar o `.db` ou migrar à mão).
3. Se `SEED_ON_STARTUP=true`, [app/seeds.py](app/seeds.py) cria usuário `Admin` / senha `001305` (idempotente).

[main.py](main.py) decide entre `/login` e `/cadastroCompanie` consultando se existe alguma `companie` no banco — onboarding é gatilhado pela ausência de empresa cadastrada.

### Configuração & paths
- `.env` resolvido em ordem: `GESTAO_ENV` (override) → `%LOCALAPPDATA%\Gestao\.env` → raiz do app. O instalador copia `env.example` para `%LOCALAPPDATA%\Gestao\.env` no `ssPostInstall`.
- `_find_install_root` em [config/__init__.py:10](config/__init__.py#L10) sobe diretórios procurando a pasta `config/` para descobrir a raiz — **não renomeie a pasta `config/`** sem ajustar isso.
- SQLite relativo (`sqlite:///gestor.db`) é reescrito para `%LOCALAPPDATA%\Gestao\gestor.db` em produção.
- Logs: `%LOCALAPPDATA%\Gestao\logs\app.log` (INFO/WARN), `app_error.log` (ERROR+). Console habilitado com `GESTAO_DEBUG=1`.

### Auth
Session-based. [config/decorators.py](config/decorators.py): `@login_required` exige `session["user_id"]`; `@admin_required` exige `session["is_admin"] == True`. Não há JWT/API token — todas as rotas `/api/*` dependem do cookie de sessão.

### Domínio
Modelos centrais: `cliente`, `veiculo` (específico de lava-jato — só carrega dados quando o módulo está ativo), `servico`, `venda` + `VendaItem`, `caixa_lancamento`, `companie`, `User`, `funcionario`. `venda.id_veiculo` é **nullable** ([model/vendaModel.py:11](model/vendaModel.py#L11)) — em ramo `generico` a venda existe sem veículo. Finalizar uma venda gera lançamento em caixa (ver fluxo no teste [test/test_venda.py:8](test/test_venda.py#L8)).

### Modularização por ramo de negócio
O app suporta múltiplos ramos via `BUSINESS_TYPE` no `.env` (`lavajato` | `generico`). A lista canônica está em [enums/business.py](enums/business.py); o mapa de módulos opcionais por ramo está em [config/business.py](config/business.py) (`OPTIONAL_MODULES_BY_TYPE`). Hoje o único módulo opcional é `veiculo`.

- **Ler o ramo:** `from config.business import current_type, is_module_enabled` — nunca leia `os.getenv("BUSINESS_TYPE")` direto, sempre passe pelo helper (que respeita `set_current_type` em testes).
- **Registrar blueprint opcional:** condicione em [app/__init__.py](app/__init__.py) (função `_register_blueprints`) com `if is_module_enabled("nome"):`.
- **Lógica de domínio que depende de módulo:** consulte `is_module_enabled` no service (ex.: [service/vendasService.py](service/vendasService.py) só exige `id_veiculo` quando `veiculo` está ativo, e usa `outerjoin` para listar).
- **Seeds por ramo:** veja `DEFAULT_SERVICOS_BY_TYPE` em [app/seeds.py](app/seeds.py) — semeia apenas em banco vazio (idempotente por checagem de `Servico.query.first()`).
- **Frontend:** templates recebem `business_type` e `enabled_modules` no contexto (ver [routes/routes_front.py](routes/routes_front.py)); JS pode bater em `GET /api/config/business`.
- **Instalador:** [installer/gestao_with_python.iss](installer/gestao_with_python.iss) tem `InitializeWizard` com `TInputOptionWizardPage` que escreve `BUSINESS_TYPE=...` em `%LOCALAPPDATA%\Gestao\.env` no `ssPostInstall` via `WriteOrReplaceEnvLine`.

**Para adicionar um ramo novo:**
1. Adicione o valor em `BusinessType` ([enums/business.py](enums/business.py)) e a label no dict `label`.
2. Liste módulos opcionais em `OPTIONAL_MODULES_BY_TYPE` ([config/business.py](config/business.py)).
3. Adicione seeds em `DEFAULT_SERVICOS_BY_TYPE` ([app/seeds.py](app/seeds.py)).
4. Adicione opção no `BusinessTypePage.Add(...)` do `.iss`.
5. Teste com `@pytest.mark.parametrize("business_type", [BusinessType.NOVO], indirect=True)`.

`venda.status` usa `enums.status`; `venda.pagamento` usa `enums.forma_pagamentoEnum.FormaPagamento` (default `NÃO_PAGO`).

`companie.imagem_bloob` armazena logo gzip-comprimida; serializada como data URL via property `photo`.

### Frontend
SSR Jinja minimalista: 4 templates em [views/](views/) (`login.html`, `cadastroCompanie.html`, `admin.html`, `index.html` — este último concentra a UI). JS/CSS estáticos em [public/](public/). Não há build de frontend.

### Distribuição & auto-update
- [GUI.py](GUI.py) é o launcher (Tk) que vira `gui.exe`. No start ele consulta `LATEST_JSON_URL` (raw do `latest.json` no `main`), compara com `config.version.__version__` e oferece atualização. O instalador roda elevado via `ShellExecuteW(..., "runas", ...)`.
- [installer/gestao_with_python.iss](installer/gestao_with_python.iss): instala em `{pf}\Gestao`, mata processos antigos (`gui.exe`, `launcher.exe`, `python.exe`, `Gestao.exe`) antes de sobrescrever, instala Python 3.12 silenciosamente, cria venv em `{app}\venv`, instala `requirements.txt`.
- `config/version.py` é **regenerado pelo workflow** a partir do nome da tag — não edite à mão para releases.

## Convenção de testes

Toda função criada ou alterada **precisa ter teste correspondente** em [test/](test/) — novo `test_*` para função nova, atualização do teste existente para função modificada. Padrão dos testes: usar a fixture `client` (Flask test client) e bater nas rotas reais (`/api/...`), não chamar serviços diretamente — ver [test/test_venda.py](test/test_venda.py) como referência.

## Pegadinhas

- Adicionar modelo novo: importar em [model/__init__.py](model/__init__.py) **e** em [test/conftest.py](test/conftest.py), senão `db.create_all()` não cria a tabela em testes.
- Não há migrations: alteração de schema em produção pede plano (export/import ou Alembic ad-hoc) — usuários têm dados em `%LOCALAPPDATA%\Gestao\gestor.db`.
- `db.create_all()` roda em todo boot — colunas novas em tabelas existentes **não são aplicadas** (SQLAlchemy só cria tabelas faltantes).
- Controllers usam métodos sem `self`/`@staticmethod`; chame sempre como `Classe.metodo`, nunca instancie.
- CORS está aberto (`origins: "*"`) com `supports_credentials=True` ([app/__init__.py](app/__init__.py)) — ok para uso local/desktop, revisar antes de expor.
- [test/pytest.ini](test/pytest.ini) está sem o cabeçalho `[pytest]` (pytest moderno reclama). Rode `pytest -c /dev/null` ou ignore o aviso até consertar.
