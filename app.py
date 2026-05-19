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

    total_doses = query_db("SELECT SUM(doses) as total FROM Vaccination;", one=True)
    total_cases = query_db("SELECT SUM(cases) as total FROM InfectionData;", one=True)
    global_coverage = query_db("SELECT COUNT(DISTINCT CountryID) as count FROM Country;", one=True)
    distinct_diseases = query_db("SELECT COUNT(DISTINCT inf_type) as count FROM InfectionData;", one=True)

    search_query = request.args.get('disease_search', '').strip()
    search_results = []

    if search_query:
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
    regions  = query_db("SELECT DISTINCT region AS RegionName FROM Region WHERE region IS NOT NULL ORDER BY region;")
    years    = query_db("SELECT DISTINCT year AS Year FROM Vaccination ORDER BY year DESC;")
    antigens = query_db("SELECT DISTINCT antigen AS Antigen FROM Vaccination ORDER BY antigen;")
    
    selected_region  = request.form.get('region') if request.method == 'POST' else None
    selected_year    = request.form.get('year', '2010') if request.method == 'POST' else '2010'
    selected_antigen = request.form.get('antigen', 'MCV2') if request.method == 'POST' else 'MCV2'

    # TABLE 1
    t1_query = """
    SELECT
        c.name                      AS CountryName,
        r.region                    AS RegionName,
        v.antigen                   AS Antigen,
        v.year                      AS Year,
        ROUND(CAST(v.coverage AS REAL), 2) AS CoveragePct,
        CAST(v.doses      AS INTEGER)  AS DosesAdministered,
        CAST(v.target_num AS INTEGER)  AS TargetPop
    FROM Vaccination v
    JOIN Country c ON v.country = c.CountryID
    JOIN Region  r ON c.region  = r.RegionID
    WHERE v.antigen = ? AND v.year = ? AND v.coverage != '' AND v.coverage IS NOT NULL AND CAST(v.coverage AS REAL) >= 90
    """
    t1_params = [selected_antigen, int(selected_year)]
    if selected_region:
        t1_query += " AND r.region = ?"
        t1_params.append(selected_region)
    t1_query += " ORDER BY CAST(v.coverage AS REAL) DESC;"
    table1 = query_db(t1_query, t1_params)

    # TABLE 2
    t2_query = """
    SELECT
        r.region  AS RegionName,
        v.antigen AS Antigen,
        v.year    AS Year,
        COUNT(DISTINCT v.country)                          AS CountriesMet,
        ROUND(AVG(CAST(v.coverage AS REAL)), 1)            AS AvgCoverage,
        COUNT(DISTINCT CASE WHEN CAST(v.coverage AS REAL) >= 90 THEN v.country END) AS CountriesAt90
    FROM Vaccination v
    JOIN Country c ON v.country = c.CountryID
    JOIN Region  r ON c.region  = r.RegionID
    WHERE v.antigen = ? AND v.year = ? AND v.coverage != '' AND v.coverage IS NOT NULL
    """
    t2_params = [selected_antigen, int(selected_year)]
    if selected_region:
        t2_query += " AND r.region = ?"
        t2_params.append(selected_region)
    t2_query += " GROUP BY r.region, v.antigen, v.year ORDER BY CountriesAt90 DESC;"
    table2 = query_db(t2_query, t2_params)

    # Sidebar Summary Stats
    stats_query = """
    SELECT
        ROUND(AVG(CAST(coverage AS REAL)), 1) AS AvgCoverage,
        COUNT(DISTINCT country)               AS TotalCountries
    FROM Vaccination v
    JOIN Country c ON v.country = c.CountryID
    JOIN Region  r ON c.region  = r.RegionID
    WHERE v.antigen = ? AND v.year = ? AND v.coverage != '' AND v.coverage IS NOT NULL
    """
    stats_params = [selected_antigen, int(selected_year)]
    if selected_region:
        stats_query += " AND r.region = ?"
        stats_params.append(selected_region)
    stats = query_db(stats_query, stats_params, one=True)

    return render_template('regional.html',
                           regions=regions, years=years, antigens=antigens,
                           table1=table1, table2=table2, stats=stats,
                           sel_region=selected_region, sel_year=selected_year, sel_antigen=selected_antigen)

