

CREATE TABLE IF NOT EXISTS patents (
    patent_id     TEXT PRIMARY KEY,
    title         TEXT,
    abstract      TEXT,
    filing_date   TEXT,
    year          INTEGER,
    tech_category TEXT
);

CREATE TABLE IF NOT EXISTS inventors (
    inventor_id TEXT PRIMARY KEY,
    name        TEXT,
    country     TEXT
);

CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    name       TEXT
);

CREATE TABLE IF NOT EXISTS relationships (
    patent_id   TEXT,
    inventor_id TEXT,
    company_id  TEXT,
    FOREIGN KEY (patent_id)   REFERENCES patents(patent_id),
    FOREIGN KEY (inventor_id) REFERENCES inventors(inventor_id),
    FOREIGN KEY (company_id)  REFERENCES companies(company_id)
);
