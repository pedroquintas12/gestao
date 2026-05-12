"""
Vínculo produto→item-serviço dentro de uma venda:
- subitem não soma no total;
- estoque é debitado na finalização;
- remoção do pai cascateia para o filho;
- filtros admin por id_servico/id_produto pegam pais e filhos.
"""


def _cria_base(client):
    cli = client.post(
        "/api/clientes",
        json={"nome": "Cliente Vinc", "cpf": "999", "numero": "81"},
    ).get_json()["cliente"]
    vei = client.post(
        "/api/veiculos",
        json={"id_cliente": cli["id_cliente"], "placa": "VINC123"},
    ).get_json()["veiculo"]
    svc = client.post(
        "/api/servicos", json={"nome": "Lavagem premium", "valor": 100}
    ).get_json()["servico"]
    prod = client.post(
        "/api/produtos",
        json={"nome": "Shampoo", "preco": 35, "quantidade": 10},
    ).get_json()["produto"]
    return cli, vei, svc, prod


def _abre_venda(client, cli, vei):
    return client.post(
        "/api/vendas",
        json={
            "id_cliente": cli["id_cliente"],
            "id_veiculo": vei["id_veiculo"],
            "descricao": "Venda Vinc",
        },
    ).get_json()["venda"]


def test_subitem_nao_soma_no_total(client):
    cli, vei, svc, prod = _cria_base(client)
    venda = _abre_venda(client, cli, vei)
    vid = venda["id_venda"]

    # adiciona serviço
    r = client.post(
        f"/api/vendas/{vid}/itens",
        json={"id_servico": svc["id_servico"], "quantidade": 1},
    )
    assert r.status_code == 200
    pai = r.get_json()["venda"]["itens"][0]
    parent_item_id = pai["id_item"]

    # vincula produto como subitem
    r = client.post(
        f"/api/vendas/{vid}/itens",
        json={
            "id_produto": prod["id_produto"],
            "quantidade": 2,
            "parent_item_id": parent_item_id,
        },
    )
    assert r.status_code == 200
    venda = r.get_json()["venda"]
    # total continua só com o valor do serviço
    assert venda["total"] == 100.0
    # filho está presente com parent_item_id setado
    itens = venda["itens"]
    filho = next(i for i in itens if i["parent_item_id"] == parent_item_id)
    assert filho["id_produto"] == prod["id_produto"]
    assert filho["quantidade"] == 2
    assert filho["subtotal"] == 0.0


def test_finalizar_debita_estoque_do_subitem(client):
    cli, vei, svc, prod = _cria_base(client)
    venda = _abre_venda(client, cli, vei)
    vid = venda["id_venda"]

    pai = client.post(
        f"/api/vendas/{vid}/itens",
        json={"id_servico": svc["id_servico"], "quantidade": 1},
    ).get_json()["venda"]["itens"][0]

    client.post(
        f"/api/vendas/{vid}/itens",
        json={
            "id_produto": prod["id_produto"],
            "quantidade": 3,
            "parent_item_id": pai["id_item"],
        },
    )

    r = client.post(
        f"/api/vendas/{vid}/finalizar", json={"forma_pagamento": "PIX"}
    )
    assert r.status_code == 200
    assert r.get_json()["venda"]["total"] == 100.0  # estoque não afeta total

    p = client.get(f"/api/produtos/{prod['id_produto']}").get_json()["produto"]
    assert p["quantidade"] == 10 - 3


def test_filho_nao_pode_ser_servico(client):
    cli, vei, svc, _ = _cria_base(client)
    venda = _abre_venda(client, cli, vei)
    vid = venda["id_venda"]
    pai = client.post(
        f"/api/vendas/{vid}/itens",
        json={"id_servico": svc["id_servico"]},
    ).get_json()["venda"]["itens"][0]

    r = client.post(
        f"/api/vendas/{vid}/itens",
        json={
            "id_servico": svc["id_servico"],
            "parent_item_id": pai["id_item"],
        },
    )
    assert r.status_code == 400


def test_filho_pai_precisa_ser_servico(client):
    cli, vei, _, prod = _cria_base(client)
    venda = _abre_venda(client, cli, vei)
    vid = venda["id_venda"]

    # pai-produto (não permitido como pai)
    pai_prod = client.post(
        f"/api/vendas/{vid}/itens",
        json={"id_produto": prod["id_produto"]},
    ).get_json()["venda"]["itens"][0]

    r = client.post(
        f"/api/vendas/{vid}/itens",
        json={
            "id_produto": prod["id_produto"],
            "parent_item_id": pai_prod["id_item"],
        },
    )
    assert r.status_code == 400


def test_remover_pai_remove_filhos(client):
    cli, vei, svc, prod = _cria_base(client)
    venda = _abre_venda(client, cli, vei)
    vid = venda["id_venda"]

    pai = client.post(
        f"/api/vendas/{vid}/itens",
        json={"id_servico": svc["id_servico"]},
    ).get_json()["venda"]["itens"][0]

    client.post(
        f"/api/vendas/{vid}/itens",
        json={
            "id_produto": prod["id_produto"],
            "quantidade": 1,
            "parent_item_id": pai["id_item"],
        },
    )

    r = client.delete(f"/api/vendas/{vid}/itens/{pai['id_item']}")
    assert r.status_code == 200
    itens = r.get_json()["venda"]["itens"]
    assert itens == []


def test_filtro_admin_por_servico(client):
    cli, vei, svc, _ = _cria_base(client)
    outro_svc = client.post(
        "/api/servicos", json={"nome": "Polimento", "valor": 200}
    ).get_json()["servico"]

    v1 = _abre_venda(client, cli, vei)
    client.post(
        f"/api/vendas/{v1['id_venda']}/itens",
        json={"id_servico": svc["id_servico"]},
    )

    v2 = _abre_venda(client, cli, vei)
    client.post(
        f"/api/vendas/{v2['id_venda']}/itens",
        json={"id_servico": outro_svc["id_servico"]},
    )

    r = client.get(f"/api/vendas?id_servico={svc['id_servico']}")
    assert r.status_code == 200
    ids = [v["id_venda"] for v in r.get_json()["vendas"]]
    assert v1["id_venda"] in ids
    assert v2["id_venda"] not in ids


def test_filtro_admin_por_produto_pega_direto_e_subitem(client):
    cli, vei, svc, prod = _cria_base(client)

    # venda 1: produto como item direto
    v1 = _abre_venda(client, cli, vei)
    client.post(
        f"/api/vendas/{v1['id_venda']}/itens",
        json={"id_produto": prod["id_produto"], "quantidade": 1},
    )

    # venda 2: produto vinculado como subitem de um serviço
    v2 = _abre_venda(client, cli, vei)
    pai = client.post(
        f"/api/vendas/{v2['id_venda']}/itens",
        json={"id_servico": svc["id_servico"]},
    ).get_json()["venda"]["itens"][0]
    client.post(
        f"/api/vendas/{v2['id_venda']}/itens",
        json={
            "id_produto": prod["id_produto"],
            "parent_item_id": pai["id_item"],
            "quantidade": 1,
        },
    )

    # venda 3: sem o produto
    v3 = _abre_venda(client, cli, vei)
    client.post(
        f"/api/vendas/{v3['id_venda']}/itens",
        json={"id_servico": svc["id_servico"]},
    )

    r = client.get(f"/api/vendas?id_produto={prod['id_produto']}")
    assert r.status_code == 200
    ids = set(v["id_venda"] for v in r.get_json()["vendas"])
    assert v1["id_venda"] in ids
    assert v2["id_venda"] in ids
    assert v3["id_venda"] not in ids
