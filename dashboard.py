import streamlit as st
st.set_page_config(page_title="Channels Dashboard", layout="wide")

import pandas as pd, matplotlib.pyplot as plt, time
from datetime import datetime
from matplotlib.patches import Wedge
from matplotlib.colors import LinearSegmentedColormap
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account
from streamlit_autorefresh import st_autorefresh

# ---------- Google creds ------------------------------------------------------
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_info(
            st.secrets["service_account"], scopes=scope)
client = gspread.authorize(creds)

# ---------- Ark & Q3-mål ------------------------------------------------------
sheets = {
    "Google Ads": {"id": "1qGfpJ5wTqLAFtDmKaauOXouAwMKWhIBg9bIyWPEbkzc",
                   "goal": 100_000, "sheet": "Salg"},
    "Project":    {"id": "1hvIk4XgXjkHRCDyR8ScRNS82nDRPpsPbdASFZZdAAOE",
                   "goal": 75_000},
    "Social":     {"id": "1hSHzko--Pnt2R6iZD_jyi-WMOycVw49snibLi575Z2M",
                   "goal": 75_000},
    "SEO":        {"id": "1sQuYdHhrA23zMO7tqyOFQ_m6uHYsfAr4vg3muXl6K_w",
                   "goal": 100_000},
    "Web":        {"id": "1plU6MRL7v9lkQ9VeaGJUD4ljuftZve16nPF8N6y36Kg",
                   "goal": 50_000},
    "Strategy":   {"id": "1qGfpJ5wTqLAFtDmKaauOXouAwMKWhIBg9bIyWPEbkzc",
                   "goal": 100_000, "sheet": "Strategy"},
}

START_UGE, SLUT_UGE = 27, 40
ALLE_UGER = list(range(START_UGE, SLUT_UGE+1))

# Q2‑range (til afdelings‑oversigt)
Q2_START, Q2_END = 18, 26

# ---------- Hent og saml data -------------------------------------------------
@st.cache_data(ttl=300)
def hent_data():
    total_goal = 0
    solgte, tilbud = [], []
    stats = []  # liste til afdelings‑opsummering

    for navn, meta in sheets.items():
        try:
            ws = client.open_by_key(meta["id"]).worksheet(meta.get("sheet", "Salg"))
            df = get_as_dataframe(ws, evaluate_formulas=True).dropna(how="all")

            # --- kolonne-navne fallback -------------------------------------
            if "Dato for salg" not in df.columns and "Dato" in df.columns:
                df = df.rename(columns={"Dato": "Dato for salg"})

            # --- standardisering -------------------------------------------
            df["Status"] = (df["Status"].astype(str).str.strip()
                            .str.capitalize().replace({"Aflsag": "Afslag"}))
            df["Dato for salg"] = pd.to_datetime(df["Dato for salg"], dayfirst=True,
                                                 errors="coerce")
            df["Pris"] = pd.to_numeric(df["Pris"], errors="coerce")
            df["Uge"]  = df["Dato for salg"].dt.isocalendar().week

            solgte.append(df[df["Status"] == "Godkendt"])
            tilbud.append(df[df["Status"] == "Tilbud"])
            # --- afdelings‑statistik ---------------------------------------
            stats.append({
                "navn"         : navn,

                "sold_q2_cnt"  : len(df[(df["Status"]=="Godkendt") &
                                         df["Uge"].between(Q2_START, Q2_END)]),
                "sold_q2_sum"  : df[(df["Status"]=="Godkendt") &
                                    df["Uge"].between(Q2_START, Q2_END)]["Pris"].sum(),
                "offer_q2_cnt" : len(df[(df["Status"]=="Tilbud") &
                                         df["Uge"].between(Q2_START, Q2_END)]),
                "offer_q2_sum" : df[(df["Status"]=="Tilbud") &
                                    df["Uge"].between(Q2_START, Q2_END)]["Pris"].sum(),

                "sold_q3_cnt"  : len(df[(df["Status"]=="Godkendt") &
                                         df["Uge"].between(START_UGE, SLUT_UGE)]),
                "sold_q3_sum"  : df[(df["Status"]=="Godkendt") &
                                    df["Uge"].between(START_UGE, SLUT_UGE)]["Pris"].sum(),
                "offer_q3_cnt" : len(df[(df["Status"]=="Tilbud") &
                                         df["Uge"].between(START_UGE, SLUT_UGE)]),
                "offer_q3_sum" : df[(df["Status"]=="Tilbud") &
                                    df["Uge"].between(START_UGE, SLUT_UGE)]["Pris"].sum()
            })
            total_goal += meta["goal"]

            time.sleep(0.8)   # dæmp 429-fejl
        except Exception as e:
            st.warning(f"Fejl ved indlæsning af {navn}: {e}")

    solgte_df = pd.concat(solgte, ignore_index=True)
    tilbud_df = pd.concat(tilbud, ignore_index=True)
    return solgte_df, tilbud_df, total_goal, stats

solgte_df, tilbud_df, TOTAL_GOAL, stats = hent_data()

# ---------- Beregninger -------------------------------------------------------
solgte_q3 = solgte_df[solgte_df["Uge"].between(START_UGE, SLUT_UGE)]
tilbud_q3 = tilbud_df[tilbud_df["Uge"].between(START_UGE, SLUT_UGE)]

solgt_sum = solgte_q3["Pris"].sum()
procent   = solgt_sum / TOTAL_GOAL if TOTAL_GOAL else 0

