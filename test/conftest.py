# tests/conftest.py
import os
import tempfile
import pytest

from app import create_app
from config.db import db

# === Importa MODELS (garante que create_all crie as tabelas) ===
from model.servicoModel import servico
from model.clienteModel import cliente
from model.veiculoModel import veiculo
from model.vendaModel import venda, VendaItem
from model.caixaModel import caixa_lancamento




@pytest.fixture()
def app():
    """App isolado por teste com SQLite em arquivo temporário."""
    db_fd, db_path = tempfile.mkstemp(prefix="test_db_", suffix=".sqlite")

    app = create_app()  # <- sem argumentos

    # Atualiza configurações de teste
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )


    # Banco limpo para este teste
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

    yield app

    # Teardown
    with app.app_context():
        db.session.remove()
        db.drop_all()

    os.close(db_fd)
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture()
def client(app):
    return app.test_client()


# =======================
# Fixtures de SEED
# =======================
@pytest.fixture()
def seed_servicos(app):
    with app.app_context():
        s1 = servico(nome="Lavagem Simples", valor=50.00)
        s2 = servico(nome="Lavagem Completa", valor=120.00)
        s3 = servico(nome="Polimento", valor=300.00)
        db.session.add_all([s1, s2, s3])
        db.session.commit()
        return [s1, s2, s3]


@pytest.fixture()
def seed_clientes(app):
    with app.app_context():
        c1 = cliente(nome="João Silva", cpf="111.111.111-11", numero="81999990001")
        c2 = cliente(nome="Maria Souza", cpf="222.222.222-22", numero="81999990002")
        db.session.add_all([c1, c2])
        db.session.commit()
        return [c1, c2]


@pytest.fixture()
def seed_veiculos(app, seed_clientes):
    c1, c2 = seed_clientes
    with app.app_context():
        v1 = veiculo(id_cliente=c1.id_cliente, placa="ABC1D23",
                     kilometragem=10000, observacao="ok")
        v2 = veiculo(id_cliente=c2.id_cliente, placa="EFG4H56",
                     kilometragem=20000, observacao="ok")
        db.session.add_all([v1, v2])
        db.session.commit()
        return [v1, v2]
