"""
Testes do módulo de estoque (Produto + FieldDefinition com extras JSON).
"""
import pytest

from enums.business import BusinessType


# ---------- field-definition CRUD ----------

def test_field_definition_create_minimal(client):
    res = client.post("/api/field-definitions", json={
        "label": "Marca", "tipo": "texto"
    })
    assert res.status_code == 201
    body = res.get_json()["campo"]
    assert body["nome"] == "marca"  # gerado a partir do label
    assert body["tipo"] == "texto"
    assert body["entity"] == "produto"


def test_field_definition_create_select_sem_opcoes_falha(client):
    res = client.post("/api/field-definitions", json={
        "label": "Categoria", "tipo": "select"
    })
    assert res.status_code == 400
    assert "opcoes" in str(res.get_json())


def test_field_definition_nome_reservado_e_rejeitado(client):
    """Slugs que colidem com colunas do Produto não podem ser usados."""
    for reserved in ["nome", "preco", "quantidade", "extras", "deleted"]:
        res = client.post("/api/field-definitions", json={
            "label": reserved.upper(), "tipo": "texto", "nome": reserved
        })
        assert res.status_code == 400, f"slug reservado '{reserved}' devia falhar"
        assert "reservado" in str(res.get_json()).lower()


def test_field_definition_unicidade_por_entity_e_nome(client):
    client.post("/api/field-definitions", json={"label": "Cor", "tipo": "texto"})
    res = client.post("/api/field-definitions", json={"label": "Cor", "tipo": "texto"})
    assert res.status_code == 409


def test_field_definition_listar(client):
    client.post("/api/field-definitions", json={"label": "A", "tipo": "texto", "ordem": 2})
    client.post("/api/field-definitions", json={"label": "B", "tipo": "numero", "ordem": 1})
    res = client.get("/api/field-definitions")
    assert res.status_code == 200
    nomes = [c["nome"] for c in res.get_json()["campos"]]
    assert nomes == ["b", "a"]  # ordem ASC


def test_field_definition_update_e_delete(client):
    cid = client.post("/api/field-definitions", json={
        "label": "Validade", "tipo": "data"
    }).get_json()["campo"]["id_field"]

    res = client.patch(f"/api/field-definitions/{cid}", json={"label": "Data Validade"})
    assert res.status_code == 200
    assert res.get_json()["campo"]["label"] == "Data Validade"

    res = client.delete(f"/api/field-definitions/{cid}")
    assert res.status_code == 200
    assert res.get_json()["deleted"] is True

    # após soft-delete não aparece mais
    rest = client.get("/api/field-definitions").get_json()["campos"]
    assert all(c["id_field"] != cid for c in rest)


# ---------- produto CRUD ----------

def _def(client, label, tipo, **extra):
    payload = {"label": label, "tipo": tipo}
    payload.update(extra)
    return client.post("/api/field-definitions", json=payload).get_json()["campo"]


def test_produto_sem_extras_passa(client):
    res = client.post("/api/produtos", json={
        "nome": "Shampoo Automotivo", "preco": 35.5, "quantidade": 10
    })
    assert res.status_code == 201
    body = res.get_json()["produto"]
    assert body["nome"] == "Shampoo Automotivo"
    assert body["preco"] == 35.5
    assert body["extras"] == {}


def test_produto_com_extras_validos(client):
    _def(client, "Marca", "texto")
    _def(client, "Validade", "data")
    _def(client, "Categoria", "select", opcoes=["limpeza", "polimento"])

    res = client.post("/api/produtos", json={
        "nome": "Cera",
        "preco": 80,
        "quantidade": 5,
        "extras": {
            "marca": "Vonixx",
            "validade": "2027-01-01",
            "categoria": "polimento",
        }
    })
    assert res.status_code == 201
    extras = res.get_json()["produto"]["extras"]
    assert extras["marca"] == "Vonixx"
    assert extras["categoria"] == "polimento"


def test_produto_extra_obrigatorio_faltando(client):
    _def(client, "Marca", "texto", obrigatorio=True)
    res = client.post("/api/produtos", json={"nome": "X", "preco": 1})
    assert res.status_code == 400
    assert "marca" in str(res.get_json()).lower()


