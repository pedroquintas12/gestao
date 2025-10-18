# tests/test_servicos.py
def test_criar_listar_servicos(client):
    # cria
    res = client.post("/api/servicos", json={"nome": "Enceramento", "valor": 199.9})
    assert res.status_code == 201
    body = res.get_json()
    assert "servico" in body
    sid = body["servico"]["id_servico"]

    # lista com paginação padrão
    res = client.get("/api/servicos")
    assert res.status_code == 200
    data = res.get_json()
    assert "servicos" in data and "pagination" in data
    assert data["pagination"]["page"] == 1

    # filtro q
    res = client.get("/api/servicos?q=Encer")
    assert res.status_code == 200
    assert len(res.get_json()["servicos"]) >= 1

def test_paginacao_servicos(client):
    # cria vários
    for i in range(35):
        client.post("/api/servicos", json={"nome": f"S{i}", "valor": i+1})
    # per_page=10, page=2
    res = client.get("/api/servicos?per_page=10&page=2")
    assert res.status_code == 200
    pag = res.get_json()["pagination"]
    assert pag["per_page"] == 10
    assert pag["page"] == 2
    assert pag["has_next"] is True
