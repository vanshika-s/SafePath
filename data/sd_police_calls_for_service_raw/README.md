- ## Data Source

The raw dataset comes from the City of San Diego Police Calls for Service public data.

Files loaded: 2014–2026 CSVs
Total rows: ___
Common columns: ___
Main usable columns: date/time, call type, location, disposition
Potential issues:
  - missing values in ___
  - inconsistent columns in ___
  - location granularity is ___
  - call type codes need reference table

Because the raw CSV files are large, they are **not stored directly in this GitHub repo**. Instead, this repo includes source information, cleaning scripts, and processed/sample outputs so the project can be reproduced.

## Repo Structure

```text
data/
  raw/
    README.md              # links and instructions for downloading raw CSV files
  processed/
    police_calls_sample.csv # smaller sample or processed output for preview

src/
  clean_police_calls.py     # script to clean and combine raw CSV files

notebooks/
  01_data_quality_check.ipynb # first-pass data quality checks and exploration
