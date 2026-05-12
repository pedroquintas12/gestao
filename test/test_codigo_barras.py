"""
Código de barras em Produto:
- cadastro com/sem código;
- código duplicado → 409;
- busca por código (200/404);
- scanner em venda: resolver código → adicionar item.
"""


def test_criar_produto_com_codigo_barras(client):
    r = client.post(
        "/api/produtos",
        json={"nome": "Shampoo", "preco": 35, "quantidade": 5, "codigo_barras": "7891234567890"},
    )
    assert r.status_code == 201
    body = r.get_json()["produto"]
    assert body["codigo_barras"] == "7891234567890"


def test_codigo_barras_opcional(client):
    r = client.post(
        "/api/produtos",
        json={"nome": "Sem código", "preco": 1, "quantidade": 1},
    )
    assert r.status_code == 201
    assert r.get_json()["produto"]["codigo_barras"] is None


def test_codigo_barras_duplicado_rejeita(client):
    client.post(
        "/api/produtos",
        json={"nome": "A", "preco": 1, "quantidade": 1, "codigo_barras": "111"},
    )
    r = client.post(
        "/api/produtos",
        json={"nome": "B", "preco": 1, "quantidade": 1, "codigo_barras": "111"},
    )
    assert r.status_code == 409


def test_buscar_por_codigo_barras_200_e_404(client):
    client.post(
        "/api/produtos",
        json={"nome": "Cera", "preco": 50, "quantidade": 3, "codigo_barras": "ABC-123"},
    )
    r = client.get("/api/produtos/by-codigo/ABC-123")
    assert r.status_code == 200
    assert r.get_json()["produto"]["nome"] == "Cera"

    r = client.get("/api/produtos/by-codigo/INEXISTENTE")
    assert r.status_code == 404


def test_codigo_barras_normaliza_espacos(client):
    """Espaços em branco no início/fim e internos são removidos."""
    r = client.post(
        "/api/produtos",
        json={"nome": "X", "preco": 1, "quantidade": 1, "codigo_barras": "  789 123 "},
    )
    assert r.status_code == 201
    assert r.get_json()["produto"]["codigo_barras"] == "789123"


def test_fluxo_scanner_em_venda(client):
    """Cliente escaneia o código → resolve produto → adiciona como item."""
    cli = client.post(
        "/api/clientes", json={"nome": "Scan", "cpf": "1", "numero": "8"}
    ).get_json()["cliente"]
    vei = client.post(
        "/api/veiculos",
        json={"id_cliente": cli["id_cliente"], "placa": "SCN1234"},
    ).get_json()["veiculo"]
    prod = client.post(
        "/api/produtos",
        json={"nome": "Item Scan", "preco": 9.9, "quantidade": 10, "codigo_barras": "EAN1"},
    ).get_json()["produto"]

    venda = client.post(
        "/api/vendas",
        json={"id_cliente": cli["id_cliente"], "id_veiculo": vei["id_veiculo"]},
    ).get_json()["venda"]

    # Passo 1: cliente escaneia e front resolve o id
    r = client.get("/api/produtos/by-codigo/EAN1")
    assert r.status_code == 200
    id_produto = r.get_json()["produto"]["id_produto"]
    assert id_produto == prod["id_produto"]

    # Passo 2: front envia POST do item
    r = client.post(
        f"/api/vendas/{venda['id_venda']}/itens",
        json={"id_produto": id_produto, "quantidade": 1},
    )
    assert r.status_code == 200
    itens = r.get_json()["venda"]["itens"]
    assert any(it["id_produto"] == id_produto for it in itens)


def test_codigo_barras_pode_ser_atualizado_e_limpado(client):
    pid = client.post(
        "/api/produtos",
        json={"nome": "Z", "preco": 1, "quantidade": 1, "codigo_barras": "AAA"},
    ).get_json()["produto"]["id_produto"]

    # troca
    r = client.patch(f"/api/produtos/{pid}", json={"codigo_barras": "BBB"})
    assert r.status_code == 200
    assert r.get_json()["produto"]["codigo_barras"] == "BBB"

    # limpa (envia null ou string vazia)
    r = client.patch(f"/api/produtos/{pid}", json={"codigo_barras": ""})
    assert r.status_code == 200
    assert r.get_json()["produto"]["codigo_barras"] is None


def test_slug_codigo_barras_eh_reservado(client):
    """FieldDefinition não pode criar campo com nome 'codigo_barras' (colide com coluna)."""
    r = client.post(
        "/api/field-definitions",
        json={"label": "Codigo", "tipo": "texto", "nome": "codigo_barras"},
    )
    assert r.status_code == 400
    assert "reservado" in str(r.get_json()).lower()


def test_busca_por_q_inclui_codigo_barras(client):
    client.post(
        "/api/produtos",
        json={"nome": "Aaa", "preco": 1, "quantidade": 1, "codigo_barras": "XYZ999"},
    )
    r = client.get("/api/produtos?q=XYZ999")
    assert r.status_code == 200
    nomes = [p["nome"] for p in r.get_json()["produtos"]]
    assert "Aaa" in nomes
