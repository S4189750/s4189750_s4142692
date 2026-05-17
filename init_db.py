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
            Name TEXT,
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
    
    # Insert sample data into Countries
    sample_countries = [
        (1, 'Australia', 'Oceania', 'High-Income'),
        (2, 'Brazil', 'Americas', 'Upper-Middle-Income'),
        (3, 'India', 'Asia', 'Lower-Middle-Income'),
        (4, 'Nigeria', 'Africa', 'Lower-Middle-Income'),
        (5, 'Germany', 'Europe', 'High-Income'),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO Countries (CountryID, CountryName, RegionName, EconomicStatus) VALUES (?, ?, ?, ?)",
        sample_countries
    )
    
    # Insert sample data into CountryPopulation
    sample_populations = [
        (1, 2020, 25687000),
        (1, 2021, 25890000),
        (1, 2022, 26068000),
        (1, 2023, 26280000),
        (1, 2024, 26466000),
        (2, 2020, 212559000),
        (2, 2021, 214326000),
        (2, 2022, 215313000),
        (2, 2023, 216182000),
        (2, 2024, 216837000),
        (3, 2020, 1380004000),
        (3, 2021, 1393409000),
        (3, 2022, 1406632000),
        (3, 2023, 1419173000),
        (3, 2024, 1431775000),
        (4, 2020, 201506000),
        (4, 2021, 206139000),
        (4, 2022, 210820000),
        (4, 2023, 223804000),
        (4, 2024, 229882000),
        (5, 2020, 83370000),
        (5, 2021, 83369000),
        (5, 2022, 83408000),
        (5, 2023, 83503000),
        (5, 2024, 84608000),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO CountryPopulation (CountryID, Year, PopulationValue) VALUES (?, ?, ?)",
        sample_populations
    )
    
    # Insert sample data into VaccinationData
    sample_vaccinations = [
        (1, 2020, 'DTP3', 18000000, 92.5),
        (1, 2021, 'DTP3', 18500000, 93.2),
        (1, 2022, 'DTP3', 19000000, 94.1),
        (1, 2023, 'DTP3', 19500000, 94.8),
        (1, 2024, 'DTP3', 20000000, 95.2),
        (1, 2020, 'Polio', 17500000, 90.1),
        (1, 2021, 'Polio', 18000000, 91.5),
        (1, 2022, 'Polio', 18500000, 92.3),
        (1, 2023, 'Polio', 19000000, 93.1),
        (1, 2024, 'Polio', 19500000, 93.8),
        (2, 2020, 'DTP3', 130000000, 78.5),
        (2, 2021, 'DTP3', 138000000, 80.2),
        (2, 2022, 'DTP3', 145000000, 82.1),
        (2, 2023, 'DTP3', 152000000, 84.3),
        (2, 2024, 'DTP3', 160000000, 85.9),
        (3, 2020, 'DTP3', 900000000, 68.5),
        (3, 2021, 'DTP3', 920000000, 70.2),
        (3, 2022, 'DTP3', 940000000, 72.1),
        (3, 2023, 'DTP3', 960000000, 74.3),
        (3, 2024, 'DTP3', 980000000, 76.9),
        (4, 2020, 'DTP3', 85000000, 52.1),
        (4, 2021, 'DTP3', 95000000, 55.8),
        (4, 2022, 'DTP3', 105000000, 59.2),
        (4, 2023, 'DTP3', 120000000, 63.5),
        (4, 2024, 'DTP3', 135000000, 67.1),
        (5, 2020, 'DTP3', 75000000, 96.2),
        (5, 2021, 'DTP3', 76500000, 96.5),
        (5, 2022, 'DTP3', 78000000, 96.8),
        (5, 2023, 'DTP3', 79500000, 97.1),
        (5, 2024, 'DTP3', 81000000, 97.3),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO VaccinationData (CountryID, Year, Antigen, DosesAdministered, CoveragePercentage) VALUES (?, ?, ?, ?, ?)",
        sample_vaccinations
    )
    
    # Insert sample data into InfectionData
    sample_infections = [
        (1, 2020, 'Measles', 15000),
        (1, 2021, 'Measles', 12000),
        (1, 2022, 'Measles', 10000),
        (1, 2023, 'Measles', 8000),
        (1, 2024, 'Measles', 5000),
        (2, 2020, 'Measles', 450000),
        (2, 2021, 'Measles', 420000),
        (2, 2022, 'Measles', 380000),
        (2, 2023, 'Measles', 350000),
        (2, 2024, 'Measles', 320000),
        (3, 2020, 'Measles', 2500000),
        (3, 2021, 'Measles', 2300000),
        (3, 2022, 'Measles', 2000000),
        (3, 2023, 'Measles', 1800000),
        (3, 2024, 'Measles', 1500000),
        (4, 2020, 'Measles', 850000),
        (4, 2021, 'Measles', 820000),
        (4, 2022, 'Measles', 780000),
        (4, 2023, 'Measles', 750000),
        (4, 2024, 'Measles', 700000),
        (5, 2020, 'Measles', 25000),
        (5, 2021, 'Measles', 20000),
        (5, 2022, 'Measles', 15000),
        (5, 2023, 'Measles', 10000),
        (5, 2024, 'Measles', 5000),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO InfectionData (CountryID, Year, InfectionType, ReportedCases) VALUES (?, ?, ?, ?)",
        sample_infections
    )
    
    # Insert sample data into TeamMembers
    sample_team = [
        ('s4189750', 'Team Member 1', 'Developer'),
        ('s4142692', 'Team Member 2', 'Developer'),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO TeamMembers (StudentID, Name, Role) VALUES (?, ?, ?)",
        sample_team
    )
    
    # Insert sample data into Personas
    sample_personas = [
        (1, 'Public Health Official', 'Decision maker focused on vaccination campaigns'),
        (2, 'Health Researcher', 'Academic researcher analyzing immunisation data'),
        (3, 'NGO Worker', 'Field worker implementing health programs'),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO Personas (PersonaID, PersonaName, Description) VALUES (?, ?, ?)",
        sample_personas
    )
    
    conn.commit()
    conn.close()
    print(f"✓ Database '{DB_FILE}' initialized successfully!")
    print("✓ All tables created and sample data inserted.")

if __name__ == '__main__':
    init_db()
