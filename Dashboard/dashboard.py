import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cucumber Test Dashboard", layout="wide")

st.title("Cucumber Test Results Dashboard")

# Upload or load CSV
def load_data():
    try:
        return pd.read_csv(r"c:/Users/yashg1/Desktop/Demoprep/Vertexone/Results/parsed_report.csv")
    except Exception:
        return pd.DataFrame()

df = load_data()


if df.empty:
    st.warning("No data found. Please ensure 'parsed_report.csv' is available in the Results folder.")
    st.stop()

# --- AI Overview Animated Section ---
import time
ai_robot_svg = """
<svg class='ai-overview-robot' width="32" height="32" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="40" height="40" rx="20" fill="#232526"/><ellipse cx="20" cy="25" rx="10" ry="7" fill="#A5D6FF" fill-opacity="0.13"/><circle cx="20" cy="18" r="9" fill="#A5D6FF"/><ellipse cx="16.5" cy="18" rx="1.5" ry="2" fill="#232526"/><ellipse cx="23.5" cy="18" rx="1.5" ry="2" fill="#232526"/><rect x="17" y="23" width="6" height="2" rx="1" fill="#232526"/></svg>
"""
st.markdown("""
<style>
.ai-overview-card {
    background: linear-gradient(90deg, #232526 0%, #414345 100%);
    color: #e0e6ed;
    border-radius: 16px;
    padding: 1.6em 2em 1.6em 2em;
    margin-bottom: 2em;
    box-shadow: 0 4px 18px rgba(61,220,151,0.10), 0 2px 8px rgba(30,30,30,0.18);
    font-size: 1.18em;
    border: 1.5px solid #444b53;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    position: relative;
    overflow: hidden;
    min-height: 90px;
}
.ai-overview-title {
    font-weight: bold;
    font-size: 1.25em;
    color: #A5D6FF;
    margin-bottom: 0.5em;
    letter-spacing: 0.01em;
    display: flex;
    align-items: center;
}
.ai-overview-robot {
    margin-right: 0.6em;
    vertical-align: middle;
}
.ai-overview-anim {
    display: inline-block;
    min-height: 2.2em;
    font-size: 1.13em;
    letter-spacing: 0.01em;
    line-height: 1.5em;
}
</style>
""", unsafe_allow_html=True)


# --- AI Overview: All variables in one block, summary assigned only once ---
from collections import Counter
import re as _re
total = len(df)
passed = (df['step_status'] == 'PASSED').sum()
failed = (df['step_status'] == 'FAILED').sum()
fail_pct = (failed / total * 100) if total else 0
unique_features = df['feature_name'].nunique()
feature_stats = df.groupby('feature_name').agg(
    total_scenarios = ('scenario_name', 'count'),
    failed_scenarios = ('step_status', lambda x: (x == 'FAILED').sum())
).reset_index()
feature_stats['defect_density'] = feature_stats['failed_scenarios'] / feature_stats['total_scenarios']
feature_stats['defect_density_pct'] = (feature_stats['defect_density'] * 100).round(2)
top_feature = feature_stats.sort_values('defect_density', ascending=False).iloc[0] if not feature_stats.empty else None
most_scenarios_feature = feature_stats.sort_values('total_scenarios', ascending=False).iloc[0] if not feature_stats.empty else None
most_failed_feature = feature_stats.sort_values('failed_scenarios', ascending=False).iloc[0] if not feature_stats.empty else None
likely_causes = []
for ai in df[df['step_status']=='FAILED']['ai_solution'].dropna():
    match = _re.search(r"Likely Cause:\n([\s\S]*?)Fix Steps:", str(ai))
    if match:
        cause = match.group(1).strip()
        likely_causes.append(cause)
cause_counts = Counter(likely_causes)
top_cause = cause_counts.most_common(1)[0][0] if cause_counts else "N/A"
if 'step_duration_ms' in df.columns and not df['step_duration_ms'].isnull().all():
    avg_duration = df['step_duration_ms'].mean()
    max_duration = df['step_duration_ms'].max()