ugevis = (solgte_q3.groupby("Uge")["Pris"]
          .sum().reindex(ALLE_UGER, fill_value=0))
ugevis.index = ugevis.index.map(lambda u: f"Uge {u}")

nu_uge = datetime.now().isocalendar().week
rest_uger = len([u for u in ALLE_UGER if u > nu_uge])
restmaal  = max(TOTAL_GOAL - solgt_sum, 0) / rest_uger if rest_uger else 0

# ---------- Layout ------------------------------------------------------------
st.markdown("<h1 style='text-align:center;margin-top:-65px'>"
            "Channels – Q3 (uge 27-40)</h1>", unsafe_allow_html=True)
st_autorefresh(interval=300_000, key="datarefresh")

col1, col2 = st.columns([2, 1])

# ---------- Line-graf ---------------------------------------------------------
with col1:
    st.subheader(" ")
    with st.columns([0.05, 0.9, 0.05])[1]:
        fig, ax = plt.subplots(figsize=(10,4))
        for s in ax.spines.values(): s.set_visible(False)
        ugevis.plot(ax=ax, marker="o", label="Realisering", color="steelblue")

        tilbud_ugevis = (tilbud_q3.groupby("Uge")["Pris"]
                         .sum().reindex(ALLE_UGER, fill_value=0))
        ax.plot(tilbud_ugevis.index.map(lambda u: f"Uge {u}"),
                tilbud_ugevis.values, ls="--", color="gray", alpha=.5,
                label="Tilbud sendt")

        ax.axhline(restmaal, color="red", ls="--", label="Ugemål")
        if START_UGE <= nu_uge <= SLUT_UGE:
            try:
                pos = list(ugevis.index).index(f"Uge {nu_uge}")
                ax.axvspan(pos-.1, pos+.1, color="lightblue", alpha=.2,
                           label="Nuværende uge")
            except ValueError:
                pass
        ax.set_xlabel("Uge"); ax.set_ylabel("kr."); ax.legend()
        st.pyplot(fig)

# ---------- Donut + hitrate ---------------------------------------------------
with col2:
    st.subheader(" ")
    with st.columns([0.2,0.6,0.2])[1]:
        fig2, ax2 = plt.subplots(figsize=(3,3))
        ax2.axis("equal"); ax2.axis("off")
        ax2.set_xlim(-1.2,1.2); ax2.set_ylim(-1.2,1.2)
        cmap = LinearSegmentedColormap.from_list("blue",["#1f77b4","#66b3ff"])

        ax2.add_patch(Wedge((0,0),1,90, 90+procent*360, width=.3, facecolor=cmap(.5)))
        ax2.add_patch(Wedge((0,0),1,90+procent*360, 450, width=.3, facecolor="#e0e0e0"))
        ax2.text(0,0,f"{procent*100:.1f}%", ha="center", va="center", fontsize=20)
        st.pyplot(fig2)

        # Hitrate
        g,a,t = len(solgte_q3), \
                len(solgte_df[solgte_df["Status"]=="Afslag"]
                    .query("Uge>=@START_UGE & Uge<=@SLUT_UGE")), \
                len(tilbud_q3)
        total_tilbud = g+a+t
        hit = g/total_tilbud*100 if total_tilbud else 0
        st.markdown(f"""
<div style='text-align:center;font-size:14px;margin-top:-10px;'>
  Hitrate: {hit:.1f}%<br>
  <span style='font-size:12px;'>(Solgt: {g}, Afslag: {a}, Tilbud: {t})</span>
</div>
""", unsafe_allow_html=True)

# ---------- Afdelings‑oversigt ----------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center;'>Salg & Tilbud pr. afdeling</h3>",
            unsafe_allow_html=True)

rows = (len(stats)+2)//3   # vis 3 kolonner per række
idx  = 0
for r in range(rows):
    cols = st.columns(3)
    for c in cols:
        if idx >= len(stats):
            break
        s = stats[idx]
        c.markdown(f"""
<div style='text-align:center;padding:10px;background:white;border-radius:10px;
              box-shadow:0 2px 8px rgba(0,0,0,0.05);'>
  <div style='font-size:18px;font-weight:bold;'>{s['navn']}</div>
  <div style='margin-top:6px;font-size:15px;'>
    <span style='text-decoration:underline;'>Q2</span><br>
    {s['sold_q2_cnt']} solgt – {s['sold_q2_sum']:,.0f} kr.<br>
    {s['offer_q2_cnt']} tilbud – {s['offer_q2_sum']:,.0f} kr.
  </div>
  <div style='margin-top:8px;font-size:15px;'>
    <span style='text-decoration:underline;'>Q3</span><br>
    {s['sold_q3_cnt']} solgt – {s['sold_q3_sum']:,.0f} kr.<br>
    {s['offer_q3_cnt']} tilbud – {s['offer_q3_sum']:,.0f} kr.
  </div>
</div>
""", unsafe_allow_html=True)
        idx += 1

# ---------- Total & progress-bar ---------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style='text-align:center;font-size:24px;font-weight:bold;margin-bottom:10px;'>
  Samlet Q3: {solgt_sum:,.0f} kr.
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style='background:#e0e0e0;border-radius:10px;height:30px;'>
  <div style='background:linear-gradient(90deg,#1f77b4,#66b3ff);
              width:{procent*100:.1f}%;height:30px;border-radius:10px;'></div>
</div>
""", unsafe_allow_html=True)