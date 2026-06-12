"""Dashboard ANATEL — Contratos (TP2 / DCC011).

App Streamlit genérico: lê as consultas declaradas em queries.py
e renderiza automaticamente explicação, SQL, parâmetros interativos, tabela,
gráfico, análise e download. Para mudar as consultas, edite apenas queries.py.

Executar:
    streamlit run streamlit_app/app.py
"""
from __future__ import annotations

import re

import pandas as pd
import plotly.express as px
import streamlit as st

import db
import queries as Q

# --------------------------------------------------------------------------- #
# Configuração da página
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Contratos ANATEL · TP2",
    layout="wide",
    initial_sidebar_state="expanded",
)

PALETA = [
    "#2E86DE", "#16A085", "#E67E22", "#8E44AD", "#E74C3C",
    "#1ABC9C", "#F39C12", "#27AE60", "#C0392B", "#2C3E50",
]

# --------------------------------------------------------------------------- #
# Estilo (CSS)
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
      .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1250px; }

      /* Hero */
      .hero {
        background: linear-gradient(120deg, #0A3D62 0%, #1B6CA8 55%, #16A085 100%);
        color: #fff; padding: 2.1rem 2.3rem; border-radius: 18px;
        box-shadow: 0 12px 30px rgba(10,61,98,.25); margin-bottom: 1.6rem;
      }
      .hero h1 { color:#fff; font-size: 2.05rem; margin: 0 0 .35rem 0; font-weight: 800; }
      .hero p  { color: #eaf3fb; font-size: 1.02rem; margin: 0; max-width: 820px; }

      /* Chips de categoria */
      .chip {
        display:inline-block; padding: .22rem .7rem; border-radius: 999px;
        font-size: .76rem; font-weight: 700; color:#fff; letter-spacing:.2px;
      }

      /* Cabeçalho de consulta */
      .q-title { font-size: 1.55rem; font-weight: 800; color:#0A3D62; margin:.2rem 0 .1rem 0; }
      .q-num   { color:#7F8C8D; font-weight:700; font-size:.9rem; }

      /* Callouts */
      .callout {
        border-left: 5px solid #2E86DE; background:#F4F8FD;
        padding: .85rem 1.1rem; border-radius: 10px; margin:.4rem 0 1rem 0;
      }
      .callout.insight { border-left-color:#16A085; background:#F1FBF8; }

      /* Botões do menu lateral */
      section[data-testid="stSidebar"] .stButton button {
        text-align:left; justify-content:flex-start; font-weight:600;
        border-radius: 10px; border: 1px solid transparent;
      }
      section[data-testid="stSidebar"] .stButton button:hover { border-color:#cdd9e5; }

      /* Métricas */
      div[data-testid="stMetric"] {
        background:#fff; border:1px solid #e7eef6; border-radius:14px;
        padding: .8rem 1rem; box-shadow: 0 2px 8px rgba(20,40,70,.04);
      }
      div[data-testid="stMetricValue"] { color:#0A3D62; }

      .cat-head { font-size:.74rem; font-weight:800; text-transform:uppercase;
                  letter-spacing:.6px; color:#90a4b8; margin:.9rem 0 .15rem .2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Helpers: parâmetros -> SQL e renderização de gráficos
# --------------------------------------------------------------------------- #
def coletar_parametros(consulta: Q.Consulta) -> dict:
    """Desenha os widgets de uma consulta e devolve {nome: valor}."""
    valores: dict = {}
    if not consulta.parametros:
        return valores
    cols = st.columns(min(len(consulta.parametros), 3))
    for i, p in enumerate(consulta.parametros):
        with cols[i % len(cols)]:
            if p.tipo == "select":
                idx = p.opcoes.index(p.padrao) if p.padrao in p.opcoes else 0
                valores[p.nome] = st.selectbox(p.rotulo, p.opcoes, index=idx, help=p.ajuda or None)
            elif p.tipo == "multiselect":
                valores[p.nome] = st.multiselect(p.rotulo, p.opcoes, default=p.padrao, help=p.ajuda or None)
            elif p.tipo == "slider":
                valores[p.nome] = st.slider(
                    p.rotulo, min_value=p.minimo, max_value=p.maximo,
                    value=p.padrao, step=p.passo, help=p.ajuda or None,
                )
    return valores


def montar_sql(consulta: Q.Consulta, valores: dict) -> tuple[str, tuple]:
    """Substitui os parâmetros :nome e devolve (sql, params hasheáveis).

    Vínculo seguro via named parameters do SQLite. Listas (multiselect) são
    expandidas em uma cláusula IN (:n_0, :n_1, ...).
    """
    sql = consulta.sql
    params: dict = {}
    for p in consulta.parametros:
        valor = valores.get(p.nome, p.padrao)
        token = re.compile(rf":{re.escape(p.nome)}\b")
        if p.tipo == "multiselect":
            vals = list(valor) if valor else []
            if not vals:
                sql = token.sub("(NULL)", sql)  # nenhuma opção -> nenhum resultado
            else:
                nomes = [f"{p.nome}_{i}" for i in range(len(vals))]
                sql = token.sub("(" + ", ".join(f":{n}" for n in nomes) + ")", sql)
                params.update(dict(zip(nomes, vals)))
        else:
            params[p.nome] = valor
    return sql, tuple(sorted(params.items()))


def _preparar_grafico(df: pd.DataFrame, g: Q.Grafico) -> tuple[pd.DataFrame, str]:
    """Aplica transformação/agregação opcional antes de plotar."""
    d = df.copy()
    if g.x_transform == "ano" and g.x in d.columns:
        d[g.x] = d[g.x].astype(str).str.slice(0, 4)
        d = d[d[g.x].str.fullmatch(r"\d{4}")]
    ycol = g.y or "qtd"
    if g.agg == "count":
        grupo = [c for c in (g.x, g.cor) if c]
        d = d.groupby(grupo, dropna=False).size().reset_index(name=ycol)
    elif g.agg in ("sum", "mean") and g.y:
        grupo = [c for c in (g.x, g.cor) if c]
        d = getattr(d.groupby(grupo, dropna=False)[g.y], g.agg)().reset_index()
        ycol = g.y
    else:
        ycol = g.y or ycol
    if g.ordenar and ycol in d.columns:
        d = d.sort_values(ycol, ascending=False)
    if g.topn and not g.cor:
        d = d.head(g.topn)
    return d, ycol


def render_grafico(df: pd.DataFrame, g: Q.Grafico | None) -> None:
    """Renderiza o gráfico declarado (se houver) usando Plotly."""
    if not g or not g.tipo or df.empty:
        return
    d, ycol = _preparar_grafico(df, g)
    if d.empty or g.x not in d.columns or ycol not in d.columns:
        return
    base = dict(template="plotly_white", color_discrete_sequence=PALETA)
    altura = 440

    if g.tipo == "bar":
        fig = px.bar(d, x=g.x, y=ycol, color=g.cor, **base)
    elif g.tipo == "barh":
        d = d.sort_values(ycol, ascending=True)
        altura = max(440, 26 * len(d))
        fig = px.bar(d, x=ycol, y=g.x, orientation="h", color=g.cor, **base)
    elif g.tipo == "line":
        fig = px.line(d, x=g.x, y=ycol, color=g.cor, markers=True, **base)
    elif g.tipo == "area":
        fig = px.area(d, x=g.x, y=ycol, color=g.cor, **base)
    elif g.tipo == "pie":
        fig = px.pie(d, names=g.x, values=ycol, hole=0.45, **base)
    elif g.tipo == "treemap":
        fig = px.treemap(d, path=[g.x], values=ycol, **base)
    else:
        return

    fig.update_layout(
        title=dict(text=g.titulo, font=dict(size=16, color="#0A3D62")),
        xaxis_title=g.rotulo_x or None,
        yaxis_title=g.rotulo_y or None,
        margin=dict(t=58, l=10, r=10, b=10),
        height=altura,
        legend_title_text=g.cor or "",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch")


def chip(categoria: str) -> str:
    cor = Q.CATEGORIAS.get(categoria, "#7F8C8D")
    return f'<span class="chip" style="background:{cor}">{categoria}</span>'


# --------------------------------------------------------------------------- #
# Navegação (menu lateral)
# --------------------------------------------------------------------------- #
# A página atual também vive na URL (?p=...), tornando os links compartilháveis.
if "pagina" not in st.session_state:
    st.session_state.pagina = st.query_params.get("p", "home")


def _ir(pagina: str) -> None:
    st.session_state.pagina = pagina
    st.query_params["p"] = pagina


def sidebar() -> None:
    with st.sidebar:
        st.markdown("### Contratos ANATEL")
        st.caption("TP2 · Introdução a Banco de Dados (DCC011)")
        st.divider()

        st.button("Visão geral", on_click=_ir, args=("home",),
                  width="stretch",
                  type="primary" if st.session_state.pagina == "home" else "secondary")

        for categoria, consultas in Q.por_categoria().items():
            if not consultas:
                continue
            st.markdown(f'<div class="cat-head">{categoria}</div>', unsafe_allow_html=True)
            for c in consultas:
                ativo = st.session_state.pagina == c.id
                st.button(
                    f"{c.numero}. {c.titulo}",
                    on_click=_ir, args=(c.id,), width="stretch",
                    type="primary" if ativo else "secondary",
                )

        st.markdown('<div class="cat-head">Ferramentas</div>', unsafe_allow_html=True)
        st.button("Console SQL", on_click=_ir, args=("console",),
                  width="stretch",
                  type="primary" if st.session_state.pagina == "console" else "secondary")

        st.divider()
        path = db.caminho_banco()
        if path:
            mb = path.stat().st_size / 1e6
            st.caption(f"{path.name} · {mb:.1f} MB")
        else:
            st.error("Banco contratos.db não encontrado.")


# --------------------------------------------------------------------------- #
# Páginas
# --------------------------------------------------------------------------- #
def pagina_home() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>Contratos da ANATEL</h1>
          <p>Exploração interativa de quatro famílias de contratos do setor de
          telecomunicações — interconexão, compartilhamento de infraestrutura,
          credenciamento de MVNO e RAN Sharing — modeladas em um banco relacional
          normalizado a partir de dados abertos governamentais.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cont = db.contagens()
    total = sum(cont.values())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tuplas no total", f"{total:,}".replace(",", "."))
    c2.metric("Contratos", f"{cont['contrato']:,}".replace(",", "."))
    c3.metric("Empresas", f"{cont['empresa']:,}".replace(",", "."))
    c4.metric("Participações", f"{cont['participacao']:,}".replace(",", "."))

    st.markdown("#### Panorama dos dados")
    g1, g2 = st.columns([1, 1.3])

    with g1:
        df_tipo = db.executar(
            "SELECT tipo_contrato, COUNT(*) AS qtd FROM contrato "
            "GROUP BY tipo_contrato ORDER BY qtd DESC"
        )
        fig = px.bar(
            df_tipo, x="tipo_contrato", y="qtd", template="plotly_white",
            color="tipo_contrato", color_discrete_sequence=PALETA,
        )
        fig.update_layout(
            title=dict(text="Contratos por tipo", font=dict(size=15, color="#0A3D62")),
            showlegend=False, height=360, margin=dict(t=50, l=10, r=10, b=10),
            xaxis_title=None, yaxis_title="Qtd.",
        )
        st.plotly_chart(fig, width="stretch")

    with g2:
        df_ano = db.executar(
            "SELECT strftime('%Y', v.protocolo_data) AS ano, c.tipo_contrato, "
            "COUNT(*) AS qtd FROM contrato c "
            "JOIN versao_contrato v ON v.id_contrato = c.id_contrato "
            "WHERE v.protocolo_data <> '' GROUP BY ano, c.tipo_contrato ORDER BY ano"
        )
        fig = px.area(
            df_ano, x="ano", y="qtd", color="tipo_contrato",
            template="plotly_white", color_discrete_sequence=PALETA,
        )
        fig.update_layout(
            title=dict(text="Evolução das versões protocoladas",
                       font=dict(size=15, color="#0A3D62")),
            height=360, margin=dict(t=50, l=10, r=10, b=10),
            xaxis_title=None, yaxis_title="Qtd.", legend_title_text="",
        )
        st.plotly_chart(fig, width="stretch")

    with st.expander("Modelo de dados (entidades e relacionamentos)"):
        st.markdown(
            """
Entidades principais

| Tabela | Papel |
|---|---|
| contrato | Contrato único (tipo + processo ANATEL). |
| interconexao / compartilhamento / mvno / ran_sharing | Subtipos 1:1 de contrato. |
| versao_contrato | Versões/aditivos de cada contrato. |
| participacao | Empresa × versão (papel, ordem, serviço, modalidade, vigência) — relacionamento M:N. |
| empresa / servico | Dimensões deduplicadas. |
| informe / acordao / despacho | Documentos SEI por versão. |

Relacionamentos

- contrato 1:N versao_contrato
- versao_contrato M:N empresa, materializado pela entidade associativa participacao
- versao_contrato N:1 informe / acordao / despacho
            """
        )

    st.markdown("#### As 10 consultas")
    grupos = Q.por_categoria()
    for categoria, consultas in grupos.items():
        if not consultas:
            continue
        st.markdown(chip(categoria), unsafe_allow_html=True)
        cols = st.columns(len(consultas))
        for col, c in zip(cols, consultas):
            with col:
                st.button(
                    f"{c.numero}. {c.titulo}",
                    key=f"home_{c.id}", on_click=_ir, args=(c.id,),
                    width="stretch",
                )
        st.write("")


def pagina_consulta(consulta: Q.Consulta) -> None:
    st.markdown(
        f'<span class="q-num">CONSULTA {consulta.numero:02d}</span> &nbsp; {chip(consulta.categoria)}',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="q-title">{consulta.titulo}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="callout">{consulta.descricao}</div>', unsafe_allow_html=True)

    # Parâmetros interativos
    if consulta.parametros:
        st.markdown("Parâmetros")
        valores = coletar_parametros(consulta)
    else:
        valores = {}

    sql_final, params = montar_sql(consulta, valores)

    # Execução
    try:
        df = db.executar(sql_final, params)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Erro ao executar a consulta: {exc}")
        st.code(sql_final, language="sql")
        return

    # SQL executado
    with st.expander("Ver comando SQL", expanded=False):
        st.code(sql_final, language="sql")

    # KPIs
    k1, k2 = st.columns(2)
    k1.metric("Linhas retornadas", f"{len(df):,}".replace(",", "."))
    k2.metric("Colunas", len(df.columns))

    # Resultado + gráfico
    abas = ["Resultado"]
    if consulta.grafico and consulta.grafico.tipo:
        abas.append("Gráfico")
    tabs = st.tabs(abas)

    with tabs[0]:
        limite = 1000
        st.dataframe(
            df.head(limite), width="stretch",
            height=min(38 * min(len(df), 14) + 40, 560), hide_index=True,
        )
        if len(df) > limite:
            st.caption(f"Exibindo as primeiras {limite:,} de {len(df):,} linhas — "
                       "baixe o CSV para o conjunto completo."
                       .replace(",", "."))
        st.download_button(
            "Baixar CSV", df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{consulta.id}.csv", mime="text/csv",
        )

    if len(tabs) > 1:
        with tabs[1]:
            render_grafico(df, consulta.grafico)

    # Análise
    if consulta.analise:
        st.markdown(
            f'<div class="callout insight">Análise. {consulta.analise}</div>',
            unsafe_allow_html=True,
        )


def pagina_console() -> None:
    st.markdown('<div class="q-title">Console SQL</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="callout">Execute consultas SELECT livres sobre o banco. '
        'Útil para explorar o modelo além das 10 consultas. Somente leitura.</div>',
        unsafe_allow_html=True,
    )
    sql = st.text_area(
        "Consulta SQL", height=170,
        value="SELECT tipo_contrato, COUNT(*) AS qtd\nFROM contrato\nGROUP BY tipo_contrato\nORDER BY qtd DESC;",
    )
    if st.button("Executar", type="primary"):
        limpo = sql.strip().rstrip(";").strip()
        if ";" in limpo:
            st.error("Execute apenas um comando por vez (sem ; internos).")
            return
        if not re.match(r"(?is)^\s*(select|with)\b", limpo):
            st.error("Apenas consultas SELECT (ou WITH) são permitidas.")
            return
        try:
            df = db.executar(limpo)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Erro: {exc}")
            return
        st.success(f"{len(df):,} linha(s) retornada(s).".replace(",", "."))
        st.dataframe(df.head(2000), width="stretch", hide_index=True, height=460)
        st.download_button(
            "Baixar CSV", df.to_csv(index=False).encode("utf-8-sig"),
            file_name="consulta_livre.csv", mime="text/csv",
        )


# --------------------------------------------------------------------------- #
# Roteamento
# --------------------------------------------------------------------------- #
def main() -> None:
    if db.caminho_banco() is None:
        st.error(
            "Não encontrei o banco contratos.db. Garanta que ele está na "
            "raiz do projeto (gerado pelo notebook 02 - Prepare Insert.ipynb)."
        )
        return

    sidebar()
    pagina = st.session_state.pagina
    if pagina == "home":
        pagina_home()
    elif pagina == "console":
        pagina_console()
    else:
        consulta = Q.por_id(pagina)
        if consulta:
            pagina_consulta(consulta)
        else:
            st.session_state.pagina = "home"
            pagina_home()


main()
