# ===========================================================
# 📊 DBTA GP2 Job Services Officers Unified Survey Dashboard
# (Smart Collaboration Analysis — Country Slicer Hidden)
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
    padding:22px 30px;
    border-radius:10px;
    box-shadow:0 3px 10px rgba(0,0,0,0.15);
    font-family:Calibri, Arial, sans-serif;
    margin-bottom:25px;
">
    <div style="display:flex; align-items:center; justify-content:space-between;">
        <div style="flex:1;">
            <h1 style="margin:0; font-size:28px; font-weight:600;">DBTA GP2 Job Services Officers Survey Dashboard</h1>
            <p style="margin:5px 0 0 0; font-size:15px; color:#f2f2f2;">
                Baseline Analysis | <span style="font-style:italic;">Empowering Youth through Quality TVET</span>
            </p>
        </div>
        <div style="text-align:right; flex-shrink:0;">
            <p style="margin:0; font-size:14px; color:#ddd;">Generated on {today}</p>
            <div style="margin-top:5px;">
                <img src="DonBoscoTechAfricaLogo.png" alt="DBTA Logo" width="120" style="border-radius:5px;">
            </div>
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
# 🧠 Detect Question Types
# ===========================================================
exclude_keywords = ["name", "respondent", "email", "phone", "id", "contact"]
filtered_cols = [c for c in data.columns if not any(k in c.lower() for k in exclude_keywords)]

# Detect Yes/No and Rating questions
yes_no_cols, rating_cols = [], []
for col in filtered_cols:
    vals = data[col].dropna().astype(str).str.lower().unique()
    if set(vals).issubset({'yes', 'no'}):
        yes_no_cols.append(col)
    else:
        series = pd.to_numeric(data[col], errors='coerce').dropna()
        if len(series) > 0 and series.between(1, 5).all():
            rating_cols.append(col)

# Detect Collaboration-type columns
collab_cols = [col for col in data.columns if "collaborate" in col.lower() and "[" in col]
collab_labels = [col.split("[")[-1].replace("]", "").strip() for col in collab_cols]
collab_map = dict(zip(collab_labels, collab_cols))

# ===========================================================
# 🎛️ Sidebar Filters
# ===========================================================
st.sidebar.header("📊 Dashboard Controls")

q_type = st.sidebar.radio(
    "Select Data Type to Explore:",
    ["✅ Yes/No", "⭐ Rating (1–5)", "🤝 Collaboration (Multi-Select)"]
)

if q_type == "🤝 Collaboration (Multi-Select)":
    st.sidebar.markdown("🌍 **Country selection disabled for collaboration analysis.**")
    country_sel = "All"
else:
    country_list = ["All"] + sorted(data[country_col].dropna().unique().tolist())
    country_sel = st.sidebar.selectbox("🌍 Select Country", country_list)

if q_type == "✅ Yes/No":
    question_list = yes_no_cols
elif q_type == "⭐ Rating (1–5)":
    question_list = rating_cols
else:
    question_list = collab_labels

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
# ⭐ RATING (1–5) Analysis
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
# 🤝 COLLABORATION (Multi-Select) Analysis
# ===========================================================
elif q_type == "🤝 Collaboration (Multi-Select)":
    col = collab_map[question_sel]
    df = data.copy()
    df[col] = df[col].astype(str).str.strip().str.lower()

    positive_values = ['yes', 'y', 'true', '1', 'x', 'selected', 'checked', '✓', '√', question_sel.lower()]
    df_filtered = df[df[col].isin(positive_values)]

    grouped = df_filtered.groupby(country_col).size().reset_index(name="Count")
    if grouped.empty:
        st.warning(f"No respondents in the dataset selected '{question_sel}'.")
    else:
        fig = px.bar(
            grouped, x=country_col, y="Count", text="Count",
            color=country_col, color_discrete_sequence=CHART_COLOR,
            title=f"Respondents Selecting “{question_sel}”<br><span style='font-size:14px; color:#555;'>(All Countries)</span>"
        )
        fig.update_traces(textposition="outside", marker_line_color="white", marker_line_width=1.3)
        fig.update_layout(title_x=0.5, plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR)
        st.plotly_chart(fig, use_container_width=True)

        total_resp = grouped["Count"].sum()
        top_country = grouped.sort_values("Count", ascending=False).iloc[0][country_col]
        top_count = grouped.sort_values("Count", ascending=False).iloc[0]["Count"]

        if total_resp >= 15:
            reco = f"Strong collaboration across regions. {top_country} leads in <b>{question_sel.lower()}</b>. DBTA should replicate their model regionally."
        elif 5 <= total_resp < 15:
            reco = f"Moderate adoption of <b>{question_sel.lower()}</b>. Promote structured peer exchanges and policy incentives."
        else:
            reco = f"Limited engagement in <b>{question_sel.lower()}</b>. Conduct sensitization sessions and follow-up assessments."

        st.markdown(f"""
        <div style="background-color:{CARD_COLOR};border-left:6px solid #0099ff;
        border-radius:10px;padding:18px 25px;margin-top:25px;
        font-family:Calibri;color:{TEXT_COLOR};">
            <h3 style="color:#0099ff;">📋 Summary</h3>
            <p>The collaboration area <b>“{question_sel}”</b> was reported by <b>{total_resp}</b> respondents across all countries.
            <b>{top_country}</b> leads with <b>{top_count}</b> mentions.</p>
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
