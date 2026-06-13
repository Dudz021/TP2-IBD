-- =====================================================================
--  Schema do Banco de Contratos (ANATEL) - SQLite
--  Baseado em: diagrama_bd.dbml
--
--  Modelo:
--    * contrato            -> contrato unico (chave natural: tipo + processo)
--    * interconexao / compartilhamento / mvno / ran_sharing
--                          -> subtipos especializados de contrato (1:1)
--    * versao_contrato     -> cada versao/aditivo de um contrato (NUM_SEQUENCIA)
--    * informe / acordao / despacho
--                          -> documentos SEI vinculados a uma versao
--    * participacao        -> participacao de uma empresa em uma versao
--    * empresa             -> dimensao de empresas (CNPJ / razao social)
--    * servico             -> dimensao de servicos ANATEL (codigo)
--
--  Observacoes de modelagem:
--    * id_processo e armazenado como TEXT (PROCESSO_ANATEL e formatado,
--      ex.: '53500.000052/2006-13', e nao um inteiro puro).
--    * datas sao armazenadas como TEXT no formato ISO 'YYYY-MM-DD'
--      (convencao SQLite).
--    * Extensoes ao DBML para nao perder dados de origem:
--        - versao_contrato.acordo_tipo  (ACORDO_TIPO: CONTRATO/ADITIVO/...)
--        - ran_sharing.tecnologia       (ACORDO_TECNOLOGIA: MOCN/GWCN/...)
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Dimensoes independentes
-- ---------------------------------------------------------------------
CREATE TABLE empresa (
    id_empresa    INTEGER PRIMARY KEY,
    cnpj          VARCHAR,
    razao_social  VARCHAR
);

CREATE TABLE servico (
    servico_id    INTEGER PRIMARY KEY,
    servico_tipo  VARCHAR,
    modalidade    VARCHAR
);

-- ---------------------------------------------------------------------
-- Documentos SEI (vinculados 1:1 a uma versao de contrato)
-- ---------------------------------------------------------------------
CREATE TABLE informe (
    informe_id    INTEGER PRIMARY KEY,
    informe_sei   VARCHAR NOT NULL,
    informe_data  DATETIME,
    informe       TEXT
);

CREATE TABLE acordao (
    acordao_id    INTEGER PRIMARY KEY,
    acordao_sei   VARCHAR NOT NULL,
    acordao_data  DATETIME,
    acordao       TEXT
);

CREATE TABLE despacho (
    despacho_id   INTEGER PRIMARY KEY,
    despacho_sei  VARCHAR NOT NULL,
    despacho_data DATETIME
);

-- ---------------------------------------------------------------------
-- Contrato e seus subtipos
-- ---------------------------------------------------------------------
CREATE TABLE contrato (
    id_contrato   INTEGER PRIMARY KEY,
    id_processo   TEXT NOT NULL,
    tipo_contrato VARCHAR(20)
);

CREATE TABLE interconexao (
    id_contrato INTEGER PRIMARY KEY,
    FOREIGN KEY (id_contrato) REFERENCES contrato (id_contrato)
);

CREATE TABLE compartilhamento (
    id_contrato INTEGER PRIMARY KEY,
    FOREIGN KEY (id_contrato) REFERENCES contrato (id_contrato)
);

CREATE TABLE ran_sharing (
    id_contrato INTEGER PRIMARY KEY,
    tecnologia  VARCHAR,
    FOREIGN KEY (id_contrato) REFERENCES contrato (id_contrato)
);

CREATE TABLE mvno (
    id_contrato                INTEGER PRIMARY KEY,
    vigencia_data_fim          DATETIME,
    processo_descredenciamento VARCHAR,
    FOREIGN KEY (id_contrato) REFERENCES contrato (id_contrato)
);

-- ---------------------------------------------------------------------
-- Versoes de contrato
-- ---------------------------------------------------------------------
CREATE TABLE versao_contrato (
    id_versao     INTEGER PRIMARY KEY,
    id_contrato   INTEGER NOT NULL,
    num_sequencia INTEGER,
    acordo_tipo   VARCHAR,
    protocolo_data DATETIME,
    conclusao_data DATETIME,
    observacao    TEXT,
    informe_id    INTEGER,
    acordao_id    INTEGER,
    despacho_id   INTEGER,
    FOREIGN KEY (id_contrato) REFERENCES contrato (id_contrato),
    FOREIGN KEY (informe_id)  REFERENCES informe (informe_id),
    FOREIGN KEY (acordao_id)  REFERENCES acordao (acordao_id),
    FOREIGN KEY (despacho_id) REFERENCES despacho (despacho_id)
);

-- ---------------------------------------------------------------------
-- Participacao de empresas em cada versao
-- ---------------------------------------------------------------------
CREATE TABLE participacao (
    id_participacao    INTEGER PRIMARY KEY,
    id_versao          INTEGER,
    id_empresa         INTEGER,
    papel              VARCHAR,
    ordem_participacao INTEGER DEFAULT 1,
    servico_id         INTEGER,
    modalidade_sftc    VARCHAR,
    vigente            BOOLEAN DEFAULT 1,
    FOREIGN KEY (id_versao)  REFERENCES versao_contrato (id_versao),
    FOREIGN KEY (id_empresa) REFERENCES empresa (id_empresa),
    FOREIGN KEY (servico_id) REFERENCES servico (servico_id)
);

-- ---------------------------------------------------------------------
-- Indices de apoio
-- ---------------------------------------------------------------------
CREATE INDEX idx_versao_contrato_id_contrato ON versao_contrato (id_contrato);
CREATE INDEX idx_participacao_id_versao      ON participacao (id_versao);
CREATE INDEX idx_participacao_id_empresa     ON participacao (id_empresa);
CREATE INDEX idx_contrato_processo           ON contrato (id_processo);
