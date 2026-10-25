"""
เครื่องมือวิเคราะห์ฟุตบอลจริงจัง
- Dixon-Coles (penaltyblog)
- สูงต่ำ (Over/Under) หลายเส้น รวม Asian style
- Asian Handicap หลายเส้น (รองรับ whole/half/quarter + push)
- คาดสกอร์ (Correct Score top scores)
- Time-decay weighting
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import penaltyblog as pb


class FootballAnalyzer:
    """เครื่องมือวิเคราะห์ฟุตบอลแบบจริงจังด้วย Dixon-Coles"""

    def __init__(self, xi: float = 0.0018):
        """
        xi: time decay parameter
        ค่าประมาณ 0.0018 ≈ ครึ่งชีวิต ~1 ปี
        ค่าสูงกว่า = ให้น้ำหนักเกมล่าสุดมากกว่า
        """
        self.xi = xi
        self.model = None
        self.teams = None
        self.fitted = False
        self.df = None

    def load_from_penaltyblog(self, competition: str = "ENG Premier League", season: str = "2024-2025", seasons: Optional[List[str]] = None) -> None:
        """ดึงข้อมูลจริงจาก football-data.co.uk (รองรับหลายฤดูกาล)"""
        try:
            if seasons is None:
                seasons = [season]
            all_dfs = []
            for s in seasons:
                try:
                    scraper = pb.scrapers.FootballData(competition, s)
                    fixtures = scraper.get_fixtures()
                    df = fixtures.copy()
                    if "goals_home" not in df.columns and "fthg" in df.columns:
                        df["goals_home"] = df["fthg"]
                        df["goals_away"] = df["ftag"]
                    df = df.rename(columns={
                        "team_home": "home_team",
                        "team_away": "away_team",
                        "goals_home": "home_goals",
                        "goals_away": "away_goals",
                    })
                    if "datetime" in df.columns:
                        df["date"] = pd.to_datetime(df["datetime"])
                    elif "date" in df.columns:
                        df["date"] = pd.to_datetime(df["date"])
                    df = df.dropna(subset=["home_goals", "away_goals"])
                    df["home_goals"] = pd.to_numeric(df["home_goals"], errors="coerce").fillna(0).astype(int)
                    df["away_goals"] = pd.to_numeric(df["away_goals"], errors="coerce").fillna(0).astype(int)
                    df = df[["date", "home_team", "away_team", "home_goals", "away_goals"]]
                    all_dfs.append(df)
                except Exception:
                    continue
            if not all_dfs:
                raise ValueError("ไม่พบข้อมูลฤดูกาลที่เลือก")
            combined = pd.concat(all_dfs, ignore_index=True).sort_values("date").reset_index(drop=True)
            self.load_data(combined)
            print(f"โหลดข้อมูลจริงสำเร็จ: {competition} ({len(combined)} แมตช์ จาก {len(all_dfs)} ฤดูกาล)")
        except Exception as e:
            raise ValueError(f"ดึงข้อมูลไม่สำเร็จ: {e}")

    def load_data(self, df: pd.DataFrame) -> None:
        """
        โหลดข้อมูล
        คอลัมน์ที่ต้องการ:
        - date (datetime หรือ string ที่ parse ได้)
        - home_team
        - away_team
        - home_goals
        - away_goals
        """
        required = ["date", "home_team", "away_team", "home_goals", "away_goals"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"ขาดคอลัมน์: {missing}")

        self.df = df.copy()
        self.df["date"] = pd.to_datetime(self.df["date"])
        self.df = self.df.sort_values("date").reset_index(drop=True)
        self.teams = sorted(set(self.df["home_team"]) | set(self.df["away_team"]))
        print(f"โหลดข้อมูลสำเร็จ: {len(self.df)} แมตช์, {len(self.teams)} ทีม")

    def _compute_weights(self) -> np.ndarray:
        """คำนวณ time-decay weights"""
        if self.df is None:
            raise ValueError("ยังไม่ได้โหลดข้อมูล")
        max_date = self.df["date"].max()
        days_ago = (max_date - self.df["date"]).dt.days
        weights = np.exp(-self.xi * days_ago)
        return weights

    def fit(self) -> None:
        """ฟิตโมเดล Dixon-Coles"""
        if self.df is None:
            raise ValueError("ต้อง load_data ก่อน")

        weights = self._compute_weights()

        self.model = pb.models.DixonColesGoalModel(
            goals_home=self.df["home_goals"].values,
            goals_away=self.df["away_goals"].values,
            teams_home=self.df["home_team"].values,
            teams_away=self.df["away_team"].values,
            weights=weights,
        )
        self.model.fit()
        self.fitted = True
        print("ฟิตโมเดลสำเร็จ")
        print(f"Log Likelihood: {self.model.loglikelihood:.2f}")
        print(f"AIC: {self.model.aic:.2f}")

    def predict_match(
        self,
        home_team: str,
        away_team: str,
        max_goals: int = 8,
        neutral: bool = False,
    ) -> pb.models.FootballProbabilityGrid:
        """ทำนายแมตช์ คืน FootballProbabilityGrid"""
        if not self.fitted:
            raise ValueError("ต้อง fit ก่อน")
        if home_team not in self.teams or away_team not in self.teams:
            raise ValueError(f"ทีมไม่พบในข้อมูล: {home_team} หรือ {away_team}")

        return self.model.predict(
            home_team=home_team,
            away_team=away_team,
            max_goals=max_goals,
            normalize=True,
            neutral_venue=neutral,
        )

    def analyze(
        self,
        home_team: str,
        away_team: str,
        ou_lines: Optional[List[float]] = None,
        ah_lines: Optional[List[float]] = None,
        top_scores: int = 10,
        neutral: bool = False,
    ) -> Dict:
        """วิเคราะห์เต็มรูปแบบ"""
        if ou_lines is None:
            ou_lines = [0.5, 1.5, 2.5, 3.5, 4.5, 2.25, 2.75]
        if ah_lines is None:
            ah_lines = [-2.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]

        grid = self.predict_match(home_team, away_team, neutral=neutral)

        # Expected goals
        xg_home = grid.home_goal_expectation
        xg_away = grid.away_goal_expectation

        # 1X2
        p_home = grid.home_win
        p_draw = grid.draw
        p_away = grid.away_win

        # Correct scores
        scores = grid.grid
        flat_scores = []
        for i in range(scores.shape[0]):
            for j in range(scores.shape[1]):
                flat_scores.append((i, j, float(scores[i, j])))
        flat_scores.sort(key=lambda x: x[2], reverse=True)
        top = flat_scores[:top_scores]

        # Over/Under
        ou_results = {}
        for line in ou_lines:
            over_prob = grid.total_goals("over", line)
            under_prob = grid.total_goals("under", line)
            ou_results[line] = {
                "over": over_prob,
                "under": under_prob,
                "push": max(0.0, 1 - over_prob - under_prob),
            }

        # Asian Handicap (home perspective)
        ah_results = {}
        for line in ah_lines:
            home_win_prob = grid.asian_handicap("home", line)
            away_win_prob = grid.asian_handicap("away", -line)
            push_prob = max(0.0, 1 - home_win_prob - away_win_prob)
            ah_results[line] = {
                "home_cover": home_win_prob,
                "away_cover": away_win_prob,
                "push": push_prob,
            }

        return {
            "home": home_team,
            "away": away_team,
            "xg_home": round(xg_home, 3),
            "xg_away": round(xg_away, 3),
            "xg_total": round(xg_home + xg_away, 3),
            "p_home": round(p_home, 4),
            "p_draw": round(p_draw, 4),
            "p_away": round(p_away, 4),
            "top_scores": [(h, a, round(p, 4)) for h, a, p in top],
            "over_under": ou_results,
            "asian_handicap": ah_results,
            "history": self.get_team_history(home_team, away_team),
        }

    def get_team_history(self, home_team: str, away_team: str, last_n: int = 10) -> Dict:
        """ดึงสถิติในอดีตของทั้งสองทีม + H2H"""
        if self.df is None:
            return {}

        def team_stats(team: str, is_home: Optional[bool] = None, n: int = last_n) -> Dict:
            if is_home is True:
                matches = self.df[self.df["home_team"] == team].tail(n)
                scored = matches["home_goals"]
                conceded = matches["away_goals"]
                results = np.where(matches["home_goals"] > matches["away_goals"], "W",
                                   np.where(matches["home_goals"] < matches["away_goals"], "L", "D"))
            elif is_home is False:
                matches = self.df[self.df["away_team"] == team].tail(n)
                scored = matches["away_goals"]
                conceded = matches["home_goals"]
                results = np.where(matches["away_goals"] > matches["home_goals"], "W",
                                   np.where(matches["away_goals"] < matches["home_goals"], "L", "D"))
            else:
                home_m = self.df[self.df["home_team"] == team]
                away_m = self.df[self.df["away_team"] == team]
                all_m = pd.concat([
                    home_m.assign(scored=home_m["home_goals"], conceded=home_m["away_goals"],
                                  res=np.where(home_m["home_goals"] > home_m["away_goals"], "W",
                                               np.where(home_m["home_goals"] < home_m["away_goals"], "L", "D"))),
                    away_m.assign(scored=away_m["away_goals"], conceded=away_m["home_goals"],
                                  res=np.where(away_m["away_goals"] > away_m["home_goals"], "W",
                                               np.where(away_m["away_goals"] < away_m["home_goals"], "L", "D")))
                ]).sort_values("date").tail(n)
                scored = all_m["scored"]
                conceded = all_m["conceded"]
                results = all_m["res"].values

            if len(scored) == 0:
                return {"matches": 0, "gf": 0, "ga": 0, "form": "", "win_rate": 0}

            form = "".join(results[-5:]) if len(results) >= 5 else "".join(results)
            wins = (results == "W").sum()
            return {
                "matches": len(scored),
                "gf": round(scored.mean(), 2),
                "ga": round(conceded.mean(), 2),
                "form": form,
                "win_rate": round(wins / len(results) * 100, 1),
            }

        # Head-to-head
        h2h = self.df[
            ((self.df["home_team"] == home_team) & (self.df["away_team"] == away_team)) |
            ((self.df["home_team"] == away_team) & (self.df["away_team"] == home_team))
        ].sort_values("date", ascending=False).head(8)

        h2h_list = []
        for _, row in h2h.iterrows():
            h2h_list.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "home": row["home_team"],
                "away": row["away_team"],
                "score": f"{int(row['home_goals'])}-{int(row['away_goals'])}",
            })

        return {
            "home_overall": team_stats(home_team, None),
            "home_home": team_stats(home_team, True),
            "away_overall": team_stats(away_team, None),
            "away_away": team_stats(away_team, False),
            "h2h": h2h_list,
        }

    def print_analysis(self, result: Dict) -> None:
        """พิมพ์ผลวิเคราะห์ให้อ่านง่าย"""
        print("\n" + "=" * 60)
        print(f"  {result['home']}  vs  {result['away']}")
        print("=" * 60)
        print(f"Expected Goals: {result['xg_home']} - {result['xg_away']}  (รวม {result['xg_total']})")
        print(f"1X2:  Home {result['p_home']*100:.1f}%  |  Draw {result['p_draw']*100:.1f}%  |  Away {result['p_away']*100:.1f}%")

        print("\n--- Top Scores ---")
        for h, a, p in result["top_scores"][:8]:
            print(f"  {h}-{a} : {p*100:.1f}%")

        print("\n--- Over / Under ---")
        for line, probs in result["over_under"].items():
            push_str = f" (push {probs['push']*100:.1f}%)" if probs["push"] > 0.001 else ""
            print(f"  O/U {line:4.2f} : Over {probs['over']*100:5.1f}%  Under {probs['under']*100:5.1f}%{push_str}")

        print("\n--- Asian Handicap (Home perspective) ---")
        for line, probs in result["asian_handicap"].items():
            push_str = f" (push {probs['push']*100:.1f}%)" if probs["push"] > 0.001 else ""
            print(f"  AH {line:+5.2f} : Home {probs['home_cover']*100:5.1f}%  Away {probs['away_cover']*100:5.1f}%{push_str}")
        print("=" * 60)


def example_usage():
    """ตัวอย่างการใช้งาน"""
    # สร้างข้อมูลจำลอง (แทนที่ด้วยข้อมูลจริงจาก football-data.co.uk)
    np.random.seed(42)
    teams = ["Arsenal", "Chelsea", "Liverpool", "Man City", "Man United", "Tottenham"]
    dates = pd.date_range("2023-01-01", periods=200, freq="D")
    data = []
    for i, d in enumerate(dates):
        h = np.random.choice(teams)
        a = np.random.choice([t for t in teams if t != h])
        # จำลองประตูแบบง่าย
        hg = np.random.poisson(1.5)
        ag = np.random.poisson(1.2)
        data.append({"date": d, "home_team": h, "away_team": a, "home_goals": hg, "away_goals": ag})

    df = pd.DataFrame(data)

    analyzer = FootballAnalyzer(xi=0.002)
    analyzer.load_data(df)
    analyzer.fit()

    result = analyzer.analyze("Arsenal", "Chelsea")
    analyzer.print_analysis(result)


if __name__ == "__main__":
    example_usage()
