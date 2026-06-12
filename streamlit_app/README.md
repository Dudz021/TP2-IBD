# Dashboard ANATEL (Streamlit)

App web para explorar as 10 consultas do TP2 sobre o banco contratos.db.
As consultas ficam em queries.py; o app.py lê essa lista e monta a interface.

## Rodar

Na raiz do projeto (onde está o contratos.db):

```bash
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```


## Arquivos

- app.py — monta a interface a partir das consultas
- queries.py — lista das consultas (SQL, parâmetros, gráfico, textos)
- db.py — conexão e execução no SQLite
- .streamlit/config.toml — tema

## Editar consultas

Edite queries.py. Cada consulta é um objeto Consulta na lista CONSULTAS; ao
adicionar um item, ele aparece sozinho no menu, na categoria indicada. A página
Console SQL permite rodar SELECTs livres sobre o banco.
