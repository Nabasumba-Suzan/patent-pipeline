"""
Global Patent Intelligence Data Pipeline
=========================================
Clean + Robust + Dashboard-ready version
"""

import json
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer

# ── Paths ─────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
DB_PATH    = BASE_DIR / "patents.db"

DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

TARGET = 5000

# ── Files ─────────────────────────────────────────────
PATENT_FILE   = DATA_DIR / "g_patent.tsv"
ABSTRACT_FILE = DATA_DIR / "g_patent_abstract.tsv"
INVENTOR_FILE = DATA_DIR / "g_inventor_disambiguated.tsv"
ASSIGNEE_FILE = DATA_DIR / "g_assignee_disambiguated.tsv"
CPC_FILE      = DATA_DIR / "g_cpc_current.tsv"


# ═════════════════════════════════════════════════════
# 1. LOAD DATA
# ═════════════════════════════════════════════════════
def fetch_all():
    print(" Loading datasets …")

    patents   = pd.read_csv(PATENT_FILE,   sep="\t", low_memory=False, nrows=TARGET)
    inventors = pd.read_csv(INVENTOR_FILE, sep="\t", low_memory=False, nrows=TARGET)
    assignees = pd.read_csv(ASSIGNEE_FILE, sep="\t", low_memory=False, nrows=TARGET)
    cpc       = pd.read_csv(CPC_FILE,      sep="\t", low_memory=False, nrows=TARGET * 3)

    if ABSTRACT_FILE.exists():
        abstracts = pd.read_csv(ABSTRACT_FILE, sep="\t", low_memory=False, nrows=TARGET)
    else:
        print("  Missing abstract file → fallback used")
        abstracts = patents[["patent_id"]].copy()
        abstracts["patent_abstract"] = ""

    patents   = patents[["patent_id", "patent_title", "patent_date", "patent_type"]]
    abstracts = abstracts[["patent_id", "patent_abstract"]]
    patents   = patents.merge(abstracts, on="patent_id", how="left")
    patents   = patents.head(TARGET)

    return patents, inventors, assignees, cpc


# ═════════════════════════════════════════════════════
# 2. CPC CLASSIFICATION
# ═════════════════════════════════════════════════════
def add_tech_category(cpc):
    def map_tech(code):
        if pd.isna(code): return "Unknown"
        if "G06" in code: return "AI / Computing"
        if "A61" in code: return "Healthcare"
        if "H01" in code: return "Electronics"
        if "Y02" in code: return "Climate Tech"
        return "Other"
    cpc["tech_category"] = cpc["cpc_class"].apply(map_tech)
    return cpc[["patent_id", "tech_category"]]


# ═════════════════════════════════════════════════════
# 3. CLEAN PATENTS
# ═════════════════════════════════════════════════════
def clean_patents(df, cpc):
    print(" Cleaning patents …")
    df["filing_date"] = pd.to_datetime(df["patent_date"], errors="coerce")
    df["year"] = df["filing_date"].dt.year
    df = df.rename(columns={"patent_title": "title", "patent_abstract": "abstract"})
    df = df.merge(add_tech_category(cpc), on="patent_id", how="left")
    return df[["patent_id","title","abstract","filing_date","year","tech_category"]].drop_duplicates()


# ═════════════════════════════════════════════════════
# 4. CLEAN INVENTORS
# ═════════════════════════════════════════════════════
def clean_inventors(df):
    print(" Cleaning inventors …")
    df["name"] = (
        df["disambig_inventor_name_first"].fillna("") + " " +
        df["disambig_inventor_name_last"].fillna("")
    ).str.strip()
    df["country"] = "Unknown"
    return df[["inventor_id","name","country"]].drop_duplicates()


# ═════════════════════════════════════════════════════
# 5. CLEAN COMPANIES
# ═════════════════════════════════════════════════════
def clean_companies(df):
    print(" Cleaning companies …")
    df["name"] = df["disambig_assignee_organization"].fillna("Unknown")
    return df[["assignee_id","name"]].rename(columns={"assignee_id":"company_id"})


# ═════════════════════════════════════════════════════
# 6. RELATIONSHIPS
# ═════════════════════════════════════════════════════
def build_relationships(raw_inventors, raw_assignees):
    print(" Building relationships …")
    inv_links  = raw_inventors[["patent_id","inventor_id"]].dropna().drop_duplicates()
    comp_links = raw_assignees[["patent_id","assignee_id"]].dropna().drop_duplicates()
    comp_links = comp_links.rename(columns={"assignee_id":"company_id"})
    relationships = inv_links.merge(comp_links, on="patent_id", how="outer")
    print(f"Relationships built: {len(relationships)} rows")
    return relationships