@app.route('/economic', methods=['GET', 'POST'])
def economic():
    statuses      = query_db("SELECT DISTINCT phase AS EconomicStatus FROM Economy WHERE phase IS NOT NULL ORDER BY phase;")
    diseases      = query_db("SELECT DISTINCT description AS Disease FROM Infection_Type ORDER BY description;")
    years         = query_db("SELECT DISTINCT year AS Year FROM InfectionData ORDER BY year DESC;")
    year_ranges   = ['2000-2024','2000-2009','2010-2019','2020-2024']

    if request.method == 'POST':
        sel_disease    = request.form.get('disease',    'Measles')
        sel_year       = request.form.get('year',       '2022')
        sel_year_range = request.form.get('year_range', '2020-2024')
        sel_left_econ  = request.form.get('left_econ',  'High Income')
        sel_right_econ = request.form.get('right_econ', 'Low Income')
    else:
        sel_disease    = 'Measles'
        sel_year       = '2022'
        sel_year_range = '2020-2024'
        sel_left_econ  = 'High Income'
        sel_right_econ = 'Low Income'

    yr_parts   = sel_year_range.split('-')
    yr_start   = int(yr_parts[0])
    yr_end     = int(yr_parts[1])

    # TABLE 1
    sort_col = request.args.get('sort', 'CasesPer100k')
    sort_dir = request.args.get('dir',  'desc')
    allowed_sorts = {'Country','EconPhase','Year','Disease','CasesPer100k'}
    if sort_col not in allowed_sorts:
        sort_col = 'CasesPer100k'
    order_clause = f"{sort_col} {'DESC' if sort_dir == 'desc' else 'ASC'}"

    t1_query = f"""
    SELECT
        it.description                                          AS Disease,
        c.name                                                  AS Country,
        e.phase                                                 AS EconPhase,
        i.year                                                  AS Year,
        i.cases                                                 AS RawCases,
        ROUND((i.cases * 100000.0) / cp.population, 2)         AS CasesPer100k
    FROM InfectionData i
    JOIN Country           c  ON i.country  = c.CountryID
    JOIN Economy           e  ON c.economy  = e.economyID
    JOIN Infection_Type    it ON i.inf_type  = it.id
    JOIN CountryPopulation cp ON i.country  = cp.country AND i.year = cp.year
    WHERE it.description = ? AND i.year = ? AND e.phase = ? AND i.cases > 0
    ORDER BY {order_clause};
    """
    table1 = query_db(t1_query, [sel_disease, int(sel_year), sel_left_econ])

    # TABLE 2
    table2 = query_db("""
    SELECT
        it.description  AS Disease,
        e.phase         AS EconPhase,
        i.year          AS Year,
        SUM(i.cases)    AS TotalCases,
        COUNT(DISTINCT i.country) AS CountryCount
    FROM InfectionData i
    JOIN Country        c  ON i.country = c.CountryID
    JOIN Economy        e  ON c.economy = e.economyID
    JOIN Infection_Type it ON i.inf_type = it.id
    WHERE it.description = ? AND i.year = ?
    GROUP BY e.phase, i.year
    ORDER BY TotalCases DESC;
    """, [sel_disease, int(sel_year)])

    # Trend data function for split-screen charts
    def get_trend(econ_phase):
        return query_db("""
        SELECT
            v.year                                           AS Year,
            ROUND(AVG(CAST(v.coverage AS REAL)), 1)         AS AvgCoverage,
            ROUND(AVG(CASE WHEN cp.population > 0 THEN (i.cases * 100000.0) / cp.population END), 2) AS AvgInfRate,
            COUNT(DISTINCT v.country)                        AS CountryCount
        FROM Vaccination v
        JOIN Country           c  ON v.country = c.CountryID
        JOIN Economy           e  ON c.economy = e.economyID
        LEFT JOIN InfectionData i  ON i.country = v.country AND i.year = v.year
        LEFT JOIN CountryPopulation cp ON cp.country = v.country AND cp.year = v.year
        WHERE e.phase = ? AND v.year BETWEEN ? AND ?
        GROUP BY v.year
        ORDER BY v.year;
        """, [econ_phase, yr_start, yr_end])

    # FIX: Run trends and directly transform the Row structures into plain JSON dictionaries
    raw_left_trend  = get_trend(sel_left_econ)
    raw_right_trend = get_trend(sel_right_econ)
    left_trend      = [dict(row) for row in raw_left_trend]
    right_trend     = [dict(row) for row in raw_right_trend]

    # Summary stat cards calculation
    def get_stats(econ_phase):
        latest = query_db("""
        SELECT ROUND(AVG(CAST(v.coverage AS REAL)),1) AS AvgCov, COUNT(DISTINCT v.country) AS Countries
        FROM   Vaccination v
        JOIN   Country c ON v.country = c.CountryID
        JOIN   Economy e ON c.economy = e.economyID
        WHERE  e.phase = ? AND v.year = ?;
        """, [econ_phase, yr_end], one=True)
        
        earliest = query_db("""
        SELECT ROUND(AVG(CAST(v.coverage AS REAL)),1) AS AvgCov
        FROM   Vaccination v
        JOIN   Country c ON v.country = c.CountryID
        JOIN   Economy e ON c.economy = e.economyID
        WHERE  e.phase = ? AND v.year = ?;
        """, [econ_phase, yr_start], one=True)
        
        # FIX: Added missing '*' operator for multiplication syntax rules
        inf_latest = query_db("""
        SELECT ROUND(AVG((i.cases * 100000.0)/cp.population),2) AS AvgRate
        FROM   InfectionData i
        JOIN   Country c ON i.country = c.CountryID
        JOIN   Economy e ON c.economy = e.economyID
        JOIN   CountryPopulation cp ON cp.country = i.country AND cp.year = i.year
        WHERE  e.phase = ? AND i.year = ? AND cp.population > 0;
        """, [econ_phase, yr_end], one=True)
        
        inf_earliest = query_db("""
        SELECT ROUND(AVG((i.cases * 100000.0)/cp.population),2) AS AvgRate
        FROM   InfectionData i
        JOIN   Country c ON i.country = c.CountryID
        JOIN   Economy e ON c.economy = e.economyID
        JOIN   CountryPopulation cp ON cp.country = i.country AND cp.year = i.year
        WHERE  e.phase = ? AND i.year = ? AND cp.population > 0;
        """, [econ_phase, yr_start], one=True)
        
        cov_now   = latest['AvgCov']   or 0 if latest else 0
        cov_then  = earliest['AvgCov'] or 0 if earliest else 0
        inf_now   = inf_latest['AvgRate']   or 0 if inf_latest else 0
        inf_then  = inf_earliest['AvgRate'] or 0 if inf_earliest else 0
        
        return {
            'countries':    latest['Countries'] or 0 if latest else 0,
            'cov_now':      cov_now,
            'cov_change':   round(cov_now - cov_then, 1),
            'inf_now':      inf_now,
            'inf_change':   round(inf_now - inf_then, 2),
        }

    left_stats  = get_stats(sel_left_econ)
    right_stats = get_stats(sel_right_econ)

    cov_gap = round(abs(left_stats['cov_now'] - right_stats['cov_now']), 1)
    inf_gap = round(abs(left_stats['inf_now'] - right_stats['inf_now']), 2)
    both_improving = left_stats['cov_change'] > 0 and right_stats['cov_change'] > 0

    return render_template('economic.html',
                           statuses=statuses, diseases=diseases, years=years, year_ranges=year_ranges,
                           sel_disease=sel_disease, sel_year=sel_year, sel_year_range=sel_year_range,
                           sel_left_econ=sel_left_econ, sel_right_econ=sel_right_econ,
                           table1=table1, table2=table2,
                           left_trend=left_trend, right_trend=right_trend,
                           left_stats=left_stats, right_stats=right_stats,
                           cov_gap=cov_gap, inf_gap=inf_gap, both_improving=both_improving,
                           sort_col=sort_col, sort_dir=sort_dir, yr_start=yr_start, yr_end=yr_end)

