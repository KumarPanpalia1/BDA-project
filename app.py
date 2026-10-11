from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

import altair as alt
import streamlit as st
from ledger_logic import (
    binary_label_counts,
    duplicate_headers,
    fraud_rate_percent,
    limited_scored_results,
    missing_required_headers,
    review_decision_labels,
    requires_review,
    scored_csv_bytes,
    scored_record_counts,
    sort_scored_results,
    validate_scoring_feature_counts,
)
try:
    from pyspark.ml import Pipeline
    from pyspark.ml.classification import LogisticRegression
    from pyspark.ml.evaluation import BinaryClassificationEvaluator
    from pyspark.ml.feature import StandardScaler, VectorAssembler
    from pyspark.ml.functions import vector_to_array
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql import functions as F
    from pyspark.sql.types import DoubleType, StructField, StructType
except ImportError as error:
    SPARK_IMPORT_ERROR = error
else:
    SPARK_IMPORT_ERROR = None


APP_DIR = Path(__file__).resolve().parent
DATA_PATH = APP_DIR / "creditcard.csv"
FEATURE_COLUMNS = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
LABEL_COLUMN = "Class"
SCORING_DISPLAY_LIMIT = 10000

if SPARK_IMPORT_ERROR is None:
    DATA_SCHEMA = StructType(
        [StructField(name, DoubleType(), True) for name in [*FEATURE_COLUMNS, LABEL_COLUMN]]
    )

