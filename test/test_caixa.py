# tests/test_caixa.py
from datetime import date, timedelta

def test_caixa_paginado_e_periodo(client):
    # prepara base: cria venda finalizada 3x
    c = client.post("/api/clientes", json={"nome":"Pagador","cpf":"x","numero":"81"}).get_json()["cliente"]
    v = client.post("/api/veiculos", json={"id_cliente": c["id_cliente"], "placa":"ZZZ9Z99"}).get_json()["veiculo"]
    s = client.post("/api/servicos", json={"nome":"Rápido","valor":10}).get_json()["servico"]

    for _ in range(3):
        vd = client.post("/api/vendas", json={"id_cliente": c["id_cliente"], "id_veiculo": v["id_veiculo"]}).get_json()["venda"]
        client.post(f"/api/vendas/{vd['id_venda']}/itens", json={"id_servico": s["id_servico"], "quantidade": 1})
        client.post(f"/api/vendas/{vd['id_venda']}/finalizar", json={"forma_pagamento":"PIX"})

    today = date.today().isoformat()
    res = client.get(f"/api/caixa?data={today}&per_page=2&page=1")
    assert res.status_code == 200
    data = res.get_json()
    assert "lancamentos" in data
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["has_next"] in (True, False)

    # período
    res = client.get(f"/api/caixa?data_ini={today}&data_fim={today}&per_page=10&page=1")
    assert res.status_code == 200
    data = res.get_json()
    assert data["pagination"]["total"] >= 3
    assert data["total_valor"] >= 30.0
