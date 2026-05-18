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
    # DB tables: Vaccination (year), InfectionData (year)
    timeframe = query_db("""
        SELECT MIN(start_year) as start, MAX(end_year) as end FROM (
            SELECT MIN(year) as start_year, MAX(year) as end_year FROM Vaccination
            UNION
            SELECT MIN(year) as start_year, MAX(year) as end_year FROM InfectionData
        );
    """, one=True)
    
    safe_timeframe = {
        'start': timeframe['start'] if timeframe else 2000,
        'start_year': timeframe['start'] if timeframe else 2000,
        'end': timeframe['end'] if timeframe else 2024,
        'end_year': timeframe['end'] if timeframe else 2024
    }
    
    # Vaccination.doses replaces VaccinationData.DosesAdministered
    total_doses = query_db("SELECT SUM(doses) as total FROM Vaccination;", one=True)
    # InfectionData.cases replaces InfectionData.ReportedCases
    total_cases = query_db("SELECT SUM(cases) as total FROM InfectionData;", one=True)
    # Country replaces Countries
    global_coverage = query_db("SELECT COUNT(DISTINCT CountryID) as count FROM Country;", one=True)
    # inf_type is the infection identifier; join Infection_Type for the human-readable name
    distinct_diseases = query_db("SELECT COUNT(DISTINCT inf_type) as count FROM InfectionData;", one=True)
    
    search_query = request.args.get('disease_search', '').strip()
    search_results = []
    
    if search_query:
        # Search against the Infection_Type description (human-readable disease name)
        results_raw = query_db(
            "SELECT DISTINCT description FROM Infection_Type WHERE description LIKE ?;", 
            ['%' + search_query + '%']
        )
        search_results = [row['description'] for row in results_raw]

    return render_template('index.html', 
                           timeframe=safe_timeframe,
                           total_doses=total_doses, 
                           total_cases=total_cases, 
                           global_coverage=global_coverage,
                           distinct_diseases=distinct_diseases,
                           search_query=search_query,
                           search_results=search_results)

@app.route('/mission')
def mission():
    return render_template('mission.html')

# ==========================================
# LEVEL 2 ROUTES: Filtering Views
# ==========================================

@app.route('/regional', methods=['GET', 'POST'])
def regional():
    # Region table holds region names; Country.region is the FK
    regions = query_db("SELECT DISTINCT region FROM Region WHERE region IS NOT NULL ORDER BY region;")
    years = query_db("SELECT DISTINCT year as Year FROM Vaccination ORDER BY year DESC;")
    
    selected_region = request.form.get('region') if request.method == 'POST' else None
    selected_year = request.form.get('year') if request.method == 'POST' else None
    
    # Join: Vaccination -> Country -> Region -> CountryPopulation
    query = """
        SELECT 
            c.name        AS CountryName,
            r.region      AS RegionName,
            v.antigen     AS Antigen,
            cp.population AS PopulationValue,
            v.doses       AS DosesAdministered,
            v.coverage    AS CoveragePercentage,
            v.year        AS Year
        FROM Vaccination v
        JOIN Country c  ON v.country  = c.CountryID
        JOIN Region  r  ON c.region   = r.RegionID
        JOIN CountryPopulation cp ON v.country = cp.country AND v.year = cp.year
        WHERE 1=1
    """
    params = []
    if selected_region:
        query += " AND r.region = ?"
        params.append(selected_region)
    if selected_year:
        query += " AND v.year = ?"
        params.append(int(selected_year) if str(selected_year).isdigit() else selected_year)
        
    query += " ORDER BY v.coverage DESC LIMIT 100;"
    records = query_db(query, params)
    
    return render_template('regional.html', regions=regions, years=years, 
                           records=records, sel_region=selected_region, sel_year=selected_year)

