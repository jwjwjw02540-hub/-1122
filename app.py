"""
Streamlit App สำหรับเครื่องมือวิเคราะห์ฟุตบอล (สำเร็จรูป)
รันด้วย: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from football_analyzer import FootballAnalyzer

st.set_page_config(
    page_title="Football Analyzer",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚽ เครื่องมือวิเคราะห์ฟุตบอล")
st.caption("Dixon-Coles · สูงต่ำ · แฮนดิแคป · คาดสกอร์")

# Sidebar
with st.sidebar:
    st.header("⚙️ ตั้งค่า")
    xi = st.slider(
        "Time Decay (xi)",
        min_value=0.0005,
        max_value=0.008,
        value=0.0018,
        step=0.0001,
        help="ค่าสูง = ให้น้ำหนักเกมล่าสุดมากกว่า"
    )

    st.subheader("📂 ข้อมูล")
    uploaded = st.file_uploader(
        "อัปโหลด CSV (football-data.co.uk)",
        type=["csv"],
        help="รองรับคอลัมน์ Date, HomeTeam, AwayTeam, FTHG, FTAG"
    )
    use_sample = st.checkbox("ใช้ข้อมูลจำลอง (ทดสอบ)", value=True)

    if st.button("🚀 โหลด & ฟิตโมเดล", type="primary", use_container_width=True):
        try:
            if uploaded is not None:
                df = pd.read_csv(uploaded)
                col_map = {
                    "HomeTeam": "home_team", "AwayTeam": "away_team",
                    "FTHG": "home_goals", "FTAG": "away_goals",
                    "Date": "date", "date": "date",
                    "home_team": "home_team", "away_team": "away_team",
                    "home_goals": "home_goals", "away_goals": "away_goals",
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            elif use_sample:
                np.random.seed(42)
                teams = [
                    "Arsenal", "Chelsea", "Liverpool", "Man City",
                    "Man United", "Tottenham", "Newcastle", "Brighton",
                    "Aston Villa", "West Ham"
                ]
                dates = pd.date_range("2022-08-01", periods=380, freq="3D")
                data = []
                for d in dates:
                    h = np.random.choice(teams)
                    a = np.random.choice([t for t in teams if t != h])
                    hg = np.random.poisson(1.48)
                    ag = np.random.poisson(1.12)
                    data.append({
                        "date": d, "home_team": h, "away_team": a,
                        "home_goals": hg, "away_goals": ag
                    })
                df = pd.DataFrame(data)
            else:
                st.error("กรุณาอัปโหลด CSV หรือเลือกใช้ข้อมูลจำลอง")
                st.stop()

            analyzer = FootballAnalyzer(xi=xi)
            analyzer.load_data(df)
            analyzer.fit()
            st.session_state.analyzer = analyzer
            st.session_state.fitted = True
            st.success(f"✅ ฟิตสำเร็จ! {len(analyzer.df)} แมตช์ · {len(analyzer.teams)} ทีม")
        except Exception as e:
            st.error(f"ผิดพลาด: {e}")

# Main area
if "fitted" not in st.session_state:
    st.session_state.fitted = False
    st.session_state.analyzer = None

if st.session_state.fitted and st.session_state.analyzer:
    analyzer = st.session_state.analyzer
    teams = analyzer.teams

    st.subheader("เลือกแมตช์")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        home = st.selectbox("ทีมเหย้า", teams, index=0)
    with c2:
        away_options = [t for t in teams if t != home]
        away = st.selectbox("ทีมเยือน", away_options, index=min(1, len(away_options)-1))
    with c3:
        neutral = st.checkbox("สนามกลาง")

    if st.button("วิเคราะห์", type="primary"):
        with st.spinner("กำลังคำนวณ..."):
            result = analyzer.analyze(home, away, neutral=neutral)

        # Key metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("xG Home", result["xg_home"])
        m2.metric("xG Away", result["xg_away"])
        m3.metric("Total xG", result["xg_total"])
        m4.metric("Draw", f"{result['p_draw']*100:.1f}%")

        # Historical stats
        hist = result.get("history", {})
        if hist:
            st.markdown("### สถิติในอดีต")
            h1, h2 = st.columns(2)

            with h1:
                st.markdown(f"**{home}**")
                ho = hist.get("home_overall", {})
                hh = hist.get("home_home", {})
                st.write(f"ฟอร์มล่าสุด: `{ho.get('form', '-')}`")
                st.write(f"เฉลี่ยประตู (รวม): {ho.get('gf', 0)} ยิง / {ho.get('ga', 0)} เสีย")
                st.write(f"เมื่อเป็นเหย้า: {hh.get('gf', 0)} ยิง / {hh.get('ga', 0)} เสีย · ชนะ {hh.get('win_rate', 0)}%")

            with h2:
                st.markdown(f"**{away}**")
                ao = hist.get("away_overall", {})
                aa = hist.get("away_away", {})
                st.write(f"ฟอร์มล่าสุด: `{ao.get('form', '-')}`")
                st.write(f"เฉลี่ยประตู (รวม): {ao.get('gf', 0)} ยิง / {ao.get('ga', 0)} เสีย")
                st.write(f"เมื่อเป็นเยือน: {aa.get('gf', 0)} ยิง / {aa.get('ga', 0)} เสีย · ชนะ {aa.get('win_rate', 0)}%")

            if hist.get("h2h"):
                st.markdown("**Head-to-Head ล่าสุด**")
                h2h_df = pd.DataFrame(hist["h2h"])
                st.dataframe(h2h_df, use_container_width=True, hide_index=True)

        # 1X2
        st.markdown("### ผลการแข่งขัน (1X2)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Home Win", f"{result['p_home']*100:.1f}%")
        c2.metric("Draw", f"{result['p_draw']*100:.1f}%")
        c3.metric("Away Win", f"{result['p_away']*100:.1f}%")

        # Scores
        st.markdown("### Top Scorelines")
        score_df = pd.DataFrame(result["top_scores"], columns=["Home", "Away", "Prob"])
        score_df["Score"] = score_df["Home"].astype(str) + "-" + score_df["Away"].astype(str)
        score_df["Prob %"] = (score_df["Prob"] * 100).round(1)
        st.dataframe(
            score_df[["Score", "Prob %"]].head(10),
            use_container_width=True,
            hide_index=True
        )

        # Over/Under
        st.markdown("### Over / Under")
        ou_rows = []
        for line, probs in result["over_under"].items():
            ou_rows.append({
                "Line": line,
                "Over %": round(probs["over"] * 100, 1),
                "Under %": round(probs["under"] * 100, 1),
                "Push %": round(probs["push"] * 100, 1),
            })
        st.dataframe(pd.DataFrame(ou_rows), use_container_width=True, hide_index=True)

        # Asian Handicap
        st.markdown("### Asian Handicap (มุมมองทีมเหย้า)")
        ah_rows = []
        for line, probs in result["asian_handicap"].items():
            ah_rows.append({
                "Line": f"{line:+.2f}",
                "Home Cover %": round(probs["home_cover"] * 100, 1),
                "Away Cover %": round(probs["away_cover"] * 100, 1),
                "Push %": round(probs["push"] * 100, 1),
            })
        st.dataframe(pd.DataFrame(ah_rows), use_container_width=True, hide_index=True)

else:
    st.info("👈 เริ่มจาก Sidebar: โหลดข้อมูลแล้วกดฟิตโมเดล")
    st.markdown("""
    ### วิธีใช้ข้อมูลจริง
    1. ไปที่ [football-data.co.uk/data.php](https://www.football-data.co.uk/data.php)
    2. ดาวน์โหลด CSV ของลีกที่ต้องการ (เช่น `E0.csv` สำหรับ Premier League)
    3. อัปโหลดใน Sidebar แล้วกด **โหลด & ฟิตโมเดล**
    """)
