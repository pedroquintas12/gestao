# tests/test_clientes.py
def test_criar_listar_clientes(client):
    # cria
    res = client.post("/api/clientes", json={"nome":"Fulano","cpf":"000","numero":"81"})
    assert res.status_code == 201
    cli = res.get_json()["cliente"]
    assert cli["nome"] == "Fulano"

    # lista
    res = client.get("/api/clientes?q=Fula&page=1&per_page=24")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["clientes"]) >= 1
    assert "pagination" in data

def test_paginacao_clientes_limites(client):
    # cria vários
    for i in range(60):
        client.post("/api/clientes", json={"nome":f"C{i}","cpf":f"{i}","numero":"81"})
    # per_page clamped a 100 (aqui 5)
    res = client.get("/api/clientes?per_page=5&page=3")
    assert res.status_code == 200
    pag = res.get_json()["pagination"]
    assert pag["per_page"] == 5
    assert pag["page"] == 3
