# app.py
# DBTA GP2 Job Services Officers Unified Survey Dashboard
# - Robust Yes/No, Rating, Collaboration (multi-select), Graduate Analysis
# - PDF export (A4 landscape) added (uses reportlab + kaleido + pillow)
# - AI Mode: "🤖 Activate Stephen AI Mode" (when ON hides charts/summaries and shows Ask Stephen AI)
# ===========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import re
import io
import tempfile
import os
import base64
import requests
import json

st.set_page_config(page_title="DBTA GP2 JSO Dashboard", layout="wide")
today = date.today().strftime("%B %d, %Y")

# ---------------- Theme ----------------
theme_choice = st.sidebar.radio("🌓 Theme", ["🌞 Light Mode", "🌙 Dark Mode"])
if theme_choice == "🌞 Light Mode":
    BG_COLOR = "#f5f7fa"; TEXT_COLOR = "#333"; CARD_COLOR = "#ffffff"; CHART_BG = "white"; ACCENT="#0099ff"
else:
    BG_COLOR = "#1e1e1e"; TEXT_COLOR = "#f2f2f2"; CARD_COLOR = "#2b2b2b"; CHART_BG = "#2b2b2b"; ACCENT="#66b0ff"

# ---------------- Header ----------------
st.markdown(f"""
<div style="background-color:#004E8C;color:white;padding:22px 30px;border-radius:10px;
            box-shadow:0 3px 10px rgba(0,0,0,0.15);font-family:Calibri, Arial, sans-serif;margin-bottom:18px;">
  <div style="display:flex;align-items:center;justify-content:space-between;">
    <div>
      <h1 style="margin:0;font-size:26px;font-weight:600;">DBTA GP2 Job Services Officers Survey Dashboard</h1>
      <p style="margin:6px 0 0 0;font-size:13px;color:#f2f2f2;">Baseline Analysis | Empowering Youth through Quality TVET</p>
    </div>
    <div style="text-align:right;">
      <p style="margin:0;font-size:13px;color:#ddd;">Generated on {today}</p>
      <img src="https://tvet.dbtechafrica.org/pluginfile.php/1/core_admin/logo/0x200/1747917709/LogoRGB%20%283%29.png" width="110" style="border-radius:6px;margin-top:6px;">
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------- Load data ----------------
@st.cache_data
def load_data(path="DBTA_GP2_Survey_JSO.xlsx", sheet="Cleaned Data"):
    return pd.read_excel(path, sheet_name=sheet)

try:
    data = load_data()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

# ---------------- Identify country col ----------------
country_candidates = [c for c in data.columns if "country" in c.lower()]
if not country_candidates:
    st.error("No 'Country' column found. Please check dataset column names.")
    st.stop()
country_col = country_candidates[0]

# ---------------- Detect question types ----------------
exclude_keywords = ["name", "respondent", "email", "phone", "id", "contact"]
cols_for_detection = [c for c in data.columns if not any(k in c.lower() for k in exclude_keywords)]

# Yes/No detection (robust)
yes_no_cols = []
rating_cols = []
for c in cols_for_detection:
    series = data[c].dropna().astype(str).str.strip().str.lower()
    if series.empty:
        continue
    unique = set(series.unique())
    # common yes/no tokens
    yes_tokens = {"yes", "y", "true", "1", "x", "✓", "selected", "checked"}
    no_tokens = {"no", "n", "false", "0"}
    # If mostly yes/no tokens -> yes/no question
    if unique.issubset(yes_tokens.union(no_tokens).union({"", "nan", "none"})):
        yes_no_cols.append(c)
        continue
    # rating detection: numeric 1-5 for a majority of non-null values
    numeric = pd.to_numeric(data[c], errors="coerce").dropna()
    if len(numeric) >= 0.5 * len(data[c].dropna()) and numeric.between(1,5).all():
        rating_cols.append(c)

# Collaboration detection (multi-select options with bracket labels)
collab_cols = [col for col in data.columns if "collaborate" in col.lower() and "[" in col]
collab_labels = [col.split("[")[-1].replace("]", "").strip() for col in collab_cols]
collab_map = dict(zip(collab_labels, collab_cols))

# Graduate year detection and grad keyword map
years_detected = sorted(set(re.findall(r"20\d{2}", " ".join(data.columns))), reverse=True)
if not years_detected:
    years_detected = ["2024","2023","2022","2021"]

GRAD_CATEGORY_KEYWORDS = {
    "Number of graduates placed by the JSO": ["placed by the jso", "placed by jso", "placed by the jso in"],
    "Number of graduates employed": ["graduates employed", "number of graduates employed", "employed in the following years"],
    "Number of graduates self-employed": ["self-employed", "self employed", "were self-employed"]
}

# ---------------- Sidebar controls ----------------
st.sidebar.header("📊 Controls")

# New AI mode toggle (option 1 as requested)
ai_mode = st.sidebar.checkbox("🤖 Activate Stephen AI Mode", value=False)

q_type = st.sidebar.radio("Select Data Type", ["✅ Yes/No", "⭐ Rating (1–5)", "🤝 Collaboration (Multi-Select)", "🎓 Graduate Analysis"])

# country selector disabled for collaboration
if q_type == "🤝 Collaboration (Multi-Select)":
    st.sidebar.markdown("🌍 Country selection disabled for collaboration (network-level counts).")
    country_sel = "All"
else:
    country_list = ["All"] + sorted(data[country_col].dropna().unique().tolist())
    country_sel = st.sidebar.selectbox("🌍 Select Country", country_list)

# question pickers
if q_type == "✅ Yes/No":
    question_list = yes_no_cols or ["(no yes/no questions found)"]
elif q_type == "⭐ Rating (1–5)":
    question_list = rating_cols or ["(no rating questions found)"]
elif q_type == "🤝 Collaboration (Multi-Select)":
    question_list = collab_labels or ["(no collaboration columns found)"]
else:
    question_list = []

question_sel = None
if question_list and q_type != "🎓 Graduate Analysis":
    question_sel = st.sidebar.selectbox("🧩 Select Question", question_list)

# graduate filters
if q_type == "🎓 Graduate Analysis":
    st.sidebar.subheader("🎓 Graduate filters")
    year_sel = st.sidebar.selectbox("Select year", years_detected)
    grad_choice = st.sidebar.selectbox("Select metric", list(GRAD_CATEGORY_KEYWORDS.keys()))
    # Option to show trend across years (line chart)
    show_trend = st.sidebar.checkbox("Show trend across years", value=True)

# ---------------- PDF Export controls ----------------
st.sidebar.markdown("---")
st.sidebar.subheader("📄 Export Report")
include_charts = st.sidebar.checkbox("Include charts in PDF", value=True)
export_pdf_btn = st.sidebar.button("Export report as PDF (A4 landscape)")

# ---------------- utility: summary card ----------------
def summary_card(title, html, accent=ACCENT):
    st.markdown(f"""
    <div style="background-color:{CARD_COLOR};border-left:6px solid {accent};
                border-radius:10px;padding:16px 20px;margin-top:18px;font-family:Calibri;color:{TEXT_COLOR};">
      <h3 style="color:{accent};margin-top:0;">{title}</h3>
      {html}
    </div>""", unsafe_allow_html=True)
    # Also record the summary for export
    try:
        summaries_for_export.append({"title": title, "html": html, "q_type": q_type, "question_sel": question_sel if question_sel else "", "grad_choice": grad_choice if q_type=="🎓 Graduate Analysis" else "", "year_sel": year_sel if q_type=="🎓 Graduate Analysis" else ""})
    except NameError:
        # ensure list exists even if called early
        pass

# lists to collect charts + summaries to include in PDF
charts_for_export = []   # each entry: {"fig": fig, "caption": "..." }
summaries_for_export = []  # list of dicts

# ---------------- If AI Mode is ON: show AI UI and skip chart rendering ----------------
if ai_mode:
    # Hide PDF/export controls when in AI mode by not rendering the export result block below (sidebar still shows controls but we'll avoid using them)
    st.sidebar.markdown("---")
    st.sidebar.header("🤖 Ask Stephen AI")
    api_key = "AIzaSyDTvEwKmRwEcrXiJV-pN91S1CVd4QjlcDw"  # user-provided
    models = [
        "models/gemini-2.5-pro",
        "models/gemini-2.5-flash",
        "models/gemini-pro-latest",
        "models/gemini-2.5-flash-lite",
        "models/gemma-3-12b-it"
    ]
    selected_model = st.sidebar.selectbox("Select Gemini Model", models)
    prompt_input = st.sidebar.text_area("Enter your analytical question or insight request:", height=160)
    use_dataset = st.sidebar.checkbox("🔗 Include current dataset context", value=True)
    analyze_btn = st.sidebar.button("💬 Analyze with Stephen AI")

    def ask_gemini(prompt_text, df=None):
        """Send a prompt (and optional dataframe context) to Gemini API and return insight."""
        base_prompt = (
            "You are Stephen AI, a professional data analyst assistant. "
            "Provide clear, actionable insights based on the user's request. "
            "If a dataset is provided, summarize patterns, correlations, or key findings in bullet points. "
            "Always be concise and label the insights as 'Findings' and 'Recommendations' when suitable."
            "Create a donloadable link pdf file for user to download"
            "File: data/DBTA_GP2_Survey_JSO.xlsx"
        )
        if df is not None:
            # attach small sample for context (first N rows)
            sample_csv = df.head(10).to_csv(index=False)
            base_prompt += "\n\nHere is a preview of the dataset (first 10 rows):\n" + sample_csv

        payload = {"contents": [{"parts": [{"text": base_prompt + "\n\nUser question:\n" + prompt_text}]}]}
        url = f"https://generativelanguage.googleapis.com/v1beta/{selected_model}:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        except Exception as e:
            return f"Error connecting to AI: {e}"
        if response.status_code == 200:
            result = response.json()
            # try multiple keys to be robust
            try:
                return result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            except Exception:
                return json.dumps(result)
        else:
            return f"API error: {response.status_code} - {response.text}"

    # Main AI panel
    st.markdown(f"""
    <div style="background-color:{CARD_COLOR};border-radius:10px;padding:18px;margin-top:6px;font-family:Calibri;color:{TEXT_COLOR};
                box-shadow:0 2px 6px rgba(0,0,0,0.06);">
      <h2 style="color:{ACCENT};margin-top:4px;">🤖 Stephen AI Mode Enabled</h2>
      <p style="margin:6px 0 0 0;">Manual charts, summaries and PDF export are temporarily hidden while AI Mode is active.  Enter a question in the sidebar to get data-aware insights from Stephen AI.</p>
    </div>
    """, unsafe_allow_html=True)

    if analyze_btn:
        if not prompt_input.strip():
            st.warning("Please enter a question or request.")
        else:
            with st.spinner("Stephen AI is thinking..."):
                insight = ask_gemini(prompt_input, data if use_dataset else None)
                st.markdown(f"""
                <div style="background-color:{CARD_COLOR};border-radius:10px;padding:20px;margin-top:15px;
                            font-family:Calibri;color:{TEXT_COLOR};box-shadow:0 2px 6px rgba(0,0,0,0.1);">
                    <h3 style="color:{ACCENT};margin-top:0;">💡 Stephen AI Insight</h3>
                    <pre style="white-space:pre-wrap;font-family:Calibri;">{insight}</pre>
                </div>
                """, unsafe_allow_html=True)

    # footer still present
    st.markdown(f"""
    <br><div style="background-color:#004E8C;color:white;padding:12px;border-radius:8px;
    text-align:center;font-family:Calibri;margin-top:28px;font-size:13px;">
    © Don Bosco Tech Africa | Data Analytics & Research Unit
    </div>
    """, unsafe_allow_html=True)

else:
    # ---------------- If AI Mode is OFF: render entire dashboard as before ----------------

    # ---------------- Yes/No logic ----------------
    if q_type == "✅ Yes/No":
        if not yes_no_cols:
            st.warning("No yes/no questions detected.")
        elif question_sel not in yes_no_cols:
            st.warning("Pick a valid Yes/No question.")
        else:
            df = data.copy() if country_sel == "All" else data.loc[data[country_col]==country_sel].copy()
            s = df[question_sel].astype(str).str.strip().str.lower()
            yes_mask = s.isin(["yes","y","true","1","x","✓","selected","checked"])
            no_mask = s.isin(["no","n","false","0"])
            other_mask = s.notna() & ~(yes_mask | no_mask)

            yes_count = int(yes_mask.sum())
            no_count = int(no_mask.sum())
            other_count = int(other_mask.sum())
            total = int(s.notna().sum())

            yes_pct = round(yes_count/total*100,1) if total>0 else 0.0
            no_pct  = round(no_count/total*100,1) if total>0 else 0.0
            other_pct = round(other_count/total*100,1) if total>0 else 0.0

            # KPIs
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("🌍 Country", country_sel if country_sel!="All" else "All")
            c2.metric("👥 Responses", total)
            c3.metric("✅ Yes (%)", f"{yes_pct:.1f}%")
            c4.metric("❌ No (%)", f"{no_pct:.1f}%")

            plot_df = pd.DataFrame({
                "Response":["Yes","No","Other"],
                "Count":[yes_count,no_count,other_count],
                "Pct":[yes_pct,no_pct,other_pct]
            }).query("Count>0")

            fig = px.bar(plot_df, x="Response", y="Count", text="Pct", color="Response",
                         color_discrete_map={"Yes":"#0099ff","No":"#E66225","Other":"#6c757d"},
                         title=f"{question_sel} — {country_sel}")
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_color="white")
            fig.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR, title_x=0.5)
            st.plotly_chart(fig, use_container_width=True)
            # store chart and caption
            charts_for_export.append({"fig": fig, "caption": f"{question_sel} — {country_sel}"})

            # Professional summary + recommendation
            if yes_pct >= 80:
                rec = ("The large majority indicate affirmative — this suggests strong adoption or awareness. "
                       "Document current practices, share them across the network and monitor continuity.")
            elif yes_pct >= 50:
                rec = ("A mixed picture: there is uptake but it is not universal. Recommend targeted follow-up "
                       "training, monthly check-ins, and distribution of quick reference materials.")
            else:
                rec = ("Low adoption/awareness. Execute root-cause diagnostics (focus groups, calls), then design "
                       "targeted capacity-building sessions and easy-to-use job aids.")

            body = (f"<p><b>{total}</b> responses examined. <b>{yes_count}</b> answered <b>Yes</b> ({yes_pct:.1f}%), "
                    f"<b>{no_count}</b> answered <b>No</b> ({no_pct:.1f}%).</p>"
                    f"<h4>💡 Recommendation</h4><p>{rec}</p>")
            summary_card("📋 Summary & Recommendation", body)

    # ---------------- Rating logic ----------------
    elif q_type == "⭐ Rating (1–5)":
        if not rating_cols:
            st.warning("No rating (1–5) questions detected.")
        elif question_sel not in rating_cols:
            st.warning("Pick a valid rating question.")
        else:
            df = data.copy() if country_sel == "All" else data.loc[data[country_col]==country_sel].copy()
            df.loc[:, question_sel] = pd.to_numeric(df[question_sel], errors="coerce")
            df_valid = df.dropna(subset=[question_sel]).copy()
            total = len(df_valid)
            if total == 0:
                st.info("No numeric ratings available for this question/country.")
            else:
                avg = round(float(df_valid[question_sel].mean()),2)
                median = round(float(df_valid[question_sel].median()),2)
                pct_4_5 = round((df_valid[question_sel] >= 4).sum()/total*100,1)

                c1,c2,c3,c4 = st.columns(4)
                c1.metric("🌍 Country", country_sel if country_sel!="All" else "All")
                c2.metric("👥 Valid responses", total)
                c3.metric("⭐ Average", avg)
                c4.metric("🌟 4–5 (%)", f"{pct_4_5:.1f}%")

                counts = df_valid[question_sel].astype(int).value_counts().sort_index()
                donut = px.pie(names=counts.index.astype(str), values=counts.values, hole=0.45,
                               title=f"{question_sel} — {country_sel}",
                               color_discrete_sequence=px.colors.sequential.Blues_r if theme_choice=="🌙 Dark Mode" else px.colors.sequential.Blues)
                donut.update_traces(textinfo="percent+label")
                donut.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR, title_x=0.5)
                st.plotly_chart(donut, use_container_width=True)
                charts_for_export.append({"fig": donut, "caption": f"{question_sel} — {country_sel}"})

                # nuanced professional summary + recommendation
                if avg >= 4:
                    rec = ("Strong satisfaction indicator. Capture local case studies, sustain current approaches, "
                           "and set up periodic peer-sharing sessions.")
                elif avg >= 3:
                    rec = ("Moderate satisfaction. Use targeted qualitative follow-up (open-ended, interviews) to "
                           "identify the most actionable improvements.")
                else:
                    rec = ("Low satisfaction. Convene a focused working group, review curriculum/delivery, "
                           "and prioritize the top 3 interventions for immediate rollout.")

                body = (f"<p><b>{total}</b> valid ratings. Average: <b>{avg}</b>; median: <b>{median}</b>. "
                        f"<b>{pct_4_5:.1f}%</b> rated 4 or 5.</p>"
                        f"<h4>💡 Recommendation</h4><p>{rec}</p>")
                summary_card("📋 Summary & Recommendation", body)

    # ---------------- Collaboration logic ----------------
    elif q_type == "🤝 Collaboration (Multi-Select)":
        if not collab_labels:
            st.warning("No collaboration multi-select columns detected (columns normally include option in brackets).")
        elif question_sel not in collab_labels:
            st.warning("Choose a collaboration option.")
        else:
            st.info("Collaboration analysis is shown network-wide (country filter disabled).")
            col = collab_map.get(question_sel)
            if col is None:
                st.warning("Mapping error for collaboration option.")
            else:
                df = data.copy()
                df.loc[:, col] = df[col].astype(str).str.strip().str.lower()
                positives = {"yes","y","true","1","x","selected","checked","✓","√", question_sel.lower()}
                df_filtered = df[df[col].isin(positives)].copy()
                # fallback: contains match (free text)
                if df_filtered.empty:
                    mask = df[col].astype(str).str.lower().str.contains(question_sel.lower(), na=False)
                    df_filtered = df[mask].copy()

                if df_filtered.empty:
                    st.warning(f"No respondents selected '{question_sel}'.")
                else:
                    grouped = df_filtered.groupby(country_col).size().reset_index(name="Count").sort_values("Count", ascending=False)
                    fig = px.bar(grouped, x=country_col, y="Count", text="Count", color=country_col, color_discrete_sequence=px.colors.qualitative.Vivid,
                                 title=f"Respondents selecting “{question_sel}” — All countries")
                    fig.update_traces(textposition="outside", marker_line_color="white")
                    fig.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR, title_x=0.5)
                    st.plotly_chart(fig, use_container_width=True)
                    charts_for_export.append({"fig": fig, "caption": f"Respondents selecting “{question_sel}” — All countries"})

                    total_resp = int(grouped["Count"].sum())
                    top_country = grouped.iloc[0][country_col]
                    top_count = int(grouped.iloc[0]["Count"])

                    if total_resp >= 30:
                        rec = (f"High adoption (n={total_resp}). Capture how {top_country} operationalises '{question_sel}' and create "
                               "a short practical guide for replication.")
                    elif total_resp >= 10:
                        rec = (f"Moderate adoption (n={total_resp}). Boost peer learning and provide implementation templates.")
                    else:
                        rec = (f"Low adoption (n={total_resp}). Run focused awareness and short practical workshops.")

                    body = (f"<p><b>{total_resp}</b> respondents reported <b>{question_sel}</b>. "
                            f"Top country: <b>{top_country}</b> ({top_count}).</p>"
                            f"<h4>💡 Recommendation</h4><p>{rec}</p>")
                    summary_card("📋 Collaboration Summary", body)

    # ---------------- Graduate Analysis ----------------
    elif q_type == "🎓 Graduate Analysis":
        # find male/female column names for chosen metric and years
        keywords = GRAD_CATEGORY_KEYWORDS[grad_choice]
        cols_lower = {c: c.lower() for c in data.columns}

        # find candidate columns that include year_sel & gender token & any keyword
        male_col = female_col = None
        for c, lower in cols_lower.items():
            if year_sel in lower and "male" in lower and any(k in lower for k in keywords):
                male_col = c if male_col is None else male_col
            if year_sel in lower and "female" in lower and any(k in lower for k in keywords):
                female_col = c if female_col is None else female_col

        # fallback: try partial matches (year present and 'male'/'female' token)
        if not male_col or not female_col:
            for c, lower in cols_lower.items():
                if year_sel in lower and "male" in lower and male_col is None:
                    male_col = c
                if year_sel in lower and "female" in lower and female_col is None:
                    female_col = c

        if not male_col or not female_col:
            st.warning(f"Could not find male/female columns for '{grad_choice}' in {year_sel}. Check column names.")
        else:
            # filter by country if applicable
            df = data.copy() if country_sel == "All" else data.loc[data[country_col]==country_sel].copy()
            # coerce to numeric and avoid SettingWithCopy by assigning with .loc
            df.loc[:, male_col] = pd.to_numeric(df[male_col], errors="coerce").fillna(0).astype(int)
            df.loc[:, female_col] = pd.to_numeric(df[female_col], errors="coerce").fillna(0).astype(int)

            grouped = df.groupby(country_col)[[male_col, female_col]].sum().reset_index()
            grouped["Total"] = grouped[male_col] + grouped[female_col]

            total_male = int(grouped[male_col].sum())
            total_female = int(grouped[female_col].sum())
            total_all = total_male + total_female
            male_pct = round(total_male/total_all*100,1) if total_all else 0.0
            female_pct = round(total_female/total_all*100,1) if total_all else 0.0

            # KPIs
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("🌍 Country", country_sel if country_sel!="All" else "All")
            c2.metric("👥 Total graduates", f"{total_all:,}")
            c3.metric("👨 Male (%)", f"{male_pct:.1f}%")
            c4.metric("👩 Female (%)", f"{female_pct:.1f}%")

            # PIE chart for gender split (network or selected country)
            pie_df = pd.DataFrame({"Gender":["Male","Female"], "Count":[total_male, total_female]}).query("Count>0")
            if not pie_df.empty:
                pie = px.pie(pie_df, names="Gender", values="Count", hole=0.4,
                             color_discrete_map={"Male":"#1f77b4","Female":"#ff7f0e"},
                             title=f"{grad_choice} ({year_sel}) — Gender split")
                pie.update_traces(textinfo="percent+label")
                pie.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR, title_x=0.5)
                st.plotly_chart(pie, use_container_width=True)
                charts_for_export.append({"fig": pie, "caption": f"{grad_choice} ({year_sel}) — Gender split"})

            # Trend line across years (aggregate by year) - only if show_trend checked
            # We'll attempt to locate columns for the same grad_choice across multiple years
            if show_trend:
                # build list of years present (use detected years)
                trend_years = years_detected.copy()
                trend_rows = []
                for y in trend_years:
                    # locate male/female columns for year y and current grad_choice
                    m_col = f_col = None
                    for c, lower in cols_lower.items():
                        if y in lower and "male" in lower and any(k in lower for k in GRAD_CATEGORY_KEYWORDS[grad_choice]):
                            m_col = c
                        if y in lower and "female" in lower and any(k in lower for k in GRAD_CATEGORY_KEYWORDS[grad_choice]):
                            f_col = c
                    # fallback by broader search
                    if m_col is None or f_col is None:
                        for c, lower in cols_lower.items():
                            if y in lower and "male" in lower and m_col is None:
                                m_col = c
                            if y in lower and "female" in lower and f_col is None:
                                f_col = c
                    if m_col and f_col:
                        m_sum = pd.to_numeric(data[m_col], errors="coerce").fillna(0).sum()
                        f_sum = pd.to_numeric(data[f_col], errors="coerce").fillna(0).sum()
                        trend_rows.append({"Year": y, "Male": int(m_sum), "Female": int(f_sum), "Total": int(m_sum + f_sum)})
                if trend_rows:
                    trend_df = pd.DataFrame(trend_rows).sort_values("Year")
                    # line for totals
                    line = px.line(trend_df, x="Year", y="Total", markers=True, title=f"Trend — {grad_choice} (Total) across years")
                    line.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR, title_x=0.5)
                    st.plotly_chart(line, use_container_width=True)
                    charts_for_export.append({"fig": line, "caption": f"Trend — {grad_choice} (Total) across years"})

            # # bar by country stacked/grouped if many countries
            # df_plot = grouped.melt(id_vars=[country_col], value_vars=[male_col, female_col], var_name="GenderCol", value_name="Count")
            # if not df_plot.empty:
            #     df_plot["Gender"] = df_plot["GenderCol"].apply(lambda x: "Male" if "male" in x.lower() else "Female")
            #     bar = px.bar(df_plot, x=country_col, y="Count", color="Gender", barmode="group",
            #                  text="Count", color_discrete_map={"Male":"#1f77b4","Female":"#ff7f0e"},
            #                  title=f"{grad_choice} ({year_sel}) — by gender and country")
            #     bar.update_traces(textposition="outside")
            #     bar.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG, font_color=TEXT_COLOR, title_x=0.5, yaxis_title="Number")
            #     st.plotly_chart(bar, use_container_width=True)
            #     charts_for_export.append({"fig": bar, "caption": f"{grad_choice} ({year_sel}) — by gender and country"})

            # Summary (no recommendation for graduates per your request)
            if not grouped.empty:
                top = grouped.sort_values("Total", ascending=False).iloc[0]
                top_country = top[country_col]
                top_total = int(top["Total"])
                body = (f"<p>For <b>{grad_choice}</b> in <b>{year_sel}</b>, total <b>{total_all:,}</b> graduates "
                        f"(<b>{total_male:,}</b> male; <b>{total_female:,}</b> female). Top country: <b>{top_country}</b> ({top_total:,}).</p>")
                summary_card("📋 Graduate Summary", body)

    # ---------------- PDF Export function ----------------
    def build_pdf_a4_landscape(summaries, charts, include_charts=True):
        """
        Build a PDF in A4 landscape using reportlab, return bytes.
        Expects:
          - summaries: list of dicts {title, html, q_type, question_sel, grad_choice, year_sel}
          - charts: list of dicts {"fig": plotly_fig, "caption": "..."}
        """
        try:
            from reportlab.lib.pagesizes import landscape, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import cm
        except Exception as e:
            st.error("PDF export requires 'reportlab'. Install with: pip install reportlab")
            return None

        # Need kaleido to render plotly figs to PNG
        try:
            import kaleido  # used by plotly fig.write_image / to_image
        except Exception:
            st.error("Saving charts to PDF requires 'kaleido'. Install with: pip install kaleido")
            return None

        try:
            from PIL import Image as PILImage
        except Exception:
            st.error("Saving charts requires 'Pillow'. Install with: pip install pillow")
            return None

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)

        styles = getSampleStyleSheet()
        if 'CustomTitle' not in styles:
            styles.add(ParagraphStyle(name='CustomTitle', fontName='Helvetica-Bold', fontSize=18, leading=22, spaceAfter=12, textColor=colors.HexColor('#004E8C')))
        if 'H1' not in styles:
            styles.add(ParagraphStyle(name='H1', fontName='Helvetica-Bold', fontSize=14, leading=18, spaceAfter=8))
        if 'Body' not in styles:
            styles.add(ParagraphStyle(name='Body', fontName='Helvetica', fontSize=11, leading=14))
        if 'Caption' not in styles:
            styles.add(ParagraphStyle(name='Caption', fontName='Helvetica-Oblique', fontSize=9, leading=11, textColor=colors.grey))

        story = []
        story.append(Paragraph("DBTA GP2 Job Services Officers Survey Dashboard", styles['CustomTitle']))
        story.append(Paragraph(f"Generated on {today}", styles['Body']))
        story.append(Spacer(1, 12))

        for s in summaries:
            story.append(Paragraph(s.get("title", "Summary"), styles['H1']))
            meta_parts = []
            if s.get("q_type"): meta_parts.append(f"Question Type: {s.get('q_type')}")
            if s.get("question_sel"): meta_parts.append(f"Question: {s.get('question_sel')}")
            if s.get("grad_choice"): meta_parts.append(f"Metric: {s.get('grad_choice')}")
            if s.get("year_sel"): meta_parts.append(f"Year: {s.get('year_sel')}")
            if meta_parts:
                story.append(Paragraph(" | ".join(meta_parts), styles['Caption']))
                story.append(Spacer(1,6))
            body_html = s.get("html", "")
            body_plain = body_html.replace("<h4>", "<b>").replace("</h4>", "</b><br/>")
            body_plain = body_plain.replace("<p>", "").replace("</p>", "<br/>")
            for piece in [p.strip() for p in body_plain.split("<br/>") if p.strip()]:
                story.append(Paragraph(piece, styles['Body']))
            story.append(Spacer(1,12))

        temp_files_to_cleanup = []
        try:
            if include_charts and charts:
                story.append(PageBreak())
                story.append(Paragraph("Charts", styles['H1']))
                story.append(Spacer(1,8))

                for ch in charts:
                    fig = ch.get("fig")
                    caption = ch.get("caption", "")
                    img_bytes = None
                    try:
                        # preferred method
                        img_bytes = fig.to_image(format="png", scale=2)
                    except Exception:
                        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                        tmp.close()
                        try:
                            fig.write_image(tmp.name, format="png", scale=2)
                            with open(tmp.name, "rb") as f:
                                img_bytes = f.read()
                        finally:
                            try: os.unlink(tmp.name)
                            except: pass

                    if not img_bytes:
                        continue

                    tmpf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                    tmpf.write(img_bytes)
                    tmpf.flush()
                    tmpf.close()
                    temp_files_to_cleanup.append(tmpf.name)

                    page_width_pt, page_height_pt = landscape(A4)
                    usable_w = page_width_pt - doc.leftMargin - doc.rightMargin
                    usable_h = page_height_pt - doc.topMargin - doc.bottomMargin - 10

                    pil_im = PILImage.open(tmpf.name)
                    img_w_px, img_h_px = pil_im.size
                    aspect = img_h_px / img_w_px if img_w_px else 1.0

                    display_w = usable_w * 0.95  # small global shrink
                    display_h = display_w * aspect
                    if display_h > usable_h * 0.95:
                        # shrink again if needed
                        scale = (usable_h * 0.95) / display_h
                        display_w *= scale
                        display_h *= scale

                    im = Image(tmpf.name, width=display_w, height=display_h)
                    story.append(im)
                    if caption:
                        story.append(Paragraph(caption, styles['Caption']))
                    story.append(Spacer(1, 12))

            doc.build(story)
        finally:
            for f in temp_files_to_cleanup:
                try: os.remove(f)
                except: pass

        buffer.seek(0)
        return buffer.getvalue()

    # ---------------- Trigger export if requested ----------------
    if export_pdf_btn:
        # safe-guard: must have at least one summary
        if not summaries_for_export:
            st.warning("Nothing to export yet — generate some charts and summaries first (view a question/metric).")
        else:
            with st.spinner("Preparing PDF..."):
                pdf_bytes = build_pdf_a4_landscape(summaries_for_export, charts_for_export if include_charts else [], include_charts=include_charts)
                if pdf_bytes:
                    b64 = base64.b64encode(pdf_bytes).decode()
                    st.success("PDF ready — click the button below to download.")
                    st.download_button(label="Download report (A4 landscape PDF)", data=pdf_bytes, file_name="DBTA_GP2_Report_landscape.pdf", mime="application/pdf")
                else:
                    st.error("PDF generation failed. Ensure 'reportlab', 'kaleido' and 'pillow' are installed in the environment. Run:\n\npip install reportlab kaleido pillow")

    # ---------------- Footer ----------------
    st.markdown(f"""
    <br><div style="background-color:#004E8C;color:white;padding:12px;border-radius:8px;
    text-align:center;font-family:Calibri;margin-top:28px;font-size:13px;">
    © Don Bosco Tech Africa | Data Analytics & Research Unit
    </div>
    """, unsafe_allow_html=True)
