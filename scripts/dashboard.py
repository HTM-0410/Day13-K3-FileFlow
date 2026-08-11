from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
SLO_PATH = REPO_ROOT / "config" / "slo.yaml"
DASHBOARD_PATH = REPO_ROOT / "config" / "dashboard.yaml"
LANGFUSE_PROJECT_ID = os.getenv("LANGFUSE_PROJECT_ID", "")

# ── Error diagnosis mapping ──────────────────────────────────────────────────

ERROR_DIAGNOSIS = {
    "AuthenticationError": {
        "title": "Authentication Error",
        "causes": [
            "Invalid or expired API key",
            "Missing OpenAI API key in .env",
            "Rate limit exceeded for API key",
        ],
        "solutions": [
            "Verify OPENAI_API_KEY is set correctly in .env",
            "Check if API key is active at platform.openai.com",
            "Ensure Langfuse keys are valid if using tracing",
        ],
        "severity": "critical",
    },
    "RateLimitError": {
        "title": "Rate Limit Exceeded",
        "causes": [
            "Too many requests in short time",
            "API tier has low rate limits",
            "Burst traffic to the system",
        ],
        "solutions": [
            "Implement request throttling on client side",
            "Upgrade to higher API tier",
            "Add exponential backoff retry logic",
        ],
        "severity": "high",
    },
    "APITimeoutError": {
        "title": "API Timeout",
        "causes": [
            "OpenAI API is slow or unresponsive",
            "Network connectivity issues",
            "Request payload too large",
        ],
        "solutions": [
            "Check OpenAI status at status.openai.com",
            "Reduce prompt length",
            "Add timeout handling with retry",
        ],
        "severity": "medium",
    },
    "InvalidRequestError": {
        "title": "Invalid Request",
        "causes": [
            "Malformed request parameters",
            "Unsupported model specified",
            "Invalid message format",
        ],
        "solutions": [
            "Check request body format matches API spec",
            "Verify OPENAI_MODEL is a valid model name",
            "Review API documentation for parameter constraints",
        ],
        "severity": "high",
    },
    "ServiceUnavailableError": {
        "title": "Service Unavailable",
        "causes": [
            "OpenAI API is down",
            "Maintenance window active",
            "Regional outage",
        ],
        "solutions": [
            "Check OpenAI status page",
            "Implement fallback to cached responses",
            "Enable circuit breaker pattern",
        ],
        "severity": "critical",
    },
    "JSONDecodeError": {
        "title": "JSON Parse Error",
        "causes": [
            "Corrupted log file",
            "Malformed JSON in logs",
            "Encoding issues in log data",
        ],
        "solutions": [
            "Check data/logs.jsonl for invalid JSON lines",
            "Validate log format matches schema",
            "Ensure UTF-8 encoding is used",
        ],
        "severity": "low",
    },
}

def get_error_diagnosis(error_type: str) -> dict:
    """Get diagnosis and solutions for an error type."""
    return ERROR_DIAGNOSIS.get(error_type, {
        "title": f"Unknown Error: {error_type}",
        "causes": ["Unknown error type - manual investigation required"],
        "solutions": [
            "Check application logs for details",
            "Verify service dependencies are running",
            "Contact support if issue persists",
        ],
        "severity": "unknown",
    })

def get_severity_color(severity: str) -> tuple[str, str]:
    """Return (bg_color, text_color) based on severity."""
    colors = {
        "critical": ("rgba(248,113,113,0.15)", "#F87171"),
        "high": ("rgba(251,191,36,0.12)", "#FBBF24"),
        "medium": ("rgba(56,189,248,0.12)", "#38BDF8"),
        "low": ("rgba(52,211,153,0.12)", "#34D399"),
        "unknown": ("rgba(148,163,184,0.12)", "#94A3B8"),
    }
    return colors.get(severity, colors["unknown"])

# ── Data loaders ──────────────────────────────────────────────────────────────

def load_slo() -> dict:
    try:
        return yaml.safe_load(SLO_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def load_dashboard_meta() -> dict:
    try:
        payload = yaml.safe_load(DASHBOARD_PATH.read_text(encoding="utf-8")) or {}
        return payload.get("dashboard", {})
    except Exception:
        return {}


def load_logs(time_range_minutes: int = 60) -> pd.DataFrame:
    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_range_minutes)
    return df[df["ts"] >= cutoff]


