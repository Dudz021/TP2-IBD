"""Arquivo de consultas — a fonte da verdade do dashboard.

Cada consulta do trabalho é declarada aqui como uma Consulta. O app
(app.py) lê esta lista e renderiza tudo automaticamente: explicação,
SQL, parâmetros interativos, tabela de resultados, gráfico, análise e download.

Para adicionar / editar / remover uma consulta, mexa SOMENTE neste arquivo.
Nada no app precisa ser alterado — ele é genérico.

Estrutura de uma consulta
--------------------------
- sql        : o comando SQL. Pode conter parâmetros nomeados :nome,
               que são vinculados de forma segura (sem injeção).
- parametros : widgets interativos que alimentam os :nome do SQL.
- grafico    : como visualizar o resultado (tipo, eixos, agregação opcional).
- descricao / analise : textos (explicação e leitura crítica).
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
    """Widget interativo que injeta um valor em um :nome do SQL."""

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
    descricao: str
    sql: str
    analise: str = ""
    grafico: Grafico | None = None
    parametros: list[Parametro] = field(default_factory=list)


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
        titulo="Mapeamento de Processos de RAN Sharing",
        categoria="Seleção e Projeção",
        descricao=(
            "Realiza a projeção de colunas fundamentais e faz uma seleção para "
            "isolar estritamente os acordos de compartilhamento de rede de acesso "
            "via rádio (RAN Sharing)."
        ),
        sql=(
            "SELECT id_contrato, tipo_contrato, id_processo\n"
            "FROM contrato\n"
            "WHERE tipo_contrato = 'ran_sharing'\n"
            "ORDER BY id_processo;"
        ),
        analise=(
            "O RAN Sharing ainda é um arranjo pouco frequente no país; a seleção "
            "isola esse subconjunto específico de contratos para inspeção direta."
        ),
        grafico=None,
    ),

    Consulta(
        id="q02",
        numero=2,
        titulo="Rastreamento de Alterações Contratuais Recentes",
        categoria="Seleção e Projeção",
        descricao=(
            "Seleciona e projeta versões ou aditivos contratuais estabelecidos a "
            "partir de 2024 que possuem uma data explícita de encerramento da "
            "vigência acordada."
        ),
        sql=(
            "SELECT id_versao, id_contrato, protocolo_data, conclusao_data\n"
            "FROM versao_contrato\n"
            "WHERE protocolo_data >= '2024-01-01'\n"
            "  AND conclusao_data IS NOT NULL\n"
            "ORDER BY protocolo_data DESC;"
        ),
        analise=(
            "Filtrar por data de protocolo recente e exigir data de conclusão "
            "evidencia os acordos firmados e já encerrados no período mais atual, "
            "úteis para acompanhar a renovação do estoque contratual."
        ),
        grafico=None,
    ),

    # ----------------------------------------------------------------------- #
    # 2) JUNÇÃO DE DUAS RELAÇÕES
    # ----------------------------------------------------------------------- #
    Consulta(
        id="q03",
        numero=3,
        titulo="Junção de Contratos e Histórico de Versões",
        categoria="Junção de duas relações",
        descricao=(
            "Realiza uma junção simples (INNER JOIN) entre a tabela mãe de "
            "contratos e seu histórico de versões para reconstruir a linha do "
            "tempo dos aditivos administrativos."
        ),
        sql=(
            "SELECT c.id_processo, c.tipo_contrato, v.num_sequencia, v.protocolo_data\n"
            "FROM contrato c\n"
            "INNER JOIN versao_contrato v ON c.id_contrato = v.id_contrato\n"
            "ORDER BY c.id_processo, v.num_sequencia;"
        ),
        analise=(
            "A junção entre contrato e versao_contrato reconstrói a linha do tempo "
            "de cada processo, em que cada versão corresponde a um aditivo ou "
            "alteração administrativa."
        ),
        grafico=None,
    ),

    Consulta(
        id="q04",
        numero=4,
        titulo="Papel Regulatório das Operadoras por Versão",
        categoria="Junção de duas relações",
        descricao=(
            "Conecta a tabela associativa de participações ao cadastro mestre de "
            "empresas para expor quais razões sociais atuam em cada ID de versão "
            "contratual."
        ),
        sql=(
            "SELECT p.id_versao, e.razao_social, p.papel\n"
            "FROM participacao p\n"
            "INNER JOIN empresa e ON p.id_empresa = e.id_empresa\n"
            "ORDER BY e.razao_social;"
        ),
        analise=(
            "Ligar participacao a empresa revela, versão a versão, qual razão "
            "social assume cada papel regulatório no contrato."
        ),
        grafico=Grafico(
            tipo="bar", x="papel", agg="count", ordenar=True,
            titulo="Participações por papel",
            rotulo_x="Papel", rotulo_y="Qtd. de participações",
        ),
    ),

    Consulta(
        id="q05",
        numero=5,
        titulo="Catálogo de Empresas com Vínculos Contratuais Ativos",
        categoria="Junção de duas relações",
        descricao=(
            "Junção entre empresas e participações filtrando operadoras que "
            "possuem CNPJs válidos e participações homologadas no sistema."
        ),
        sql=(
            "SELECT DISTINCT e.razao_social, e.cnpj\n"
            "FROM empresa e\n"
            "INNER JOIN participacao p ON e.id_empresa = p.id_empresa\n"
            "WHERE e.cnpj IS NOT NULL\n"
            "ORDER BY e.razao_social;"
        ),
        analise=(
            "Restringir a CNPJs válidos e participações registradas produz um "
            "catálogo das operadoras efetivamente ativas no ecossistema."
        ),
        grafico=None,
    ),

    # ----------------------------------------------------------------------- #
    # 3) JUNÇÃO DE TRÊS OU MAIS RELAÇÕES
    # ----------------------------------------------------------------------- #
    Consulta(
        id="q06",
        numero=6,
        titulo="Rastreamento Completo de Transações Administrativas",
        categoria="Junção de três ou mais relações",
        descricao=(
            "Junção quádrupla unindo contrato, versao_contrato, participacao e "
            "empresa para recompor a cadeia informacional completa de cada "
            "processo regulatório."
        ),
        sql=(
            "SELECT c.tipo_contrato, c.id_processo, e.razao_social, p.papel\n"
            "FROM contrato c\n"
            "INNER JOIN versao_contrato v ON c.id_contrato = v.id_contrato\n"
            "INNER JOIN participacao p ON v.id_versao = p.id_versao\n"
            "INNER JOIN empresa e ON p.id_empresa = e.id_empresa\n"
            "ORDER BY c.id_processo;"
        ),
        analise=(
            "A junção das quatro relações recompõe a cadeia completa do processo "
            "— do tipo de contrato à empresa participante — base para as demais "
            "análises."
        ),
        grafico=Grafico(
            tipo="bar", x="tipo_contrato", agg="count", ordenar=True,
            titulo="Participações por tipo de contrato",
            rotulo_x="Tipo de contrato", rotulo_y="Qtd. de participações",
        ),
    ),

    Consulta(
        id="q07",
        numero=7,
        titulo="Análise Espacial do Mercado de MVNOs",
        categoria="Junção de três ou mais relações",
        descricao=(
            "Cruza quatro tabelas aplicando uma restrição na relação primária "
            "para mapear exclusivamente os atores envolvidos nos acordos de "
            "operadoras móveis virtuais."
        ),
        sql=(
            "SELECT c.id_processo, v.protocolo_data, e.razao_social, p.papel\n"
            "FROM contrato c\n"
            "INNER JOIN versao_contrato v ON c.id_contrato = v.id_contrato\n"
            "INNER JOIN participacao p ON v.id_versao = p.id_versao\n"
            "INNER JOIN empresa e ON p.id_empresa = e.id_empresa\n"
            "WHERE c.tipo_contrato = 'mvno'\n"
            "ORDER BY c.id_processo;"
        ),
        analise=(
            "Ao restringir o tipo de contrato a mvno, a mesma junção de quatro "
            "tabelas isola os atores e papéis específicos do mercado de operadoras "
            "móveis virtuais."
        ),
        grafico=Grafico(
            tipo="bar", x="papel", agg="count", ordenar=True,
            titulo="Papéis nos contratos de MVNO",
            rotulo_x="Papel", rotulo_y="Qtd. de participações",
        ),
    ),

    Consulta(
        id="q08",
        numero=8,
        titulo="Auditoria de Propriedade de Infraestrutura Passiva",
        categoria="Junção de três ou mais relações",
        descricao=(
            "Identifica quais corporações atuam especificamente no papel de "
            "DETENTORA de ativos físicos (torres, postes e dutos) em contratos de "
            "compartilhamento."
        ),
        sql=(
            "SELECT c.id_processo, v.protocolo_data, e.razao_social AS empresa_detentora\n"
            "FROM contrato c\n"
            "INNER JOIN versao_contrato v ON c.id_contrato = v.id_contrato\n"
            "INNER JOIN participacao p ON v.id_versao = p.id_versao\n"
            "INNER JOIN empresa e ON p.id_empresa = e.id_empresa\n"
            "WHERE c.tipo_contrato = 'compartilhamento'\n"
            "  AND p.papel = 'DETENTORA'\n"
            "ORDER BY c.id_processo;"
        ),
        analise=(
            "Filtrar pelo papel DETENTORA em contratos de compartilhamento "
            "identifica as empresas proprietárias da infraestrutura passiva "
            "(torres, postes e dutos)."
        ),
        grafico=Grafico(
            tipo="barh", x="empresa_detentora", agg="count", ordenar=True, topn=12,
            titulo="Detentoras de infraestrutura passiva",
            rotulo_x="Qtd. de participações", rotulo_y="Empresa",
        ),
    ),

    # ----------------------------------------------------------------------- #
    # 4) AGREGAÇÃO SOBRE JUNÇÃO
    # ----------------------------------------------------------------------- #
    Consulta(
        id="q09",
        numero=9,
        titulo="Análise de Volatilidade Contratual por Processo",
        categoria="Agregação sobre junção",
        descricao=(
            "Agrupa dados de junção e computa a função agregada COUNT para mapear "
            "os contratos que sofreram maior volume de aditivos e reajustes "
            "históricos. Use o controle para definir o tamanho do ranking."
        ),
        sql=(
            "SELECT c.id_processo, c.tipo_contrato, COUNT(v.id_versao) AS total_versoes\n"
            "FROM contrato c\n"
            "INNER JOIN versao_contrato v ON c.id_contrato = v.id_contrato\n"
            "GROUP BY c.id_contrato\n"
            "ORDER BY total_versoes DESC\n"
            "LIMIT :n;"
        ),
        parametros=[
            Parametro(
                nome="n", rotulo="Tamanho do ranking", tipo="slider",
                minimo=5, maximo=30, padrao=10, passo=1,
            ),
        ],
        analise=(
            "Contar versões por processo destaca os contratos mais voláteis — "
            "aqueles que acumularam mais aditivos e alterações ao longo do tempo."
        ),
        grafico=Grafico(
            tipo="barh", x="id_processo", y="total_versoes", ordenar=True,
            titulo="Processos com mais versões / aditivos",
            rotulo_x="Qtd. de versões", rotulo_y="Processo",
        ),
    ),

    Consulta(
        id="q10",
        numero=10,
        titulo="Índice de Concentração de Mercado em Compartilhamento Passivo",
        categoria="Agregação sobre junção",
        descricao=(
            "Executa um agrupamento por empresa e calcula o volume total de "
            "participações contratuais na modalidade de compartilhamento de "
            "infraestrutura, expondo os principais players do setor. Use o "
            "controle para definir o tamanho do ranking."
        ),
        sql=(
            "SELECT e.razao_social AS empresa, COUNT(p.id_participacao) AS total_participacoes\n"
            "FROM empresa e\n"
            "INNER JOIN participacao p ON e.id_empresa = p.id_empresa\n"
            "INNER JOIN versao_contrato v ON p.id_versao = v.id_versao\n"
            "INNER JOIN contrato c ON v.id_contrato = c.id_contrato\n"
            "WHERE c.tipo_contrato = 'compartilhamento'\n"
            "GROUP BY e.id_empresa\n"
            "ORDER BY total_participacoes DESC\n"
            "LIMIT :n;"
        ),
        parametros=[
            Parametro(
                nome="n", rotulo="Tamanho do ranking", tipo="slider",
                minimo=5, maximo=30, padrao=10, passo=1,
            ),
        ],
        analise=(
            "Somar participações por empresa nos contratos de compartilhamento "
            "expõe a concentração de mercado, com poucos grupos respondendo pela "
            "maior parte dos vínculos."
        ),
        grafico=Grafico(
            tipo="barh", x="empresa", y="total_participacoes", ordenar=True,
            titulo="Empresas por participações em compartilhamento",
            rotulo_x="Qtd. de participações", rotulo_y="Empresa",
        ),
    ),
]


def por_id(consulta_id: str) -> Consulta | None:
    """Retorna a consulta de dado id (ou None)."""
    return next((c for c in CONSULTAS if c.id == consulta_id), None)


def por_categoria() -> dict[str, list[Consulta]]:
    """Agrupa as consultas por categoria, preservando a ordem de CATEGORIAS."""
    grupos: dict[str, list[Consulta]] = {cat: [] for cat in CATEGORIAS}
    for consulta in CONSULTAS:
        grupos.setdefault(consulta.categoria, []).append(consulta)
    return grupos
