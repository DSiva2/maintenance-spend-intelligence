# Maintenance Spend Intelligence

From data to decisions in maintenance procurement, for GulfChem Industries (a fictional chemical company with five Gulf Coast plants).

> Work in progress. See `01_project_charter.md` for the project goals.

## Quick start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/fetch_fred.py       # needs FRED_API_KEY in .env
python src/generate_data.py
```

## Data note

Internal procurement data is synthetic, because real procurement data is confidential. Price trends follow real U.S. Bureau of Labor Statistics indices from FRED. All company and supplier names are fictional.
