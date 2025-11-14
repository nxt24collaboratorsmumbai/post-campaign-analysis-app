import pandas as pd
from tabulate import tabulate
from pathlib import Path
from typing import List, Tuple, Dict, Any
import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


# Canonical KPIs we care about
KPI_CANDIDATES: Dict[str, List[str]] = {
    "lands": ["lands", "landings", "land", "landing_visits"],
    "cost": ["cost", "spend", "media_cost", "total_cost"],
    "HVEA": ["hvea", "high_value_events", "high_value_event_actions"],
    "channel": ["channel", "channels", "media_channel", "source", "platform"],
}


def _load_single_table(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    elif ext in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file type for {path}")


def load_multiple_tables(
    paths: List[str],
    max_rows_for_llm: int = 800,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Load multiple CSV/XLS/XLSX files and combine into one DataFrame.
    Adds a '__source_file__' column indicating origin.
    """
    frames = []
    file_summaries: List[Dict[str, Any]] = []

    for p in paths:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        df = _load_single_table(path)
        df["__source_file__"] = path.name
        frames.append(df)

        file_summaries.append(
            {
                "file_name": path.name,
                "n_rows": len(df),
                "n_cols": df.shape[1],
                "columns": list(df.columns),
            }
        )

    if not frames:
        raise ValueError("No valid CSV/XLS/XLSX files were provided.")

    combined = pd.concat(frames, ignore_index=True)

    if len(combined) > max_rows_for_llm:
        combined = combined.sample(max_rows_for_llm, random_state=42).reset_index(drop=True)

    return combined, file_summaries


def build_file_overview(file_summaries: List[Dict[str, Any]]) -> str:
    rows = []
    for meta in file_summaries:
        sample_cols = ", ".join(meta["columns"][:8])
        rows.append(
            [
                meta["file_name"],
                meta["n_rows"],
                meta["n_cols"],
                sample_cols,
            ]
        )

    table = tabulate(
        rows,
        headers=["file_name", "n_rows", "n_cols", "sample_columns"],
        tablefmt="github",
    )
    return f"### File Overview (per input file)\n\n{table}"


def build_kpi_view(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Extract only the KPI columns:
      - lands
      - cost
      - HVEA
      - channel

    Returns:
      kpi_df: DataFrame with only those cols (plus __source_file__ if present),
              renamed to canonical names where possible.
      kpi_mapping: {canonical_kpi_name -> original_column_name}
    """
    lower_map = {c.lower(): c for c in df.columns}
    kpi_mapping: Dict[str, str] = {}

    for kpi, candidates in KPI_CANDIDATES.items():
        for cand in candidates:
            if cand.lower() in lower_map:
                kpi_mapping[kpi] = lower_map[cand.lower()]
                break

    if not kpi_mapping:
        raise ValueError(
            "Could not find any of the required KPI columns: lands, cost, HVEA, channel. "
            "Please ensure your files have at least some of these."
        )

    cols = list(kpi_mapping.values())
    if "__source_file__" in df.columns:
        cols.append("__source_file__")

    kpi_df = df[cols].copy()

    # Rename to canonical KPI names
    rename_map = {orig: canon for canon, orig in kpi_mapping.items()}
    kpi_df = kpi_df.rename(columns=rename_map)

    return kpi_df, kpi_mapping


def build_kpi_mapping_summary(kpi_mapping: Dict[str, str]) -> str:
    rows = [[kpi, orig] for kpi, orig in kpi_mapping.items()]
    table = tabulate(rows, headers=["canonical_kpi", "source_column"], tablefmt="github")
    return f"### KPI Column Mapping\n\n{table}"


def build_schema_summary(df: pd.DataFrame) -> str:
    schema_rows = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = df[col].notna().sum()
        nulls = df[col].isna().sum()
        unique_vals = df[col].nunique(dropna=True)
        schema_rows.append([col, dtype, non_null, nulls, unique_vals])

    table = tabulate(
        schema_rows,
        headers=["column", "dtype", "non_null", "nulls", "n_unique"],
        tablefmt="github",
    )
    return f"### KPI Schema summary\n\n{table}"


def build_numeric_summary(df: pd.DataFrame) -> str:
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return "No numeric KPI columns in this dataset."
    desc = numeric_df.describe().T.reset_index()
    table = tabulate(desc, headers=desc.columns, tablefmt="github", floatfmt=".3f")
    return f"### KPI Numeric summary (describe())\n\n{table}"


def build_categorical_summary(df: pd.DataFrame) -> str:
    cat_df = df.select_dtypes(include=["object", "category"])
    if cat_df.empty:
        return "No categorical KPI columns in this dataset."
    lines = ["### KPI Categorical summary (top categories)"]
    for col in cat_df.columns:
        vc = cat_df[col].value_counts(dropna=False).head(8)
        vc = vc.reset_index()
        vc.columns = [col, "count"]
        table = tabulate(vc, headers=vc.columns, tablefmt="github")
        lines.append(f"\n#### Column: {col}\n\n{table}")
    return "\n".join(lines)


def build_sample_rows(df: pd.DataFrame, n: int = 5) -> str:
    sample = df.head(n)
    table = tabulate(sample, headers=sample.columns, tablefmt="github", floatfmt=".3f")
    return f"### KPI Sample rows (first {n})\n\n{table}"


def generate_charts_from_spec(df: pd.DataFrame, chart_spec_json: str, out_dir: str):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    try:
        parsed = json.loads(chart_spec_json)
        charts = parsed.get("charts", [])
    except Exception as e:
        print("Error parsing chart JSON:", e)
        return []

    generated_paths = []

    for idx, chart in enumerate(charts):
        if idx >= 6:
            break  # hard limit 6 charts

        ctype = chart.get("type")
        x = chart.get("x")
        y = chart.get("y")
        title = chart.get("title", f"chart_{idx}")

        file_path = out_path / f"chart_{idx+1}_{ctype}.png"

        # ---------------------------------------------------------------------
        # Flexible chart generator
        # ---------------------------------------------------------------------

        plt.figure(figsize=(6, 4))
        try:
            if ctype == "bar":
                df.groupby(x)[y].sum().plot(kind="bar")
            elif ctype == "line":
                df.sort_values(x).plot(x=x, y=y)
            elif ctype == "scatter":
                plt.scatter(df[x], df[y])
                plt.xlabel(x)
                plt.ylabel(y)
            elif ctype == "box":
                df[[y]].plot(kind="box")
            elif ctype == "stacked_bar":
                temp = df.groupby(x)[y].sum().unstack(fill_value=0)
                temp.plot(kind="bar", stacked=True)
            elif ctype == "funnel":
                values = df[y].value_counts().sort_values(ascending=False)
                values.plot(kind="barh")
            else:
                continue  # skip unknown chart type

            plt.title(title)
            plt.tight_layout()
            plt.savefig(file_path)
            plt.close()

            generated_paths.append(str(file_path))
        except Exception as e:
            print(f"Error generating chart {title}: {e}")
            plt.close()

    return generated_paths
