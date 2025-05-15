import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib.patches import Wedge
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

# --- Setup ---
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["service_account"]
credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(credentials)

# --- Sheet IDs ---
sheets = {
    "Google Ads": {"id": "1qGfpJ5wTqLAFtDmKaauOXouAwMKWhIBg9bIyWPEbkzc", "goal": 96555},
    "Project":    {"id": "1hvIk4XgXjkHRCDyR8ScRNS82nDRPpsPbdASFZZdAAOE", "goal": 72465},
    "Social":     {"id": "1hSHzko--Pnt2R6iZD_jyi-WMOycVw49snibLi575Z2M", "goal": 90880},
    "SEO":        {"id": "1sQuYdHhrA23zMO7tqyOFQ_m6uHYsfAr4vg3muXl6K_w", "goal": 80000},
}

# --- Hent og saml data ---
all_data = []
total_goal = 0

for name, meta in sheets.items():
    try:
        sheet_name = "Mersalg" if name == "Google Ads" else "Salg"
        ws = client.open_by_key(meta["id"]).worksheet(sheet_name)
        df = get_as_dataframe(ws, evaluate_formulas=True)
        df = df.dropna(how="all")
        df = df[["Produkt", "Pris", "Dato for salg"]].dropna(subset=["Produkt", "Pris"])
        df["Dato for salg"] = pd.to_datetime(df["Dato for salg"], dayfirst=True, errors="coerce")
        df["Uge"] = df["Dato for salg"].dt.isocalendar().week
        df["Pris"] = pd.to_numeric(df["Pris"], errors="coerce")
        all_data.append(df)
        total_goal += meta["goal"]
    except Exception as e:
        st.warning(f"Fejl ved indlæsning af {name}: {e}")

df = pd.concat(all_data)

# --- Beregninger ---
total_sum = df["Pris"].sum()
total_count = len(df)
procent = total_sum / total_goal if total_goal else 0

# --- Ugeopsætning ---
start_uge = 18
slut_uge = 26
alle_uger = list(range(start_uge, slut_uge + 1))

ugevis = df.groupby("Uge")["Pris"].sum().reindex(alle_uger, fill_value=0)
ugevis.index = ugevis.index.map(lambda u: f"Uge {u}")

# --- Restmål-beregning ---
nu_uge = datetime.now().isocalendar().week
resterende_uger = len([u for u in alle_uger if u > nu_uge])
manglende_beloeb = max(total_goal - total_sum, 0)
restmaal = manglende_beloeb / resterende_uger if resterende_uger > 0 else manglende_beloeb

# --- Layout ---
st.set_page_config(page_title="Channels Dashboard", layout="wide")
st.markdown("<h1 style='text-align: center;margin-top:-50px;margin-bottom:-80px'>Channels - Samlet overblik (Q2)</h1>", unsafe_allow_html=True)
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=300_000, key="datarefresh")

col1, col2 = st.columns([2, 1])

# --- Linechart ---
with col1:
    st.subheader(" ")
    inner_cols = st.columns([0.1, 0.8, 0.1])
    with inner_cols[1]:
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor('none')
        ax.set_facecolor('none')
        for spine in ax.spines.values():
            spine.set_visible(False)
        ugevis.plot(ax=ax, marker='o', label='Realisering', color='steelblue')

        ugentlig_maal = total_goal / len(alle_uger)
        ax.axhline(y=ugentlig_maal, color='orange', linestyle='--', label='Mål pr. uge')
        if restmaal > 0:
            ax.axhline(y=restmaal, color='red', linestyle='--', label='Nyt ugemål for at nå Q2')

        uge_labels = list(ugevis.index)
        if f"Uge {nu_uge}" in uge_labels:
            pos = uge_labels.index(f"Uge {nu_uge}")
            ax.axvspan(pos - 0.1, pos + 0.1, color='lightblue', alpha=0.2, label='Nuværende uge')

        ax.set_xlabel("Uge")
        ax.set_ylabel("kr.")
        ax.legend()
        st.pyplot(fig)

# --- Donutgraf ---
with col2:
    st.subheader(" ")
    inner_cols = st.columns([0.2, 0.6, 0.2])
    with inner_cols[1]:
        fig2, ax2 = plt.subplots(figsize=(3, 3))
        ax2.set_xlim(-1.2, 1.2)
        ax2.set_ylim(-1.2, 1.2)
        ax2.axis('off')

        gradient_cmap = LinearSegmentedColormap.from_list("custom_blue", ["#1f77b4", "#66b3ff"])
        gradient_color = gradient_cmap(0.5)

        wedges = [
            Wedge(center=(0, 0), r=1, theta1=90 - procent * 360, theta2=90,
                  facecolor=gradient_color, width=0.3),
            Wedge(center=(0, 0), r=1, theta1=90, theta2=450 - procent * 360,
                  facecolor="#e0e0e0", width=0.3)
        ]
        for w in wedges:
            ax2.add_patch(w)

        ax2.text(0, 0, f"{procent*100:.2f}%", ha='center', va='center', fontsize=20)
        st.pyplot(fig2)

# --- Top produkter + totalboks ---
st.markdown("<br>", unsafe_allow_html=True)
produkt_data = df.groupby("Produkt")["Pris"].agg(["sum", "count"]).sort_values("sum", ascending=False).head(5)
cols = st.columns(6)

for i, (navn, row) in enumerate(produkt_data.iterrows()):
    cols[i].markdown(f"""
    <div style="text-align:center; padding:10px; background:white; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.05);">
      <div style="font-size:18px; font-weight:bold;">{navn}</div>
      <div style="font-size:16px;">{int(row['count'])} solgt</div>
      <div style="font-size:24px; font-weight:normal;">{row['sum']:,.0f} kr.</div>
    </div>
    """, unsafe_allow_html=True)

cols[5].markdown(f"""
<div style="text-align:center; padding:10px; background:white; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.05);">
  <div style="font-size:18px; font-weight:bold;">Antal produkter solgt</div>
  <div style="font-size:24px; font-weight:normal;">{total_count}</div>
  <div style="font-size:16px;">&nbsp;</div>
</div>
""", unsafe_allow_html=True)

# --- Total og progressbar ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align:center; font-size:24px; font-weight:bold; margin-bottom:10px;">
  Samlet: {total_sum:,.0f} kr.
</div>
""", unsafe_allow_html=True)
progress_text = f"{total_sum:,.0f} kr. / {total_goal:,.0f} kr."
st.markdown(f"""
<div style="margin-top: 20px;">
  <div style="font-size:16px; text-align:center; margin-bottom:4px;">
    {progress_text}
  </div>
  <div style="background-color:#e0e0e0; border-radius:10px; height:30px; width:100%;">
    <div style="background: linear-gradient(90deg, #1f77b4, #66b3ff); width:{procent*100}%; height:30px; border-radius:10px;"></div>
  </div>
</div>
""", unsafe_allow_html=True)