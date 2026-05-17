from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)
DB_FILE = "immunisation.db"

def query_db(query, args=(), one=False):
    """Helper function to cleanly open, execute, and pull data rows from SQLite."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Enables column access by column name strings
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# ==========================================
# LEVEL 1 ROUTES: Big Picture Summary Metrics
# ==========================================

@app.route('/')
def index():
    # Requirement: 4 facts/snapshot metrics pulled live using SQL Aggregations
    timeframe = query_db("SELECT MIN(Year) as start, MAX(Year) as end FROM VaccinationData;", one=True)
    total_doses = query_db("SELECT SUM(DosesAdministered) as total FROM VaccinationData;", one=True)
    total_cases = query_db("SELECT SUM(cases) as total FROM InfectionData;", one=True)
    distinct_diseases = query_db("SELECT COUNT(DISTINCT inf_type) as count FROM InfectionData;", one=True)
    
    return render_template('index.html', 
                           timeframe=timeframe, 
                           total_doses=total_doses, 
                           total_cases=total_cases, 
                           distinct_diseases=distinct_diseases)

@app.route('/mission')
def mission():
    # Requirement: Pull team profile records and target group personas from the database
    team = query_db("SELECT * FROM TeamMembers ORDER BY StudentID ASC;")
    personas = query_db("SELECT * FROM Personas;")
    return render_template('mission.html', team=team, personas=personas)

# ==========================================
# LEVEL 2 ROUTES: Filtering & Shallow Glances
# ==========================================

@app.route('/regional', methods=['GET', 'POST'])
def regional():
    # Populate dropdown filter selections directly from unique database records
    regions = query_db("SELECT DISTINCT RegionName FROM Countries WHERE RegionName IS NOT NULL;")
    years = query_db("SELECT DISTINCT Year FROM VaccinationData ORDER BY Year DESC;")
    
    selected_region = request.form.get('region') if request.method == 'POST' else None
    selected_year = request.form.get('year') if request.method == 'POST' else None
    
    # Base Raw SQL Query demonstrating dynamic structural joins & user-input filtering
    query = """
        SELECT c.CountryName, c.RegionName, v.Antigen, p.population, v.DosesAdministered, v.CoveragePercentage, v.Year
        FROM VaccinationData v
        JOIN Countries c ON v.CountryID = c.CountryID
        JOIN CountryPopulation p ON v.CountryID = p.country AND v.Year = p.year
        WHERE 1=1
    """
    params = []
    if selected_region:
        query += " AND c.RegionName = ?"
        params.append(selected_region)
    if selected_year:
        query += " AND v.Year = ?"
        params.append(selected_year)
        
    query += " ORDER BY v.CoveragePercentage DESC;"
    records = query_db(query, params)
    
    return render_template('regional.html', regions=regions, years=years, 
                           records=records, sel_region=selected_region, sel_year=selected_year)

@app.route('/economic', methods=['GET', 'POST'])
def economic():
    statuses = query_db("SELECT DISTINCT EconomicStatus FROM Countries WHERE EconomicStatus IS NOT NULL;")
    selected_status = request.form.get('status') if request.method == 'POST' else None
    
    query = """
        SELECT c.CountryName, c.EconomicStatus, i.inf_type, i.cases, i.year
        FROM InfectionData i
        JOIN Countries c ON i.country = c.CountryID
    """
    params = []
    if selected_status:
        query += " WHERE c.EconomicStatus = ?"
        params.append(selected_status)
    query += " ORDER BY i.cases DESC LIMIT 100;"
    
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
    sel_end = request.form.get('end_year', '2024')
    limit_n = request.form.get('limit', '10')
    
    # Complex Level 3 Query: Compares performance metrics over time purely using SQL logic
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
    records = query_db(query, [sel_antigen, sel_start, sel_end, int(limit_n)])
    return render_template('improvement.html', antigens=antigens, records=records,
                           sel_antigen=sel_antigen, sel_start=sel_start, sel_end=sel_end, limit=limit_n)

@app.route('/integrity', methods=['GET', 'POST'])
def integrity():
    years = query_db("SELECT DISTINCT year FROM InfectionData ORDER BY year DESC;")
    sel_year = request.form.get('year', '2020')
    
    # CRITICAL LEVEL 3 RULES: Calculates an aggregated global average inside a subquery, 
    # then exposes records that exceed that average baseline. No Python filtering used.
    query = """
        SELECT c.CountryName, i.inf_type, i.cases, i.year,
               ((i.cases * 100000.0) / cp.population) as CasesPer100k
        FROM InfectionData i
        JOIN Countries c ON i.country = c.CountryID
        JOIN CountryPopulation cp ON i.country = cp.country AND i.year = cp.year
        WHERE i.year = ? 
        AND ((i.cases * 100000.0) / cp.population) > (
            SELECT AVG((sub_i.cases * 100000.0) / sub_cp.population)
            FROM InfectionData sub_i
            JOIN CountryPopulation sub_cp ON sub_i.country = sub_cp.country AND sub_i.year = sub_cp.year
            WHERE sub_i.year = ?
        )
        ORDER BY CasesPer100k DESC;
    """
    records = query_db(query, [sel_year, sel_year])
    
    # Calculate the standalone global average baseline for display at the top of the table
    avg_row = query_db("""
        SELECT AVG((sub_i.cases * 100000.0) / sub_cp.population) as global_avg
        FROM InfectionData sub_i
        JOIN CountryPopulation sub_cp ON sub_i.country = sub_cp.country AND sub_i.year = sub_cp.year
        WHERE sub_i.year = ?;
    """, [sel_year], one=True)
    
    return render_template('integrity.html', years=years, records=records, 
                           sel_year=sel_year, global_avg=avg_row['global_avg'] if avg_row else 0)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
