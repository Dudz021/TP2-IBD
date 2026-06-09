# Dashboard ANATEL — Contratos (Streamlit)

Aplicação web interativa para explorar as **10 consultas** do TP2 sobre o banco
`contratos.db`. O app é **genérico**: ele lê as consultas de um arquivo de
definições e monta a interface sozinho.

## Como rodar

A partir da **raiz do projeto** (onde está o `contratos.db`):

```bash
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

O navegador abre em `http://localhost:8501`.

## Estrutura

```
streamlit_app/
├── app.py             # renderizador genérico (não precisa mexer p/ trocar consultas)
├── queries.py         # >>> ARQUIVO DE CONSULTAS — a fonte da verdade <<<
├── db.py              # acesso ao SQLite (conexão + execução em cache)
├── .streamlit/
│   └── config.toml    # tema visual
└── README.md
```

## Como trocar / editar / adicionar uma consulta

Mexa **apenas** em [`queries.py`](queries.py). Cada consulta é um objeto
`Consulta`. Adicione um item à lista `CONSULTAS` e ele aparece automaticamente
no menu, na categoria correta, com SQL, tabela, gráfico e análise.

```python
Consulta(
    id="q11",                       # identificador único
    numero=11,
    titulo="Minha nova consulta",
    categoria="Agregação sobre junção",   # uma das chaves de CATEGORIAS
    icone="🔥",
    descricao="Explicação em **Markdown**.",
    sql="SELECT ... WHERE coluna = :param ...",
    parametros=[                     # opcional — widgets interativos
        Parametro(nome="param", rotulo="Filtro", tipo="select",
                  opcoes=["a", "b"], padrao="a"),
    ],
    grafico=Grafico(tipo="bar", x="coluna", agg="count", titulo="..."),  # opcional
    analise="Leitura crítica do resultado.",
)
```

### Parâmetros (`Parametro`)

| `tipo`        | Widget        | Vínculo no SQL                          |
|---------------|---------------|-----------------------------------------|
| `select`      | dropdown      | `:nome` (escalar)                       |
| `slider`      | controle      | `:nome` (inteiro)                       |
| `multiselect` | múltipla esc. | `:nome` → expande para `IN (:n_0, ...)` |

Tudo é vinculado via *named parameters* do SQLite (sem injeção de SQL).

### Gráfico (`Grafico`)

- `tipo`: `bar` · `barh` · `line` · `area` · `pie` · `treemap` (ou `None` p/ só tabela)
- `x`, `y`, `cor`: colunas do resultado
- `agg`: `count` · `sum` · `mean` (agrega no cliente, sem alterar o SQL)
- `x_transform="ano"`: extrai o ano de uma coluna de data ISO
- `ordenar`, `topn`: ordena por `y` e mantém só as N maiores categorias

## Página "Console SQL"

Um console somente-leitura para rodar `SELECT` livres sobre o banco — útil na
apresentação para responder perguntas ao vivo.
