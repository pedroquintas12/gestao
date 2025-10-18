# tests/test_vendas.py
def _cria_base(client):
    cli = client.post("/api/clientes", json={"nome":"Cliente 1","cpf":"1","numero":"81"}).get_json()["cliente"]
    vei = client.post("/api/veiculos", json={"id_cliente":cli["id_cliente"], "placa":"KLM1N23"}).get_json()["veiculo"]
    svc = client.post("/api/servicos", json={"nome":"Lavagem","valor":100}).get_json()["servico"]
    return cli, vei, svc

def test_fluxo_venda_com_item_e_finalizacao_gera_caixa(client):
    cli, vei, svc = _cria_base(client)

    # cria venda
    res = client.post("/api/vendas", json={
        "id_cliente": cli["id_cliente"],
        "id_veiculo": vei["id_veiculo"],
        "descricao": "Orc 001"
    })
    assert res.status_code == 201
    venda = res.get_json()["venda"]
    vid = venda["id_venda"]

    # adiciona item
    res = client.post(f"/api/vendas/{vid}/itens", json={"id_servico": svc["id_servico"], "quantidade": 2})
    assert res.status_code == 200
    venda = res.get_json()["venda"]
    assert venda["total"] == 200.0  # 2 * 100

    # finalizar
    res = client.post(f"/api/vendas/{vid}/finalizar", json={"forma_pagamento":"PIX","descricao":"pg à vista"})
    assert res.status_code == 200
    venda = res.get_json()["venda"]
    assert venda["status"] == "FINALIZADA"
    assert venda["pagamento"] == "PIX"

    # caixa do dia deve ter 1 lançamento com valor 200
    from datetime import date
    today = date.today().isoformat()
    c = client.get(f"/api/caixa?data={today}").get_json()
    assert c["total_valor"] == 200.0 or c.get("total") == 200.0  # compat com versões
    assert any(l["venda_id"] == vid and l["valor"] == 200.0 for l in c.get("lancamentos", c.get("items", [])))

def test_listar_vendas_com_paginacao_e_filtro(client):
    cli, vei, svc = _cria_base(client)
    # cria 12 vendas rápidas
    for i in range(12):
        v = client.post("/api/vendas", json={
            "id_cliente": cli["id_cliente"],
            "id_veiculo": vei["id_veiculo"],
            "descricao": f"venda {i}"
        }).get_json()["venda"]
        client.post(f"/api/vendas/{v['id_venda']}/itens", json={"id_servico": svc["id_servico"]})
        if i % 2 == 0:
            client.post(f"/api/vendas/{v['id_venda']}/finalizar", json={"forma_pagamento":"DINHEIRO"})

    # pagina 2, per_page 5
    res = client.get("/api/vendas?per_page=5&page=2")
    assert res.status_code == 200
    data = res.get_json()
    assert data["pagination"]["page"] == 2
    assert len(data["vendas"]) <= 5

    # filtro por status FINALIZADA
    res = client.get("/api/vendas?status=FINALIZADA")
    assert res.status_code == 200
    vs = res.get_json()["vendas"]
    assert all(v["status"] == "FINALIZADA" for v in vs)
