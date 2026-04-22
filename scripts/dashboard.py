
"""
Patent Intelligence Dashboard  –  Streamlit app
================================================
Run:  streamlit run scripts/dashboard.py
"""

import sqlite3
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

BASE_DIR    = Path(__file__).resolve().parent.parent
DB_PATH     = BASE_DIR / "patents.db"
REPORTS_DIR = BASE_DIR / "reports"

st.set_page_config(
    page_title="Patent Intelligence",
    page_icon="",
    layout="wide",
)

@st.cache_resource
def get_connection():
    if not DB_PATH.exists():
        st.error("Database not found. Run `python scripts/pipeline.py` first.")
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data(ttl=300)
def query(_con, sql):
    return pd.read_sql_query(sql, _con)

con = get_connection()

total_patents = query(con, "SELECT COUNT(*) AS n FROM patents").iloc[0]["n"]
top_inventors = query(con, """
    SELECT i.name, i.country, COUNT(DISTINCT r.patent_id) AS patents
    FROM inventors i JOIN relationships r ON i.inventor_id = r.inventor_id
    GROUP BY i.inventor_id ORDER BY patents DESC LIMIT 20
""")
top_companies = query(con, """
    SELECT c.name, COUNT(DISTINCT r.patent_id) AS patents
    FROM companies c JOIN relationships r ON c.company_id = r.company_id
    GROUP BY c.company_id ORDER BY patents DESC LIMIT 20
""")
tech_dist = query(con, """
    SELECT tech_category AS category, COUNT(*) AS patents
    FROM patents GROUP BY tech_category ORDER BY patents DESC
""")
yearly_trends = query(con, """
    SELECT year, COUNT(*) AS patents FROM patents
    WHERE year BETWEEN 1976 AND 2025
    GROUP BY year ORDER BY year
""")

st.title(" Global Patent Intelligence Dashboard")
st.caption("Source: PatentsView – USPTO Granted Patent Disambiguated Data")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Patents",  f"{total_patents:,}")
c2.metric("Top Inventor",   top_inventors.iloc[0]["name"]  if not top_inventors.empty else "–")
c3.metric("Top Company",    top_companies.iloc[0]["name"]  if not top_companies.empty else "–")
c4.metric("Top Category",   tech_dist.iloc[0]["category"]  if not tech_dist.empty     else "–")

st.divider()

col_a, col_b = st.columns([3, 2])
with col_a:
    st.subheader(" Patents per Year")
    if not yearly_trends.empty:
        fig = px.area(yearly_trends, x="year", y="patents",
                      color_discrete_sequence=["#2563EB"])
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("💡 Patents by Tech Category")
    if not tech_dist.empty:
        fig = px.bar(tech_dist, x="patents", y="category",
                     orientation="h",
                     color="patents", color_continuous_scale="Blues")
        fig.update_layout(yaxis={"categoryorder": "total ascending"},
                          margin=dict(l=0, r=0, t=10, b=0),
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

col_c, col_d = st.columns(2)
with col_c:
    st.subheader(" Top 20 Inventors")
    if not top_inventors.empty:
        fig = px.bar(top_inventors, x="patents", y="name",
                     orientation="h",
                     color_discrete_sequence=["#2563EB"])
        fig.update_layout(yaxis={"categoryorder": "total ascending"},
                          margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

with col_d:
    st.subheader(" Top 10 Companies")
    if not top_companies.empty:
        fig = px.pie(top_companies.head(10), names="name", values="patents",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_traces(textposition="inside")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader(" Search Patents")
search = st.text_input("Search by title keyword")
limit  = st.slider("Results to show", 10, 500, 100, step=10)

sql = f"""
    SELECT p.patent_id, p.title, p.year, p.tech_category,
           i.name AS inventor, c.name AS company
    FROM patents p
    LEFT JOIN relationships r ON p.patent_id = r.patent_id
    LEFT JOIN inventors i     ON r.inventor_id = i.inventor_id
    LEFT JOIN companies c     ON r.company_id  = c.company_id
    {'WHERE p.title LIKE ?' if search else ''}
    LIMIT {limit}
"""
params = (f"%{search}%",) if search else ()
df = pd.read_sql_query(sql, con, params=params)
st.dataframe(df, use_container_width=True)

st.divider()
st.subheader("⬇Download Reports")
col1, col2, col3 = st.columns(3)

def csv_btn(col, label, filename):
    path = REPORTS_DIR / filename
    if path.exists():
        col.download_button(label, path.read_bytes(), filename, "text/csv")
    else:
        col.warning(f"{filename} not found – run pipeline first")

csv_btn(col1, "Top Inventors CSV",  "top_inventors.csv")
csv_btn(col2, "Top Companies CSV",  "top_companies.csv")
csv_btn(col3, "Country Trends CSV", "country_trends.csv")

json_path = REPORTS_DIR / "dashboard.json"
if json_path.exists():
    st.download_button("Download Full JSON Report",
                       json_path.read_bytes(),
                       "dashboard.json", "application/json")
