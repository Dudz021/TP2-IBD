# Contratos ANATEL

Pipeline de tratamento e modelagem dos contratos da ANATEL: parte das bases brutas
publicadas em dados abertos, normaliza os dados e materializa um banco **SQLite**
pronto para consultas e análises.

> Dataset original: https://dados.gov.br/dados/conjuntos-dados/empresas-credenciadas-de-rede-virtual-do-servico-movel-pessoal-telefonia-movel

O conjunto reúne quatro famílias de contratos da ANATEL:

| Tipo | Descrição |
|------|-----------|
| **Interconexão** | Acordos de interconexão entre prestadoras (com serviço e modalidade STFC). |
| **Compartilhamento** | Compartilhamento de infraestrutura passiva (postes, dutos, torres) entre detentora e solicitante. |
| **MVNO** | Credenciamento de operadoras de rede virtual móvel (prestadora de origem × credenciada). |
| **RAN Sharing** | Compartilhamento de rede de acesso (RAN) entre prestadoras, com tecnologia (MOCN/GWCN/...). |

---

## Estrutura do repositório

```
vic-ibd/
├── Dados - Contratos/               # dados crus, como vieram da origem
│   ├── contratos_interconexao.csv
│   ├── contratos_compartilhamento.csv
│   ├── contratos_mvno.csv
│   ├── contratos_ran_sharing.csv
│   └── empresas_credenciadas_vigentes.csv
├── Dados - Contratos Normalizados/  # dados limpos (saída do notebook 01)
│   ├── contratos_int.csv
│   ├── contratos_comp.csv
│   ├── contratos_mvno.csv
│   └── contratos_ran_sharing.csv
├── 00 - EDA.ipynb                   # análise exploratória das bases cruas
├── 01 - Clean Dataset.ipynb         # limpeza e normalização
├── 02 - Prepare Insert.ipynb        # gera o schema + dados no SQLite
├── diagrama_bd.dbml                 # modelo lógico do banco (dbdiagram.io)
├── schema.sql                       # DDL (CREATE TABLE) do banco
├── inserts.sql                      # comandos INSERT de todos os registros
├── database.sql                     # schema.sql + inserts.sql (recria o banco do zero)
└── contratos.db                     # >>> banco SQLite materializado <<<
```

---

## Pipeline (notebooks)

O fluxo é sequencial — cada notebook consome a saída do anterior:

1. **`00 - EDA.ipynb`** — Análise exploratória das bases cruas em `Dados - Contratos/`.
   Entende formatos, valores, nulos e inconsistências antes da limpeza.

2. **`01 - Clean Dataset.ipynb`** — Tratamento e normalização: padronização de texto,
   datas (formato ISO `YYYY-MM-DD`), extração de CNPJs e processos ANATEL válidos,
   limpeza dos números SEI, remoção de duplicatas e criação das colunas de
   versionamento (`NUM_SEQUENCIA`, `FINAL`).
   **Saída:** os CSVs limpos em `Dados - Contratos Normalizados/`.

3. **`02 - Prepare Insert.ipynb`** — Lê os quatro CSVs normalizados, transforma-os no
   modelo relacional do `diagrama_bd.dbml` e gera os artefatos de banco
   (`inserts.sql`, `database.sql` e `contratos.db`). Ao final, materializa o
   `contratos.db` e valida a integridade referencial (`PRAGMA foreign_key_check`).

---

## Modelo de dados

O schema (definido em [`diagrama_bd.dbml`](diagrama_bd.dbml) e implementado em
[`schema.sql`](schema.sql)) normaliza os contratos em torno de algumas ideias centrais:

- **`contrato`** — um contrato único, identificado pela chave natural
  *(tipo + processo ANATEL)*. Cada tipo tem uma tabela de **subtipo** 1:1
  (`interconexao`, `compartilhamento`, `mvno`, `ran_sharing`) para os atributos
  específicos.
- **`versao_contrato`** — cada **linha** de um CSV vira uma **versão/aditivo**
  (`NUM_SEQUENCIA`). Linhas com o mesmo processo, dentro do mesmo tipo,
  compartilham o mesmo `contrato`.
- **`participacao`** — liga uma **empresa** a uma **versão**, com seu papel
  (ex.: `DETENTORA`, `SOLICITANTE`, `PRESTADORA_1`), ordem, serviço, modalidade
  STFC e a flag `vigente` (derivada do `FINAL`).
- **`empresa`** e **`servico`** — dimensões deduplicadas.
- **`informe`**, **`acordao`**, **`despacho`** — documentos SEI vinculados a cada versão.

### Tabelas

