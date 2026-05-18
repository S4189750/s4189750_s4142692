"""
Database initialization script to create and populate the immunisation.db database
with all required tables and sample data.
"""
import sqlite3

DB_FILE = "immunisation.db"

def init_db():
    """Initialize the database with all required tables and sample data."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create Countries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Countries (
            CountryID INTEGER PRIMARY KEY,
            CountryName TEXT NOT NULL,
            RegionName TEXT,
            EconomicStatus TEXT
        )
    """)
    
    # Create CountryPopulation table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CountryPopulation (
            CountryID INTEGER NOT NULL,
            Year INTEGER NOT NULL,
            PopulationValue INTEGER NOT NULL,
            PRIMARY KEY (CountryID, Year),
            FOREIGN KEY (CountryID) REFERENCES Countries(CountryID)
        )
    """)
    
    # Create VaccinationData table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS VaccinationData (
            CountryID INTEGER NOT NULL,
            Year INTEGER NOT NULL,
            Antigen TEXT NOT NULL,
            DosesAdministered INTEGER NOT NULL,
            CoveragePercentage REAL NOT NULL,
            PRIMARY KEY (CountryID, Year, Antigen),
            FOREIGN KEY (CountryID) REFERENCES Countries(CountryID)
        )
    """)
    
    # Create InfectionData table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS InfectionData (
            CountryID INTEGER NOT NULL,
            Year INTEGER NOT NULL,
            InfectionType TEXT NOT NULL,
            ReportedCases INTEGER NOT NULL,
            PRIMARY KEY (CountryID, Year, InfectionType),
            FOREIGN KEY (CountryID) REFERENCES Countries(CountryID)
        )
    """)
    
    # Create TeamMembers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TeamMembers (
            StudentID TEXT PRIMARY KEY,
            Name TEXT NOT NULL,
            Role TEXT
        )
    """)
    
    # Create Personas table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Personas (
            PersonaID INTEGER PRIMARY KEY,
            PersonaName TEXT NOT NULL,
            Description TEXT
        )
    """)
    
    # Insert sample data for Countries
    sample_countries = [
        (1, 'United States', 'North America', 'High Income'),
        (2, 'Brazil', 'South America', 'Upper Middle Income'),
        (3, 'India', 'Asia', 'Lower Middle Income'),
        (4, 'Nigeria', 'Africa', 'Lower Middle Income'),
        (5, 'Germany', 'Europe', 'High Income'),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO Countries (CountryID, CountryName, RegionName, EconomicStatus)
        VALUES (?, ?, ?, ?)
    """, sample_countries)
    
    # Insert sample vaccination data
    sample_vaccinations = [
        (1, 2020, 'DTP3', 85000000, 95.0),
        (1, 2021, 'DTP3', 87000000, 96.0),
        (1, 2022, 'DTP3', 89000000, 97.0),
        (2, 2020, 'DTP3', 45000000, 85.0),
        (2, 2021, 'DTP3', 48000000, 87.0),
        (3, 2020, 'DTP3', 120000000, 75.0),
        (3, 2021, 'DTP3', 125000000, 78.0),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO VaccinationData (CountryID, Year, Antigen, DosesAdministered, CoveragePercentage)
        VALUES (?, ?, ?, ?, ?)
    """, sample_vaccinations)
    
    # Insert sample population data
    sample_populations = [
        (1, 2020, 331000000),
        (1, 2021, 332000000),
        (1, 2022, 333000000),
        (2, 2020, 212500000),
        (2, 2021, 213500000),
        (3, 2020, 1380000000),
        (3, 2021, 1390000000),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO CountryPopulation (CountryID, Year, PopulationValue)
        VALUES (?, ?, ?)
    """, sample_populations)
    
    # Insert sample infection data
    sample_infections = [
        (1, 2020, 'COVID-19', 10000000),
        (1, 2021, 'COVID-19', 5000000),
        (2, 2020, 'COVID-19', 3500000),
        (2, 2021, 'COVID-19', 2000000),
        (3, 2020, 'COVID-19', 8000000),
        (3, 2021, 'COVID-19', 4500000),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO InfectionData (CountryID, Year, InfectionType, ReportedCases)
        VALUES (?, ?, ?, ?)
    """, sample_infections)
    
    # Insert sample team members
    sample_team = [
        ('S001', 'Alice Johnson', 'Data Analyst'),
        ('S002', 'Bob Smith', 'Developer'),
        ('S003', 'Carol White', 'Researcher'),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO TeamMembers (StudentID, Name, Role)
        VALUES (?, ?, ?)
    """, sample_team)
    
    # Insert sample personas
    sample_personas = [
        (1, 'Public Health Official', 'Tracks disease trends and vaccination coverage'),
        (2, 'Epidemiologist', 'Analyzes patterns and outbreaks'),
        (3, 'Government Policy Maker', 'Makes decisions based on vaccination data'),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO Personas (PersonaID, PersonaName, Description)
        VALUES (?, ?, ?)
    """, sample_personas)
    
    conn.commit()
    conn.close()
    print(f"✓ Database '{DB_FILE}' initialized successfully!")

if __name__ == '__main__':
    init_db()