def percentile_col(col: pd.Series, q: float) -> float:
    if col.empty:
        return 0.0
    return round(float(col.quantile(q / 100)), 2)


# ── Streamlit config ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Observability",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design tokens (custom CSS) ───────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  :root {
    --bg:          #0B0F14;
    --surface:     #11161D;
    --surface-hi:  #151B23;
    --border:      rgba(255,255,255,0.07);
    --border-hi:   rgba(255,255,255,0.13);
    --text-1:      #F1F5F9;
    --text-2:      #94A3B8;
    --text-3:      #4B5563;
    --accent:      #38BDF8;
    --accent-dim:  rgba(56,189,248,0.12);
    --green:       #34D399;
    --green-dim:   rgba(52,211,153,0.12);
    --amber:       #FBBF24;
    --amber-dim:   rgba(251,191,36,0.12);
    --red:         #F87171;
    --red-dim:     rgba(248,113,113,0.12);
    --purple:      #A78BFA;
    --radius:      10px;
    --radius-sm:   6px;
  }

  /* ── Base ────────────────────────────────────────────────── */
  .stApp > header { background: var(--bg) !important; border: none !important; }
  [data-testid="stAppViewContainer"] { background: var(--bg) !important; padding: 0 !important; }
  [data-testid="stMainBlockContainer"] {
    padding: 0 28px 40px !important;
    max-width: 100% !important;
    background: var(--bg) !important;
  }
  /* Metric value font */
  [data-testid="stMetricValue"] {
    font-family: 'Inter', sans-serif !important;
    font-variant-numeric: tabular-nums !important;
    letter-spacing: -0.02em !important;
    font-weight: 700 !important;
  }
  [data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    color: var(--text-2) !important;
  }
  [data-testid="stMetricDelta"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 11px !important;
  }
  /* Toolbar */
  [data-testid="stToolbar"] { display: none !important; }
  /* Scrollbar */
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: #1f2937; border-radius: 3px; }
  /* Caption */
  p, .stCaption { font-family: 'Inter', sans-serif !important; color: var(--text-2) !important; }
  /* Divider */
  hr { border-color: var(--border) !important; }
  /* Streamlit metric container spacing fix */
  [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] {
    gap: 0 !important;
  }

  /* ── Sidebar ──────────────────────────────────────────────── */
  [data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
    width: 230px !important;
    padding: 20px 16px !important;
  }

  /* ── Card container (wraps each chart section) ────────────── */
  .chart-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 20px 14px;
    transition: border-color 0.15s;
  }
  .chart-wrap:hover { border-color: var(--border-hi); }

  /* ── Section header inside cards ─────────────────────────── */
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }
  .section-title {
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-1);
    margin: 0;
  }
  .section-meta {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: var(--text-2);
    font-variant-numeric: tabular-nums;
  }

  /* ── Top header bar ──────────────────────────────────────── */
  .dash-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 0 14px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 18px;
  }
  .dash-title {
    font-family: 'Inter', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: var(--text-1);
    margin: 0 0 2px;
    letter-spacing: -0.02em;
  }
  .dash-sub {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: var(--text-2);
    margin: 0;
  }
  .dash-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .dash-time {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: var(--text-2);
    text-align: right;
    line-height: 1.4;
  }
  .live-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: var(--green-dim);
    color: var(--green);
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 600;
    padding: 5px 12px;
    border-radius: 20px;
    letter-spacing: 0.02em;
  }
  .live-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--green);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  /* ── Status bar ──────────────────────────────────────────── */
  .status-bar {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 20px;
    display: flex;
    align-items: center;
    gap: 36px;
    margin-bottom: 18px;
    flex-wrap: wrap;
  }
  .status-item {
    display: flex;
    align-items: center;
    gap: 7px;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-2);
  }
  .status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .status-dot.green { background: var(--green); box-shadow: 0 0 5px var(--green); }
  .status-dot.amber { background: var(--amber); box-shadow: 0 0 5px var(--amber); }
  .status-dot.red   { background: var(--red);   box-shadow: 0 0 5px var(--red); }
  .status-dot.blue  { background: var(--accent); }
  .status-value {
    color: var(--text-1);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  /* ── SLO sidebar ────────────────────────────────────────── */
  .slo-title {
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-3);
    margin: 18px 0 8px;
  }
  .slo-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 2px;
    border-bottom: 1px solid var(--border);
    font-family: 'Inter', sans-serif;
    font-size: 12px;
  }
  .slo-row:last-child { border-bottom: none; }
  .slo-name { color: var(--text-2); }
  .slo-val  { color: var(--text-1); font-weight: 500; font-variant-numeric: tabular-nums; }
  .slo-chk  { font-size: 13px; }

  /* ── Nav items ──────────────────────────────────────────── */
  .nav-item {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-2);
    margin-bottom: 2px;
    transition: background 0.12s, color 0.12s;
  }
  .nav-item.active {
    background: var(--accent-dim);
    color: var(--accent);
  }
  .nav-item:hover:not(.active) {
    background: rgba(255,255,255,0.04);
    color: var(--text-1);
  }

  /* ── Data source info ──────────────────────────────────── */
  .ds-label {
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-3);
    margin: 14px 0 4px;
  }
  .ds-value {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: var(--text-2);
    margin-bottom: 4px;
  }

  /* ── Spacer ────────────────────────────────────────────── */
  .gap { height: 14px; }

  /* ── Progress bar ──────────────────────────────────────── */
  .prog-wrap {
    background: var(--surface-hi);
    border-radius: 4px;
    height: 5px;
    overflow: hidden;
    margin-top: 8px;
  }
  .prog-fill {
    height: 100%;
    border-radius: 4px;
    background: var(--accent);
    transition: width 0.5s ease;
  }
  .prog-fill.green { background: var(--green); }
  .prog-fill.amber { background: var(--amber); }
  .prog-fill.red   { background: var(--red); }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────