st.set_page_config(
    page_title="Ledger | Fraud Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
            :root { --ink:#14243a; --muted:#617184; --paper:#f7f9fb; --line:#dce4eb; --blue:#245a87; --teal:#287a78; --red:#bd514b; }
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background:var(--paper); color:var(--ink); }
        [data-testid="stMainBlockContainer"] { padding:1.75rem 2.5rem 3rem; max-width:1440px; }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"] p { color:var(--ink); }
        [data-testid="stSidebar"] { background:#eef3f6; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:var(--muted); }
        .brand { font-family:'DM Mono',monospace; font-size:12px; letter-spacing:1px; color:var(--blue); font-weight:500; }
        .eyebrow { font-family:'DM Mono',monospace; font-size:11px; color:var(--teal); text-transform:uppercase; }
        .hero { padding:24px 0 20px; border-bottom:1px solid var(--line); margin-bottom:28px; }
        .hero h1 { color:var(--ink) !important; font-size:34px; line-height:1.15; margin:8px 0; letter-spacing:0; }
    .hero p { color:var(--muted) !important; margin:0; font-size:14px; }
        .section-title { font-size:18px; font-weight:800; margin:24px 0 10px; }
        .mono { font-family:'DM Mono',monospace; }
        [data-testid="stSidebar"] [data-testid="stRadio"] > label { color:var(--ink); font-size:12px; font-weight:700; text-transform:uppercase; }
        [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] { gap:5px; }
        [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label { border-radius:5px; padding:8px 10px; }
        [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) { background:#dceaf1; color:var(--blue); font-weight:700; }
        [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label p { color:inherit; }
        div[data-testid="stMetric"] { background:#fff; color:var(--ink); padding:15px 17px; border:1px solid var(--line); border-top:3px solid var(--teal); border-radius:5px; }
        div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] p { color:var(--muted) !important; }
        div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] p { color:var(--ink) !important; }
        div[data-testid="stMetricDelta"] { color:var(--teal) !important; }
        .stButton > button[kind="primary"] { background:var(--blue); border:1px solid var(--blue); color:white; }
        .stButton > button { border-radius:5px; }
        div[data-testid="stDataFrame"] { border:1px solid var(--line); }
        .stAlert { border-radius:5px; }
        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] { padding:1.25rem 1.5rem 2rem; }
        }
        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] { padding:1rem 1rem 2rem; }
            .hero { padding:14px 0 16px; margin-bottom:20px; }
            .hero h1 { font-size:28px; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if SPARK_IMPORT_ERROR is not None:
    st.title("Ledger / Fraud Intelligence")
    st.error(f"PySpark is not available to this Python interpreter: {SPARK_IMPORT_ERROR}")
    st.code("python -m pip install -r requirements.txt\nstreamlit run app.py", language="powershell")
    st.stop()


@st.cache_resource(show_spinner=False)
def get_spark() -> SparkSession:
    spark = (
        SparkSession.builder.master("local[*]")
        .appName("LedgerFraudIntelligence")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


@st.cache_resource(show_spinner="Reading the transaction dataset with Spark...")
def load_dataset(csv_path: str) -> DataFrame:
    spark = get_spark()
    data = (
        spark.read.option("header", True)
        .option("mode", "FAILFAST")
        .schema(DATA_SCHEMA)
        .csv(csv_path)
        .cache()
    )
    data.count()
    return data


@st.cache_resource(show_spinner="Training the fraud model with Spark ML...")
def train_model(csv_path: str, max_iter: int) -> dict:
    data = load_dataset(csv_path)
    train_data, test_data = data.randomSplit([0.8, 0.2], seed=42)
    class_counts = {
        row[LABEL_COLUMN]: row["count"]
        for row in train_data.groupBy(LABEL_COLUMN).count().collect()
    }
    legitimate_count, fraud_count = binary_label_counts(class_counts)
    if fraud_count == 0 or legitimate_count == 0:
        raise ValueError("The training split must contain both fraud and legitimate transactions.")

    total = fraud_count + legitimate_count
    weighted_train = train_data.withColumn(
        "class_weight",
        F.when(F.col(LABEL_COLUMN) == 1.0, total / (2.0 * fraud_count)).otherwise(
            total / (2.0 * legitimate_count)
        ),
    )

    assembler = VectorAssembler(inputCols=FEATURE_COLUMNS, outputCol="raw_features")
    scaler = StandardScaler(
        inputCol="raw_features", outputCol="features", withStd=True, withMean=True
    )
    classifier = LogisticRegression(
        featuresCol="features",
        labelCol=LABEL_COLUMN,
        weightCol="class_weight",
        maxIter=max_iter,
        regParam=0.01,
    )
    model = Pipeline(stages=[assembler, scaler, classifier]).fit(weighted_train)
    predictions = model.transform(test_data).cache()
    counts = predictions.agg(
        F.count("*").alias("total"),
        F.sum(F.when((F.col(LABEL_COLUMN) == 1) & (F.col("prediction") == 1), 1).otherwise(0)).alias("tp"),
        F.sum(F.when((F.col(LABEL_COLUMN) == 0) & (F.col("prediction") == 1), 1).otherwise(0)).alias("fp"),
        F.sum(F.when((F.col(LABEL_COLUMN) == 1) & (F.col("prediction") == 0), 1).otherwise(0)).alias("fn"),
        F.sum(F.when((F.col(LABEL_COLUMN) == 0) & (F.col("prediction") == 0), 1).otherwise(0)).alias("tn"),
    ).first()
    true_positive = int(counts["tp"] or 0)
    false_positive = int(counts["fp"] or 0)
    false_negative = int(counts["fn"] or 0)
    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(true_positive + false_negative, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    evaluator = BinaryClassificationEvaluator(
        labelCol=LABEL_COLUMN, rawPredictionCol="rawPrediction", metricName="areaUnderPR"
    )
    pr_auc = evaluator.evaluate(predictions)
    predictions.unpersist()

    return {
        "model": model,
        "metrics": {
            "pr_auc": pr_auc,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": true_positive,
            "fp": false_positive,
            "fn": false_negative,
            "tn": int(counts["tn"] or 0),
            "test_count": int(counts["total"]),
        },
    }


def page_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{kicker}</div><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def show_setup_error(error: Exception) -> None:
    st.error(f"Spark could not start: {error}")
    with st.expander("Setup checks"):
        st.markdown(
            "Install **Java 17 or newer**, set `JAVA_HOME`, then install the packages in "
            "`requirements.txt`. Restart the terminal and run `streamlit run app.py`."
        )
    st.stop()


with st.sidebar:
    st.markdown('<div class="brand">◈ LEDGER / RISK SYSTEMS</div>', unsafe_allow_html=True)
    st.markdown(" ")
    current_page = st.radio(
        "Workspace",
        ["Business analytics", "Model lab", "Transaction scoring"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**ACTIVE WORKSPACE**")
    st.caption(current_page)
    st.markdown("**DATA SOURCE**")
    st.caption(DATA_PATH.name if DATA_PATH.exists() else "Dataset not found")
    st.caption("Spark ML · local execution")
    st.markdown("**MODEL STATUS**")
    if st.session_state.get("trained_result"):
        st.success("Ready · trained this session")
    else:
        st.info("Not trained yet")
        st.caption("Open Model lab to train before scoring.")
    st.markdown(" ")
    st.caption("Model scores support review; they are not a final fraud determination.")


if not DATA_PATH.exists():
    st.error(f"Dataset not found at `{DATA_PATH}`. Place `creditcard.csv` beside `app.py`.")
    st.stop()

try:
    data = load_dataset(str(DATA_PATH))
except Exception as error:
    show_setup_error(error)


if current_page == "Business analytics":
    page_header(
        "Business analytics / 01",
        "Understand the transaction portfolio.",
        "Explore transaction value, labeled fraud patterns, and data quality before reviewing model results.",
    )
    try:
        totals = data.agg(
            F.count("*").alias("transactions"),
            F.count(LABEL_COLUMN).alias("labeled_transactions"),
            F.sum(F.when(F.col(LABEL_COLUMN) == 1, 1).otherwise(0)).alias("fraud"),
            F.sum(F.when(F.col(LABEL_COLUMN) == 0, 1).otherwise(0)).alias("legitimate"),
            F.sum(F.when(F.col(LABEL_COLUMN) == 1, F.col("Amount")).otherwise(0.0)).alias("fraud_amount"),
            F.avg("Amount").alias("average_amount"),
        ).first()
        missing_fields = [*FEATURE_COLUMNS, LABEL_COLUMN]
        missing_per_row = F.lit(0)
        for field in missing_fields:
            missing_per_row = missing_per_row + F.col(field).isNull().cast("long")
        profile = data.agg(
            F.sum(missing_per_row).alias("missing_cells"),
            F.sum(F.when(missing_per_row > 0, 1).otherwise(0)).alias("rows_with_missing"),
        ).first()
        amount_quantiles = data.approxQuantile("Amount", [0.5, 0.95], 0.01)
    except Exception as error:
        show_setup_error(error)

    fraud_rate = fraud_rate_percent(totals["fraud"], totals["labeled_transactions"])
    metric_cols = st.columns(4)
    metric_cols[0].metric("Transactions", f"{totals['transactions']:,}", "All records")
    metric_cols[1].metric("Labeled fraud rate", f"{fraud_rate:.3f}%", f"{totals['fraud']:,} of {totals['labeled_transactions']:,} labeled")
    metric_cols[2].metric("Labeled fraud amount", f"${totals['fraud_amount']:,.2f}", "Observed amount, not confirmed loss")
    metric_cols[3].metric("Median transaction", f"${amount_quantiles[0]:,.2f}", f"95th percentile ${amount_quantiles[1]:,.2f}")

    st.markdown('<div class="section-title">Portfolio composition</div>', unsafe_allow_html=True)
    class_summary = (
        data.groupBy(LABEL_COLUMN)
        .agg(F.count("*").alias("Transactions"), F.sum("Amount").alias("Total amount"))
        .orderBy(LABEL_COLUMN)
        .toPandas()
    )
    class_summary["Class"] = class_summary["Class"].map({0.0: "Legitimate", 1.0: "Fraud"})
    left, right = st.columns([1.15, 1])
    with left:
        chart = (
            alt.Chart(class_summary)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X(
                    "Transactions:Q",
                    scale=alt.Scale(type="log", domain=[1, 350000]),
                    axis=alt.Axis(format="~s"),
                    title="Transactions · log scale",
                ),
                x2=alt.datum(1),
                y=alt.Y("Class:N", sort=["Fraud", "Legitimate"], title=None),
                color=alt.Color(
                    "Class:N",
                    scale=alt.Scale(domain=["Legitimate", "Fraud"], range=["#24634d", "#c3503d"]),
                    legend=None,
                ),
                tooltip=["Class:N", "Transactions:Q", alt.Tooltip("Total amount:Q", format="$.2f")],
            )
            .properties(height=190)
        )
        st.altair_chart(chart, width="stretch")
    with right:
        st.dataframe(class_summary, hide_index=True, width="stretch")
        st.caption("Fraud is rare in this labeled dataset; compare rates as well as raw counts when interpreting segments.")

    st.markdown('<div class="section-title">Where does labeled fraud concentrate?</div>', unsafe_allow_html=True)
    amount_band = (
        F.when(F.col("Amount").isNull(), "Missing amount")
        .when(F.col("Amount") <= 25, "$0-25")
        .when(F.col("Amount") <= 100, "$25-100")
        .when(F.col("Amount") <= 250, "$100-250")
        .otherwise("$250+")
    )
    amount_order = (
        F.when(F.col("Amount").isNull(), 5)
        .when(F.col("Amount") <= 25, 0)
        .when(F.col("Amount") <= 100, 1)
        .when(F.col("Amount") <= 250, 2)
        .otherwise(3)
    )
    time_bucket = F.floor(F.col("Time") / 21600)
    time_window = F.when(F.col("Time").isNull(), "Missing time").otherwise(
        F.concat(
            (time_bucket * 6).cast("int").cast("string"),
            F.lit("-"),
            ((time_bucket + 1) * 6).cast("int").cast("string"),
            F.lit(" hours"),
        )
    )
    time_order = F.when(F.col("Time").isNull(), 999).otherwise(time_bucket)

    def summarize_segments(segment, order):
        return (
            data.withColumn("segment", segment)
            .withColumn("segment_order", order)
            .groupBy("segment", "segment_order")
            .agg(
                F.count("*").alias("Transactions"),
                F.count(LABEL_COLUMN).alias("Labeled transactions"),
                F.sum(F.when(F.col(LABEL_COLUMN) == 1, 1).otherwise(0)).alias("Labeled fraud"),
                F.sum(F.when(F.col(LABEL_COLUMN) == 1, F.col("Amount")).otherwise(0.0)).alias("Labeled fraud amount"),
            )
            .withColumn(
                "Fraud rate (%)",
                F.when(
                    F.col("Labeled transactions") > 0,
                    100 * F.col("Labeled fraud") / F.col("Labeled transactions"),
                ),
            )
            .orderBy("segment_order")
            .toPandas()
            .rename(columns={"segment": "Segment"})
        )

    amount_summary = summarize_segments(amount_band, amount_order)
    time_summary = summarize_segments(time_window, time_order)
    amount_tab, time_tab = st.tabs(["Transaction amount", "Elapsed time"])
    for tab, summary, axis_title in [
        (amount_tab, amount_summary, "Transaction amount band"),
        (time_tab, time_summary, "Elapsed-time window"),
    ]:
        with tab:
            chart = (
                alt.Chart(summary)
                .mark_bar(cornerRadiusEnd=3, color="#24634d")
                .encode(
                    x=alt.X("Segment:N", sort=summary["Segment"].tolist(), title=axis_title),
                    y=alt.Y("Fraud rate (%):Q", title="Labeled fraud rate (%)"),
                    tooltip=[
                        "Segment:N",
                        "Transactions:Q",
                        "Labeled transactions:Q",
                        "Labeled fraud:Q",
                        alt.Tooltip("Fraud rate (%):Q", format=".3f"),
                        alt.Tooltip("Labeled fraud amount:Q", format="$.2f"),
                    ],
                )
                .properties(height=250)
            )
            st.altair_chart(chart, width="stretch")
            st.dataframe(summary.drop(columns=["segment_order"]), hide_index=True, width="stretch")
    st.caption("Rates use labeled transactions within each segment. Elapsed-time windows are relative to the dataset start, not calendar times; these comparisons are descriptive, not causal.")

    st.markdown('<div class="section-title">Data quality snapshot</div>', unsafe_allow_html=True)
    quality_cols = st.columns(3)
    quality_cols[0].metric("Labeled records", f"{totals['labeled_transactions']:,}", f"of {totals['transactions']:,} total")
    quality_cols[1].metric("Rows with missing values", f"{profile['rows_with_missing'] or 0:,}")
    quality_cols[2].metric("Missing cells", f"{profile['missing_cells'] or 0:,}", f"across {len(missing_fields)} expected fields")
    st.caption(f"Amount mean: ${totals['average_amount']:,.2f}. Input is profiled against the expected transaction schema.")

elif current_page == "Model lab":
    page_header(
        "Model lab / 02",
        "Train and evaluate.",
        "Fit a class-weighted logistic regression pipeline with Spark ML and inspect held-out performance.",
    )
    st.markdown("The dataset is split 80/20 with a fixed seed. Features are assembled and standardized in Spark; class weights counter the severe label imbalance.")
    max_iter = st.slider("Training iterations", min_value=20, max_value=120, value=60, step=10)
    if st.button("Train fraud model", type="primary", icon=":material/shield:"):
        try:
            st.session_state["trained_result"] = train_model(str(DATA_PATH), max_iter)
        except Exception as error:
            st.error(f"Model training failed: {error}")

    result = st.session_state.get("trained_result")
    if result:
        metrics = result["metrics"]
        st.markdown('<div class="section-title">Held-out test results</div>', unsafe_allow_html=True)
        metric_cols = st.columns(4)
        metric_cols[0].metric("PR AUC", f"{metrics['pr_auc']:.3f}")
        metric_cols[1].metric("Recall", f"{metrics['recall']:.1%}")
        metric_cols[2].metric("Precision", f"{metrics['precision']:.1%}")
        metric_cols[3].metric("F1", f"{metrics['f1']:.3f}")
        st.caption(f"Test set: {metrics['test_count']:,} transactions · TP {metrics['tp']:,} · FP {metrics['fp']:,} · FN {metrics['fn']:,} · TN {metrics['tn']:,}")
        st.caption("Precision, recall, and F1 use Spark's default 0.5 classification threshold; PR AUC evaluates ranking across thresholds.")
        st.session_state["fraud_model"] = result["model"]
    else:
        st.info("Train a model to see held-out metrics and enable transaction scoring.")

elif current_page == "Transaction scoring":
    page_header(
        "Review queue / 03",
        "Score a transaction file.",
        "Upload a CSV with the same feature columns to estimate fraud probabilities in batch.",
    )
    result = st.session_state.get("trained_result")
    if not result:
        st.warning("Train the model in Model lab before scoring transactions.")
        st.stop()

    uploaded = st.file_uploader("Transaction CSV", type=["csv"], help="Required columns: Time, V1 to V28, Amount. Class is optional.")
    review_threshold = st.slider(
        "Review threshold (inclusive)",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.01,
        help="Rows at or above this estimated fraud probability are review signals, not confirmed fraud.",
    )
    if uploaded is not None:
        try:
            header = next(csv.reader(io.StringIO(uploaded.getvalue().decode("utf-8-sig").splitlines()[0])))
            duplicates = duplicate_headers(header)
            missing = missing_required_headers(header, FEATURE_COLUMNS)
            if duplicates:
                st.error("Duplicate CSV headers: " + ", ".join(duplicates) + ". Each column name must appear only once.")
            elif missing:
                st.error("Missing required feature columns: " + ", ".join(missing))
            else:
                spark = get_spark()
                upload_fields = [StructField(name, DoubleType(), True) for name in header]
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
                    temp_file.write(uploaded.getvalue())
                    temp_path = temp_file.name
                try:
                    score_input = (
                        spark.read.option("header", True)
                        .option("mode", "PERMISSIVE")
                        .schema(StructType(upload_fields))
                        .csv(temp_path)
                        .select(*FEATURE_COLUMNS)
                    )
                    invalid_count_columns = [
                        F.sum(
                            F.when(
                                F.col(name).isNull()
                                | F.isnan(F.col(name))
                                | (F.abs(F.col(name)) == float("inf")),
                                1,
                            ).otherwise(0)
                        ).alias(name)
                        for name in FEATURE_COLUMNS
                    ]
                    invalid_counts = score_input.agg(*invalid_count_columns).first().asDict()
                    validate_scoring_feature_counts(invalid_counts, FEATURE_COLUMNS)
                    scored = result["model"].transform(score_input)
                    scored = scored.withColumn("fraud_probability", vector_to_array("probability")[1])
                    review_label, below_threshold_label = review_decision_labels(review_threshold)
                    scored_output = scored.select(
                        *FEATURE_COLUMNS,
                        "fraud_probability",
                        F.when(requires_review(F.col("fraud_probability"), review_threshold), review_label)
                        .otherwise(below_threshold_label)
                        .alias("decision"),
                    )
                    ordered_scored = sort_scored_results(scored_output, F)
                    total_rows, flagged = scored_record_counts(
                        ordered_scored, review_threshold, F
                    )
                    display_output = limited_scored_results(
                        ordered_scored, SCORING_DISPLAY_LIMIT
                    )
                    with tempfile.TemporaryDirectory(prefix="ledger-scored-") as output_directory:
                        download_data = scored_csv_bytes(ordered_scored, output_directory)
                finally:
                    Path(temp_path).unlink(missing_ok=True)

                col_a, col_b = st.columns(2)
                col_a.metric("Scored rows", f"{total_rows:,}")
                col_b.metric("Review signals", f"{flagged:,}")
                st.dataframe(display_output, width="stretch", hide_index=True)
                st.download_button(
                    "Download scored results",
                    data=download_data,
                    file_name="fraud_review_results.csv",
                    mime="text/csv",
                    type="primary",
                )
                st.caption("Scores are review signals, not confirmed fraud. Rows below the selected threshold are not labeled as legitimate.")
                if total_rows > SCORING_DISPLAY_LIMIT:
                    st.caption(f"Showing the highest-scoring {SCORING_DISPLAY_LIMIT:,} rows; the counts and download include all {total_rows:,} uploaded records.")
        except Exception as error:
            st.error(f"Could not score this file: {error}")