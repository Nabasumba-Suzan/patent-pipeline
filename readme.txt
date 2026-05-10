
PATENT INTELLIGENCE DATA PIPELINE
================================

Project Overview
----------------
This project is a Patent Intelligence Data Pipeline developed in Python to process,
analyze, and report insights from patent datasets.

The system performs the following tasks:
1. Loads patent, inventor, and company datasets.
2. Cleans and standardizes the data.
3. Builds relationships between patents, inventors, and companies.
4. Stores the processed data in a SQLite database.
5. Executes SQL queries for analysis.
6. Extracts keywords from patent titles and abstracts.
7. Generates a patent intelligence report.
8. Launches an interactive dashboard for visualization.

Project Structure
-----------------
patent_pipeline/
├── data/
│   └── patents.csv
├── database/
│   └── patent_intelligence.db
├── output/
│   └── report.txt
├── scripts/
│   ├── pipeline.py
│   └── dashboard.py
├── requirements.txt
└── README.txt

How to Run the Project
----------------------

1. Create and activate a virtual environment:

   python3 -m venv venv
   source venv/bin/activate

2. Install dependencies:

   pip install -r requirements.txt

3. Run the data pipeline:

   python3 scripts/pipeline.py

4. Launch the dashboard:

   python3 scripts/dashboard.py

Expected Output
---------------
After running the pipeline, the system will:
- Process 5,000 patent records
- Identify top inventors
- Identify top companies
- Show yearly patent trends
- Store data in SQLite
- Generate analytical reports

Sample Results
--------------
Top Companies:
1. Samsung Electronics Co., Ltd.
2. International Business Machines Corporation (IBM)
3. Canon Kabushiki Kaisha
4. Sony Group Corporation
5. Hitachi, Ltd.

Technologies Used
-----------------
- Python 3
- Pandas
- SQLite3
- Scikit-learn
- Matplotlib
- Streamlit (Dashboard)

Business Value
--------------
This project helps organizations:
- Track innovation trends
- Analyze competitor patents
- Identify leading inventors
- Support research and development decisions

Future Improvements
-------------------
- Machine learning-based patent classification
- Predictive analytics
- Interactive web dashboards
- Technology category detection

Author
------
Nabasumba Suzan
Bachelor of Science in Software Engineering
Makerere University

Year
----
2026