else:
    avg_duration = 0
    max_duration = 0
if 'ai_solution' in df.columns and not df['ai_solution'].isnull().all():
    ai_suggestion_pct = (df['ai_solution'].notna().sum() / total * 100) if total else 0
else:
    ai_suggestion_pct = 0
ai_summary = (
    f"<b>AI Overview:</b> <b>{unique_features}</b> features, <b>{total}</b> scenarios.<br>"
    f"<b>{passed}</b> passed, <b>{failed}</b> failed (<b>{fail_pct:.1f}%</b> fail rate).<br>"
    f"<b>Most tested feature:</b> {most_scenarios_feature['feature_name']} ({most_scenarios_feature['total_scenarios']} scenarios)<br>"
    f"<b>Most failed feature:</b> {most_failed_feature['feature_name']} ({most_failed_feature['failed_scenarios']} failed)<br>"
    f"<b>Top defect density:</b> {top_feature['feature_name']} ({top_feature['defect_density_pct']}%)<br>"
    f"<b>Most common failure cause:</b> {top_cause}<br>"
    f"<b>Avg. scenario duration:</b> {avg_duration:.0f} ms<br>"
    f"<b>Max scenario duration:</b> {max_duration:.0f} ms<br>"
    f"<b>AI suggestions present in:</b> {ai_suggestion_pct:.1f}% of scenarios<br>"
    "<span style='color:#FFD740;'>Actionable insights and fixes are provided below for each failure. Review high defect density features and common causes for targeted improvements.</span>"
)