# ═════════════════════════════════════════════════════
# 7. NLP KEYWORDS
# ═════════════════════════════════════════════════════
def extract_keywords(patents):
    print(" Extracting keywords …")
    texts = patents["abstract"].fillna("").tolist()
    tfidf = TfidfVectorizer(stop_words="english", max_features=15)
    tfidf.fit(texts)
    return tfidf.get_feature_names_out()


# ═════════════════════════════════════════════════════
# 8. DATABASE
# ═════════════════════════════════════════════════════
def store_db(patents, inventors, companies, relationships):
    print(" Saving database …")
    con = sqlite3.connect(DB_PATH)
    patents.to_sql("patents",             con, if_exists="replace", index=False)
    inventors.to_sql("inventors",         con, if_exists="replace", index=False)
    companies.to_sql("companies",         con, if_exists="replace", index=False)
    relationships.to_sql("relationships", con, if_exists="replace", index=False)
    con.close()
    print(" DB saved")


# ═════════════════════════════════════════════════════
# 9. SQL ANALYTICS (Q1–Q7)
# ═════════════════════════════════════════════════════
def run_queries():
    print(" Running SQL queries …")
    con = sqlite3.connect(DB_PATH)

    queries = {

        # Q1: Top Inventors
        "top_inventors": """
            SELECT i.name, COUNT(DISTINCT r.patent_id) AS patents
            FROM relationships r
            JOIN inventors i ON r.inventor_id = i.inventor_id
            GROUP BY i.inventor_id
            ORDER BY patents DESC
            LIMIT 10
        """,

        # Q2: Top Companies
        "top_companies": """
            SELECT c.name, COUNT(DISTINCT r.patent_id) AS patents
            FROM relationships r
            JOIN companies c ON r.company_id = c.company_id
            GROUP BY c.company_id
            ORDER BY patents DESC
            LIMIT 10
        """,

        # Q3: Tech Categories (replaces countries — no country data available)
        "tech_distribution": """
            SELECT tech_category, COUNT(*) AS patents
            FROM patents
            GROUP BY tech_category
            ORDER BY patents DESC
        """,

        # Q4: Trends Over Time
        "yearly_trends": """
            SELECT year, COUNT(*) AS patents
            FROM patents
            WHERE year IS NOT NULL
            GROUP BY year
            ORDER BY year
        """,

        # Q5: JOIN — patents with inventors and companies
        "patents_with_inventors_companies": """
            SELECT
                p.patent_id,
                p.title,
                p.year,
                p.tech_category,
                i.name  AS inventor_name,
                c.name  AS company_name
            FROM patents p
            LEFT JOIN relationships r ON p.patent_id = r.patent_id
            LEFT JOIN inventors i     ON r.inventor_id = i.inventor_id
            LEFT JOIN companies c     ON r.company_id  = c.company_id
            LIMIT 100
        """,

        # Q6: CTE — top tech categories with their top company
        "cte_top_category_companies": """
            WITH category_counts AS (
                SELECT tech_category, COUNT(*) AS total
                FROM patents
                GROUP BY tech_category
            ),
            company_counts AS (
                SELECT p.tech_category, c.name AS company_name,
                       COUNT(*) AS company_patents
                FROM patents p
                JOIN relationships r ON p.patent_id = r.patent_id
                JOIN companies c     ON r.company_id = c.company_id
                GROUP BY p.tech_category, c.company_id
            ),
            ranked AS (
                SELECT cc.tech_category, cc.company_name, cc.company_patents,
                       ROW_NUMBER() OVER (
                           PARTITION BY cc.tech_category
                           ORDER BY cc.company_patents DESC
                       ) AS rnk
                FROM company_counts cc
            )
            SELECT cat.tech_category, cat.total AS category_patents,
                   r.company_name AS top_company, r.company_patents
            FROM category_counts cat
            LEFT JOIN ranked r ON cat.tech_category = r.tech_category AND r.rnk = 1
            ORDER BY cat.total DESC
        """,

        # Q7: Ranking — inventors ranked by patent count using window function
        "inventor_rankings": """
            SELECT
                i.name,
                COUNT(DISTINCT r.patent_id) AS patents,
                RANK()       OVER (ORDER BY COUNT(DISTINCT r.patent_id) DESC) AS rank,
                DENSE_RANK() OVER (ORDER BY COUNT(DISTINCT r.patent_id) DESC) AS dense_rank,
                NTILE(4)     OVER (ORDER BY COUNT(DISTINCT r.patent_id) DESC) AS quartile
            FROM relationships r
            JOIN inventors i ON r.inventor_id = i.inventor_id
            GROUP BY i.inventor_id
            ORDER BY rank
            LIMIT 20
        """
    }

    results = {k: pd.read_sql(v, con) for k, v in queries.items()}
    con.close()
    return results