def test_produto_extra_desconhecido_eh_rejeitado(client):
    res = client.post("/api/produtos", json={
        "nome": "X", "preco": 1, "extras": {"campo_que_nao_existe": "abc"}
    })
    assert res.status_code == 400
    assert "campo_que_nao_existe" in str(res.get_json())


def test_produto_extra_tipo_numero_invalido(client):
    _def(client, "Peso", "numero")
    res = client.post("/api/produtos", json={
        "nome": "X", "preco": 1, "extras": {"peso": "abc"}
    })
    assert res.status_code == 400
    assert "peso" in str(res.get_json()).lower()


def test_produto_select_valor_fora_das_opcoes(client):
    _def(client, "Cat", "select", opcoes=["A", "B"])
    res = client.post("/api/produtos", json={
        "nome": "X", "preco": 1, "extras": {"cat": "C"}
    })
    assert res.status_code == 400


def test_produto_data_invalida(client):
    _def(client, "Validade", "data")
    res = client.post("/api/produtos", json={
        "nome": "X", "preco": 1, "extras": {"validade": "31/12/2025"}
    })
    assert res.status_code == 400


def test_produto_ajustar_quantidade(client):
    pid = client.post("/api/produtos", json={
        "nome": "X", "preco": 1, "quantidade": 5
    }).get_json()["produto"]["id_produto"]

    res = client.post(f"/api/produtos/{pid}/ajustar", json={"delta": 3})
    assert res.status_code == 200
    assert res.get_json()["produto"]["quantidade"] == 8

    res = client.post(f"/api/produtos/{pid}/ajustar", json={"delta": -100})
    assert res.status_code == 400  # ficaria negativa


def test_produto_listagem_pagina(client):
    for i in range(5):
        client.post("/api/produtos", json={"nome": f"P{i}", "preco": 1})
    res = client.get("/api/produtos?per_page=3&page=1")
    assert res.status_code == 200
    body = res.get_json()
    assert body["pagination"]["total"] == 5
    assert len(body["produtos"]) == 3


# ---------- módulo desligado ----------

@pytest.mark.parametrize("estoque_module", [False], indirect=True)
def test_rotas_de_estoque_404_quando_desligado(client):
    """Sem o blueprint registrado, as rotas não existem."""
    assert client.get("/api/produtos").status_code == 404
    assert client.get("/api/field-definitions").status_code == 404


@pytest.mark.parametrize(
    "business_type,estoque_module",
    [(BusinessType.GENERICO, False)],
    indirect=True,
)
def test_generico_sem_estoque_so_tem_modulos_core(client):
    body = client.get("/api/config/business").get_json()
    assert body["modules"] == []


# ============================================================
#  Integração estoque ↔ vendas (Fase 2)
# ============================================================

def _criar_cliente_e_veiculo(client):
    cli = client.post("/api/clientes", json={"nome": "C", "cpf": "1", "numero": "81"}).get_json()["cliente"]
    vei = client.post("/api/veiculos", json={"id_cliente": cli["id_cliente"], "placa": "ABC1D23"}).get_json()["veiculo"]
    return cli, vei


def test_venda_aceita_produto_como_item(client):
    cli, vei = _criar_cliente_e_veiculo(client)
    prod = client.post("/api/produtos", json={
        "nome": "Cera", "preco": 50, "quantidade": 10
    }).get_json()["produto"]

    venda = client.post("/api/vendas", json={
        "id_cliente": cli["id_cliente"], "id_veiculo": vei["id_veiculo"]
    }).get_json()["venda"]

    res = client.post(f"/api/vendas/{venda['id_venda']}/itens", json={
        "id_produto": prod["id_produto"], "quantidade": 3
    })
    assert res.status_code == 200
    itens = res.get_json()["venda"]["itens"]
    assert len(itens) == 1
    assert itens[0]["tipo"] == "produto"
    assert itens[0]["id_produto"] == prod["id_produto"]
    assert itens[0]["id_servico"] is None


def test_venda_rejeita_servico_e_produto_juntos(client):
    cli, vei = _criar_cliente_e_veiculo(client)
    prod = client.post("/api/produtos", json={"nome": "P", "preco": 1, "quantidade": 1}).get_json()["produto"]
    svc = client.post("/api/servicos", json={"nome": "S", "valor": 1}).get_json()["servico"]
    venda = client.post("/api/vendas", json={
        "id_cliente": cli["id_cliente"], "id_veiculo": vei["id_veiculo"]
    }).get_json()["venda"]

    res = client.post(f"/api/vendas/{venda['id_venda']}/itens", json={
        "id_servico": svc["id_servico"],
        "id_produto": prod["id_produto"],
        "quantidade": 1,
    })
    assert res.status_code == 400


