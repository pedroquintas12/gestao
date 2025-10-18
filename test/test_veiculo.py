# tests/test_veiculos.py
def test_criar_listar_veiculos(client):
    # cria cliente
    c = client.post("/api/clientes", json={"nome":"Dono","cpf":"123","numero":"81"}).get_json()["cliente"]
    # cria veiculo
    res = client.post("/api/veiculos", json={"id_cliente": c["id_cliente"], "placa":"JJJ0A00"})
    assert res.status_code == 201
    v = res.get_json()["veiculo"]
    assert v["placa"] == "JJJ0A00"

    # lista filtrando por id_cliente
    res = client.get(f"/api/veiculos?id_cliente={c['id_cliente']}")
    assert res.status_code == 200
    items = res.get_json()["veiculos"]
    assert any(x["placa"] == "JJJ0A00" for x in items)

def test_busca_placa_e_paginacao(client):
    # cria cliente e vários veículos
    c = client.post("/api/clientes", json={"nome":"X","cpf":"x","numero":"81"}).get_json()["cliente"]
    for i in range(15):
        client.post("/api/veiculos", json={"id_cliente": c["id_cliente"], "placa": f"AAA{i:02d}B{i%10}"})
    # busca por q
    res = client.get("/api/veiculos?q=AAA&per_page=5&page=2")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["veiculos"]) <= 5
    assert data["pagination"]["page"] == 2