@app.route('/economic', methods=['GET', 'POST'])
def economic():
    # Economy table holds economic status labels; Country.economy is the FK
    statuses = query_db("SELECT DISTINCT phase as EconomicStatus FROM Economy WHERE phase IS NOT NULL ORDER BY phase;")
    selected_status = request.form.get('status') if request.method == 'POST' else None
    
    # Join: InfectionData -> Country -> Economy -> Infection_Type
    query = """
        SELECT 
            c.name          AS CountryName,
            e.phase         AS EconomicStatus,
            it.description  AS InfectionType,
            i.cases         AS ReportedCases,
            i.year          AS Year
        FROM InfectionData i
        JOIN Country c       ON i.country  = c.CountryID
        JOIN Economy e       ON c.economy  = e.economyID
        JOIN Infection_Type it ON i.inf_type = it.id
    """
    params = []
    if selected_status:
        query += " WHERE e.phase = ?"
        params.append(selected_status)
    query += " ORDER BY i.cases DESC LIMIT 100;"
    
    records = query_db(query, params)
    return render_template('economic.html', statuses=statuses, records=records, sel_status=selected_status)

# ==========================================
# LEVEL 3 ROUTES: Deep Analysis Subqueries
# ==========================================

@app.route('/improvement', methods=['GET', 'POST'])
def improvement():
    # Use Antigen table for the dropdown list of antigen names
    antigens = query_db("SELECT DISTINCT antigen as Antigen FROM Vaccination ORDER BY antigen;")
    sel_antigen = request.form.get('antigen', 'DTPCV3')
    sel_start   = request.form.get('start_year', '2000')
    sel_end     = request.form.get('end_year', '2024')
    limit_n     = request.form.get('limit', '10')
    
    # Self-join Vaccination to compare coverage between two years
    query = """
        SELECT 
            v1.country          AS CountryID,
            c.name              AS CountryName,
            v1.antigen          AS Antigen,
            v1.coverage         AS StartCoverage, 
            v2.coverage         AS EndCoverage,
            (v2.coverage - v1.coverage) AS ProgressJump
        FROM Vaccination v1
        JOIN Vaccination v2 ON v1.country = v2.country AND v1.antigen = v2.antigen
        JOIN Country c      ON v1.country = c.CountryID
        WHERE v1.antigen = ? AND v1.year = ? AND v2.year = ?
        ORDER BY ProgressJump DESC
        LIMIT ?;
    """
    records = query_db(query, [sel_antigen, int(sel_start), int(sel_end), int(limit_n)])
    return render_template('improvement.html', antigens=antigens, records=records,
                           sel_antigen=sel_antigen, sel_start=sel_start, sel_end=sel_end, limit=limit_n)

@app.route('/integrity', methods=['GET', 'POST'])
def integrity():
    years = query_db("SELECT DISTINCT year as Year FROM InfectionData ORDER BY year DESC;")
    sel_year = request.form.get('year', '2020')
    
    # CasesPer100k using InfectionData.cases / CountryPopulation.population
    query = """
        SELECT 
            c.name          AS CountryName,
            it.description  AS InfectionType,
            i.cases         AS ReportedCases,
            i.year          AS Year,
            ((i.cases * 100000.0) / cp.population) AS CasesPer100k
        FROM InfectionData i
        JOIN Country c         ON i.country  = c.CountryID
        JOIN Infection_Type it ON i.inf_type  = it.id
        JOIN CountryPopulation cp ON i.country = cp.country AND i.year = cp.year
        WHERE i.year = ? 
        AND ((i.cases * 100000.0) / cp.population) > (
            SELECT AVG((sub_i.cases * 100000.0) / sub_cp.population)
            FROM InfectionData sub_i
            JOIN CountryPopulation sub_cp 
              ON sub_i.country = sub_cp.country AND sub_i.year = sub_cp.year
            WHERE sub_i.year = ?
        )
        ORDER BY CasesPer100k DESC;
    """
    records = query_db(query, [int(sel_year), int(sel_year)])
    
    avg_row = query_db("""
        SELECT AVG((sub_i.cases * 100000.0) / sub_cp.population) AS global_avg
        FROM InfectionData sub_i
        JOIN CountryPopulation sub_cp 
          ON sub_i.country = sub_cp.country AND sub_i.year = sub_cp.year
        WHERE sub_i.year = ?;
    """, [int(sel_year)], one=True)
    
    return render_template('integrity.html', years=years, records=records, 
                           sel_year=sel_year, global_avg=avg_row['global_avg'] if avg_row else 0)

if __name__ == '__main__':
    app.run(debug=True, port=5000)