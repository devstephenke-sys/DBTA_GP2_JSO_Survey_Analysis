# ===========================================================
# 📊 DBTA GP2 Job Services Officers Unified Survey Dashboard
# (with robust Collaboration / Multi-Select behavior)
# ===========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import re

# ===========================================================
# ⚙️ Page Setup & Theme
# ===========================================================
st.set_page_config(page_title="DBTA GP2 JSO Dashboard", layout="wide")
today = date.today().strftime("%B %d, %Y")

# ===========================================================
# 🎨 Theme Switch
# ===========================================================
theme_choice = st.sidebar.radio("🌓 Select Theme", ["🌞 Light Mode", "🌙 Dark Mode"])

if theme_choice == "🌞 Light Mode":
    BG_COLOR = "#f5f7fa"
    TEXT_COLOR = "#333"
    CARD_COLOR = "#ffffff"
    CHART_BG = "white"
    CHART_COLOR = px.colors.qualitative.Vivid
else:
    BG_COLOR = "#1e1e1e"
    TEXT_COLOR = "#f2f2f2"
    CARD_COLOR = "#2b2b2b"
    CHART_BG = "#2b2b2b"
    CHART_COLOR = px.colors.qualitative.Safe

# ===========================================================
# 🧱 Don Bosco Header
# ===========================================================
st.markdown(f"""
<div style="
    background-color:#004E8C;
    color:white;
    padding:25px 35px;
    border-radius:12px;
    box-shadow:0px 3px 10px rgba(0,0,0,0.3);
    font-family:Calibri, Arial, sans-serif;
    margin-bottom:25px;
">
    <div style="display:flex; align-items:center; justify-content:space-between;">
        <div>
            <h1 style="margin:0; font-size:28px; font-weight:600;">DBTA GP2 Job Services Officers Survey Dashboard</h1>
            <p style="margin:5px 0 0 0; font-size:15px; color:#E5ECF6;">Baseline Analysis | Empowering Youth through Quality TVET</p>
        </div>
        <div style="text-align:right;">
            <p style="margin:0; font-size:14px; color:#ddd;">Generated on {today}</p>
            <img src="DonBoscoTechAfricaLogo.png" width="120" style="border-radius:8px; margin-top:6px;">
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ===========================================================
# 📥 Load Data
# ===========================================================
@st.cache_data
def load_data():
    file_path = "DBTA_GP2_Survey_JSO.xlsx"
    df = pd.read_excel(file_path, sheet_name="Cleaned Data")
    return df

data = load_data()
country_col = [c for c in data.columns if "country" in c.lower()][0]

# ===========================================================
# 🧠 Detect Question Types (Yes/No, Rating, Collaboration)
# ===========================================================
exclude_keywords = ["name", "respondent", "email", "phone", "id", "contact"]
filtered_cols = [c for c in data.columns if not any(k in c.lower() for k in exclude_keywords)]

yes_no_cols, rating_cols = [], []
for col in filtered_cols:
    vals = data[col].dropna().astype(str).str.lower().unique()
    if set(vals).issubset({'yes', 'no'}):
        yes_no_cols.append(col)
    else:
        series = pd.to_numeric(data[col], errors='coerce').dropna()
        if len(series) > 0 and series.between(1, 5).all():
            rating_cols.append(col)

# Collaboration detection:
# Two possible patterns in your dataset:
# 1) multiple columns where column name contains the option (with bracket label)
# 2) a single multi-select column (cells contain "opt1; opt2" etc.)
# We'll try to detect both.
collab_cols_multi = []      # columns that are single multi-select (contain separators)
collab_cols_yesno = []      # columns that are per-option yes/no (contain bracket labels or option text)

# heuristics: if a column contains separators like ';' or ',' it's likely multi-select single-column
sep_pattern = re.compile(r"[;,/|]")

for col in data.columns:
    sample = data[col].dropna().astype(str).head(200).str.lower()
    if sample.str.contains(sep_pattern).any():
        # treat as multi-select single column
        collab_cols_multi.append(col)
    # identify per-option columns (e.g. columns containing '[' or known option text)
    if ("collaborate" in col.lower() and "[" in col) or ("collaborate" in col.lower() and "choose all" in col.lower()):
        collab_cols_yesno.append(col)

# For per-option yes/no columns, derive readable labels if they include bracket text
collab_labels_yesno = []
collab_map_yesno = {}
for col in collab_cols_yesno:
    # try to extract the bracket label e.g. "... [Sharing best practices]" -> "Sharing best practices"
    m = re.search(r"\[([^\]]+)\]", col)
    label = (m.group(1).strip() if m else col).strip()
    collab_labels_yesno.append(label)
    collab_map_yesno[label] = col

# For multi-select single columns, create labels by sampling unique options
collab_labels_multi = []
collab_map_multi = {}
for col in collab_cols_multi:
    # extract distinct options from sample rows
    opts = (
        data[col].dropna().astype(str)
        .str.split(sep_pattern)
        .explode()
        .str.strip()
        .str.lower()
        .value_counts()
    )
    # pick top N options as labels (store lowercase keys)
    labels = opts.index.tolist()[:20]
    for lab in labels:
        label_display = lab.title()
        collab_labels_multi.append(label_display)
        collab_map_multi[label_display] = (col, lab)  # store (column, canonical option lowercase)

# unify labels and mapping for sidebar selection
collab_labels = collab_labels_yesno + collab_labels_multi
collab_map = {}
collab_map.update(collab_map_yesno)   # maps label -> col (yes/no column)
collab_map.update(collab_map_multi)    # maps label -> (col, option_lower)

# ===========================================================
# 🎛️ Sidebar Filters
# ===========================================================
st.sidebar.header("📊 Dashboard Controls")

q_type = st.sidebar.radio(
    "Select Data Type to Explore:",
    ["✅ Yes/No", "⭐ Rating (1–5)", "🤝 Collaboration (Multi-Select)"]
)
country_list = ["All"] + sorted(data[country_col].dropna().unique().tolist())
country_sel = st.sidebar.selectbox("🌍 Select Country", country_list)

if q_type == "✅ Yes/No":
    question_list = yes_no_cols
elif q_type == "⭐ Rating (1–5)":
    question_list = rating_cols
else:
    # if no collaboration labels found, fallback to reasonable default string
    question_list = collab_labels if collab_labels else ["In what ways do Don Bosco TVET centres collaborate?"]

question_sel = st.sidebar.selectbox("🧩 Select Question / Collaboration Option", question_list)

# ===========================================================
# ✅ YES/NO Analysis (unchanged)
# ===========================================================
if q_type == "✅ Yes/No":
    df = data.copy() if country_sel == "All" else data[data[country_col] == country_sel]
    total = df[question_sel].count()
    yes_count = (df[question_sel].astype(str).str.lower() == "yes").sum()
    no_count = (df[question_sel].astype(str).str.lower() == "no").sum()

    yes_pct = round((yes_count / total) * 100, 1) if total > 0 else 0.0
    no_pct = round(100 - yes_pct, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌍 Country", country_sel if country_sel != "All" else "All")
    c2.metric("👥 Total Responses", total)
    c3.metric("✅ Yes (%)", f"{yes_pct:.1f}%")
    c4.metric("❌ No (%)", f"{no_pct:.1f}%")

    fig = px.bar(
        x=["Yes", "No"], y=[yes_count, no_count],
        text=[f"{yes_pct:.1f}%", f"{no_pct:.1f}%"],
        color=["Yes", "No"],
        color_discrete_map={'Yes': '#0099ff', 'No': '#E66225'},
        title=f"{question_sel}<br><span style='font-size:14px; color:#ccc;'>({country_sel})</span>"
    )
    fig.update_traces(textposition="outside", width=0.4)
    fig.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR, title_x=0.5)
    st.plotly_chart(fig, use_container_width=True)

    if yes_pct >= 80:
        rec = "Strong alignment with DBTA’s objectives. This area shows excellence and can be a model for replication."
    elif 50 <= yes_pct < 80:
        rec = "Moderate engagement. Reinforcing capacity-building, mentoring, and improved access to tools may enhance outcomes."
    else:
        rec = "Low engagement detected. Targeted sensitization and support are needed to raise awareness and participation."

    st.markdown(f"""
    <div style="background-color:{CARD_COLOR};border-left:6px solid #0099ff;
    border-radius:10px;padding:18px 25px;margin-top:25px;
    font-family:Calibri;color:{TEXT_COLOR};">
        <h3 style="color:#0099ff;">📋 Summary</h3>
        <p>The question <b>“{question_sel}”</b> received <b>{total}</b> responses.
        <b>{yes_pct:.1f}%</b> answered <span style="color:#00A859;">Yes</span> and
        <b>{no_pct:.1f}%</b> answered <span style="color:#E66225;">No</span>.</p>
        <h3 style="color:#0099ff;">💡 Recommendation</h3>
        <p>{rec}</p>
    </div>
    """, unsafe_allow_html=True)

# ===========================================================
# ⭐ RATING (1–5) Analysis (unchanged)
# ===========================================================
elif q_type == "⭐ Rating (1–5)":
    df = data.copy() if country_sel == "All" else data[data[country_col] == country_sel]
    df[question_sel] = pd.to_numeric(df[question_sel], errors='coerce')
    df = df.dropna(subset=[question_sel])

    total = len(df)
    avg_rating = round(df[question_sel].mean(), 2)
    high_pct = round(((df[question_sel] >= 4).sum() / total) * 100, 1) if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌍 Country", country_sel if country_sel != "All" else "All")
    c2.metric("👥 Total Responses", total)
    c3.metric("⭐ Average Rating", avg_rating)
    c4.metric("🌟 Rated 4–5 (%)", f"{high_pct:.1f}%")

    fig = px.pie(
        df, names=question_sel, hole=0.4,
        title=f"{question_sel}<br><span style='font-size:14px; color:#ccc;'>({country_sel})</span>",
        color_discrete_sequence=px.colors.sequential.Blues_r if theme_choice == "🌙 Dark Mode" else px.colors.sequential.Blues
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR, title_x=0.5)
    st.plotly_chart(fig, use_container_width=True)

    if avg_rating >= 4:
        rec = "High satisfaction reflects strong standards. Sustain mentorship and peer learning to maintain excellence."
    elif 3 <= avg_rating < 4:
        rec = "Moderate satisfaction—room for growth. Encourage practical feedback alignment."
    else:
        rec = "Low satisfaction signals improvement areas in training and accessibility."

    st.markdown(f"""
    <div style="background-color:{CARD_COLOR};border-left:6px solid #0099ff;
    border-radius:10px;padding:18px 25px;margin-top:25px;
    font-family:Calibri;color:{TEXT_COLOR};">
        <h3 style="color:#0099ff;">📋 Summary</h3>
        <p>{total} valid responses. Average rating: <b>{avg_rating}</b>, with <b>{high_pct:.1f}%</b> rating 4–5.</p>
        <h3 style="color:#0099ff;">💡 Recommendation</h3>
        <p>{rec}</p>
    </div>
    """, unsafe_allow_html=True)

# ===========================================================
# 🤝 COLLABORATION (Multi-Select) Analysis — NEW LOGIC
# ===========================================================
elif q_type == "🤝 Collaboration (Multi-Select)":
    # NOTE: For collaboration we IGNORE the country_sel filter and always show counts across all countries.
    st.info("Country filter is ignored for Collaboration analysis. Showing counts across all countries for the selected collaboration option.")

    # Determine whether the selected label maps to a yes/no column or a multi-select column+option
    mapping = collab_map.get(question_sel)

    # Prepare dataframe copy and normalize country
    df = data.copy()
    df[country_col] = df[country_col].astype(str).str.strip()

    # boolean mask of respondents who selected the chosen collaboration option
    if mapping is None:
        # fallback: try to search the text across all columns for that label string
        target_lower = question_sel.lower()
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(target_lower).any(), axis=1)
    else:
        # mapping can be either:
        # - a column name string (yes/no column), or
        # - a tuple (col, option_lower) for multi-select single column
        if isinstance(mapping, str):
            col = mapping
            # normalize values and test membership in positive set
            positive_values = {'yes','y','true','1','x','selected','checked','✓','√'}
            mask = df[col].astype(str).str.strip().str.lower().isin(positive_values)
        else:
            # mapping is (col, option_lower)
            col, option_lower = mapping
            # handle single-cell multi-select: split by separators and match option_lower
            def row_has_option(val):
                if pd.isna(val):
                    return False
                parts = re.split(r"[;,/|]", str(val))
                parts = [p.strip().lower() for p in parts if p.strip()]
                return option_lower in parts
            mask = df[col].apply(row_has_option)

    # Now group by country for counts (we use all countries)
    grouped = df[mask].groupby(country_col).size().reset_index(name="Count")
    # Ensure countries with zero are not shown (we want only countries that have selected the option)
    grouped = grouped.sort_values("Count", ascending=False)

    # If no respondents found
    if grouped.empty:
        st.warning(f"No respondents in the entire dataset selected '{question_sel}'.")
    else:
        # Bar chart across all countries (country_sel ignored)
        fig = px.bar(
            grouped, x=country_col, y="Count", text="Count",
            color=country_col, color_discrete_sequence=CHART_COLOR,
            title=f"Respondents Selecting “{question_sel}” — All Countries"
        )
        fig.update_traces(textposition="outside", marker_line_color="white", marker_line_width=1.3)
        fig.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR, title_x=0.5)
        st.plotly_chart(fig, use_container_width=True)

        # Summary + collaboration-specific recommendation
        total_resp = int(grouped["Count"].sum())
        top_row = grouped.iloc[0]
        top_country = top_row[country_col]
        top_count = int(top_row["Count"])

        # Collaboration-specific messaging (different thresholds & tone)
        if total_resp >= 30:
            reco = (
                f"High adoption of <b>{question_sel}</b> across the network (n={total_resp}). "
                f"{top_country} leads with {top_count} mentions — consider documenting their approach and hosting a regional exchange."
            )
        elif 10 <= total_resp < 30:
            reco = (
                f"Moderate adoption of <b>{question_sel}</b> (n={total_resp}). "
                "Opportunity to strengthen this collaboration by organizing targeted peer-learning sessions and sharing resource packs."
            )
        else:
            reco = (
                f"Low adoption of <b>{question_sel}</b> (n={total_resp}). "
                "Recommend targeted outreach, brief case studies showcasing benefits, and quick-start guidance to encourage uptake."
            )

        st.markdown(f"""
        <div style="background-color:{CARD_COLOR};border-left:6px solid #0099ff;
        border-radius:10px;padding:18px 25px;margin-top:25px;font-family:Calibri;color:{TEXT_COLOR};">
            <h3 style="color:#0099ff;">📋 Collaboration Summary</h3>
            <p><b>{total_resp}</b> respondents reported <b>{question_sel}</b> across the network.
            The country with the highest mentions is <b>{top_country}</b> ({top_count}).</p>
            <h3 style="color:#0099ff;">💡 Recommendation</h3>
            <p>{reco}</p>
        </div>
        """, unsafe_allow_html=True)

# ===========================================================
# 🧭 Footer
# ===========================================================
st.markdown(f"""
<br><div style="background-color:#004E8C;color:white;padding:12px;
border-radius:8px;text-align:center;font-family:Calibri;margin-top:40px;font-size:14px;">
© Don Bosco Tech Africa | Data Analytics & Research Unit
</div>
""", unsafe_allow_html=True)
