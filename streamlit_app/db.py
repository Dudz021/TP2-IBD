"""Camada de acesso ao banco SQLite `contratos.db`.

Responsável por localizar o arquivo do banco, abrir a conexão (em cache) e
executar consultas devolvendo um ``pandas.DataFrame``. Toda a interação com o
SQLite passa por aqui — o restante do app não conhece detalhes de conexão.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

# Locais onde o banco pode estar, em ordem de preferência.
_CANDIDATOS = [
    Path(__file__).resolve().parent.parent / "contratos.db",  # raiz do repositório
    Path(__file__).resolve().parent / "contratos.db",          # dentro de streamlit_app/
    Path.cwd() / "contratos.db",                               # diretório de execução
]

# Tabelas do modelo, na ordem em que fazem sentido para exibição.
TABELAS = [
    "contrato",
    "versao_contrato",
    "participacao",
    "empresa",
    "servico",
    "informe",
    "acordao",
    "despacho",
    "interconexao",
    "compartilhamento",
    "ran_sharing",
    "mvno",
]


def caminho_banco() -> Path | None:
    """Retorna o primeiro `contratos.db` encontrado, ou ``None``."""
    for candidato in _CANDIDATOS:
        if candidato.exists():
            return candidato
    return None


@st.cache_resource(show_spinner=False)
def _conectar(path_str: str) -> sqlite3.Connection:
    """Abre (uma única vez) a conexão SQLite somente-leitura."""
    con = sqlite3.connect(path_str, check_same_thread=False)
    return con


@st.cache_data(show_spinner=False, ttl=3600)
def executar(sql: str, params_items: tuple = ()) -> pd.DataFrame:
    """Executa ``sql`` e devolve um ``DataFrame``.

    ``params_items`` é uma tupla de pares ``(nome, valor)`` (ordenada para ser
    "hasheável" pelo cache do Streamlit). Os parâmetros são vinculados de forma
    segura via *named parameters* do SQLite (``:nome``), evitando injeção de SQL.
    """
    path = caminho_banco()
    if path is None:
        raise FileNotFoundError(
            "Banco `contratos.db` não encontrado. Coloque-o na raiz do projeto."
        )
    con = _conectar(str(path))
    cursor = con.execute(sql, dict(params_items))
    colunas = [d[0] for d in cursor.description] if cursor.description else []
    linhas = cursor.fetchall()
    return pd.DataFrame(linhas, columns=colunas)


@st.cache_data(show_spinner=False, ttl=3600)
def contagens() -> dict[str, int]:
    """Número de tuplas de cada tabela (para os indicadores da visão geral)."""
    resultado: dict[str, int] = {}
    for tabela in TABELAS:
        df = executar(f"SELECT COUNT(*) AS n FROM {tabela}")
        resultado[tabela] = int(df["n"].iloc[0]) if not df.empty else 0
    return resultado


def total_tuplas() -> int:
    """Soma de tuplas de todas as tabelas modeladas."""
    return sum(contagens().values())