# Typewriter animation (safe for HTML tags)
import html
import re
ai_card = st.empty()
def safe_typewriter(text, delay=0.012):
    tag_stack = []
    out = ""
    i = 0
    while i < len(text):
        if text[i] == '<':
            # Find the end of the tag
            close = text.find('>', i)
            if close == -1:
                break
            tag = text[i:close+1]
            out += tag
            # Track open/close tags
            if not tag.startswith('</') and not tag.endswith('/>'):
                tag_name = re.sub(r'[\s/>].*', '', tag[1:])
                tag_stack.append(tag_name)
            elif tag.startswith('</'):
                if tag_stack:
                    tag_stack.pop()
            i = close+1
        else:
            out += text[i]
            i += 1
        ai_card.markdown(f"""
        <div class='ai-overview-card'>
          <div class='ai-overview-title'>{ai_robot_svg}AI Overview</div>
          <span class='ai-overview-anim'>{out}{''.join(f'</{t}>' for t in reversed(tag_stack))}</span>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(delay)
safe_typewriter(ai_summary)

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    features = ["All"] + sorted(df['feature_name'].dropna().unique().tolist())
    feature = st.selectbox("Feature", features)
    status = st.selectbox("Status", ["All", "PASSED", "FAILED"])
    search = st.text_input("Search scenario/steps")

filtered = df.copy()
if feature != "All":
    filtered = filtered[filtered['feature_name'] == feature]
if status != "All":
    filtered = filtered[filtered['step_status'] == status]
if search:
    filtered = filtered[
        filtered['scenario_name'].str.contains(search, case=False, na=False) |
        filtered['steps'].str.contains(search, case=False, na=False)
    ]


# Summary stats

# Add Pending and Skipped scenario counts
pending = (df['step_status'].str.upper() == 'PENDING').sum() if 'step_status' in df.columns else 0
skipped = (df['step_status'].str.upper() == 'SKIPPED').sum() if 'step_status' in df.columns else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Scenarios", len(df))
col2.metric("Passed", (df['step_status'] == 'PASSED').sum())
col3.metric("Failed", (df['step_status'] == 'FAILED').sum())
col4.metric("Pending", pending)
col5.metric("Skipped", skipped)

# --- DEFECT DENSITY BY FEATURE ---
st.markdown("""
<style>
.defect-density-card {
    background: linear-gradient(90deg, #232526 0%, #414345 100%);
    color: #e0e6ed;
    border-radius: 12px;
    padding: 1.2em 1.5em 1.2em 1.5em;
    margin-bottom: 1.5em;
    box-shadow: 0 2px 8px rgba(30,30,30,0.25);
    font-size: 1.08em;
    border: 1px solid #444b53;
    transition: box-shadow 0.2s;
    overflow-x: auto;
}
.defect-density-card:hover {
    box-shadow: 0 4px 16px rgba(255,215,64,0.18), 0 2px 8px rgba(30,30,30,0.25);
}
.defect-density-title { font-weight: bold; font-size: 1.18em; margin-bottom: 0.7em; font-family: 'Georgia', serif; }
.defect-density-table {
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
    margin: 0 auto;
    font-size: 1.04em;
    table-layout: fixed;
}
.defect-density-table th, .defect-density-table td {
    padding: 0.7em 1.2em;
    text-align: center;
    vertical-align: middle;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.defect-density-table th {
    color: #FFD740;
    border-bottom: 2px solid #444b53;
    background: #232526;
    text-align: center;
}
.defect-density-table td {
    border-bottom: 1px solid #33373c;
    text-align: center;
}
.defect-density-table tr.high-density {
    background: rgba(255,64,64,0.13);
}
</style>
""", unsafe_allow_html=True)

# Calculate defect density by feature
feature_stats = df.groupby('feature_name').agg(
    total_scenarios = ('scenario_name', 'count'),
    failed_scenarios = ('step_status', lambda x: (x == 'FAILED').sum())
).reset_index()

# Show defect density as a percentage
feature_stats['defect_density'] = feature_stats['failed_scenarios'] / feature_stats['total_scenarios']
feature_stats['defect_density_pct'] = (feature_stats['defect_density'] * 100).round(2)
feature_stats = feature_stats.sort_values('defect_density', ascending=False)

# --- Modern Defect Density Table Card (Aligned) ---
st.markdown("""
<style>
.defect-density-card {
    background: linear-gradient(90deg, #232526 0%, #414345 100%);
    border-radius: 14px;
    box-shadow: 0 2px 12px rgba(61,220,151,0.10), 0 1px 4px rgba(30,30,30,0.13);
    padding: 1.2em 1.2em 1.2em 1.2em;
    margin-bottom: 2em;
    border: 1.5px solid #444b53;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    color: #e0e6ed;
    max-width: 820px;
}
.defect-density-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.2em;
    font-size: 1.08em;
    background: none;
}
.defect-density-table th {
    background: #2a2d32;
    color: #A5D6FF;
    font-weight: 600;
    padding: 0.55em 0.3em 0.55em 0.3em;
    border-bottom: 2.5px solid #3ddc97;
    text-align: center;
    letter-spacing: 0.01em;
}
.defect-density-table td {
    padding: 0.45em 0.3em 0.45em 0.3em;
    border-bottom: 1.5px solid #33373c;
    text-align: center;
    font-size: 1.04em;
}
.defect-density-table tr.high-density {
    background: rgba(255,64,64,0.13);
}
.defect-density-table tr:last-child td {
    border-bottom: none;
}
.defect-density-title {
    font-size: 1.18em;
    font-weight: bold;
    color: #FFD740;
    margin-bottom: 0.1em;
    letter-spacing: 0.01em;
    text-align: left;
}
</style>
""", unsafe_allow_html=True)

# Build the table as a single HTML block for perfect alignment
table_rows = []
for i, row in feature_stats.iterrows():
    highlight = " class='high-density'" if i < 3 and row['defect_density'] > 0 else ""
    table_rows.append(f"<tr{highlight}><td>{row['feature_name']}</td><td>{row['total_scenarios']}</td><td>{row['failed_scenarios']}</td><td><b>{row['defect_density_pct']}%</b></td></tr>")
table_html = f"""
<div class='defect-density-card'>
  <div class='defect-density-title'>Defect Density by Feature</div>
  <table class='defect-density-table'>
    <colgroup>
      <col style='width:38%;'>
      <col style='width:18%;'>
      <col style='width:18%;'>
      <col style='width:26%;'>
    </colgroup>
    <tr><th>Feature</th><th>Total Scenarios</th><th>Failed</th><th>Defect Density (%)</th></tr>
    {''.join(table_rows)}
  </table>
</div>
"""
st.markdown(table_html, unsafe_allow_html=True)


# --- CATCHY FAILED SCENARIO CARDS ---
failed = df[df['step_status'] == 'FAILED']
if not failed.empty:

    # --- TOP 5 FAILURE REASONS & FAILING TESTS ---

    import re as _re
    from collections import Counter
    st.markdown("""
    <style>
    .fail-metrics-card {
        background: linear-gradient(90deg, #232526 0%, #414345 100%);
        color: #e0e6ed;
        border-radius: 12px;
        padding: 1.2em 1.5em 1.2em 1.5em;
        margin-bottom: 1.5em;
        box-shadow: 0 2px 8px rgba(30,30,30,0.25);
        font-size: 1.08em;
        border: 1px solid #444b53;
        transition: box-shadow 0.2s;
    }
    .fail-metrics-card:hover {
        box-shadow: 0 4px 16px rgba(61,220,151,0.18), 0 2px 8px rgba(30,30,30,0.25);
    }
    .fail-metrics-title { font-weight: bold; font-size: 1.18em; margin-bottom: 0.7em; font-family: 'Georgia', serif; }
    .fail-metrics-list { margin: 0.2em 0 0.7em 0.5em; }
    .fail-metrics-list li { margin-bottom: 0.2em; }
    </style>
    """, unsafe_allow_html=True)

    # --- Top 5 Failure Reasons ---
    likely_causes = []
    cause_examples = {}
    for idx, row in failed.iterrows():
        ai = row['ai_solution']
        match = _re.search(r"Likely Cause:\n([\s\S]*?)Fix Steps:", str(ai))
        if match:
            cause = match.group(1).strip()
            likely_causes.append(cause)
            cause_examples.setdefault(cause, []).append(row['scenario_name'])
    cause_counts = Counter(likely_causes)
    top_causes = cause_counts.most_common(5)

    # --- Top 5 Failing Tests ---
    failed['test_id'] = failed['feature_name'].astype(str) + " | " + failed['scenario_name'].astype(str)
    test_examples = {}
    for idx, row in failed.iterrows():
        test_id = row['test_id']
        test_examples.setdefault(test_id, []).append(row['error_message'])
    test_counts = Counter(failed['test_id'])
    top_tests = test_counts.most_common(5)

    colA, colB = st.columns(2)
    with colA:
        st.markdown("<div class='fail-metrics-card'>", unsafe_allow_html=True)
        st.markdown("<div class='fail-metrics-title'>Top 5 Failure Reasons</div>", unsafe_allow_html=True)
        for cause, count in top_causes:
            with st.expander(f"{cause}  ", expanded=False):
                st.markdown(f"<span style='color:#A5D6FF;font-weight:bold;'>(x{count})</span>", unsafe_allow_html=True)
                st.markdown("<b>Example Scenarios:</b>", unsafe_allow_html=True)
                for scen in cause_examples[cause][:3]:
                    st.markdown(f"- {scen}")
        st.markdown("</div>", unsafe_allow_html=True)
    with colB:
        st.markdown("<div class='fail-metrics-card'>", unsafe_allow_html=True)
        st.markdown("<div class='fail-metrics-title'>Top 5 Failing Tests</div>", unsafe_allow_html=True)
        for test, count in top_tests:
            with st.expander(f"{test}", expanded=False):
                st.markdown(f"<span style='color:#FFD740;font-weight:bold;'>(x{count})</span>", unsafe_allow_html=True)
                st.markdown("<b>Error Messages (sample):</b>", unsafe_allow_html=True)
                for err in (em for em in test_examples[test] if pd.notna(em)):
                    st.markdown(f"- {err[:200]}{'...' if len(str(err))>200 else ''}")
                    break
        st.markdown("</div>", unsafe_allow_html=True)

    # GitHub Copilot glitter SVG logo (small, inline)
    copilot_glitter_svg = '''<svg width="28" height="28" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle;margin-right:8px;"><rect width="40" height="40" rx="20" fill="#232526"/><circle cx="20" cy="20" r="13" fill="url(#paint0_radial)"/><g filter="url(#glow)"><ellipse cx="14.5" cy="20" rx="2.5" ry="3.5" fill="#fff"/><ellipse cx="25.5" cy="20" rx="2.5" ry="3.5" fill="#fff"/></g><circle cx="14.5" cy="20" r="1.2" fill="#232526"/><circle cx="25.5" cy="20" r="1.2" fill="#232526"/><rect x="17" y="26" width="6" height="2" rx="1" fill="#232526"/><rect x="17" y="12" width="6" height="2" rx="1" fill="#232526"/><defs><radialGradient id="paint0_radial" cx="0" cy="0" r="1" gradientTransform="translate(20 20) scale(13)" gradientUnits="userSpaceOnUse"><stop stop-color="#A5D6FF"/><stop offset="1" stop-color="#232526" stop-opacity="0"/></radialGradient><filter id="glow" x="8" y="15" width="25" height="10" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="1.5"/></filter></defs></svg>'''
    st.markdown("""
    <style>
    .fail-card {
        background: linear-gradient(90deg, #232526 0%, #414345 100%);
        color: #e0e6ed;
        border-radius: 12px;
        padding: 1.2em 1.5em 1.2em 1.5em;
        margin-bottom: 1em;
        box-shadow: 0 2px 8px rgba(30,30,30,0.25);
        font-size: 1.1em;
        border: 1px solid #444b53;
    }
    .fail-title { font-weight: bold; font-size: 1.2em; display: flex; align-items: center; }
    .fail-ai { margin-top: 0.5em; font-size: 1em; }
    </style>
    """, unsafe_allow_html=True)
    st.subheader(":blue[Failed Scenarios & AI Insights]")
    import re as _re
    for idx, row in failed.iterrows():
        ai = row['ai_solution']
        # Split into sections for custom rendering
        cause = fix = benefit = ""
        cause_match = _re.search(r"Likely Cause:\n([\s\S]*?)Fix Steps:", ai)
        fix_match = _re.search(r"Fix Steps:\n([\s\S]*?)Benefits:", ai)
        benefit_match = _re.search(r"Benefits:\n([\s\S]*)", ai)
        if cause_match:
            cause = cause_match.group(1).strip()
        if fix_match:
            fix = fix_match.group(1).strip()
        if benefit_match:
            benefit = benefit_match.group(1).strip()
        st.markdown(f"""
        <div class='fail-card'>
            <div class='fail-title'>{copilot_glitter_svg} <span style='font-size:1.15em;'>{row['scenario_name']}</span></div>
            <div style='margin-top:0.7em;'>
                <div style='background:rgba(165,214,255,0.10);border-radius:8px;padding:0.7em 1em 0.7em 1em;margin-bottom:0.5em;'>
                    <span style='font-weight:600;color:#A5D6FF;'><svg width="18" height="18" style="vertical-align:middle;margin-right:4px;" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#A5D6FF"/><path d="M12 8v4" stroke="#232526" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="16" r="1" fill="#232526"/></svg> Likely Cause</span><br>
                    <span style='color:#e0e6ed;font-size:1.04em;'>{cause.replace(chr(10),'<br>')}</span>
                </div>
                <div style='background:rgba(61,220,151,0.10);border-radius:8px;padding:0.7em 1em 0.7em 1em;margin-bottom:0.5em;'>
                    <span style='font-weight:600;color:#3ddc97;'><svg width="18" height="18" style="vertical-align:middle;margin-right:4px;" viewBox="0 0 24 24" fill="none"><rect x="2" y="2" width="20" height="20" rx="5" fill="#3ddc97"/><path d="M8 12h8M12 8v8" stroke="#232526" stroke-width="2" stroke-linecap="round"/></svg> Fix Steps</span><br>
                    <span style='color:#e0e6ed;font-size:1.04em;'>{fix.replace(chr(10),'<br>')}</span>
                </div>
                <div style='background:rgba(255,215,64,0.10);border-radius:8px;padding:0.7em 1em 0.7em 1em;'>
                    <span style='font-weight:600;color:#FFD740;'><svg width="18" height="18" style="vertical-align:middle;margin-right:4px;" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#FFD740"/><path d="M12 8v4" stroke="#232526" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="16" r="1" fill="#232526"/></svg> Benefit</span><br>
                    <span style='color:#e0e6ed;font-size:1.04em;'>{benefit.replace(chr(10),'<br>')}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)



# Table
st.subheader("Scenario Details")
st.dataframe(filtered[['feature_name','scenario_name','step_status','step_duration_ms','error_message','ai_solution']], height=400)

# Drill-down
st.subheader("Scenario Drill-down")
row = st.selectbox("Select a scenario to view details:", filtered['scenario_name'].unique())
if row:
    details = filtered[filtered['scenario_name'] == row].iloc[0]
    st.markdown(f"**Feature:** {details['feature_name']}")
    st.markdown(f"**Scenario:** {details['scenario_name']}")
    st.markdown(f"**Status:** {details['step_status']}")
    st.markdown(f"**Duration (ms):** {details['step_duration_ms']}")
    st.markdown("**Steps:**")
    st.code(details['steps'])
    if details['step_status'] != 'PASSED':
        if details['error_message']:
            st.markdown("**Error Message:**")
            st.error(details['error_message'])
        if details['ai_solution']:
            import re as _re
            ai = details['ai_solution']
            cause = fix = benefit = ""
            cause_match = _re.search(r"Likely Cause:\n([\s\S]*?)Fix Steps:", ai)
            fix_match = _re.search(r"Fix Steps:\n([\s\S]*?)Benefits:", ai)
            benefit_match = _re.search(r"Benefits:\n([\s\S]*)", ai)
            if cause_match:
                cause = cause_match.group(1).strip()
            if fix_match:
                fix = fix_match.group(1).strip()
            if benefit_match:
                benefit = benefit_match.group(1).strip()
            st.markdown("**AI Solution:**")
            if cause:
                st.markdown(
                    """
<div style='background:rgba(165,214,255,0.10);border-radius:8px;padding:0.7em 1em 0.7em 1em;margin-bottom:0.5em;'>
<b style='color:#A5D6FF;'>Likely Cause</b><br>
<span style='color:#e0e6ed;font-size:1.04em;'>""" + cause.replace('\n', '<br>') + "</span></div>" , unsafe_allow_html=True)
            if fix:
                st.markdown(
                    """
<div style='background:rgba(61,220,151,0.10);border-radius:8px;padding:0.7em 1em 0.7em 1em;margin-bottom:0.5em;'>
<b style='color:#3ddc97;'>Fix Steps</b><br>
<span style='color:#e0e6ed;font-size:1.04em;'>""" + '<br>'.join([f"{step.strip()}" for step in fix.split('\n') if step.strip()]) + "</span></div>" , unsafe_allow_html=True)
            if benefit:
                st.markdown(
                    """
<div style='background:rgba(255,215,64,0.10);border-radius:8px;padding:0.7em 1em 0.7em 1em;'>
<b style='color:#FFD740;'>Benefits</b><br>
<span style='color:#e0e6ed;font-size:1.04em;'>""" + '<br>'.join([f"- {b.strip()}" for b in benefit.split('\n') if b.strip()]) + "</span></div>" , unsafe_allow_html=True)
