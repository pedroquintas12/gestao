"""
Testes da modularização por ramo de negócio.

- Ramo LAVAJATO (default): módulo `veiculo` ativo, venda exige id_veiculo.
- Ramo GENERICO: módulo `veiculo` desligado, rotas de veículo retornam 404,
  venda pode ser criada e finalizada sem veículo.
"""
import pytest

from enums.business import BusinessType


# ---------- LAVAJATO (default) ----------

def test_lavajato_endpoint_business_config(client):
    res = client.get("/api/config/business")
    assert res.status_code == 200
    body = res.get_json()
    assert body["type"] == "lavajato"
    assert "veiculo" in body["modules"]
    assert "estoque" in body["modules"]


def test_lavajato_venda_sem_veiculo_retorna_400(client):
    cli = client.post(
        "/api/clientes",
        json={"nome": "C1", "cpf": "1", "numero": "81"},
    ).get_json()["cliente"]

    res = client.post(
        "/api/vendas",
        json={"id_cliente": cli["id_cliente"], "descricao": "sem veículo"},
    )
    assert res.status_code == 400
    body = res.get_json()
    # mensagem do api_error vai em "details" (vendaService.valid_payload)
    assert "id_veiculo" in str(body)


# ---------- GENERICO ----------

@pytest.mark.parametrize("business_type", [BusinessType.GENERICO], indirect=True)
def test_generico_endpoint_business_config(client):
    res = client.get("/api/config/business")
    assert res.status_code == 200
    body = res.get_json()
    assert body["type"] == "generico"
    assert "veiculo" not in body["modules"]
    # estoque é independente do ramo — vem ativo por padrão
    assert "estoque" in body["modules"]


@pytest.mark.parametrize("estoque_module", [False], indirect=True)
def test_estoque_pode_ser_desligado_em_qualquer_ramo(client):
    """ENABLE_ESTOQUE=false (simulado via override) desliga o módulo."""
    body = client.get("/api/config/business").get_json()
    assert "estoque" not in body["modules"]


@pytest.mark.parametrize("business_type", [BusinessType.GENERICO], indirect=True)
def test_generico_rotas_de_veiculo_nao_existem(client):
    """Blueprint de veículo não é registrado quando o módulo está desligado."""
    res = client.get("/api/veiculos")
    assert res.status_code == 404


@pytest.mark.parametrize("business_type", [BusinessType.GENERICO], indirect=True)
def test_generico_fluxo_venda_sem_veiculo(client):
    cli = client.post(
        "/api/clientes",
        json={"nome": "C Generico", "cpf": "9", "numero": "81"},
    ).get_json()["cliente"]
    svc = client.post(
        "/api/servicos",
        json={"nome": "Consulta", "valor": 200},
    ).get_json()["servico"]

    res = client.post(
        "/api/vendas",
        json={"id_cliente": cli["id_cliente"], "descricao": "atendimento"},
    )
    assert res.status_code == 201
    venda = res.get_json()["venda"]
    assert venda["id_veiculo"] is None

    res = client.post(
        f"/api/vendas/{venda['id_venda']}/itens",
        json={"id_servico": svc["id_servico"], "quantidade": 1},
    )
    assert res.status_code == 200
    assert res.get_json()["venda"]["total"] == 200.0

    res = client.post(
        f"/api/vendas/{venda['id_venda']}/finalizar",
        json={"forma_pagamento": "PIX"},
    )
    assert res.status_code == 200
    assert res.get_json()["venda"]["status"] == "FINALIZADA"


@pytest.mark.parametrize("business_type", [BusinessType.GENERICO], indirect=True)
def test_generico_listagem_de_vendas_sem_veiculo(client):
    cli = client.post(
        "/api/clientes",
        json={"nome": "C", "cpf": "9", "numero": "81"},
    ).get_json()["cliente"]
    for i in range(3):
        client.post(
            "/api/vendas",
            json={"id_cliente": cli["id_cliente"], "descricao": f"v{i}"},
        )

    res = client.get("/api/vendas?per_page=10")
    assert res.status_code == 200
    data = res.get_json()
    assert data["pagination"]["total"] == 3
    assert all(v["id_veiculo"] is None for v in data["vendas"])