slo = load_slo()
dash_meta = load_dashboard_meta()
time_range = dash_meta.get("time_range_minutes", 60)
refresh_sec = dash_meta.get("refresh_seconds", 20)

with st.sidebar:
    st.markdown('<p style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#4B5563;margin:0 0 4px;">AI OBSERVABILITY</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:19px;font-weight:700;color:#F1F5F9;margin:0 0 2px;letter-spacing:-0.02em;">Day 13</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:12px;color:#94A3B8;margin:0 0 16px;">Observability Lab</p>', unsafe_allow_html=True)

    st.markdown('<div class="nav-item active">📊 Overview</div>', unsafe_allow_html=True)

    # SLO list
    st.markdown('<div class="slo-title">SLO Thresholds</div>', unsafe_allow_html=True)
    slis = slo.get("slis", {})
    for name, val, chk, color in [
        ("Latency P95", f"≤ {slis.get('latency_p95_ms',{}).get('objective','?')} ms",   "✓", "#34D399"),
        ("Error Rate",  f"≤ {slis.get('error_rate_pct',{}).get('objective','?')}%",        "✓", "#34D399"),
        ("Daily Cost",  f"≤ ${slis.get('daily_cost_usd',{}).get('objective','?')}",       "✓", "#34D399"),
        ("Quality",     f"≥ {slis.get('quality_score_avg',{}).get('objective','?')}",     "✓", "#34D399"),
    ]:
        st.markdown(f'<div class="slo-row"><span class="slo-name">{name}</span><span class="slo-val">{val}</span><span class="slo-chk" style="color:{color}">{chk}</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="ds-label">Data Source</div>', unsafe_allow_html=True)
    st.markdown('<div class="ds-value">`data/logs.jsonl`</div>', unsafe_allow_html=True)
    st.markdown('<div class="ds-label">Config</div>', unsafe_allow_html=True)
    st.markdown('<div class="ds-value">`config/slo.yaml`</div>', unsafe_allow_html=True)

    # Langfuse trace viewer
    st.divider()
    st.markdown('<div class="ds-label">Tracing</div>', unsafe_allow_html=True)

    # Check for latest trace in logs
    try:
        df_check = load_logs(60)
        if not df_check.empty:
            latest_success = df_check[df_check["event"] == "response_sent"].sort_values("ts", ascending=False).head(1)
            if not latest_success.empty and latest_success.iloc[0].get("trace_id"):
                trace_id = latest_success.iloc[0]["trace_id"]
                trace_link = (
                    f'<a href="https://jp.cloud.langfuse.com/project/{LANGFUSE_PROJECT_ID}/traces/{trace_id}" target="_blank" style="display:inline-block;width:100%;text-align:center;padding:5px 8px;background:#38BDF8;color:#0B0F14;font-family:Inter,sans-serif;font-size:10px;font-weight:600;border-radius:4px;text-decoration:none;">View on Langfuse →</a>'
                    if LANGFUSE_PROJECT_ID
                    else '<div style="font-family:Inter,sans-serif;font-size:10px;color:#4B5563;">Set LANGFUSE_PROJECT_ID to enable link</div>'
                )
                st.markdown(f"""
                <div style="margin-top:8px;padding:10px;background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.2);border-radius:6px;">
                  <div style="font-family:Inter,sans-serif;font-size:10px;color:#94A3B8;margin-bottom:6px;">Latest Trace:</div>
                  <div style="font-family:monospace;font-size:9px;color:#38BDF8;word-break:break-all;margin-bottom:8px;">{trace_id[:32]}...</div>
                  {trace_link}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-family:Inter,sans-serif;font-size:11px;color:#4B5563;margin-top:8px;">No traces yet</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-family:Inter,sans-serif;font-size:11px;color:#4B5563;margin-top:8px;">Send requests to generate traces</div>', unsafe_allow_html=True)
    except Exception:
        st.markdown('<div style="font-family:Inter,sans-serif;font-size:11px;color:#4B5563;margin-top:8px;">Trace viewer unavailable</div>', unsafe_allow_html=True)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.caption(f"Window: {time_range}m")
    with col_b:
        if st.button("↻ Refresh", use_container_width=True):
            st.rerun()


# ── Load data ────────────────────────────────────────────────────────────────

df = load_logs(time_range)

if df.empty:
    st.error(f"No log data in the last {time_range} minutes. Send requests first.")
    st.stop()

latency_df = df[df["event"] == "response_sent"]
req_df     = df[df["event"] == "request_received"]
fail_df    = df[df["event"] == "request_failed"]
cost_df    = latency_df.copy()

# ── Compute metrics ───────────────────────────────────────────────────────────

latency_obj = slo.get("slis", {}).get("latency_p95_ms",    {}).get("objective", 3000)
error_obj   = slo.get("slis", {}).get("error_rate_pct",   {}).get("objective", 2.0)
cost_obj    = slo.get("slis", {}).get("daily_cost_usd",    {}).get("objective", 2.5)
qual_obj    = slo.get("slis", {}).get("quality_score_avg", {}).get("objective", 0.75)

p50        = percentile_col(latency_df["latency_ms"], 50)
p95        = percentile_col(latency_df["latency_ms"], 95)
p99        = percentile_col(latency_df["latency_ms"], 99)
req_count  = len(req_df)
err_rate   = round(len(fail_df) / req_count * 100, 2) if req_count > 0 else 0.0
total_cost = round(float(cost_df["cost_usd"].sum()), 6) if not cost_df.empty else 0.0
tok_in     = int(cost_df["tokens_in"].sum())  if not cost_df.empty else 0
tok_out    = int(cost_df["tokens_out"].sum()) if not cost_df.empty else 0
mean_qual  = round(float(cost_df["quality_score"].mean()), 4) if not cost_df.empty else 0.0
cost_pct   = round(total_cost / cost_obj * 100, 2) if cost_obj > 0 else 0.0
req_rate   = round(req_count / time_range, 2) if time_range > 0 else 0.0

# SLO status
slo_lat   = p95 <= latency_obj
slo_err   = err_rate <= error_obj
slo_cost  = total_cost <= cost_obj
slo_qual  = mean_qual >= qual_obj
slo_pass  = sum([slo_lat, slo_err, slo_cost, slo_qual])
all_ok    = slo_pass == 4

# ── Top header ───────────────────────────────────────────────────────────────

now_str = datetime.now().astimezone().strftime("%H:%M:%S")
health_cls = "green" if all_ok else ("amber" if slo_pass >= 2 else "red")
health_txt = "All Systems Operational" if all_ok else f"{slo_pass}/4 SLOs passing"

st.markdown(f"""
<div class="dash-header">
  <div>
    <p class="dash-title">AI Observability</p>
    <p class="dash-sub">Monitor latency, reliability, traffic, cost and quality</p>
  </div>
  <div class="dash-right">
    <div class="dash-time">Last updated<br><strong style="color:#F1F5F9;font-size:13px;">{now_str}</strong></div>
    <div class="live-badge"><div class="live-dot"></div>Live</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Status bar ──────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="status-bar">
  <div class="status-item">
    <div class="status-dot {health_cls}"></div>
    <span>System Health</span>
    <span class="status-value">{health_txt}</span>
  </div>
  <div class="status-item">
    <div class="status-dot blue"></div>
    <span>SLOs Passing</span>
    <span class="status-value">{slo_pass} / 4</span>
  </div>
  <div class="status-item">
    <div class="status-dot blue"></div>
    <span>Requests</span>
    <span class="status-value">{req_count}</span>
  </div>
  <div class="status-item">
    <div class="status-dot {'red' if err_rate > 0 else 'green'}"></div>
    <span>Error Rate</span>
    <span class="status-value">{err_rate}%</span>
  </div>
  <div class="status-item">
    <div class="status-dot green"></div>
    <span>Total Cost</span>
    <span class="status-value">${total_cost:.4f}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Error Alert Banner ────────────────────────────────────────────────────────

if not fail_df.empty:
    recent_errors = fail_df.sort_values("ts", ascending=False).head(5)
    error_counts = recent_errors["error_type"].value_counts()

    # Error alert banner
    st.markdown("""
    <div style="background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);border-radius:10px;padding:16px 20px;margin-bottom:14px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <span style="font-size:20px;">🚨</span>
        <span style="font-family:Inter,sans-serif;font-size:14px;font-weight:600;color:#F87171;">System Errors Detected</span>
      </div>
      <div style="font-family:Inter,sans-serif;font-size:12px;color:#94A3B8;">
        The following errors occurred in the selected time window:
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Error breakdown in columns
    err_col1, err_col2 = st.columns([1, 1], gap="small")

    with err_col1:
        st.markdown("""
        <div class="chart-wrap">
          <div class="section-header">
            <p class="section-title">📋 Recent Errors</p>
            <span class="section-meta">Last 5 errors</span>
          </div>
        </div>""", unsafe_allow_html=True)

        for idx, (_, row) in enumerate(recent_errors.iterrows()):
            ts_str = row["ts"].strftime("%H:%M:%S")
            error_type = row.get("error_type", "Unknown")
            error_detail = row.get("payload", {}).get("detail", "No details available")
            if isinstance(error_detail, str) and len(error_detail) > 150:
                error_detail = error_detail[:150] + "..."

            # Get diagnosis for this error type
            diagnosis = get_error_diagnosis(error_type)
            sev_bg, sev_color = get_severity_color(diagnosis["severity"])

            with st.container():
                st.markdown(f"""
                <div style="background:rgba(248,113,113,0.05);border-left:3px solid {sev_color};border-radius:4px;padding:12px 14px;margin-bottom:10px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-family:Inter,sans-serif;font-size:13px;font-weight:600;color:{sev_color};">{diagnosis["title"]}</span>
                    <span style="font-family:Inter,sans-serif;font-size:11px;color:#4B5563;">{ts_str}</span>
                  </div>
                  <div style="font-family:Inter,sans-serif;font-size:11px;color:#94A3B8;line-height:1.4;margin-bottom:8px;">
                    <strong>Error:</strong> {error_detail}
                  </div>
                  <details style="margin-top:6px;">
                    <summary style="font-family:Inter,sans-serif;font-size:11px;font-weight:600;color:#38BDF8;cursor:pointer;margin-bottom:4px;">💡 View Solutions</summary>
                    <div style="margin-top:6px;padding:8px;background:rgba(52,211,153,0.08);border-radius:4px;">
                      <div style="font-family:Inter,sans-serif;font-size:10px;font-weight:600;color:#34D399;margin-bottom:4px;">CAUSES:</div>
                """, unsafe_allow_html=True)

                for cause in diagnosis["causes"]:
                    st.markdown(f'<div style="font-family:Inter,sans-serif;font-size:10px;color:#94A3B8;margin-left:8px;margin-bottom:2px;">• {cause}</div>', unsafe_allow_html=True)

                st.markdown(f"""
                      <div style="font-family:Inter,sans-serif;font-size:10px;font-weight:600;color:#34D399;margin-top:8px;margin-bottom:4px;">SOLUTIONS:</div>
                """, unsafe_allow_html=True)

                for solution in diagnosis["solutions"]:
                    st.markdown(f'<div style="font-family:Inter,sans-serif;font-size:10px;color:#94A3B8;margin-left:8px;margin-bottom:2px;">✓ {solution}</div>', unsafe_allow_html=True)

                st.markdown("""
                    </div>
                  </details>
                </div>
                """, unsafe_allow_html=True)

    with err_col2:
        st.markdown("""
        <div class="chart-wrap">
          <div class="section-header">
            <p class="section-title">📊 Error Distribution</p>
            <span class="section-meta">By type</span>
          </div>
        </div>""", unsafe_allow_html=True)

        for err_type, count in error_counts.items():
            diagnosis = get_error_diagnosis(err_type)
            sev_bg, sev_color = get_severity_color(diagnosis["severity"])
            pct = count / len(fail_df) * 100
            st.markdown(f"""
            <div style="background:{sev_bg};border-left:3px solid {sev_color};border-radius:4px;padding:10px 12px;margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:Inter,sans-serif;font-size:12px;font-weight:600;color:{sev_color};">{diagnosis["title"]}</span>
                <span style="font-family:Inter,sans-serif;font-size:12px;font-weight:600;color:#F1F5F9;">{count} ({pct:.0f}%)</span>
              </div>
              <div style="margin-top:4px;">
                <div style="background:rgba(255,255,255,0.1);border-radius:2px;height:4px;overflow:hidden;">
                  <div style="background:{sev_color};height:100%;width:{pct:.0f}%;border-radius:2px;"></div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Langfuse trace link
        latest_error = recent_errors.iloc[0] if not recent_errors.empty else None
        if latest_error is not None and latest_error.get("trace_id") and LANGFUSE_PROJECT_ID:
            st.markdown("""
            <div style="margin-top:16px;padding:12px;background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.2);border-radius:8px;">
              <div style="font-family:Inter,sans-serif;font-size:11px;font-weight:600;color:#38BDF8;margin-bottom:6px;">🔍 VIEW TRACE ON LANGFUSE</div>
              <div style="font-family:Inter,sans-serif;font-size:10px;color:#94A3B8;margin-bottom:8px;">Trace ID: {trace_id}</div>
              <a href="https://jp.cloud.langfuse.com/project/{project_id}/traces/{trace_id}" target="_blank" style="display:inline-block;padding:6px 12px;background:#38BDF8;color:#0B0F14;font-family:Inter,sans-serif;font-size:11px;font-weight:600;border-radius:4px;text-decoration:none;">Open in Langfuse →</a>
            </div>
            """.format(project_id=LANGFUSE_PROJECT_ID, trace_id=latest_error["trace_id"]), unsafe_allow_html=True)

    st.markdown('<div class="gap"></div>', unsafe_allow_html=True)


# ── KPI row (4 cards using st.metric inside HTML-wrapped columns) ───────────

# We use HTML divs for card styling + st.metric for values
# KPI cols: 4 equal columns
kc1, kc2, kc3, kc4 = st.columns(4, gap="small")

def metric_card(container, label, value, delta, slo_text, badge, badge_cls, top_cls):
    """Render a styled KPI card using markdown + native metric."""
    badge_icon = "✓" if badge_cls == "ok" else ("⚠" if badge_cls == "warn" else "✗")
    top_color  = {"ok": "#34D399", "warn": "#FBBF24", "error": "#F87171"}.get(badge_cls, "#38BDF8")
    container.markdown(f"""
<div style="background:#11161D;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:16px 16px 14px;position:relative;overflow:hidden;margin-bottom:4px;">
  <div style="position:absolute;top:0;left:0;right:0;height:2px;background:{top_color};border-radius:10px 10px 0 0;"></div>
  <div style="font-family:Inter,sans-serif;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:#94A3B8;margin-bottom:6px;">{label}</div>
  <div style="font-family:Inter,sans-serif;font-size:26px;font-weight:700;color:#F1F5F9;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-0.02em;margin-bottom:4px;">{value}</div>
  <div style="font-family:Inter,sans-serif;font-size:12px;color:#94A3B8;margin-bottom:10px;">{delta}</div>
  <span style="display:inline-flex;align-items:center;gap:3px;font-family:Inter,sans-serif;font-size:11px;font-weight:600;padding:3px 8px;border-radius:20px;background:{'rgba(52,211,153,0.12)' if badge_cls=='ok' else 'rgba(251,191,36,0.12)' if badge_cls=='warn' else 'rgba(248,113,113,0.12)'};color:{'#34D399' if badge_cls=='ok' else '#FBBF24' if badge_cls=='warn' else '#F87171'}">{badge_icon} {badge}</span>
</div>""", unsafe_allow_html=True)

lat_badge = "Within SLO" if slo_lat else "SLO Breach"
lat_cls   = "ok" if slo_lat else "error"
metric_card(kc1, "P95 Latency", f"{p95:,} ms",
            f"P50: {p50:,}ms  ·  P99: {p99:,}ms",
            f"SLO ≤ {latency_obj:,}ms", lat_badge, lat_cls, "")

metric_card(kc2, "Request Volume", f"{req_count}",
            f"{req_rate} req/min  ·  {len(fail_df)} failed",
            "≥ 1 req", "✓ Healthy", "ok", "")

err_badge = "Healthy" if slo_err else "SLO Breach"
err_cls   = "ok" if slo_err else "error"
metric_card(kc3, "Error Rate", f"{err_rate:.2f}%",
            f"{len(fail_df)} failed  ·  {req_count} total",
            f"SLO ≤ {error_obj}%", err_badge, err_cls, "")

cost_badge = "Within Budget" if slo_cost else "Budget Exceeded"
cost_cls   = "ok" if slo_cost else ("warn" if cost_pct > 80 else "ok")
metric_card(kc4, "Total Cost", f"${total_cost:.4f}",
            f"Budget ${cost_obj:.2f}  ·  Used {cost_pct:.1f}%",
            f"≤ ${cost_obj}", cost_badge, cost_cls, "")

st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

# ── Latency + Traffic row ────────────────────────────────────────────────────

c_lat, c_tra = st.columns([2, 1], gap="small")

with c_lat:
    st.markdown("""
<div class="chart-wrap">
  <div class="section-header">
    <p class="section-title">⏱ Latency Percentiles</p>
    <span class="section-meta">P50 · P95 · P99 · SLO ≤ {:,}ms</span>
  </div>
</div>""".format(latency_obj), unsafe_allow_html=True)
    # Build percentile time-series
    ts_lat = (
        latency_df.set_index("ts")["latency_ms"]
        .resample("1min")
        .agg(["median", lambda x: x.quantile(0.95), lambda x: x.quantile(0.99)])
        .reset_index()
    )
    ts_lat.columns = ["ts", "P50", "P95", "P99"]
    st.line_chart(
        ts_lat.set_index("ts"),
        height=180,
        color=["#38BDF8", "#A78BFA", "#F87171"],
    )
    # SLO indicator
    col_slo_l, col_slo_r = st.columns([1, 1])
    with col_slo_l:
        st.caption(f"P50: **{p50:,}ms** | P95: **{p95:,}ms** | P99: **{p99:,}ms**")
    with col_slo_r:
        ok = "✓ Within SLO" if slo_lat else "✗ SLO Breach"
        col = "#34D399" if slo_lat else "#F87171"
        st.markdown(f'<p style="text-align:right;color:{col};font-size:12px;font-weight:600;font-family:Inter,sans-serif;margin:0;">{ok}</p>', unsafe_allow_html=True)

with c_tra:
    st.markdown("""
<div class="chart-wrap">
  <div class="section-header">
    <p class="section-title">📬 Request Traffic</p>
    <span class="section-meta">{:,} total</span>
  </div>
</div>""".format(req_count), unsafe_allow_html=True)
    ts_req = req_df.set_index("ts").resample("1min").count()["event"].reset_index()
    ts_req.columns = ["ts", "requests"]
    st.bar_chart(ts_req.set_index("ts"), height=180, color="#4ADE80")

st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

# ── Error Rate + Cost row ────────────────────────────────────────────────────

c_err, c_cst = st.columns(2, gap="small")

with c_err:
    st.markdown("""
<div class="chart-wrap">
  <div class="section-header">
    <p class="section-title">🚨 Error Rate</p>
    <span class="section-meta">{:,} failed of {:,} total</span>
  </div>
</div>""".format(len(fail_df), req_count), unsafe_allow_html=True)
    # Build error rate time-series
    ts_req_e = req_df.set_index("ts").resample("1min").count()["event"].reset_index()
    ts_req_e.columns = ["ts", "total"]
    if not fail_df.empty:
        ts_fail_e = fail_df.set_index("ts").resample("1min").count()["event"].reset_index()
        ts_fail_e.columns = ["ts", "errors"]
        ts_err_e = ts_req_e.merge(ts_fail_e, on="ts", how="left").fillna(0)
        ts_err_e["error_rate"] = ts_err_e.apply(
            lambda r: r["errors"] / r["total"] * 100 if r["total"] > 0 else 0.0, axis=1
        )
        err_ts = ts_err_e[["ts", "error_rate"]].copy()
    else:
        err_ts = pd.DataFrame({"ts": ts_req_e["ts"], "error_rate": [0.0] * len(ts_req_e)})
    st.line_chart(err_ts.set_index("ts"), height=160, color="#FBBF24")
    # SLO
    ok = "✓ Within SLO" if slo_err else "✗ SLO Breach"
    col = "#34D399" if slo_err else "#F87171"
    st.markdown(f'<p style="color:{col};font-size:12px;font-weight:600;font-family:Inter,sans-serif;margin:0;">{ok} · SLO ≤ {error_obj}%</p>', unsafe_allow_html=True)

with c_cst:
    st.markdown(f"""
<div class="chart-wrap">
  <div class="section-header">
    <p class="section-title">💰 Cost Over Time</p>
    <span class="section-meta">${total_cost:.4f} / ${cost_obj:.2f}</span>
  </div>
</div>""", unsafe_allow_html=True)
    ts_cost = (
        cost_df.set_index("ts")["cost_usd"]
        .resample("1min").sum()
        .reset_index()
    )
    ts_cost.columns = ["ts", "cost_usd"]
    st.line_chart(ts_cost.set_index("ts"), height=160, color="#34D399")
    # Budget bar
    bar_cls = "green" if cost_pct < 50 else ("amber" if cost_pct < 80 else "red")
    st.markdown(f"""
<div style="margin-top:2px;">
  <div style="display:flex;justify-content:space-between;font-family:Inter,sans-serif;font-size:11px;color:#94A3B8;margin-bottom:4px;">
    <span>Budget used: {cost_pct:.1f}%</span>
    <span>${total_cost:.4f} / ${cost_obj:.2f}</span>
  </div>
  <div class="prog-wrap">
    <div class="prog-fill {bar_cls}" style="width:{min(cost_pct,100):.1f}%"></div>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

# ── Tokens + Quality row ─────────────────────────────────────────────────────

c_tok, c_qual = st.columns(2, gap="small")

with c_tok:
    st.markdown("""
<div class="chart-wrap">
  <div class="section-header">
    <p class="section-title">🔢 Input & Output Tokens</p>
    <span class="section-meta">{:,} total</span>
  </div>
</div>""".format(tok_in + tok_out), unsafe_allow_html=True)
    tok_ts = cost_df.set_index("ts")[["tokens_in", "tokens_out"]].resample("1min").sum().reset_index()
    tok_ts.columns = ["ts", "Input", "Output"]
    st.bar_chart(
        tok_ts.set_index("ts"),
        height=160,
        color=["#38BDF8", "#A78BFA"],
    )
    st.caption(f"In: **{tok_in:,}**  ·  Out: **{tok_out:,}**  ·  Total: **{tok_in+tok_out:,}**")

with c_qual:
    st.markdown(f"""
<div class="chart-wrap">
  <div class="section-header">
    <p class="section-title">⭐ Quality Proxy Score</p>
    <span class="section-meta">Mean: {mean_qual:.4f}</span>
  </div>
</div>""", unsafe_allow_html=True)
    ts_qual = (
        cost_df.set_index("ts")["quality_score"]
        .resample("1min").mean()
        .reset_index()
    )
    ts_qual.columns = ["ts", "quality_score"]
    st.line_chart(ts_qual.set_index("ts"), height=160, color="#34D399")
    ok = "✓ Healthy" if slo_qual else "⚠ Low Quality"
    col = "#34D399" if slo_qual else "#FBBF24"
    st.markdown(f'<p style="color:{col};font-size:12px;font-weight:600;font-family:Inter,sans-serif;margin:0;">{ok} · SLO ≥ {qual_obj}</p>', unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    f"Day 13 Observability Lab · 6 panels · Source: `data/logs.jsonl` · "
    f"SLO: `config/slo.yaml` · Schema v{dash_meta.get('schema_version','?')}"
)
