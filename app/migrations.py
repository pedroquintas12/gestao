"""
Migrações leves chamadas após `db.create_all()`.

Não substituem Alembic — apenas tratam casos pontuais onde:
- create_all() não cria coluna nova em tabela existente;
- create_all() não consegue alterar nullable de coluna existente.

Hoje cobrem só SQLite. Idempotentes.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

from config.logger import get_logger

logger = get_logger(__name__)


def run_migrations(db) -> None:
    engine = db.engine
    inspector = inspect(engine)
    if "venda_itens" in inspector.get_table_names():
        _migrate_venda_itens(db, inspector)


def _migrate_venda_itens(db, inspector) -> None:
    """
    Garante:
      - coluna `id_produto` existe;
      - `id_servico` é nullable.
    """
    cols = {c["name"]: c for c in inspector.get_columns("venda_itens")}

    has_produto = "id_produto" in cols
    servico_not_null = cols.get("id_servico", {}).get("nullable") is False

    if has_produto and not servico_not_null:
        return

    logger.info(
        "Migrando venda_itens: add id_produto=%s, id_servico nullable=%s",
        not has_produto, servico_not_null,
    )

    if servico_not_null:
        # SQLite não tem ALTER COLUMN — precisamos recriar a tabela.
        with db.engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=off"))
            conn.execute(text("""
                CREATE TABLE venda_itens__new (
                    id_item    INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_venda   INTEGER NOT NULL,
                    id_servico INTEGER,
                    id_produto INTEGER,
                    descricao  VARCHAR(200) NOT NULL,
                    preco_unit NUMERIC(10,2) NOT NULL,
                    quantidade INTEGER NOT NULL DEFAULT 1,
                    desconto   NUMERIC(10,2) NOT NULL DEFAULT 0,
                    CONSTRAINT ck_venda_itens_xor
                        CHECK ((id_servico IS NULL) <> (id_produto IS NULL)),
                    FOREIGN KEY(id_venda)   REFERENCES vendas(id_venda),
                    FOREIGN KEY(id_servico) REFERENCES servico(id_servico),
                    FOREIGN KEY(id_produto) REFERENCES produto(id_produto)
                )
            """))
            conn.execute(text("""
                INSERT INTO venda_itens__new
                    (id_item, id_venda, id_servico, id_produto,
                     descricao, preco_unit, quantidade, desconto)
                SELECT id_item, id_venda, id_servico, NULL,
                       descricao, preco_unit, quantidade, desconto
                  FROM venda_itens
            """))
            conn.execute(text("DROP TABLE venda_itens"))
            conn.execute(text("ALTER TABLE venda_itens__new RENAME TO venda_itens"))
            conn.execute(text("PRAGMA foreign_keys=on"))
        logger.info("venda_itens recriada com schema novo (XOR servico/produto).")
    elif not has_produto:
        with db.engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE venda_itens ADD COLUMN id_produto INTEGER "
                "REFERENCES produto(id_produto)"
            ))
        logger.info("Coluna id_produto adicionada em venda_itens.")
