# -*- coding: utf-8 -*-
"""
用資料夾真數據重生 Day9 決策表
================================
依使用者原則「真數字不照抄」：decision_summary / decision_supports 裡凡是
「可以從原始 CSV 算出來」的數字，一律重算覆蓋，不用答案版（老師環境）的舊值。
口徑完全依照第6組報告版：
  - D7 完美訂單 OTD = 在時窗內 AND 貨損旗標==0（D7_遲到偵探_報告版.py §口徑）
  - D8 庫存積壓量 = 實際進貨量 − 九月銷量；LT變異 CV = std/mean（D8_供應商儀表板_報告版.py）
decision_risks.csv 無資料衍生數字 → 不動。
重跑：在 v2\ 執行  python build_decision_csv.py
"""
import sys, io
from pathlib import Path
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = Path(__file__).parent

# ============================================================
# 故事 B：配送紀錄 → 完美訂單 OTD（D7 報告版口徑）
# ============================================================
d7 = pd.read_csv(HERE / "配送紀錄_202509.csv", encoding="utf-8-sig",
                 parse_dates=["實際到達", "客戶時窗起", "客戶時窗迄"])
d7["在窗內"] = (d7["實際到達"] >= d7["客戶時窗起"]) & (d7["實際到達"] <= d7["客戶時窗迄"])
d7["完美"] = d7["在窗內"] & (d7["貨損旗標"] == 0)

整體OTD = d7["完美"].mean()
路線 = d7.groupby("路線代碼")["完美"].agg(["mean", "count"])
worst_route = 路線["mean"].idxmin()
worst_route_otd = 路線["mean"].min()
司機 = d7.groupby("司機代碼")["完美"].agg(["mean", "count"])
worst_driver = 司機["mean"].idxmin()
worst_driver_otd = 司機["mean"].min()

# 控制變量（雙向查核）：鎖定最差司機看他跑各路線；鎖定最差路線看各司機
鎖司機 = (d7[d7["司機代碼"] == worst_driver]
          .groupby("路線代碼")["完美"].agg(["mean", "count"])
          .sort_values("mean"))
鎖路線 = (d7[d7["路線代碼"] == worst_route]
          .groupby("司機代碼")["完美"].agg(["mean", "count"])
          .sort_values("mean"))

print("=== 故事 B（配送紀錄實算）===")
print(f"整體完美OTD = {整體OTD:.1%} | 最差路線 {worst_route} = {worst_route_otd:.1%} | "
      f"最差司機 {worst_driver} = {worst_driver_otd:.1%}")
print(f"鎖定 {worst_driver} 跑各路線:\n{(鎖司機['mean']*100).round(1).to_string()}")
print(f"鎖定 {worst_route} 各司機:\n{(鎖路線['mean']*100).round(1).to_string()}")

# ============================================================
# 故事 A：SKU 出貨明細 → ABC（D6 口徑：累計佔比 80%）
# ============================================================
d6 = pd.read_csv(HERE / "SKU_出貨明細_202509.csv", encoding="utf-8-sig")
sku = d6.groupby("SKU")["數量"].sum().sort_values(ascending=False).reset_index()
sku["累計佔比"] = sku["數量"].cumsum() / sku["數量"].sum()
n_A = int((sku["累計佔比"] <= 0.80).sum() + 1)  # pd.cut(bins=[0,.8,...]) 含首筆超線者
# 與 D6 報告版 pd.cut 口徑對齊：類別 = cut(累計佔比, [0, .8, .95, 1])
sku["類別"] = pd.cut(sku["累計佔比"], bins=[0, 0.80, 0.95, 1.0001], labels=["A", "B", "C"])
n_A = int((sku["類別"] == "A").sum())
share_A = sku.loc[sku["類別"] == "A", "數量"].sum() / sku["數量"].sum()
print(f"\n=== 故事 A（SKU 明細實算）===\nA 類 = {n_A} 個 | A 類出貨佔比 = {share_A:.1%}")

# ============================================================
# 故事 C：purchase + receipt + sales → SUP-03 LT / 積壓（D8 口徑）
# ============================================================
p = pd.read_csv(HERE / "purchase.csv", encoding="utf-8-sig", parse_dates=["下單日", "預計到貨"])
r = pd.read_csv(HERE / "receipt.csv", encoding="utf-8-sig", parse_dates=["實際到貨"])
s = pd.read_csv(HERE / "sales.csv", encoding="utf-8-sig", parse_dates=["出貨日"])

pr = p.merge(r, on=["採購單號", "SKU"], how="left")
pr["實際LT"] = (pr["實際到貨"] - pr["下單日"]).dt.days
pr["計畫LT"] = (pr["預計到貨"] - pr["下單日"]).dt.days
已進 = pr[pr["實際到貨"].notna()]
sup3 = 已進[已進["供應商"] == "SUP-03"]
sup3_lt = sup3["實際LT"].mean()
sup3_cv = sup3["實際LT"].std() / sup3["實際LT"].mean()
sup3_delay = (sup3["實際LT"] - sup3["計畫LT"]).mean()

