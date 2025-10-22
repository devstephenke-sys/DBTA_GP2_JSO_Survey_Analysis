# ===========================================================
# 📊 DBTA GP2 Job Services Officers Unified Survey Dashboard
# ===========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

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
    PLOT_COLOR = "white"
else:
    BG_COLOR = "#1e1e1e"
    TEXT_COLOR = "#f2f2f2"
    CARD_COLOR = "#2b2b2b"
    CHART_BG = "#2b2b2b"
    PLOT_COLOR = "#1e1e1e"

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
country_col = "Country"

# ===========================================================
# 🧠 Detect Question Types
# ===========================================================
exclude_keywords = ["name", "respondent", "email", "phone", "id", "contact"]
filtered_cols = [c for c in data.columns if not any(k in c.lower() for k in exclude_keywords)]

yes_no_cols = []
rating_cols = []

for col in filtered_cols:
    unique_vals = data[col].dropna().astype(str).str.lower().unique()
    if set(unique_vals).issubset({'yes', 'no'}):
        yes_no_cols.append(col)
    else:
        series = pd.to_numeric(data[col], errors='coerce').dropna()
        if len(series) > 0 and series.between(1, 5).all():
            rating_cols.append(col)

# ===========================================================
# 🎛️ Sidebar Filters
# ===========================================================
st.sidebar.header("📊 Dashboard Controls")

q_type = st.sidebar.radio("Select Question Type", ["✅ Yes/No", "⭐ Rating (1–5)"])
country_list = ["All"] + sorted(data[country_col].dropna().unique().tolist())
country_sel = st.sidebar.selectbox("🌍 Select Country", country_list)

if q_type == "✅ Yes/No":
    question_list = yes_no_cols
else:
    question_list = rating_cols

question_sel = st.sidebar.selectbox("🧩 Select Question", question_list)

# ===========================================================
# ✅ YES/NO Analysis
# ===========================================================
if q_type == "✅ Yes/No":
    df = data.copy() if country_sel == "All" else data[data[country_col] == country_sel]
    total = df[question_sel].count()
    yes_count = (df[question_sel].astype(str).str.lower() == "yes").sum()
    no_count = (df[question_sel].astype(str).str.lower() == "no").sum()

    yes_pct = round((yes_count / total) * 100, 1) if total > 0 else 0
    no_pct = 100 - yes_pct

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌍 Country", country_sel if country_sel != "All" else "All")
    c2.metric("👥 Total Responses", total)
    c3.metric("✅ Yes (%)", f"{yes_pct}%")
    c4.metric("❌ No (%)", f"{no_pct}%")

    fig = px.bar(
        x=["Yes", "No"], y=[yes_count, no_count],
        text=[f"{yes_pct}%", f"{no_pct}%"],
        color=["Yes", "No"],
        color_discrete_map={'Yes': '#0099ff', 'No': '#E66225'},
        title=f"{question_sel}<br><span style='font-size:14px; color:#ccc;'>({country_sel})</span>"
    )
    fig.update_traces(textposition="outside", width=0.4)
    fig.update_layout(
        plot_bgcolor=CHART_BG,
        paper_bgcolor=CHART_BG,
        font_color=TEXT_COLOR,
        title_x=0.5
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary & Recommendation
    if yes_pct >= 80:
        rec = "Strong alignment with DBTA’s objectives. This area shows excellence and can be a model for replication."
    elif 50 <= yes_pct < 80:
        rec = "Moderate engagement. Reinforcing capacity-building, mentoring, and improved access to tools may enhance outcomes."
    else:
        rec = "Low engagement detected. Targeted sensitization and support are needed to raise awareness and participation."

    st.markdown(f"""
    <div style="
        background-color:{CARD_COLOR};
        border-left:6px solid #0099ff;
        border-radius:10px;
        padding:18px 25px;
        margin-top:25px;
        box-shadow:1px 2px 6px rgba(0,0,0,0.1);
        font-family:Calibri, Arial, sans-serif;
        color:{TEXT_COLOR};
    ">
        <h3 style="color:#0099ff;">📋 Summary</h3>
        <p>The question <b>“{question_sel}”</b> received <b>{total}</b> responses from 
        <b>{country_sel if country_sel != 'All' else 'all countries'}</b>. 
        <b>{yes_pct}%</b> answered <span style="color:#00A859;">Yes</span> and <b>{no_pct}%</b> answered 
        <span style="color:#E66225;">No</span>.</p>
        <h3 style="color:#0099ff;">💡 Recommendation</h3>
        <p>{rec}</p>
    </div>
    """, unsafe_allow_html=True)

# ===========================================================
# ⭐ RATING Analysis
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
    c4.metric("🌟 Rated 4–5 (%)", f"{high_pct}%")

    fig = px.pie(
        df, names=question_sel, hole=0.4,
        title=f"{question_sel}<br><span style='font-size:14px; color:#ccc;'>({country_sel})</span>",
        color_discrete_sequence=px.colors.sequential.Blues_r if theme_choice == "🌙 Dark Mode" else px.colors.sequential.Blues
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(
        plot_bgcolor=CHART_BG,
        paper_bgcolor=CHART_BG,
        font_color=TEXT_COLOR,
        title_x=0.5
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary & Recommendation
    if avg_rating >= 4:
        rec = "High satisfaction levels reflect strong operational standards. Sustain mentorship and peer learning to maintain excellence."
    elif 3 <= avg_rating < 4:
        rec = "Moderate satisfaction suggests room for growth. Encourage feedback and align training materials with field realities."
    else:
        rec = "Low satisfaction indicates improvement areas in content delivery, accessibility, or training relevance."

    st.markdown(f"""
    <div style="
        background-color:{CARD_COLOR};
        border-left:6px solid #0099ff;
        border-radius:10px;
        padding:18px 25px;
        margin-top:25px;
        box-shadow:1px 2px 6px rgba(0,0,0,0.1);
        font-family:Calibri, Arial, sans-serif;
        color:{TEXT_COLOR};
    ">
        <h3 style="color:#0099ff;">📋 Summary</h3>
        <p>The question <b>“{question_sel}”</b> received <b>{total}</b> responses with an average rating of 
        <b>{avg_rating}</b>. <b>{high_pct}%</b> rated 4 or 5.</p>
        <h3 style="color:#0099ff;">💡 Recommendation</h3>
        <p>{rec}</p>
    </div>
    """, unsafe_allow_html=True)

# ===========================================================
# 🧭 Footer
# ===========================================================
st.markdown(f"""
<br>
<div style="
    background-color:#004E8C;
    color:white;
    padding:12px;
    border-radius:8px;
    text-align:center;
    font-family:Calibri, Arial, sans-serif;
    margin-top:40px;
    font-size:14px;
">
    © Don Bosco Tech Africa | Data Analytics & Research Unit
</div>
""", unsafe_allow_html=True)