# ═════════════════════════════════════════════════════
# 10. CONSOLE REPORT
# ═════════════════════════════════════════════════════
def print_console_report(results, total_patents):
    print("\n")
   
    print("           PATENT INTELLIGENCE REPORT")
  

    print(f"\n Total Patents Loaded : {total_patents:,}")

    print("\n Top 5 Inventors:")
    for i, row in results["top_inventors"].head(5).iterrows():
        print(f"   {i+1}. {row['name']} — {row['patents']} patents")

    print("\n Top 5 Companies:")
    for i, row in results["top_companies"].head(5).iterrows():
        print(f"   {i+1}. {row['name']} — {row['patents']} patents")

    print("\n Patents by Tech Category:")
    for i, row in results["tech_distribution"].iterrows():
        print(f"   {row['tech_category']} : {row['patents']:,}")

    print("\n Yearly Trends (last 5 years):")
    for i, row in results["yearly_trends"].tail(5).iterrows():
        print(f"   {int(row['year'])} : {row['patents']:,} patents")

    print("\n Top 5 Inventors by Rank:")
    for i, row in results["inventor_rankings"].head(5).iterrows():
        print(f"   Rank {int(row['rank'])} | {row['name']} — {row['patents']} patents")

    


# ═════════════════════════════════════════════════════
# 11. EXPORT REPORTS
# ═════════════════════════════════════════════════════
def export_reports(results, patents, inventors, companies, keywords):
    # print(" Exporting reports …")

    # ── CSV exports ───────────────────────────────────
    patents.to_csv(REPORTS_DIR   / "clean_patents.csv",   index=False)
    inventors.to_csv(REPORTS_DIR / "clean_inventors.csv", index=False)
    companies.to_csv(REPORTS_DIR / "clean_companies.csv", index=False)

    results["top_inventors"].to_csv(REPORTS_DIR   / "top_inventors.csv",   index=False)
    results["top_companies"].to_csv(REPORTS_DIR   / "top_companies.csv",   index=False)
    results["tech_distribution"].to_csv(REPORTS_DIR / "country_trends.csv", index=False)
    results["yearly_trends"].to_csv(REPORTS_DIR   / "yearly_trends.csv",   index=False)
    results["inventor_rankings"].to_csv(REPORTS_DIR / "inventor_rankings.csv", index=False)
    results["patents_with_inventors_companies"].to_csv(
        REPORTS_DIR / "patents_joined.csv", index=False
    )

    # ── JSON report ───────────────────────────────────
    total    = len(patents)
    top_inv  = results["top_inventors"].head(10).to_dict(orient="records")
    top_comp = results["top_companies"].head(10).to_dict(orient="records")
    top_tech = results["tech_distribution"].to_dict(orient="records")

    report = {
        "generated_at" : datetime.now().isoformat(),
        "total_patents" : total,
        "top_inventors" : [{"name": r["name"], "patents": r["patents"]} for r in top_inv],
        "top_companies" : [{"name": r["name"], "patents": r["patents"]} for r in top_comp],
        "top_countries" : [{"category": r["tech_category"], "patents": r["patents"],
                             "share": round(r["patents"] / total, 4)} for r in top_tech],
        "keywords"      : list(keywords),
        "yearly_trends" : results["yearly_trends"].to_dict(orient="records")
    }

    with open(REPORTS_DIR / "dashboard.json", "w") as f:
        json.dump(report, f, indent=2)

    

# ═════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════
def main():
    print(" Patent Pipeline Starting …")

    patents, inventors, assignees, cpc = fetch_all()

    # build relationships BEFORE cleaning (patent_id still present)
    relationships = build_relationships(inventors, assignees)

    patents   = clean_patents(patents, cpc)
    inventors = clean_inventors(inventors)
    companies = clean_companies(assignees)

    print("\n SUMMARY")
    print("Patents      :", len(patents))
    print("Inventors    :", len(inventors))
    print("Companies    :", len(companies))
    print("Relationships:", len(relationships))

    store_db(patents, inventors, companies, relationships)

    results  = run_queries()
    keywords = extract_keywords(patents)

    print_console_report(results, len(patents))
    export_reports(results, patents, inventors, companies, keywords)

    


if __name__ == "__main__":
    main()
