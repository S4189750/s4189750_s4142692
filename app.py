from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)
DB_FILE = "immunisation.db"

def query_db(query, args=(), one=False):
    """Helper function to cleanly open, execute, and pull data rows from SQLite."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# ==========================================
# LEVEL 1 ROUTES: Dashboard & Metrics
# ==========================================

@app.route('/')
def index():
    timeframe = query_db("SELECT MIN(Year) as start, MAX(Year) as end FROM VaccinationData;", one=True)
    total_doses = query_db("SELECT SUM(DosesAdministered) as total FROM VaccinationData;", one=True)
    total_cases = query_db("SELECT SUM(ReportedCases) as total FROM InfectionData;", one=True)
    distinct_diseases = query_db("SELECT COUNT(DISTINCT InfectionType) as count FROM InfectionData;", one=True)
    
    search_query = request.args.get('disease_search', '').strip()
    search_results = []
    
    if search_query:
        results_raw = query_db(
            "SELECT DISTINCT InfectionType FROM InfectionData WHERE InfectionType LIKE ?;", 
            ['%' + search_query + '%']
        )
        search_results = [row['InfectionType'] for row in results_raw]

    return render_template('index.html', 
                           timeframe=timeframe, 
                           total_doses=total_doses, 
                           total_cases=total_cases, 
                           distinct_diseases=distinct_diseases,
                           search_query=search_query,
                           search_results=search_results)

@app.route('/mission')
def mission():
    # Renders the static pastel blocks and target personas profile layout safely
    return render_template('mission.html')

# ==========================================
# LEVEL 2 ROUTES: Filtering Views
# ==========================================

@app.route('/regional', methods=['GET', 'POST'])
def regional():
    regions = query_db("SELECT DISTINCT RegionName FROM Countries WHERE RegionName IS NOT NULL;")
    years = query_db("SELECT DISTINCT Year FROM VaccinationData ORDER BY Year DESC;")
    
    selected_region = request.form.get('region') if request.method == 'POST' else None
    selected_year = request.form.get('year') if request.method == 'POST' else None
    
    query = """
        SELECT c.CountryName, c.RegionName, v.Antigen, p.PopulationValue, v.DosesAdministered, v.CoveragePercentage, v.Year
        FROM VaccinationData v
        JOIN Countries c ON v.CountryID = c.CountryID
        JOIN CountryPopulation p ON v.CountryID = p.CountryID AND v.Year = p.Year
        WHERE 1=1
    """
    params = []
    if selected_region:
        query += " AND c.RegionName = ?"
        params.append(selected_region)
    if selected_year:
        query += " AND v.Year = ?"
        params.append(int(selected_year) if selected_year.isdigit() else selected_year)
        
    query += " ORDER BY v.CoveragePercentage DESC LIMIT 100;"
    records = query_db(query, params)
    
    return render_template('regional.html', regions=regions, years=years, 
                           records=records, sel_region=selected_region, sel_year=selected_year)

@app.route('/economic', methods=['GET', 'POST'])
def economic():
    statuses = query_db("SELECT DISTINCT EconomicStatus FROM Countries WHERE EconomicStatus IS NOT NULL;")
    selected_status = request.form.get('status') if request.method == 'POST' else None
    
    query = """
        SELECT c.CountryName, c.EconomicStatus, i.InfectionType, i.ReportedCases, i.Year
        FROM InfectionData i
        JOIN Countries c ON i.CountryID = c.CountryID
    """
    params = []
    if selected_status:
        query += " WHERE c.EconomicStatus = ?"
        params.append(selected_status)
    query += " ORDER BY i.ReportedCases DESC LIMIT 100;"
    
    records = query_db(query, params)
    return render_template('economic.html', statuses=statuses, records=records, sel_status=selected_status)

# ==========================================
# LEVEL 3 ROUTES: Deep Analysis Subqueries
# ==========================================

@app.route('/improvement', methods=['GET', 'POST'])
def improvement():
    antigens = query_db("SELECT DISTINCT Antigen FROM VaccinationData;")
    sel_antigen = request.form.get('antigen', 'DTP3')
    sel_start = request.form.get('start_year', '2020')
    sel_end = request.form.get('end_year', '2022')
    limit_n = request.form.get('limit', '10')
    
    query = """
        SELECT v1.CountryID, c.CountryName, v1.Antigen,
               v1.CoveragePercentage as StartCoverage, 
               v2.CoveragePercentage as EndCoverage,
               (v2.CoveragePercentage - v1.CoveragePercentage) as ProgressJump
        FROM VaccinationData v1
        JOIN VaccinationData v2 ON v1.CountryID = v2.CountryID AND v1.Antigen = v2.Antigen
        JOIN Countries c ON v1.CountryID = c.CountryID
        WHERE v1.Antigen = ? AND v1.Year = ? AND v2.Year = ?
        ORDER BY ProgressJump DESC
        LIMIT ?;
    """
    records = query_db(query, [sel_antigen, int(sel_start), int(sel_end), int(limit_n)])
    return render_template('improvement.html', antigens=antigens, records=records,
                           sel_antigen=sel_antigen, sel_start=sel_start, sel_end=sel_end, limit=limit_n)

@app.route('/integrity', methods=['GET', 'POST'])
def integrity():
    years = query_db("SELECT DISTINCT Year FROM InfectionData ORDER BY Year DESC;")
    sel_year = request.form.get('year', '2020')
    
    query = """
        SELECT c.CountryName, i.InfectionType, i.ReportedCases, i.Year,
               ((i.ReportedCases * 100000.0) / cp.PopulationValue) as CasesPer100k
        FROM InfectionData i
        JOIN Countries c ON i.CountryID = c.CountryID
        JOIN CountryPopulation cp ON i.CountryID = cp.CountryID AND i.Year = cp.Year
        WHERE i.Year = ? 
        AND ((i.ReportedCases * 100000.0) / cp.PopulationValue) > (
            SELECT AVG((sub_i.ReportedCases * 100000.0) / sub_cp.PopulationValue)
            FROM InfectionData sub_i
            JOIN CountryPopulation sub_cp ON sub_i.CountryID = sub_cp.CountryID AND sub_i.Year = sub_cp.Year
            WHERE sub_i.Year = ?
        )
        ORDER BY CasesPer100k DESC;
    """
    records = query_db(query, [int(sel_year), int(sel_year)])
    
    avg_row = query_db("""
        SELECT AVG((sub_i.ReportedCases * 100000.0) / sub_cp.PopulationValue) as global_avg
        FROM InfectionData sub_i
        JOIN CountryPopulation sub_cp ON sub_i.CountryID = sub_cp.CountryID AND sub_i.Year = sub_cp.Year
        WHERE sub_i.Year = ?;
    """, [int(sel_year)], one=True)
    
    return render_template('integrity.html', years=years, records=records, 
                           sel_year=sel_year, global_avg=avg_row['global_avg'] if avg_row else 0)

if __name__ == '__main__':
    app.run(debug=True, port=5000)