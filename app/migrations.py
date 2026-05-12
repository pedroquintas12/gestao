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
    if "produto" in inspector.get_table_names():
        _migrate_produto(db, inspector)


def _migrate_produto(db, inspector) -> None:
    """Garante coluna `codigo_barras` + índice único parcial."""
    cols = {c["name"] for c in inspector.get_columns("produto")}
    has_codigo = "codigo_barras" in cols

    indexes = {idx["name"] for idx in inspector.get_indexes("produto")}
    has_index = "ux_produto_codigo_barras" in indexes

    if has_codigo and has_index:
        return

    with db.engine.begin() as conn:
        if not has_codigo:
            conn.execute(text("ALTER TABLE produto ADD COLUMN codigo_barras VARCHAR(64)"))
            logger.info("Coluna codigo_barras adicionada em produto.")
        if not has_index:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_produto_codigo_barras "
                "ON produto(codigo_barras) WHERE codigo_barras IS NOT NULL"
            ))
            logger.info("Índice ux_produto_codigo_barras criado.")


def _migrate_venda_itens(db, inspector) -> None:
    """
    Garante:
      - coluna `id_produto` existe;
      - `id_servico` é nullable;
      - coluna `parent_item_id` existe (vínculo serviço→produto-insumo).
    """
    cols = {c["name"]: c for c in inspector.get_columns("venda_itens")}

    has_produto = "id_produto" in cols
    has_parent  = "parent_item_id" in cols
    servico_not_null = cols.get("id_servico", {}).get("nullable") is False

    if has_produto and has_parent and not servico_not_null:
        return

    logger.info(
        "Migrando venda_itens: add id_produto=%s, add parent_item_id=%s, "
        "id_servico nullable=%s",
        not has_produto, not has_parent, servico_not_null,
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
                    parent_item_id INTEGER,
                    descricao  VARCHAR(200) NOT NULL,
                    preco_unit NUMERIC(10,2) NOT NULL,
                    quantidade INTEGER NOT NULL DEFAULT 1,
                    desconto   NUMERIC(10,2) NOT NULL DEFAULT 0,
                    CONSTRAINT ck_venda_itens_xor
                        CHECK ((id_servico IS NULL) <> (id_produto IS NULL)),
                    CONSTRAINT ck_venda_itens_filho_e_produto
                        CHECK ((parent_item_id IS NULL) OR (id_produto IS NOT NULL)),
                    FOREIGN KEY(id_venda)   REFERENCES vendas(id_venda),
                    FOREIGN KEY(id_servico) REFERENCES servico(id_servico),
                    FOREIGN KEY(id_produto) REFERENCES produto(id_produto),
                    FOREIGN KEY(parent_item_id) REFERENCES venda_itens(id_item) ON DELETE CASCADE
                )
            """))
            conn.execute(text("""
                INSERT INTO venda_itens__new
                    (id_item, id_venda, id_servico, id_produto, parent_item_id,
                     descricao, preco_unit, quantidade, desconto)
                SELECT id_item, id_venda, id_servico, NULL, NULL,
                       descricao, preco_unit, quantidade, desconto
                  FROM venda_itens
            """))
            conn.execute(text("DROP TABLE venda_itens"))
            conn.execute(text("ALTER TABLE venda_itens__new RENAME TO venda_itens"))
            conn.execute(text("PRAGMA foreign_keys=on"))
        logger.info("venda_itens recriada com schema novo (XOR + parent_item_id).")
    else:
        with db.engine.begin() as conn:
            if not has_produto:
                conn.execute(text(
                    "ALTER TABLE venda_itens ADD COLUMN id_produto INTEGER "
                    "REFERENCES produto(id_produto)"
                ))
                logger.info("Coluna id_produto adicionada em venda_itens.")
            if not has_parent:
                conn.execute(text(
                    "ALTER TABLE venda_itens ADD COLUMN parent_item_id INTEGER "
                    "REFERENCES venda_itens(id_item)"
                ))
                logger.info("Coluna parent_item_id adicionada em venda_itens.")
