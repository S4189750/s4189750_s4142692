# s4189750_s4142692
# 🌐 Global Vaccine Impact Explorer

A Flask-based web application for exploring global vaccination coverage, infection trends, and public health data across 194 countries from 2000–2024.

## Declaration/References
--- 
This web app was made with the guidance of w3schools, geeksforgeeks, and Gemini AI. Gemini AI assisted code made it possible for the website to do exactly as our desired website.
---

## 👥 Team

| Name | Student ID |
|------|-----------|
| Hiya Rana | s4142692 |
| Bach Nguyen Ho Viet | s4189750 |
---

## 📋 Overview

The Global Vaccine Impact Explorer connects directly to a local SQLite database (`immunisation.db`) to deliver live, query-driven insights across six pages. All data processing and filtering is handled in SQL — Python is used only for routing and rendering.

---

## 🗂️ Project Structure

```
project/
├── app.py                  # Flask routes & SQL queries
├── immunisation.db         # SQLite database (not included — see below)
├── static/
│   └── style.css           # Global stylesheet
├── templates/
│   ├── base.html           # Shared layout & navigation
│   ├── index.html          # Home dashboard
│   ├── mission.html        # Mission & team page
│   ├── regional.html       # Regional Analytics (Level 2)
│   ├── economic.html       # Economic Trends (Level 2)
│   ├── improvement.html    # Antigen Analytics (Level 3)
│   └── integrity.html      # Data Integrity (Level 3)
└── static/
    └── images/
        ├── hiya.jpeg
        ├── bach.jpeg
        ├── marie.jpeg
        └── derek.jpeg
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/S4189750/s4189750_s4142692.git

```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install flask
```

No other external libraries are required. The app uses only:
- `flask` — web framework
- `sqlite3` — built into Python, no install needed
- `jinja2` — built into Flask, no install needed

### 4. Add the database file

Place your `immunisation.db` file in the **root project folder** (same level as `app.py`).

```
project/
├── app.py
├── immunisation.db    ← place here
```

### 5. Run the application

```bash
python app.py
```

Then open your browser and go to:

```
http://127.0.0.1:5000
```

---

## 🖥️ Pages & Features

| Page | URL | Level | Description |
|------|-----|-------|-------------|
| Home | `/` | 1 | Dashboard with stat cards, disease search, mission overview |
| Mission & Team | `/mission` | 1 | Project values, personas, team members |
| Regional Analytics | `/regional` | 2 | Filter vaccination coverage by region, year, and vaccine type. Tables 1 & 2 with sortable columns and herd immunity summary cards |
| Economic Trends | `/economic` | 2 | Split-screen income group comparison with live charts. Country-level infection data (Table 1) and total cases by economic phase (Table 2) |
| Antigen Analytics | `/improvement` | 3 | Sub-Task A: countries with the biggest vaccination rate jump. Historical income gap chart and zero-dose population trends |
| Data Integrity | `/integrity` | 3 | Sub-Task B: global vs above-average infection rates. Coverage deviation audit table with quality tier ratings |

---

## 🗃️ Database Schema

The app queries the following tables in `immunisation.db`:

| Table | Key Columns |
|-------|-------------|
| `Vaccination` | `country`, `antigen`, `year`, `coverage`, `doses`, `target_num` |
| `InfectionData` | `country`, `inf_type`, `year`, `cases` |
| `Country` | `CountryID`, `name`, `region`, `economy` |
| `Region` | `RegionID`, `region` |
| `Economy` | `economyID`, `phase` |
| `Infection_Type` | `id`, `description` |
| `CountryPopulation` | `country`, `year`, `population` |
| `Antigen` | `AntigenID`, `name` |

---

## 🔍 SQL Techniques Used

- **Multi-table JOINs** — up to 5 tables in a single query
- **Correlated subqueries** — finding countries above global average infection rate
- **UNION ALL** — combining global average row with country rows in one query
- **Conditional aggregation** — `AVG(CASE WHEN ...)` for income group comparisons
- **Self-JOIN** — comparing vaccination rates between two different years
- **HAVING** — filtering quality tiers after GROUP BY
- **Dynamic ORDER BY** — all sorting handled in SQL, not Python

---

## 🚀 Quick Start (one-liner)

```bash
pip install flask && then input python app.py
```
Then visit `http://127.0.0.1:5000`

---

## 📄 License

This project was created for academic purposes at RMIT University for their Python Programming Studio final assignment.