| Tabela | Papel |
|--------|-------|
| `contrato` | Contrato único (tipo + processo). |
| `interconexao` / `compartilhamento` / `mvno` / `ran_sharing` | Subtipos 1:1 de `contrato`. |
| `versao_contrato` | Versões/aditivos de cada contrato. |
| `participacao` | Empresa × versão (papel, ordem, serviço, modalidade, vigente). |
| `empresa` | Dimensão de empresas (CNPJ / razão social). |
| `servico` | Dimensão de serviços ANATEL (código). |
| `informe` / `acordao` / `despacho` | Documentos SEI por versão. |

### Decisões de modelagem

- `contrato.id_processo` é **`TEXT`** (não `integer`), pois `PROCESSO_ANATEL` é
  formatado — ex.: `53500.000052/2006-13`.
- Datas são guardadas como **`TEXT` ISO `YYYY-MM-DD`** (convenção do SQLite).
- Duas colunas foram **acrescentadas ao DBML** para não perder dados de origem:
  - `versao_contrato.acordo_tipo` → `ACORDO_TIPO` (CONTRATO/ADITIVO/...)
  - `ran_sharing.tecnologia` → `ACORDO_TECNOLOGIA` (MOCN/GWCN/...)
- `participacao.vigente` é derivada do `FINAL` da versão.

---

## Arquivos de banco

O notebook `02 - Prepare Insert.ipynb` gera quatro artefatos. **Atenção à diferença
entre script SQL e arquivo de banco:**

| Arquivo | O que é | Abre no DBeaver? |
|---------|---------|------------------|
| `schema.sql` | **Script de texto** — só os `CREATE TABLE` (estrutura). | Não como banco — execute como SQL. |
| `inserts.sql` | **Script de texto** — os `INSERT` de todos os registros. | Não como banco — execute como SQL. |
| `database.sql` | **Script de texto** — `schema.sql` + `inserts.sql`; recria o banco do zero. | **Não.** É texto, não um `.db`. |
| **`contratos.db`** | **Arquivo binário SQLite** com estrutura + dados. | ✅ **Sim — é este que você abre.** |

> ⚠️ **Erro `[SQLITE_NOTADB] file is not a database`?**
> Você tentou abrir um `.sql` como se fosse um banco. Os arquivos `.sql` são
> *scripts de texto*; o banco SQLite de verdade é o **`contratos.db`**.

---

## Como usar

### Abrir no DBeaver

1. *New Database Connection* → **SQLite**.
2. Em *Path*, aponte para **`contratos.db`**.
3. *Finish*. As tabelas aparecem em `main`.

### Recriar o banco a partir do `database.sql`

Se você só tem o script (ou quer gerar um `.db` novo a partir dele):

```bash
sqlite3 contratos.db < database.sql
```

> Use um arquivo `contratos.db` inexistente/vazio como destino; o script cria as
> tabelas e insere os dados.

### Regenerar tudo do zero

Instale as dependências e execute **`02 - Prepare Insert.ipynb`**. Ele relê os
CSVs normalizados e regrava `inserts.sql`, `database.sql` e `contratos.db`.

```bash
pip install -r requirements.txt
```

> As dependências de terceiros são apenas `pandas` e `numpy` (mais `jupyter`/
> `ipykernel` para rodar os notebooks). As demais libs usadas — `pathlib`, `re`,
> `sqlite3`, `unicodedata` — fazem parte da biblioteca-padrão do Python.

### Exemplo de consulta

```sql
SELECT c.tipo_contrato,
       c.id_processo,
       COUNT(DISTINCT v.id_versao)      AS qtd_versoes,
       GROUP_CONCAT(DISTINCT e.razao_social) AS empresas
  FROM contrato c
  JOIN versao_contrato v ON v.id_contrato = c.id_contrato
  JOIN participacao p    ON p.id_versao   = v.id_versao
  JOIN empresa e         ON e.id_empresa  = p.id_empresa
 GROUP BY c.id_contrato
 ORDER BY qtd_versoes DESC
 LIMIT 10;
```

---

## Aplicação Streamlit ([`streamlit_app/`](streamlit_app/))

Dashboard web interativo para explorar as **10 consultas** do trabalho sobre o
`contratos.db`. O app é **genérico**: lê as consultas de um único arquivo de
definições ([`streamlit_app/queries.py`](streamlit_app/queries.py)) e monta a
interface sozinho — explicação, SQL, parâmetros interativos, tabela, gráfico,
análise e download de CSV. Para trocar/editar/adicionar uma consulta, edita-se
apenas `queries.py`; nada no app precisa mudar.

```bash
pip install -r requirements.txt
streamlit run streamlit_app/app.py        # execute a partir da raiz do projeto
```

Recursos: navegação por categoria, parâmetros interativos (`select`, `slider`,
`multiselect` — vinculados de forma segura via *named parameters*), gráficos
Plotly, links compartilháveis (`?p=q09`) e um **Console SQL** somente-leitura.
Detalhes em [`streamlit_app/README.md`](streamlit_app/README.md).