# ==========================================
# LEVEL 3 ROUTES: Deep Analysis Subqueries
# ==========================================
@app.route('/improvement', methods=['GET', 'POST'])
def improvement():
    antigens = query_db("SELECT DISTINCT antigen as Antigen FROM Vaccination ORDER BY antigen;")
    sel_antigen = request.form.get('antigen', 'DTPCV3')
    sel_start   = request.form.get('start_year', '2000')
    sel_end     = request.form.get('end_year', '2024')
    limit_n     = request.form.get('limit', '10')

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
            JOIN CountryPopulation sub_cp ON sub_i.country = sub_cp.country AND sub_i.year = sub_cp.year
            WHERE sub_i.year = ?
        )
        ORDER BY CasesPer100k DESC;
    """
    records = query_db(query, [int(sel_year), int(sel_year)])

    avg_row = query_db("""
        SELECT AVG((sub_i.cases * 100000.0) / sub_cp.population) AS global_avg
        FROM InfectionData sub_i
        JOIN CountryPopulation sub_cp ON sub_i.country = sub_cp.country AND sub_i.year = sub_cp.year
        WHERE sub_i.year = ?;
    """, [int(sel_year)], one=True)

    return render_template('integrity.html', years=years, records=records, 
                           sel_year=sel_year, global_avg=avg_row['global_avg'] if avg_row else 0)

if __name__ == '__main__':
    app.run(debug=True, port=5000)