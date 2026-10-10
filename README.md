# Ledger Fraud Intelligence

Ledger Fraud Intelligence is a Business Data Analytics (BDA) project for exploring a labeled credit-card transaction dataset and supporting fraud-review decisions. Its primary focus is descriptive and diagnostic analysis; a classification model is included as one supporting component.

The Streamlit dashboard uses PySpark to profile the portfolio, compare labeled fraud rates across transaction amount and elapsed-time segments, and make the data available for review. It also includes a class-weighted logistic regression model for held-out evaluation and optional batch scoring.

## Business questions

The dashboard is designed to help explore questions such as:

- How many transactions are represented, and what share of labeled transactions are fraud?
- How do transaction amount distributions and labeled fraud rates differ across amount bands?
- How do labeled fraud rates vary across elapsed-time windows in the dataset?
- Are expected transaction fields missing values?
- How does the model balance precision and recall on a held-out test set?
- How many uploaded transactions would be sent for review at a chosen probability threshold?

These are descriptive comparisons, not causal explanations. Results depend on the labels and fields available in the supplied dataset.

## BDA workflow

1. **Data ingestion:** read `creditcard.csv` with a fixed Spark schema.
2. **Data profiling:** summarize transaction counts, label coverage, amount statistics, and missing values.
3. **Descriptive analysis:** review portfolio composition, labeled fraud prevalence, transaction value, and amount distribution.
4. **Diagnostic analysis:** compare counts and fraud rates by transaction amount band and six-hour elapsed-time window.
5. **Decision support:** inspect review workload from uploaded transactions at a configurable probability threshold.
6. **Predictive analysis:** train and evaluate a class-weighted logistic regression pipeline as a supporting capability.

## Business problem

Financial institutions face rising fraud risk, especially in digital payments and card-based transactions. Fraud is usually rare, but the cost of missing a fraudulent transaction is high. A business needs a way to:

- detect unusual payment behavior quickly,
- reduce false positives,
- prioritize investigation effort,
- minimize financial losses,
- support operational decisions using data rather than guesswork.

This dashboard is designed to help with exactly that.

## Dashboard

### Business analytics

The primary view presents transaction totals, labeled fraud rate, observed amount on labeled fraud records, transaction amount percentiles, portfolio composition, segment comparisons, and a missing-value snapshot. Segment rates use labeled transactions within each segment; counts are shown alongside rates to make class imbalance visible.

### Model lab

Trains a class-weighted logistic regression pipeline using an 80/20 split with a fixed seed. The held-out report includes PR AUC, precision, recall, F1, and confusion-matrix counts. Precision, recall, and F1 use Spark's default 0.5 classification threshold; PR AUC evaluates ranking across thresholds.

### Transaction scoring

Scores uploaded transaction files and marks records for review when their estimated fraud probability meets the selected threshold. Scores are triage signals, not confirmed fraud determinations.

## Data limitations

- `Time` is elapsed time in seconds from the beginning of the dataset, not a calendar timestamp. The dashboard groups it into six-hour elapsed windows.
- `V1` through `V28` are anonymized features, so they do not support direct business explanations about customers, merchants, locations, or transaction channels.
- Segment comparisons show association in this dataset; they do not establish why fraud occurred.
- The sum of `Amount` for labeled fraud records is an observed transaction amount, not independently verified financial loss or recoverable savings.
- Model performance on this dataset does not establish performance on future or production traffic.

## Technology

- Python, PySpark, Spark ML, Streamlit, Pandas, and Altair

## Requirements

- Python 3.9 or newer
- Java 17 or newer, with `JAVA_HOME` configured

> PySpark 4 requires Java 17+. If Java 8 is installed, upgrade to Java 17+ before running the project.

## Run the project

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Make sure `creditcard.csv` is stored beside `app.py`.

## Data format

The app expects a CSV with the following transaction fields:

- `Time`
- `V1` through `V28`
- `Amount`
- optional `Class` column for labeled evaluation

During scoring, the optional `Class` field is ignored.

## Model details

- Train/test split: 80/20 with a fixed seed
- Model type: logistic regression
- Feature scaling: StandardScaler applied before classification
- Class balancing: class weights used to address fraud imbalance
- Evaluation: PR AUC, precision, recall, F1, and confusion-matrix counts
- Classification threshold: Spark's default 0.5 threshold for reported precision, recall, and F1
- Scoring review threshold: configurable on the Transaction scoring page; defaults to 0.50

## Final note

This project demonstrates a BDA workflow for examining transaction data and supporting review prioritization. Operational use would require validation on representative current data, a defined review capacity, and human investigation of flagged records.