s_cur = s[s["出貨日"].dt.month == 9]
sku_sales = s_cur.groupby("SKU")["出貨量"].sum()
sku_c = (pr.groupby("SKU")
           .agg(訂購量=("訂購量", "sum"), 實際進貨量=("實際數量", "sum"))
           .fillna(0))
sku_c["九月銷量"] = sku_c.index.map(sku_sales).fillna(0)
sku_c["積壓_進貨視角"] = sku_c["實際進貨量"] - sku_c["九月銷量"]
sku_c["積壓_訂購視角"] = sku_c["訂購量"] - sku_c["九月銷量"]
top3_受 = sku_c.sort_values("積壓_進貨視角", ascending=False).head(3).index.tolist()
top3_訂 = sku_c.sort_values("積壓_訂購視角", ascending=False).head(3).index.tolist()

print(f"\n=== 故事 C（三表實算）===")
print(f"SUP-03 平均LT = {sup3_lt:.1f} 天 | CV = {sup3_cv:.2f} | 平均超出計畫 {sup3_delay:+.1f} 天")
print(f"Top3 積壓（進貨-銷）= {top3_受}")
print(f"Top3 積壓（訂購-銷）= {top3_訂}")

# ============================================================
# 重生 decision_summary.csv / decision_supports.csv
# ============================================================
summary = pd.read_csv(HERE / "decision_summary.csv", encoding="utf-8-sig")
supports = pd.read_csv(HERE / "decision_supports.csv", encoding="utf-8-sig")

B = summary["story_id"] == "B"
summary.loc[B, "主結論"] = (f"分割 {worst_route} 路線 + 司機 {worst_driver} 重訓,"
                            f"1 個月內恢復 95% OTD,月效益 +5 萬")
summary.loc[B, "kpi1_label"] = "整體完美訂單 OTD"
summary.loc[B, "kpi1_value"] = f"{整體OTD:.1%}"
summary.loc[B, "kpi2_label"] = f"{worst_route} OTD"
summary.loc[B, "kpi2_value"] = f"{worst_route_otd:.1%}"
summary.loc[B, "kpi3_label"] = f"最差司機 {worst_driver}"
summary.loc[B, "kpi3_value"] = f"{worst_driver_otd:.1%}"

A = summary["story_id"] == "A"
summary.loc[A, "主結論"] = (f"重排前 {n_A} 個 A 類 SKU 儲位,可省約 28% 揀貨工時,"
                            f"2 個月內回收投資")
summary.loc[A, "kpi1_value"] = f"{n_A} 個"
summary.loc[A, "kpi2_value"] = f"{share_A:.1%}"

C = summary["story_id"] == "C"
summary.loc[C, "kpi1_value"] = f"{sup3_lt:.1f} 天"
summary.loc[C, "kpi1_delta"] = f"超出計畫 {sup3_delay:+.1f} 天"
summary.loc[C, "kpi2_value"] = f"{sup3_cv*100:.0f}%"
summary.loc[C, "kpi3_value"] = " · ".join(top3_訂)

sB1 = (supports["story_id"] == "B") & (supports["idx"] == 1)
supports.loc[sB1, "evidence"] = (f"整體完美訂單 OTD {整體OTD:.1%}(在窗+無貨損),"
                                 f"{worst_route} 僅 {worst_route_otd:.1%},顯著低於其他路線")
sB2 = (supports["story_id"] == "B") & (supports["idx"] == 2)
r05 = 鎖司機.loc["R-05", "mean"] if "R-05" in 鎖司機.index else 鎖司機["mean"].max()
supports.loc[sB2, "evidence"] = (
    f"控制變量雙向查核:鎖定 {worst_driver} - {worst_route} {鎖司機['mean'].min():.1%} vs "
    f"其他路線 {r05:.1%}+;鎖定 {worst_route} - 各司機皆差 → 路線為主因,疑路線×司機交互")
sA1 = (supports["story_id"] == "A") & (supports["idx"] == 1)
supports.loc[sA1, "evidence"] = f"A 類 {n_A} 個 SKU 占出貨 {share_A:.1%},儲位卻照字母排"
sC1 = (supports["story_id"] == "C") & (supports["idx"] == 1)
supports.loc[sC1, "evidence"] = (f"SUP-03 LT 平均 {sup3_lt:.1f} 天 σ 大(CV {sup3_cv*100:.0f}%)"
                                 f"→ 安全庫存被迫拉高")

summary.to_csv(HERE / "decision_summary.csv", index=False, encoding="utf-8-sig")
supports.to_csv(HERE / "decision_supports.csv", index=False, encoding="utf-8-sig")
print("\nOK: decision_summary.csv / decision_supports.csv 已用真數據重生(risks 未動)")
