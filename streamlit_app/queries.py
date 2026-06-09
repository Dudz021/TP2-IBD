"""Arquivo de consultas — a "fonte da verdade" do dashboard.

Cada consulta do trabalho é declarada aqui como uma ``Consulta``. O app
([app.py](app.py)) lê esta lista e renderiza tudo automaticamente: explicação,
SQL, parâmetros interativos, tabela de resultados, gráfico, análise e download.

>>> Para adicionar / editar / remover uma consulta, mexa SOMENTE neste arquivo.
    Nada no app precisa ser alterado — ele é genérico.

Estrutura de uma consulta
--------------------------
- ``sql``        : o comando SQL. Pode conter parâmetros nomeados ``:nome``,
                   que são vinculados de forma segura (sem injeção).
- ``parametros`` : widgets interativos que alimentam os ``:nome`` do SQL.
- ``grafico``    : como visualizar o resultado (tipo, eixos, agregação opcional).
- ``descricao`` / ``analise`` : textos em Markdown (explicação e leitura crítica).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------- #
# Categorias exigidas pelo enunciado (rótulo -> cor de destaque)
# --------------------------------------------------------------------------- #
CATEGORIAS: dict[str, str] = {
    "Seleção e Projeção": "#2E86DE",
    "Junção de duas relações": "#8E44AD",
    "Junção de três ou mais relações": "#E67E22",
    "Agregação sobre junção": "#16A085",
}


@dataclass
class Parametro:
    """Widget interativo que injeta um valor em um ``:nome`` do SQL."""

    nome: str                       # token usado no SQL (ex.: ":tipo" -> nome="tipo")
    rotulo: str                     # rótulo exibido ao usuário
    tipo: str                       # "select" | "slider" | "multiselect"
    opcoes: list = field(default_factory=list)
    padrao: Any = None
    minimo: int = 0
    maximo: int = 100
    passo: int = 1
    ajuda: str = ""


@dataclass
class Grafico:
    """Especificação declarativa de visualização do resultado."""

    tipo: str | None = None         # bar | barh | line | area | pie | treemap
    x: str | None = None
    y: str | None = None
    cor: str | None = None          # coluna de cor/agrupamento (opcional)
    agg: str | None = None          # None | "count" | "sum" | "mean"
    x_transform: str | None = None  # None | "ano" (extrai o ano de uma data ISO)
    ordenar: bool = False           # ordena por y (desc) antes de plotar
    topn: int | None = None         # mantém apenas as N maiores categorias
    titulo: str = ""
    rotulo_x: str = ""
    rotulo_y: str = ""


@dataclass
class Consulta:
    """Uma consulta do trabalho, com tudo que o app precisa para renderizá-la."""

    id: str
    numero: int
    titulo: str
    categoria: str
    icone: str
    descricao: str
    sql: str
    analise: str = ""
    grafico: Grafico | None = None
    parametros: list[Parametro] = field(default_factory=list)


# Opções reutilizadas em vários parâmetros.
TIPOS_CONTRATO = ["interconexao", "compartilhamento", "mvno", "ran_sharing"]
PAPEIS = [
    "PRESTADORA_1", "PRESTADORA_2", "PRESTADORA_3",
    "SOLICITANTE", "DETENTORA", "PRESTADORA_ORIGEM", "CREDENCIADA",
]


# =========================================================================== #
#  AS 10 CONSULTAS
# =========================================================================== #
CONSULTAS: list[Consulta] = [

    # ----------------------------------------------------------------------- #
    # 1) SELEÇÃO E PROJEÇÃO
    # ----------------------------------------------------------------------- #
    Consulta(
        id="q01",
        numero=1,
        titulo="Catálogo de contratos por tipo",
        categoria="Seleção e Projeção",
        icone="🗂️",
        descricao=(
            "Lista os processos ANATEL de um **tipo de contrato** escolhido pelo "
            "usuário. É o exemplo mais direto de **seleção** (filtro `WHERE` sobre "
            "o tipo) combinada com **projeção** (apenas `id_processo` e "
            "`tipo_contrato`), tudo sobre uma única relação."
        ),
        sql=(
            "SELECT id_processo, tipo_contrato\n"
            "FROM contrato\n"
            "WHERE tipo_contrato = :tipo\n"
            "ORDER BY id_processo;"
        ),
        parametros=[
            Parametro(
                nome="tipo", rotulo="Tipo de contrato", tipo="select",
                opcoes=TIPOS_CONTRATO, padrao="mvno",
                ajuda="Filtra os contratos pela natureza do acordo.",
            ),
        ],
        analise=(
            "O volume varia muito por tipo: **compartilhamento** (~3,1 mil) e "
            "**interconexão** (~1,7 mil) dominam, enquanto **RAN Sharing** tem "
            "apenas 15 contratos — um arranjo ainda incipiente no mercado brasileiro."
        ),
        grafico=None,  # resultado é uma listagem; o destaque é a tabela + KPI
    ),

    Consulta(
        id="q02",
        numero=2,
        titulo="MVNOs descredenciadas",
        categoria="Seleção e Projeção",
        icone="📵",
        descricao=(
            "Seleciona, na tabela de subtipo `mvno`, apenas os credenciamentos que "
            "**possuem processo de descredenciamento** registrado — ou seja, "
            "operadoras de rede virtual móvel que deixaram de operar. **Seleção** "
            "pelo campo não nulo + **projeção** das colunas relevantes."
        ),
        sql=(
            "SELECT id_contrato, vigencia_data_fim, processo_descredenciamento\n"
            "FROM mvno\n"
            "WHERE processo_descredenciamento IS NOT NULL\n"
            "  AND TRIM(processo_descredenciamento) <> ''\n"
            "ORDER BY vigencia_data_fim DESC;"
        ),
        analise=(
            "Dos 245 credenciamentos MVNO, **47 já foram descredenciados**. A "
            "concentração de encerramentos em anos recentes sugere uma "
            "reacomodação do mercado de operadoras virtuais após o pico de "
            "credenciamentos."
        ),
        grafico=Grafico(
            tipo="bar", x="vigencia_data_fim", x_transform="ano", agg="count",
            titulo="Descredenciamentos de MVNO por ano",
            rotulo_x="Ano", rotulo_y="Qtd. de descredenciamentos",
        ),
    ),

    # ----------------------------------------------------------------------- #
    # 2) JUNÇÃO DE DUAS RELAÇÕES
    # ----------------------------------------------------------------------- #
    Consulta(
        id="q03",
        numero=3,
        titulo="Tecnologias de RAN Sharing",
        categoria="Junção de duas relações",
        icone="📡",
        descricao=(
            "Junta `contrato` com o subtipo `ran_sharing` para mostrar, de cada "
            "acordo de compartilhamento de rede de acesso, o **processo** e a "
            "**tecnologia** empregada (MOCN, GWCN, MORAN…). Junção 1:1 entre a "
            "entidade e seu subtipo."
        ),
        sql=(
            "SELECT c.id_processo, r.tecnologia\n"
            "FROM contrato c\n"
            "JOIN ran_sharing r ON r.id_contrato = c.id_contrato\n"
            "ORDER BY r.tecnologia, c.id_processo;"
        ),
        analise=(
            "Embora poucos, os acordos de RAN Sharing concentram-se em **MOCN** "
            "(*Multi-Operator Core Network*), tecnologia que permite a operadoras "
            "compartilharem a rede de acesso mantendo núcleos independentes — a "
            "forma mais comum de compartilhamento de rede 4G/5G no país."
        ),
        grafico=Grafico(
            tipo="bar", x="tecnologia", agg="count", ordenar=True,
            titulo="Contratos de RAN Sharing por tecnologia",
            rotulo_x="Tecnologia", rotulo_y="Qtd. de contratos",
        ),
    ),

    Consulta(
        id="q04",
        numero=4,
        titulo="Versões e aditivos por contrato",
        categoria="Junção de duas relações",
        icone="🧾",
        descricao=(
            "Junta `contrato` com `versao_contrato` para expor o **histórico de "
            "versões/aditivos** de cada contrato de um tipo escolhido. Cada linha "
            "do CSV original virou uma versão — esta consulta reconstrói a linha "
            "do tempo de cada processo."
        ),
        sql=(
            "SELECT c.id_processo, c.tipo_contrato, v.num_sequencia,\n"
            "       v.acordo_tipo, v.protocolo_data\n"
            "FROM contrato c\n"
            "JOIN versao_contrato v ON v.id_contrato = c.id_contrato\n"
            "WHERE c.tipo_contrato = :tipo\n"
            "ORDER BY c.id_processo, v.num_sequencia;"
        ),
        parametros=[
            Parametro(
                nome="tipo", rotulo="Tipo de contrato", tipo="select",
                opcoes=TIPOS_CONTRATO, padrao="interconexao",
            ),
        ],
        analise=(
            "O número de protocolos cresce de forma acentuada a partir de ~2014, "
            "refletindo tanto a digitalização do processo (SEI) quanto a "
            "intensificação dos acordos de interconexão entre prestadoras."
        ),
        grafico=Grafico(
            tipo="line", x="protocolo_data", x_transform="ano", agg="count",
            titulo="Versões protocoladas por ano",
            rotulo_x="Ano", rotulo_y="Qtd. de versões",
        ),
    ),

    Consulta(
        id="q05",
        numero=5,
        titulo="Participações vigentes por papel",
        categoria="Junção de duas relações",
        icone="✅",
        descricao=(
            "Junta `participacao` com `empresa` e filtra apenas as participações "
            "**vigentes** (`vigente = 1`). Permite escolher quais **papéis** "
            "considerar. Mostra quem está ativo em cada função dos contratos."
        ),
        sql=(
            "SELECT e.razao_social, e.cnpj, p.papel\n"
            "FROM participacao p\n"
            "JOIN empresa e ON e.id_empresa = p.id_empresa\n"
            "WHERE p.vigente = 1\n"
            "  AND p.papel IN :papeis\n"
            "ORDER BY e.razao_social;"
        ),
        parametros=[
            Parametro(
                nome="papeis", rotulo="Papéis", tipo="multiselect",
                opcoes=PAPEIS, padrao=PAPEIS,
                ajuda="Selecione um ou mais papéis a considerar.",
            ),
        ],
        analise=(
            "Apenas ~10,1 mil das ~44,7 mil participações estão vigentes: a maior "
            "parte do histórico corresponde a versões superadas por aditivos "
            "posteriores. Entre as vigentes, os papéis de **prestadora** e "
            "**solicitante** predominam."
        ),
        grafico=Grafico(
            tipo="bar", x="papel", agg="count", ordenar=True,
            titulo="Participações vigentes por papel",
            rotulo_x="Papel", rotulo_y="Qtd. de participações",
        ),
    ),

    # ----------------------------------------------------------------------- #
    # 3) JUNÇÃO DE TRÊS OU MAIS RELAÇÕES
    # ----------------------------------------------------------------------- #
    Consulta(
        id="q06",
        numero=6,
        titulo="Informes SEI vinculados às versões",
        categoria="Junção de três ou mais relações",
        icone="📄",
        descricao=(
            "Junta **três** relações — `contrato`, `versao_contrato` e `informe` — "
            "para rastrear, de cada versão de contrato, o **informe SEI** que a "
            "instruiu e sua data. Demonstra a ligação documento ↔ versão ↔ contrato."
        ),
        sql=(
            "SELECT c.id_processo, c.tipo_contrato, v.num_sequencia,\n"
            "       i.informe_sei, i.informe_data\n"
            "FROM contrato c\n"
            "JOIN versao_contrato v ON v.id_contrato = c.id_contrato\n"
            "JOIN informe i ON i.informe_id = v.informe_id\n"
            "ORDER BY i.informe_data DESC;"
        ),
        analise=(
            "Há ~9,4 mil informes vinculados a versões. O fluxo documental se "
            "intensifica ano a ano, evidenciando o papel central do SEI como "
            "instrumento de instrução dos processos de contrato na ANATEL."
        ),
        grafico=Grafico(
            tipo="area", x="informe_data", x_transform="ano", agg="count",
            titulo="Informes SEI por ano",
            rotulo_x="Ano", rotulo_y="Qtd. de informes",
        ),
    ),

    Consulta(
        id="q07",
        numero=7,
        titulo="Participações por serviço e modalidade",
        categoria="Junção de três ou mais relações",
        icone="🔀",
        descricao=(
            "Junta **três** relações — `participacao`, `empresa` e `servico` — "
            "cruzando empresas, o **serviço ANATEL** associado e a **modalidade "
            "STFC** (Local, LDN, LDI). Mostra como as prestadoras se distribuem "
            "entre serviços e modalidades de telefonia."
        ),
        sql=(
            "SELECT e.razao_social, s.servico_tipo, p.papel, p.modalidade_sftc\n"
            "FROM participacao p\n"
            "JOIN empresa e ON e.id_empresa = p.id_empresa\n"
            "JOIN servico s ON s.servico_id = p.servico_id\n"
            "WHERE p.modalidade_sftc IS NOT NULL\n"
            "  AND TRIM(p.modalidade_sftc) <> ''\n"
            "ORDER BY e.razao_social;"
        ),
        analise=(
            "As modalidades **Local**, **LDN** (longa distância nacional) e **LDI** "
            "(internacional) aparecem em volumes próximos, indicando que boa parte "
            "das prestadoras atua simultaneamente nas três frentes de telefonia fixa."
        ),
        grafico=Grafico(
            tipo="bar", x="modalidade_sftc", agg="count", ordenar=True,
            titulo="Participações por modalidade STFC",
            rotulo_x="Modalidade STFC", rotulo_y="Qtd. de participações",
        ),
    ),

    Consulta(
        id="q08",
        numero=8,
        titulo="Pares de prestadoras em interconexão",
        categoria="Junção de três ou mais relações",
        icone="🔗",
        descricao=(
            "Consulta avançada com **auto-junção**: cruza `contrato`, "
            "`versao_contrato`, `participacao` (duas vezes — Prestadora 1 e "
            "Prestadora 2) e `empresa` (duas vezes) para revelar **quem se "
            "interconecta com quem**. Cada linha é um acordo entre duas operadoras."
        ),
        sql=(
            "SELECT c.id_processo,\n"
            "       e1.razao_social AS prestadora_1,\n"
            "       e2.razao_social AS prestadora_2,\n"
            "       v.protocolo_data\n"
            "FROM contrato c\n"
            "JOIN versao_contrato v ON v.id_contrato = c.id_contrato\n"
            "JOIN participacao p1 ON p1.id_versao = v.id_versao AND p1.papel = 'PRESTADORA_1'\n"
            "JOIN empresa e1 ON e1.id_empresa = p1.id_empresa\n"
            "JOIN participacao p2 ON p2.id_versao = v.id_versao AND p2.papel = 'PRESTADORA_2'\n"
            "JOIN empresa e2 ON e2.id_empresa = p2.id_empresa\n"
            "WHERE c.tipo_contrato = 'interconexao'\n"
            "ORDER BY c.id_processo;"
        ),
        analise=(
            "As grandes operadoras (TIM, Oi, Claro, Vivo) concentram o papel de "
            "**Prestadora 1**, atuando como hubs de interconexão para uma longa "
            "cauda de provedores regionais — um retrato claro da assimetria de "
            "porte no mercado de telecom."
        ),
        grafico=Grafico(
            tipo="bar", x="prestadora_1", agg="count", ordenar=True, topn=12,
            titulo="Operadoras com mais acordos de interconexão (como Prestadora 1)",
            rotulo_x="Prestadora 1", rotulo_y="Qtd. de acordos",
        ),
    ),

    # ----------------------------------------------------------------------- #
    # 4) AGREGAÇÃO SOBRE JUNÇÃO
    # ----------------------------------------------------------------------- #
    Consulta(
        id="q09",
        numero=9,
        titulo="Ranking de empresas mais ativas",
        categoria="Agregação sobre junção",
        icone="🏆",
        descricao=(
            "**Agregação** (`COUNT`, `COUNT DISTINCT`) sobre a junção de "
            "`participacao`, `versao_contrato` e `empresa`, agrupando por empresa. "
            "Ranqueia as operadoras por **nº de contratos distintos** em que "
            "aparecem e pelo **total de participações** (somando todas as "
            "versões/aditivos). Use o controle para definir o tamanho do ranking."
        ),
        sql=(
            "SELECT e.razao_social,\n"
            "       COUNT(DISTINCT v.id_contrato) AS contratos,\n"
            "       COUNT(*) AS participacoes\n"
            "FROM participacao p\n"
            "JOIN versao_contrato v ON v.id_versao = p.id_versao\n"
            "JOIN empresa e ON e.id_empresa = p.id_empresa\n"
            "GROUP BY e.id_empresa\n"
            "ORDER BY participacoes DESC\n"
            "LIMIT :n;"
        ),
        parametros=[
            Parametro(
                nome="n", rotulo="Tamanho do ranking", tipo="slider",
                minimo=5, maximo=30, padrao=15, passo=1,
            ),
        ],
        analise=(
            "Um punhado de grandes grupos responde por uma fração desproporcional "
            "de todas as participações — comportamento típico de **cauda longa**, "
            "em que poucas operadoras nacionais firmam a maioria dos acordos e "
            "milhares de provedores menores aparecem poucas vezes cada."
        ),
        grafico=Grafico(
            tipo="barh", x="razao_social", y="participacoes", ordenar=True,
            titulo="Empresas por número de participações",
            rotulo_x="Qtd. de participações", rotulo_y="Empresa",
        ),
    ),

    Consulta(
        id="q10",
        numero=10,
        titulo="Evolução dos contratos por tipo",
        categoria="Agregação sobre junção",
        icone="📈",
        descricao=(
            "**Agregação temporal** sobre a junção de `contrato` e "
            "`versao_contrato`: conta versões protocoladas por **ano** e por "
            "**tipo de contrato**. Revela a dinâmica histórica de cada modalidade "
            "de acordo ao longo de quase duas décadas (2006–2025)."
        ),
        sql=(
            "SELECT strftime('%Y', v.protocolo_data) AS ano,\n"
            "       c.tipo_contrato,\n"
            "       COUNT(*) AS qtd\n"
            "FROM contrato c\n"
            "JOIN versao_contrato v ON v.id_contrato = c.id_contrato\n"
            "WHERE v.protocolo_data IS NOT NULL\n"
            "  AND v.protocolo_data <> ''\n"
            "GROUP BY ano, c.tipo_contrato\n"
            "ORDER BY ano, c.tipo_contrato;"
        ),
        analise=(
            "**Interconexão** e **compartilhamento** disparam a partir de meados "
            "da década de 2010; **MVNO** surge mais tarde, acompanhando a "
            "regulamentação das operadoras virtuais. A inflexão recente coincide "
            "com a adoção plena do SEI e com a expansão do 4G/5G."
        ),
        grafico=Grafico(
            tipo="area", x="ano", y="qtd", cor="tipo_contrato",
            titulo="Versões protocoladas por ano e tipo de contrato",
            rotulo_x="Ano", rotulo_y="Qtd. de versões",
        ),
    ),
]


def por_id(consulta_id: str) -> Consulta | None:
    """Retorna a consulta de dado ``id`` (ou ``None``)."""
    return next((c for c in CONSULTAS if c.id == consulta_id), None)


def por_categoria() -> dict[str, list[Consulta]]:
    """Agrupa as consultas por categoria, preservando a ordem de ``CATEGORIAS``."""
    grupos: dict[str, list[Consulta]] = {cat: [] for cat in CATEGORIAS}
    for consulta in CONSULTAS:
        grupos.setdefault(consulta.categoria, []).append(consulta)
    return grupos
