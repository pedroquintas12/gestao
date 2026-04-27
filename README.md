# Gestao

Sistema de gestão financeira para pequenos negócios, empacotado como aplicativo desktop para Windows. Suporta múltiplos ramos: hoje **lava-jato** (com cadastro de veículos, placas, KM) e **genérico** (sem veículos). O ramo é escolhido na instalação. Inclui módulo opcional de **estoque** com campos customizáveis pelo próprio usuário.

## Funcionalidades

- Cadastro de clientes, serviços, vendas (com itens), caixa diário e empresa.
- Cadastro de veículos vinculado ao cliente (ramo lava-jato).
- Estoque com campos custom: o usuário define que colunas o produto tem (texto, número, data, booleano, lista) e o app valida automaticamente.
- Geração de orçamento em PDF.
- Login com sessões e usuário admin.
- Auto-update via GitHub Releases (a cada abertura, o launcher checa se há versão nova e oferece atualizar).

## Instalação (usuário final)

Baixe o instalador mais recente em [Releases](https://github.com/pedroquintas12/gestao/releases) e execute.

O instalador:
1. Pergunta o **ramo do negócio** (lava-jato ou genérico).
2. Pergunta quais **módulos opcionais** instalar (atualmente: estoque).
3. Instala o Python 3.12 silenciosamente.
4. Cria um ambiente virtual em `C:\Program Files\Gestao\venv` e instala as dependências.
5. Cria atalho na Área de Trabalho (opcional).
6. Escreve `BUSINESS_TYPE` e `ENABLE_ESTOQUE` no `.env` em `%LOCALAPPDATA%\Gestao\.env` conforme as escolhas.

Os dados do app (banco SQLite, logs e `.env`) ficam em:
```
%LOCALAPPDATA%\Gestao\
├─ gestor.db
├─ .env
└─ logs\
   ├─ app.log
   └─ app_error.log
```

## Stack

- **Backend:** Flask 3, Flask-SQLAlchemy 2, SQLite, Flask-Bcrypt
- **Frontend:** Jinja templates + JS/CSS estáticos (sem build)
- **PDF:** ReportLab
- **Launcher/GUI:** Tkinter (`gui.exe` via PyInstaller)
- **Instalador:** Inno Setup 6

## Desenvolvimento

```bash
# clone e venv
git clone https://github.com/pedroquintas12/gestao.git
cd gestao
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# deps
pip install -r requirements.txt

# rodar (sobe Flask em http://127.0.0.1:5000)
python main.py
```

No primeiro acesso você é redirecionado para `/cadastroCompanie` para registrar a empresa. O usuário admin padrão é semeado automaticamente:

- **Usuário:** `Admin`
- **Senha:** `001305`

Troque a senha após o primeiro login.

### Variáveis de ambiente

Copie `env.example` para `.env` na raiz (em dev) ou em `%LOCALAPPDATA%\Gestao\.env` (em produção):

| Variável | Default | Descrição |
|---|---|---|
| `BUSINESS_TYPE` | `lavajato` | Ramo do negócio: `lavajato` ou `generico` |
| `ENABLE_ESTOQUE` | `true` | Liga/desliga o módulo de estoque (independente do ramo) |
| `SECRET_KEY` | `change-me` | Chave para assinatura de sessão Flask |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///gestor.db` | Em produção é reescrita para `%LOCALAPPDATA%\Gestao\gestor.db` |
| `SEED_ON_STARTUP` | `true` | Se `true`, semeia admin e serviços padrão na inicialização |
| `TEMPLATE_FOLDER` | `views` | Pasta dos templates |
| `STATIC_FOLDER` | `public` | Pasta dos estáticos |
| `GESTAO_DEBUG` | _(vazio)_ | Setar `1` ativa log no console |

### Modo dev no Windows

Há um script `gestor.bat` que faz `git pull`, atualiza dependências e roda `main.py` com logs em `%LOCALAPPDATA%\Gestao\logs\app_console.log`.

## Testes

```bash
pytest                                    # tudo
pytest test/test_venda.py                 # um arquivo
pytest test/test_venda.py::test_fluxo...  # um teste
```

Cada teste cria um SQLite temporário isolado via `create_app()` (ver [test/conftest.py](test/conftest.py)). Para rodar testes em outro ramo:

```python
@pytest.mark.parametrize("business_type", [BusinessType.GENERICO], indirect=True)
def test_meu_caso(client):
    ...
```

## Build do instalador

### Local (Windows)

Pré-requisitos:
- Python 3.12
- [Inno Setup 6](https://jrsoftware.org/isinfo.php)
- `installer/binaries/python-3.12.6-amd64.exe` baixado do site oficial

```powershell
.\build_local.ps1
```

O instalador resultante sai em `installer/Output/`.

### CI

Push de tag `V*` (ex.: `git tag V0.5.0 && git push --tags`) dispara [.github/workflows/release.yml](.github/workflows/release.yml), que:
1. Gera `config/version.py` a partir da tag.
2. Builda `gui.exe` com PyInstaller.
3. Compila o instalador via Inno Setup.
4. Anexa o `.exe` ao GitHub Release.
5. Atualiza `latest.json` no `main` (consumido pelo auto-update do app).

Também é possível rodar via `workflow_dispatch` para gerar um build de teste sem criar release.

## Arquitetura

Camadas em ordem do request:
```
routes/      Blueprints, mapeiam HTTP → controller
controller/  Parsing de request, paginação, monta resposta
service/     Regra de negócio, transações, queries
model/       SQLAlchemy models
helpers/     Padronização de respostas
utils/       api_error, geração de orçamento
```

### Modularização por ramo

O ramo é lido de `BUSINESS_TYPE` e cada ramo ativa um conjunto de **módulos opcionais** (ex.: `veiculo` só existe em lava-jato). Alguns módulos têm flag dedicada e são independentes do ramo (ex.: `estoque` ↔ `ENABLE_ESTOQUE`).

- **Definição dos ramos:** [enums/business.py](enums/business.py)
- **Mapa de módulos por ramo + env flags:** [config/business.py](config/business.py) → `OPTIONAL_MODULES_BY_TYPE` e `MODULE_ENV_FLAGS`
- **Registro condicional dos blueprints:** [app/__init__.py](app/__init__.py) → `_register_blueprints`
- **Endpoint para o frontend:** `GET /api/config/business` retorna `{type, label, modules}`

Para adicionar um novo ramo (ex.: barbearia):
1. Adicione o valor em `BusinessType` e a label em `BusinessType.label`.
2. Liste os módulos opcionais em `OPTIONAL_MODULES_BY_TYPE`.
3. Adicione serviços padrão em `DEFAULT_SERVICOS_BY_TYPE` ([app/seeds.py](app/seeds.py)).
4. Adicione a opção no `BusinessTypePage` do [installer/gestao_with_python.iss](installer/gestao_with_python.iss).

### Estoque com campos customizáveis

O módulo `estoque` permite ao usuário **definir as colunas dos produtos**. Cada negócio cadastra os campos que faz sentido para ele (validade, marca, fornecedor, voltagem etc.) e o app valida tipos automaticamente.

**Tipos suportados:** `texto`, `numero`, `data`, `booleano`, `select` (com opções).

**Como funciona:**

1. Admin cadastra as definições de campo:
   ```http
   POST /api/field-definitions
   { "label": "Marca", "tipo": "texto" }
   POST /api/field-definitions
   { "label": "Validade", "tipo": "data", "obrigatorio": true }
   POST /api/field-definitions
   { "label": "Categoria", "tipo": "select", "opcoes": ["limpeza", "polimento"] }
   ```

2. Ao criar/editar um produto, os campos custom vão em `extras`:
   ```http
   POST /api/produtos
   {
     "nome": "Cera Vonixx",
     "preco": 80.0,
     "quantidade": 5,
     "extras": {
       "marca": "Vonixx",
       "validade": "2027-01-01",
       "categoria": "polimento"
     }
   }
   ```

3. O backend valida automaticamente: campos desconhecidos são rejeitados (400), tipos errados retornam mensagem clara, obrigatórios faltando retornam erro, e valores de `select` precisam estar entre as opções.

**Endpoints:**

| Método | Rota | Descrição |
|---|---|---|
| `GET/POST` | `/api/field-definitions` | Listar / criar campo custom |
| `GET/PATCH/DELETE` | `/api/field-definitions/<id>` | Detalhar / editar / soft-delete |
| `GET/POST` | `/api/produtos` | Listar (com paginação `q`, `page`, `per_page`) / criar |
| `GET/PATCH/DELETE` | `/api/produtos/<id>` | Detalhar / editar / soft-delete |
| `POST` | `/api/produtos/<id>/ajustar` | Body `{"delta": int}` — soma na quantidade (não permite negativa) |

**UI:** o app abre uma aba "Estoque" na sidebar (só aparece com o módulo ativo) com duas seções:

- **Produtos:** listagem paginada, criar/editar/excluir, ajuste rápido de quantidade (`±`).
- **Campos customizados:** CRUD das definições. O formulário de produto é gerado dinamicamente conforme você cadastra/altera campos.

**Para desligar o módulo:** edite `%LOCALAPPDATA%\Gestao\.env` e troque `ENABLE_ESTOQUE=false` (ou desmarque o checkbox no instalador). Os blueprints não são registrados e as tabelas continuam no banco mas vazias/intocadas.

## Versionamento e auto-update

A versão fica em [config/version.py](config/version.py) (regenerada pelo CI a partir da tag). O launcher [GUI.py](GUI.py) consulta `latest.json` no `main` e oferece atualizar quando há versão mais recente. O processo de update mata `gui.exe`, `python.exe` e `Gestao.exe` antes de sobrescrever os arquivos.

## Licença

Privado.
