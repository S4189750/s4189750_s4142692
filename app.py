from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)
# Built-in fallback helper registration 
app.jinja_env.globals.update(int=int)
DB_FILE = "immunisation.db"

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# 1. Ensure the table exists
cur.execute("""
    CREATE TABLE IF NOT EXISTS ProjectMetadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        identifier TEXT,
        role TEXT NOT NULL
    );
""")

# 2. Clear out the old placeholder data
cur.execute("DELETE FROM ProjectMetadata;")

# 3. Insert the exact Team Members and Personas
metadata_entries = [
    ("Hiya Rana", "s4142692", "Team Member"),
    ("Bach Nguyen Ho Viet", "s4189750", "Team Member"),
    ("Marie Jose", "Level 1 User", "Persona"),
    ("Derek Nguyen", "Level 2/3 User", "Persona")
]

cur.executemany("""
    INSERT INTO ProjectMetadata (name, identifier, role) 
    VALUES (?, ?, ?);
""", metadata_entries)

conn.commit()
conn.close()

def query_db(query, args=(), one=False):
    """Helper function to cleanly open, execute, and pull data rows from SQLite."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv
 
def rows_to_dicts(rows):
    """Convert sqlite3.Row objects to plain dicts — required for tojson in Jinja templates."""
    return [dict(row) for row in rows]

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
        'start':      timeframe['start'] if timeframe else 2000,
        'start_year': timeframe['start'] if timeframe else 2000,
        'end':        timeframe['end']   if timeframe else 2024,
        'end_year':   timeframe['end']   if timeframe else 2024
    }

    total_doses       = query_db("SELECT SUM(doses) as total FROM Vaccination;", one=True)
    total_cases       = query_db("SELECT SUM(cases) as total FROM InfectionData;", one=True)
    global_coverage   = query_db("SELECT COUNT(DISTINCT CountryID) as count FROM Country;", one=True)
    distinct_diseases = query_db("SELECT COUNT(DISTINCT inf_type) as count FROM InfectionData;", one=True)

    search_query   = request.args.get('disease_search', '').strip()
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
    # Fetch all records from the metadata table
    try:
        metadata_rows = query_db("SELECT name, identifier, role FROM ProjectMetadata;")
    except sqlite3.OperationalError:
        # Fallback to empty list if the table hasn't been created yet
        metadata_rows = []
        
    return render_template('mission.html', metadata=metadata_rows)


# ==========================================
# LEVEL 2 ROUTES: Filtering Views
# ==========================================

@app.route('/regional', methods=['GET', 'POST'])
def regional():
    regions  = query_db("SELECT DISTINCT region AS RegionName FROM Region WHERE region IS NOT NULL ORDER BY region;")
    years    = query_db("SELECT DISTINCT year AS Year FROM Vaccination ORDER BY year DESC;")
    antigens = query_db("SELECT DISTINCT antigen AS Antigen FROM Vaccination ORDER BY antigen;")

    selected_region  = request.form.get('region')           if request.method == 'POST' else None
    selected_year    = request.form.get('year',   '2010')   if request.method == 'POST' else '2010'
    selected_antigen = request.form.get('antigen', 'MCV2')  if request.method == 'POST' else 'MCV2'

    # Table 1 sort configuration
    t1_sort     = request.form.get('t1_sort', 'CoveragePct')
    t1_sort_dir = request.form.get('t1_sort_dir', 'DESC')
    t1_allowed  = {'CountryName': 'c.name', 'CoveragePct': 'CAST(v.coverage AS REAL)'}
    t1_order    = f"{t1_allowed.get(t1_sort, 'CAST(v.coverage AS REAL)')} {t1_sort_dir}"

    # Table 2 sort configuration
    t2_sort     = request.form.get('t2_sort', 'AvgCoverage')
    t2_sort_dir = request.form.get('t2_sort_dir', 'DESC')
    t2_allowed  = {'AvgCoverage': 'AvgCoverage', 'CountriesAt90': 'CountriesAt90', 'RegionName': 'r.region'}
    t2_order    = f"{t2_allowed.get(t2_sort, 'AvgCoverage')} {t2_sort_dir}"

    # ── TABLE 1 ──
    t1_query = f"""
        SELECT
            c.name                             AS CountryName,
            r.region                           AS RegionName,
            v.antigen                          AS Antigen,
            v.year                             AS Year,
            ROUND(CAST(v.coverage AS REAL), 2) AS CoveragePct,
            CAST(v.doses      AS INTEGER)      AS DosesAdministered,
            CAST(v.target_num AS INTEGER)      AS TargetPop
        FROM  Vaccination v
        JOIN  Country c ON v.country = c.CountryID
        JOIN  Region  r ON c.region  = r.RegionID
        WHERE v.antigen = ? AND v.year = ?
          AND v.coverage != '' AND v.coverage IS NOT NULL
          AND CAST(v.coverage AS REAL) >= 90
    """
    t1_params = [selected_antigen, int(selected_year)]
    if selected_region:
        t1_query += " AND r.region = ?"
        t1_params.append(selected_region)
    t1_query += f" ORDER BY {t1_order};"
    table1 = query_db(t1_query, t1_params)

    # ── TABLE 2 ──
    t2_query = f"""
        SELECT
            r.region  AS RegionName,
            v.antigen AS Antigen,
            v.year    AS Year,
            COUNT(DISTINCT v.country)                                       AS CountriesMet,
            ROUND(AVG(CAST(v.coverage AS REAL)), 1)                         AS AvgCoverage,
            COUNT(DISTINCT CASE WHEN CAST(v.coverage AS REAL) >= 90
                                THEN v.country END)                         AS CountriesAt90
        FROM  Vaccination v
        JOIN  Country c ON v.country = c.CountryID
        JOIN  Region  r ON c.region  = r.RegionID
        WHERE v.antigen = ? AND v.year = ?
          AND v.coverage != '' AND v.coverage IS NOT NULL
    """
    t2_params = [selected_antigen, int(selected_year)]
    if selected_region:
        t2_query += " AND r.region = ?"
        t2_params.append(selected_region)
    t2_query += f" GROUP BY r.region, v.antigen, v.year ORDER BY {t2_order};"
    table2 = query_db(t2_query, t2_params)

    # ── Sidebar Stats ──
    stats_query = """
        SELECT
            ROUND(AVG(CAST(coverage AS REAL)), 1) AS AvgCoverage,
            COUNT(DISTINCT country)               AS TotalCountries
        FROM  Vaccination v
        JOIN  Country c ON v.country = c.CountryID
        JOIN  Region  r ON c.region  = r.RegionID
        WHERE v.antigen = ? AND v.year = ?
          AND v.coverage != '' AND v.coverage IS NOT NULL
    """
    stats_params = [selected_antigen, int(selected_year)]
    if selected_region:
        stats_query += " AND r.region = ?"
        stats_params.append(selected_region)
    stats = query_db(stats_query, stats_params, one=True)

    return render_template('regional.html',
                           regions=regions, years=years, antigens=antigens,
                           table1=table1, table2=table2, stats=stats,
                           sel_region=selected_region,
                           sel_year=selected_year,
                           sel_antigen=selected_antigen,
                           t1_sort=t1_sort, t1_sort_dir=t1_sort_dir,
                           t2_sort=t2_sort, t2_sort_dir=t2_sort_dir)


@app.route('/economic', methods=['GET', 'POST'])
def economic():
    statuses    = query_db("SELECT DISTINCT phase AS EconomicStatus FROM Economy WHERE phase IS NOT NULL ORDER BY phase;")
    diseases    = query_db("SELECT DISTINCT description AS Disease FROM Infection_Type ORDER BY description;")
    years       = query_db("SELECT DISTINCT year AS Year FROM InfectionData ORDER BY year DESC;")
    year_ranges = ['2000-2024', '2000-2009', '2010-2019', '2020-2024']

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

    yr_parts = sel_year_range.split('-')
    yr_start = int(yr_parts[0])
    yr_end   = int(yr_parts[1])

    sort_col = request.args.get('sort', 'CasesPer100k')
    sort_dir = request.args.get('dir',  'desc')
    allowed_sorts = {'Country', 'EconPhase', 'Year', 'Disease', 'CasesPer100k'}
    if sort_col not in allowed_sorts:
        sort_col = 'CasesPer100k'
    order_clause = f"{sort_col} {'DESC' if sort_dir == 'desc' else 'ASC'}"

    t1_query = f"""
        SELECT
            it.description                                  AS Disease,
            c.name                                          AS Country,
            e.phase                                         AS EconPhase,
            i.year                                          AS Year,
            i.cases                                         AS RawCases,
            ROUND((i.cases * 100000.0) / cp.population, 2) AS CasesPer100k
        FROM  InfectionData i
        JOIN  Country           c  ON i.country  = c.CountryID
        JOIN  Economy           e  ON c.economy   = e.economyID
        JOIN  Infection_Type    it ON i.inf_type  = it.id
        JOIN  CountryPopulation cp ON i.country   = cp.country AND i.year = cp.year
        WHERE it.description = ? AND i.year = ? AND e.phase = ? AND i.cases > 0
        ORDER BY {order_clause};
    """
    table1 = query_db(t1_query, [sel_disease, int(sel_year), sel_left_econ])

    table2 = query_db("""
        SELECT
            it.description            AS Disease,
            e.phase                   AS EconPhase,
            i.year                    AS Year,
            SUM(i.cases)              AS TotalCases,
            COUNT(DISTINCT i.country) AS CountryCount
        FROM  InfectionData i
        JOIN  Country        c  ON i.country  = c.CountryID
        JOIN  Economy        e  ON c.economy   = e.economyID
        JOIN  Infection_Type it ON i.inf_type  = it.id
        WHERE it.description = ? AND i.year = ?
        GROUP BY e.phase, i.year
        ORDER BY TotalCases DESC;
    """, [sel_disease, int(sel_year)])

    def get_trend(econ_phase):
        rows = query_db("""
            SELECT
                v.year                                  AS Year,
                ROUND(AVG(CAST(v.coverage AS REAL)), 1) AS AvgCoverage,
                ROUND(AVG(
                    CASE WHEN cp.population > 0
                         THEN (i.cases * 100000.0) / cp.population
                    END
                ), 2)                                   AS AvgInfRate,
                COUNT(DISTINCT v.country)               AS CountryCount
            FROM  Vaccination v
            JOIN  Country           c  ON v.country = c.CountryID
            JOIN  Economy           e  ON c.economy  = e.economyID
            LEFT JOIN InfectionData i  ON i.country  = v.country AND i.year = v.year
            LEFT JOIN CountryPopulation cp ON cp.country = v.country AND cp.year = v.year
            WHERE e.phase = ? AND v.year BETWEEN ? AND ?
            GROUP BY v.year
            ORDER BY v.year;
        """, [econ_phase, yr_start, yr_end])
        return rows_to_dicts(rows)

    left_trend  = get_trend(sel_left_econ)
    right_trend = get_trend(sel_right_econ)

    def get_stats(econ_phase):
        latest = query_db("""
            SELECT ROUND(AVG(CAST(v.coverage AS REAL)), 1) AS AvgCov,
                   COUNT(DISTINCT v.country)               AS Countries
            FROM   Vaccination v
            JOIN   Country c ON v.country = c.CountryID
            JOIN   Economy e ON c.economy  = e.economyID
            WHERE  e.phase = ? AND v.year = ?;
        """, [econ_phase, yr_end], one=True)
        earliest = query_db("""
            SELECT ROUND(AVG(CAST(v.coverage AS REAL)), 1) AS AvgCov
            FROM   Vaccination v
            JOIN   Country c ON v.country = c.CountryID
            JOIN   Economy e ON c.economy  = e.economyID
            WHERE  e.phase = ? AND v.year = ?;
        """, [econ_phase, yr_start], one=True)
        inf_latest = query_db("""
            SELECT ROUND(AVG((i.cases * 100000.0) / cp.population), 2) AS AvgRate
            FROM   InfectionData i
            JOIN   Country c ON i.country = c.CountryID
            JOIN   Economy e ON c.economy  = e.economyID
            JOIN   CountryPopulation cp ON cp.country = i.country AND cp.year = i.year
            WHERE  e.phase = ? AND i.year = ? AND cp.population > 0;
        """, [econ_phase, yr_end], one=True)
        inf_earliest = query_db("""
            SELECT ROUND(AVG((i.cases * 100000.0) / cp.population), 2) AS AvgRate
            FROM   InfectionData i
            JOIN   Country c ON i.country = c.CountryID
            JOIN   Economy e ON c.economy  = e.economyID
            JOIN   CountryPopulation cp ON cp.country = i.country AND cp.year = i.year
            WHERE  e.phase = ? AND i.year = ? AND cp.population > 0;
        """, [econ_phase, yr_start], one=True)
        cov_now  = (latest['AvgCov']        or 0) if latest   else 0
        cov_then = (earliest['AvgCov']      or 0) if earliest else 0
        inf_now  = (inf_latest['AvgRate']   or 0) if inf_latest   else 0
        inf_then = (inf_earliest['AvgRate'] or 0) if inf_earliest else 0
        return {
            'countries':  (latest['Countries'] or 0) if latest else 0,
            'cov_now':    cov_now,
            'cov_change': round(cov_now  - cov_then,  1),
            'inf_now':    inf_now,
            'inf_change': round(inf_now  - inf_then,  2),
        }

    left_stats  = get_stats(sel_left_econ)
    right_stats = get_stats(sel_right_econ)

    cov_gap       = round(abs(left_stats['cov_now'] - right_stats['cov_now']), 1)
    inf_gap       = round(abs(left_stats['inf_now'] - right_stats['inf_now']), 2)
    both_improving = left_stats['cov_change'] > 0 and right_stats['cov_change'] > 0

    return render_template('economic.html',
        statuses=statuses, diseases=diseases, years=years, year_ranges=year_ranges,
        sel_disease=sel_disease, sel_year=sel_year,
        sel_year_range=sel_year_range,
        sel_left_econ=sel_left_econ, sel_right_econ=sel_right_econ,
        table1=table1, table2=table2,
        left_trend=left_trend, right_trend=right_trend,
        left_stats=left_stats, right_stats=right_stats,
        cov_gap=cov_gap, inf_gap=inf_gap,
        both_improving=both_improving,
        sort_col=sort_col, sort_dir=sort_dir,
        yr_start=yr_start, yr_end=yr_end,
    )


# ==========================================
# LEVEL 3 ROUTES: Deep Analysis Subqueries
# ==========================================

@app.route('/improvement', methods=['GET', 'POST'])
def improvement():
    sidebar_antigens = query_db("""
        SELECT
            a.AntigenID                                    AS Antigen,
            a.name                                         AS AntigenName,
            ROUND(AVG(CAST(v.coverage AS REAL)), 0)        AS AvgCoverage2024
        FROM Antigen a
        LEFT JOIN Vaccination v
               ON a.AntigenID = v.antigen
              AND v.year      = 2024
              AND v.coverage != ''
              AND v.coverage IS NOT NULL
        GROUP BY a.AntigenID, a.name
        ORDER BY a.AntigenID;
    """)

    if request.method == 'POST':
        sel_antigen = request.form.get('antigen',    'DTPCV3')
        sel_start   = request.form.get('start_year', '2000')
        sel_end     = request.form.get('end_year',   '2024')
        limit_n     = request.form.get('limit',      '10')
        sort_by     = request.form.get('sort_by',    'RateIncrease')
    else:
        sel_antigen = request.args.get('antigen',    'DTPCV3')
        sel_start   = '2000'
        sel_end     = '2024'
        limit_n     = '10'
        sort_by     = 'RateIncrease'

    allowed_sorts = {'RateIncrease', 'Country', 'StartRate', 'EndRate'}
    if sort_by not in allowed_sorts:
        sort_by = 'RateIncrease'

    subtask_a = query_db(f"""
        SELECT
            c.name                                                          AS Country,
            r.region                                                        AS Region,
            e.phase                                                         AS EconPhase,
            v1.year                                                         AS StartYear,
            v2.year                                                         AS EndYear,
            ROUND((CAST(v1.doses AS REAL) / cp1.population) * 100, 2)      AS StartRate,
            ROUND((CAST(v2.doses AS REAL) / cp2.population) * 100, 2)      AS EndRate,
            ROUND(
                ((CAST(v2.doses AS REAL) / cp2.population)
               - (CAST(v1.doses AS REAL) / cp1.population)) * 100
            , 2)                                                            AS RateIncrease
        FROM  Vaccination v1
        JOIN  Vaccination       v2  ON  v1.country = v2.country
                                    AND v1.antigen  = v2.antigen
        JOIN  Country           c   ON  v1.country = c.CountryID
        JOIN  Region            r   ON  c.region   = r.RegionID
        JOIN  Economy           e   ON  c.economy  = e.economyID
        JOIN  CountryPopulation cp1 ON  v1.country = cp1.country AND v1.year = cp1.year
        JOIN  CountryPopulation cp2 ON  v2.country = cp2.country AND v2.year = cp2.year
        WHERE v1.antigen     = ?
          AND v1.year        = ?
          AND v2.year        = ?
          AND cp1.population > 0
          AND cp2.population > 0
          AND v1.doses IS NOT NULL
          AND v2.doses IS NOT NULL
        ORDER BY {sort_by} DESC
        LIMIT ?;
    """, [sel_antigen, int(sel_start), int(sel_end), int(limit_n)])

    headline = query_db("""
        SELECT
            v.antigen                                                  AS Antigen,
            ROUND(AVG(CAST(v.coverage AS REAL)), 0)                    AS GlobalCoverage,
            COUNT(CASE WHEN CAST(v.coverage AS REAL) < 90 THEN 1 END) AS ZeroDoseCountries
        FROM Vaccination v
        WHERE v.antigen = ? AND v.year = 2024
          AND v.coverage != '' AND v.coverage IS NOT NULL
        GROUP BY v.antigen;
    """, [sel_antigen], one=True)

    historical = rows_to_dicts(query_db("""
        SELECT
            v.year                                                                     AS Year,
            ROUND(AVG(CASE WHEN e.phase IN ('High Income','Upper Middle Income')
                           THEN CAST(v.coverage AS REAL) END), 1)                     AS HigherIncome,
            ROUND(AVG(CASE WHEN e.phase IN ('Low Income','Lower Middle Income')
                           THEN CAST(v.coverage AS REAL) END), 1)                     AS LowerIncome
        FROM  Vaccination v
        JOIN  Country c ON v.country = c.CountryID
        JOIN  Economy e ON c.economy = e.economyID
        WHERE v.antigen = ? AND v.year >= 2015
          AND v.coverage != '' AND v.coverage IS NOT NULL
        GROUP BY v.year
        ORDER BY v.year;
    """, [sel_antigen]))

    zero_dose = query_db("""
        SELECT
            v.year                                                                  AS Year,
            COUNT(CASE WHEN CAST(v.coverage AS REAL) < 90 THEN 1 END)              AS ZeroDoseCount,
            ROUND(AVG(CAST(v.coverage AS REAL)), 0)                                 AS GlobalCoverage,
            ROUND(
                AVG(CASE WHEN e.phase IN ('High Income','Upper Middle Income')
                         THEN CAST(v.coverage AS REAL) END)
              - AVG(CASE WHEN e.phase IN ('Low Income','Lower Middle Income')
                         THEN CAST(v.coverage AS REAL) END)
            , 0)                                                                    AS IncomeGap
        FROM  Vaccination v
        JOIN  Country c ON v.country = c.CountryID
        JOIN  Economy e ON c.economy = e.economyID
        WHERE v.antigen = ?
          AND v.coverage != '' AND v.coverage IS NOT NULL
        GROUP BY v.year
        ORDER BY v.year DESC
        LIMIT 10;
    """, [sel_antigen])

    antigen_info = {
        'DTPCV1': ('DTPCV1 — DTP-Containing Vaccine 1st Dose',
                   'First dose of combined vaccine protecting against three bacterial diseases',
                   'Diphtheria, Tetanus, Pertussis'),
        'DTPCV3': ('DTPCV3 — DTP-Containing Vaccine 3rd Dose',
                   'Third dose of combined vaccine protecting against three bacterial diseases',
                   'Diphtheria, Tetanus, Pertussis'),
        'MCV1':   ('MCV1 — Measles-Containing Vaccine 1st Dose',
                   'First dose of measles-containing vaccine given in routine immunisation',
                   'Measles'),
        'MCV2':   ('MCV2 — Measles-Containing Vaccine 2nd Dose',
                   'Second dose of measles-containing vaccine for sustained protection',
                   'Measles'),
        'RCV1':   ('RCV1 — Rubella-Containing Vaccine',
                   'Rubella-containing vaccine protecting against congenital rubella syndrome',
                   'Rubella'),
    }
    a_title, a_desc, a_protects = antigen_info.get(
        sel_antigen, (sel_antigen, 'Vaccine antigen data', 'Various diseases'))

    return render_template('improvement.html',
        sidebar_antigens=sidebar_antigens,
        subtask_a=subtask_a,
        headline=headline,
        historical=historical,
        zero_dose=zero_dose,
        sel_antigen=sel_antigen,
        sel_start=sel_start,
        sel_end=sel_end,
        limit_n=limit_n,
        sort_by=sort_by,
        a_title=a_title,
        a_desc=a_desc,
        a_protects=a_protects,
    )


# ==========================================
# Integrity route: Finished & Deduplicated
# ==========================================

@app.route('/integrity', methods=['GET', 'POST'])
def integrity():
    years       = query_db("SELECT DISTINCT year AS Year FROM InfectionData ORDER BY year DESC;")
    diseases    = query_db("SELECT DISTINCT description AS Disease FROM Infection_Type ORDER BY description;")
    audit_years = query_db("SELECT DISTINCT year AS Year FROM Vaccination ORDER BY year DESC;")

    if request.method == 'POST':
        sel_year       = request.form.get('year',       '2020')
        sel_disease    = request.form.get('disease',    'Measles')
        sel_quality    = request.form.get('quality',    '')
        sel_audit_year = request.form.get('audit_year', '2024')
        sort_col       = request.form.get('sort_col',   'DiscrepancyPct')
        sort_dir       = request.form.get('sort_dir',   'asc')
    else:
        sel_year       = '2020'
        sel_disease    = 'Measles'
        sel_quality    = ''
        sel_audit_year = '2024'
        sort_col       = 'DiscrepancyPct'
        sort_dir       = 'asc'

    allowed_sorts = {'Country', 'Year', 'AvgCoverage', 'DiscrepancyPct', 'Quality'}
    if sort_col not in allowed_sorts:
        sort_col = 'DiscrepancyPct'
    order_clause = f"{sort_col} {'DESC' if sort_dir == 'desc' else 'ASC'}"

    # ── SUB-TASK B: global row + above-average countries in one UNION query ──
    subtask_b = query_db("""
        SELECT
            'Global'       AS Country,
            it.description AS InfectionType,
            ROUND(AVG((i.cases * 100000.0) / cp.population), 2) AS RatePer100k,
            i.year         AS Year,
            0              AS is_country
        FROM  InfectionData i
        JOIN  Infection_Type    it ON i.inf_type = it.id
        JOIN  CountryPopulation cp ON i.country  = cp.country AND i.year = cp.year
        WHERE it.description = ? AND i.year = ? AND cp.population > 0

        UNION ALL

        SELECT
            c.name         AS Country,
            it.description AS InfectionType,
            ROUND((i.cases * 100000.0) / cp.population, 2) AS RatePer100k,
            i.year         AS Year,
            1              AS is_country
        FROM  InfectionData i
        JOIN  Country           c  ON i.country = c.CountryID
        JOIN  Infection_Type    it ON i.inf_type = it.id
        JOIN  CountryPopulation cp ON i.country  = cp.country AND i.year = cp.year
        WHERE it.description = ?
          AND i.year         = ?
          AND cp.population  > 0
          AND (i.cases * 100000.0) / cp.population > (
              SELECT AVG((s.cases * 100000.0) / sp.population)
              FROM   InfectionData s
              JOIN   CountryPopulation sp ON s.country = sp.country AND s.year = sp.year
              JOIN   Infection_Type   sit ON s.inf_type = sit.id
              WHERE  sit.description = ? AND s.year = ? AND sp.population > 0
          )
        ORDER BY is_country ASC, RatePer100k DESC;
    """, [sel_disease, int(sel_year),
          sel_disease, int(sel_year),
          sel_disease, int(sel_year)])

    # ── AUDIT TABLE: coverage deviation from 100% target, quality tiered in SQL
    quality_filter = ""
    audit_params   = [int(sel_audit_year)]
    if sel_quality:
        quality_filter = """
            HAVING CASE
                WHEN ABS(100 - AVG(CAST(v.coverage AS REAL))) < 2  THEN 'Excellent'
                WHEN ABS(100 - AVG(CAST(v.coverage AS REAL))) < 5  THEN 'Good'
                WHEN ABS(100 - AVG(CAST(v.coverage AS REAL))) < 10 THEN 'Fair'
                ELSE 'Poor'
            END = ?
        """
        audit_params.append(sel_quality)

    audit_records = query_db(f"""
        SELECT
            c.name                                             AS Country,
            v.year                                             AS Year,
            ROUND(AVG(CAST(v.coverage AS REAL)), 1)            AS AvgCoverage,
            ROUND(ABS(100 - AVG(CAST(v.coverage AS REAL))), 1) AS DiscrepancyPct,
            CASE
                WHEN ABS(100 - AVG(CAST(v.coverage AS REAL))) < 2  THEN 'Excellent'
                WHEN ABS(100 - AVG(CAST(v.coverage AS REAL))) < 5  THEN 'Good'
                WHEN ABS(100 - AVG(CAST(v.coverage AS REAL))) < 10 THEN 'Fair'
                ELSE 'Poor'
            END AS Quality
        FROM  Vaccination v
        JOIN  Country c ON v.country = c.CountryID
        WHERE v.year = ?
          AND v.coverage != '' AND v.coverage IS NOT NULL
          AND CAST(v.coverage AS REAL) > 0
        GROUP BY v.country, v.year
        {quality_filter}
        ORDER BY {order_clause};
    """, audit_params)

    # ── Quality summary counts for the 4 stat cards ───────────────────────────
    quality_counts_rows = query_db("""
        SELECT Quality, COUNT(*) AS cnt FROM (
            SELECT CASE
                WHEN ABS(100 - AVG(CAST(v.coverage AS REAL))) < 2  THEN 'Excellent'
                WHEN ABS(100 - AVG(CAST(v.coverage AS REAL))) < 5  THEN 'Good'
                WHEN ABS(100 - AVG(CAST(v.coverage AS REAL))) < 10 THEN 'Fair'
                ELSE 'Poor'
            END AS Quality
            FROM Vaccination v
            WHERE v.year = ?
              AND v.coverage != '' AND v.coverage IS NOT NULL
              AND CAST(v.coverage AS REAL) > 0
            GROUP BY v.country
        )
        GROUP BY Quality
        ORDER BY CASE Quality
            WHEN 'Excellent' THEN 1 WHEN 'Good' THEN 2
            WHEN 'Fair'      THEN 3 WHEN 'Poor' THEN 4
        END;
    """, [int(sel_audit_year)])

    # Convert to plain dict so template can do quality_counts.get('Excellent', 0)
    qc = {row['Quality']: row['cnt'] for row in quality_counts_rows}

    return render_template('integrity.html',
        years=years, diseases=diseases, audit_years=audit_years,
        subtask_b=subtask_b,
        audit_records=audit_records,
        quality_counts=qc,
        sel_year=sel_year,
        sel_disease=sel_disease,
        sel_quality=sel_quality,
        sel_audit_year=sel_audit_year,
        sort_col=sort_col,
        sort_dir=sort_dir,
    )

if __name__ == '__main__':
    app.run(debug=True)