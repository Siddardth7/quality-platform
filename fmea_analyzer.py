"""
fmea_analyzer.py
FMEA Risk Prioritization Tool — CLI Entry Point

Usage:
    python fmea_analyzer.py --input data/composite_panel_fmea_demo.csv
    python fmea_analyzer.py --input path/to/your_fmea.csv

Outputs a ranked FMEA table to the terminal, with Risk Tier labels
(Red / Yellow / Green) and AIAG flag summary.

Author: Siddardth | M.S. Aerospace Engineering, UIUC
Engineering reference: AIAG FMEA-4 + AIAG/VDA FMEA Handbook (5th Ed., 2019)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.rpn_engine import run_pipeline
from src.visualizer import pareto_chart, risk_heatmap

# ---------------------------------------------------------------------------
# ANSI color codes for terminal output
# ---------------------------------------------------------------------------

ANSI_RED    = "\033[91m"
ANSI_YELLOW = "\033[93m"
ANSI_GREEN  = "\033[92m"
ANSI_BOLD   = "\033[1m"
ANSI_RESET  = "\033[0m"

TIER_COLORS = {
    "Red":    ANSI_RED,
    "Yellow": ANSI_YELLOW,
    "Green":  ANSI_GREEN,
}

FLAG_EMOJI = {
    "Flag_High_RPN":          "🔴 High RPN",
    "Flag_High_Severity":     "⚠️  High Severity",
    "Flag_Action_Priority_H": "🚨 Action Priority H",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _color(text: str, tier: str) -> str:
    """Wrap text in the ANSI color for the given Risk_Tier."""
    return f"{TIER_COLORS.get(tier, '')}{text}{ANSI_RESET}"


def _bold(text: str) -> str:
    return f"{ANSI_BOLD}{text}{ANSI_RESET}"


def _load_file(path: Path) -> pd.DataFrame:
    """Load CSV or Excel FMEA file into a DataFrame."""
    MAX_BYTES = 20 * 1024 * 1024  # 20 MB — mirror app.py MAX_UPLOAD_BYTES
    if path.exists() and path.stat().st_size > MAX_BYTES:
        raise ValueError(
            f"File exceeds the {MAX_BYTES // (1024 * 1024)} MB limit: {path}. "
            "Split your FMEA or process in chunks."
        )
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    elif suffix == ".xlsx":
        return pd.read_excel(path)
    else:
        raise ValueError(
            f"Unsupported file format '{suffix}'. "
            "Provide a .csv or .xlsx file."
        )


def _build_flags_str(row: pd.Series) -> str:
    """Return a comma-separated string of active flags for a row."""
    active = [label for col, label in FLAG_EMOJI.items() if row.get(col, False)]
    return ", ".join(active) if active else "—"


def _print_summary(df: pd.DataFrame) -> None:
    """Print aggregate summary metrics above the ranked table."""
    total        = len(df)
    red_count    = (df["Risk_Tier"] == "Red").sum()
    yellow_count = (df["Risk_Tier"] == "Yellow").sum()
    green_count  = (df["Risk_Tier"] == "Green").sum()
    high_rpn     = df["Flag_High_RPN"].sum()
    high_sev     = df["Flag_High_Severity"].sum()
    action_h     = df["Flag_Action_Priority_H"].sum()

    print()
    print(_bold("=" * 72))
    print(_bold("  FMEA RISK ANALYSIS SUMMARY"))
    print(_bold("=" * 72))
    print(f"  Total failure modes analyzed : {total}")
    print(f"  {_color('Red    (immediate action)', 'Red')}    : {red_count}")
    print(f"  {_color('Yellow (action recommended)', 'Yellow')} : {yellow_count}")
    print(f"  {_color('Green  (monitor)', 'Green')}           : {green_count}")
    print()
    print("  AIAG Flag Counts:")
    print(f"    🔴 High RPN (> 100)          : {high_rpn}")
    print(f"    ⚠️  High Severity (≥ 9)       : {high_sev}")
    print(f"    🚨 Action Priority H          : {action_h}")
    print(_bold("=" * 72))
    print()


def _print_table(df: pd.DataFrame) -> None:
    """Print the ranked FMEA table with color-coded Risk Tier column."""
    # Column widths
    COL_WIDTHS = {
        "Rank":         4,
        "ID":           4,
        "Process_Step": 18,
        "Failure_Mode": 28,
        "S":            3,
        "O":            3,
        "D":            3,
        "RPN":          5,
        "Tier":         8,
        "Flags":        38,
    }

    # Header
    header = (
        f"{'Rank':<{COL_WIDTHS['Rank']}} "
        f"{'ID':<{COL_WIDTHS['ID']}} "
        f"{'Process Step':<{COL_WIDTHS['Process_Step']}} "
        f"{'Failure Mode':<{COL_WIDTHS['Failure_Mode']}} "
        f"{'S':>{COL_WIDTHS['S']}} "
        f"{'O':>{COL_WIDTHS['O']}} "
        f"{'D':>{COL_WIDTHS['D']}} "
        f"{'RPN':>{COL_WIDTHS['RPN']}} "
        f"{'Tier':<{COL_WIDTHS['Tier']}} "
        f"{'Active Flags':<{COL_WIDTHS['Flags']}}"
    )
    separator = "-" * len(header)

    print(_bold(header))
    print(separator)

    for rank, (_, row) in enumerate(df.iterrows(), start=1):
        tier       = row["Risk_Tier"]
        flags_str  = _build_flags_str(row)
        failure    = str(row["Failure_Mode"])[:COL_WIDTHS["Failure_Mode"]]
        step       = str(row["Process_Step"])[:COL_WIDTHS["Process_Step"]]

        tier_w   = COL_WIDTHS["Tier"]
        tier_str = f"{tier:<{tier_w}}"
        line = (
            f"{rank:<{COL_WIDTHS['Rank']}} "
            f"{int(row['ID']):<{COL_WIDTHS['ID']}} "
            f"{step:<{COL_WIDTHS['Process_Step']}} "
            f"{failure:<{COL_WIDTHS['Failure_Mode']}} "
            f"{int(row['Severity']):>{COL_WIDTHS['S']}} "
            f"{int(row['Occurrence']):>{COL_WIDTHS['O']}} "
            f"{int(row['Detection']):>{COL_WIDTHS['D']}} "
            f"{int(row['RPN']):>{COL_WIDTHS['RPN']}} "
            f"{_color(tier_str, tier)} "
            f"{flags_str:<{COL_WIDTHS['Flags']}}"
        )
        print(line)

    print(separator)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fmea_analyzer",
        description=(
            "FMEA Risk Prioritization Tool — reads a CSV/Excel FMEA file, "
            "calculates RPN scores, applies AIAG FMEA-4 flags, and prints "
            "a ranked risk table to the terminal."
        ),
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        metavar="FILE",
        help="Path to the FMEA input file (.csv or .xlsx)",
    )
    parser.add_argument(
        "--charts",
        action="store_true",
        default=False,
        help="Generate Pareto chart and risk heatmap PNG files alongside the report",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        metavar="DIR",
        help="Directory to save chart PNGs (default: same directory as input file)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)

    # --- Load ---
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\nLoading FMEA file: {input_path.resolve()}")

    try:
        df_raw = _load_file(input_path)
    except Exception as exc:
        print(f"[ERROR] Failed to load file: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"  → {len(df_raw)} rows loaded.")

    # --- Run pipeline ---
    print("Running FMEA analysis pipeline...")

    try:
        df_result = run_pipeline(df_raw)
    except (ValueError, KeyError) as exc:
        print(f"[ERROR] Validation failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print("  → Pipeline complete.\n")

    # --- Print results ---
    _print_summary(df_result)
    _print_table(df_result)

    print(f"Analysis complete. {len(df_result)} failure modes ranked by RPN.")
    print()

    # --- Generate charts if requested ---
    if args.charts:
        chart_dir = Path(args.output_dir) if args.output_dir else input_path.parent
        chart_dir.mkdir(parents=True, exist_ok=True)

        pareto_path = chart_dir / (input_path.stem + "_pareto.png")
        heatmap_path = chart_dir / (input_path.stem + "_heatmap.png")

        try:
            pareto_chart(df_result, output_path=pareto_path)
            print(f"  Pareto chart saved  → {pareto_path}")
            risk_heatmap(df_result, output_path=heatmap_path)
            print(f"  Risk heatmap saved  → {heatmap_path}")
            print()
        except Exception as exc:
            print(f"[ERROR] Chart generation failed: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