def test_finalizar_venda_decrementa_estoque(client):
    cli, vei = _criar_cliente_e_veiculo(client)
    prod = client.post("/api/produtos", json={
        "nome": "Cera", "preco": 50, "quantidade": 10
    }).get_json()["produto"]
    venda = client.post("/api/vendas", json={
        "id_cliente": cli["id_cliente"], "id_veiculo": vei["id_veiculo"]
    }).get_json()["venda"]
    client.post(f"/api/vendas/{venda['id_venda']}/itens", json={
        "id_produto": prod["id_produto"], "quantidade": 4
    })

    res = client.post(f"/api/vendas/{venda['id_venda']}/finalizar", json={"forma_pagamento": "PIX"})
    assert res.status_code == 200

    # Estoque deve estar 10 - 4 = 6
    body = client.get(f"/api/produtos/{prod['id_produto']}").get_json()
    assert body["produto"]["quantidade"] == 6


def test_finalizar_permite_estoque_negativo(client):
    """Regra: não bloqueia mesmo se quantidade ficaria negativa (aviso só na UI)."""
    cli, vei = _criar_cliente_e_veiculo(client)
    prod = client.post("/api/produtos", json={
        "nome": "Cera", "preco": 50, "quantidade": 2
    }).get_json()["produto"]
    venda = client.post("/api/vendas", json={
        "id_cliente": cli["id_cliente"], "id_veiculo": vei["id_veiculo"]
    }).get_json()["venda"]
    client.post(f"/api/vendas/{venda['id_venda']}/itens", json={
        "id_produto": prod["id_produto"], "quantidade": 5
    })

    res = client.post(f"/api/vendas/{venda['id_venda']}/finalizar", json={"forma_pagamento": "PIX"})
    assert res.status_code == 200

    body = client.get(f"/api/produtos/{prod['id_produto']}").get_json()
    assert body["produto"]["quantidade"] == -3


def test_cancelar_venda_finalizada_devolve_estoque(client):
    cli, vei = _criar_cliente_e_veiculo(client)
    prod = client.post("/api/produtos", json={
        "nome": "X", "preco": 1, "quantidade": 10
    }).get_json()["produto"]
    venda = client.post("/api/vendas", json={
        "id_cliente": cli["id_cliente"], "id_veiculo": vei["id_veiculo"]
    }).get_json()["venda"]
    client.post(f"/api/vendas/{venda['id_venda']}/itens", json={
        "id_produto": prod["id_produto"], "quantidade": 3
    })
    client.post(f"/api/vendas/{venda['id_venda']}/finalizar", json={"forma_pagamento": "PIX"})
    assert client.get(f"/api/produtos/{prod['id_produto']}").get_json()["produto"]["quantidade"] == 7

    res = client.post(f"/api/vendas/{venda['id_venda']}/cancelar")
    assert res.status_code == 200
    assert client.get(f"/api/produtos/{prod['id_produto']}").get_json()["produto"]["quantidade"] == 10


def test_finalizar_idempotente_nao_debita_2x(client):
    cli, vei = _criar_cliente_e_veiculo(client)
    prod = client.post("/api/produtos", json={
        "nome": "X", "preco": 1, "quantidade": 10
    }).get_json()["produto"]
    venda = client.post("/api/vendas", json={
        "id_cliente": cli["id_cliente"], "id_veiculo": vei["id_veiculo"]
    }).get_json()["venda"]
    client.post(f"/api/vendas/{venda['id_venda']}/itens", json={
        "id_produto": prod["id_produto"], "quantidade": 2
    })

    client.post(f"/api/vendas/{venda['id_venda']}/finalizar", json={"forma_pagamento": "PIX"})
    client.post(f"/api/vendas/{venda['id_venda']}/finalizar", json={"forma_pagamento": "DINHEIRO"})

    body = client.get(f"/api/produtos/{prod['id_produto']}").get_json()
    assert body["produto"]["quantidade"] == 8  # debitou só 1x
