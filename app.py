# -*- coding: utf-8 -*-
"""
物流控制塔 v2 · W2 第6組(Day6-9 合併 stlite 版)
============================================================
由 build_v2.py 從 W2第6組 四支報告版自動合併,原始檔未動。
  📦 Day6 倉庫整理師 · 🚚 Day7 遲到偵探 · 🔗 Day8 供應鏈串接 · 📋 Day9 決策簡報
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from pathlib import Path

try:
    import folium
    FOLIUM_OK = True
except ImportError:
    FOLIUM_OK = False

st.set_page_config(
    page_title="物流控制塔 v2 · W2 第6組",
    layout="wide",
    page_icon="🚚",
    initial_sidebar_state="expanded",  # 一進來先展開；左上角 « 箭頭可收合成窄軌
)

# 側邊欄收合後那顆箭頭太不顯眼，加文字提示引導總經理點開
# （同時相容新舊兩種 Streamlit testid，其中一個吃不到沒關係）
st.markdown(
    """
    <style>
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {
        position: relative;
    }
    [data-testid="stExpandSidebarButton"]::after,
    [data-testid="stSidebarCollapsedControl"]::after,
    [data-testid="collapsedControl"]::after {
        content: "👈 點開看四個故事";
        position: absolute;
        left: 44px;
        top: 8px;
        background: #1f6feb;
        color: #ffffff;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        white-space: nowrap;
        box-shadow: 0 2px 8px rgba(0,0,0,.3);
        pointer-events: none;
        z-index: 999;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def page_day6():
    # -*- coding: utf-8 -*-
    """
    D6 任務 06「倉庫整理師」 · 儲位重排 Streamlit(答案版 / 講師完整版)
    ============================================================
    完整實作:ABC 分類 + 5×10 儲位 heatmap 前後對照 + 揀貨距離預估 +
            服務洞察痛點卡 + sidebar 門檻調整 + 反直覺三問

    預期數值(以 D6_資料產生器.py 種子 42 為準):
      - 約 5,800-6,200 行出貨明細 / 100 SKU
      - A 類:~18-22 個 SKU(累計 80%)
      - B 類:~25-32 個 SKU(80-95%)
      - C 類:~50 個 SKU(95-100%)
      - 重排後預估走動距離縮短 ~25-35%

    對應 Day 6 講義:
      §2.4 ABC 分類 / §3.2 程式骨架 / §4.4 服務設計觀點

    執行:
        streamlit run D6_儲位重排_報告版.py
    """


    # ============================================================
    # §0 頁面設定
    # ============================================================

    GRID_ROWS = 5    # A ~ E 列
    GRID_COLS = 10   # 1 ~ 10 排

    # 顏色映射(Day 6 講師備課提醒:統一規定 A=紅、B=綠、C=灰)
    ABC_COLORS = {"A": "#d62728", "B": "#2ca02c", "C": "#bdbdbd"}
    ABC_NUMERIC = {"A": 2, "B": 1, "C": 0}

    # ============================================================
    # §1 載入資料 + ABC 分類
    # ============================================================
    BASE = Path(".")
    CSV  = BASE / "SKU_出貨明細_202509.csv"


    @st.cache_data
    def load_and_abc(threshold_a: float, threshold_b: float):
        df = pd.read_csv(CSV, encoding="utf-8-sig", parse_dates=["訂單日期"])

        sku = (df.groupby(["SKU", "品名"])
                 .agg(總出貨量=("數量", "sum"),
                      出貨筆數=("訂單編號", "nunique"))
                 .reset_index()
                 .sort_values("總出貨量", ascending=False))

        sku["累計佔比"] = sku["總出貨量"].cumsum() / sku["總出貨量"].sum()
        sku["類別"] = pd.cut(
            sku["累計佔比"],
            bins=[0, threshold_a, threshold_b, 1.0001],
            labels=["A", "B", "C"],
        )
        sku["SKU排名"] = range(1, len(sku) + 1)
        return df, sku


    # ============================================================
    # §2 Sidebar 門檻 slider
    # ============================================================
    st.sidebar.title("⚙ ABC 門檻")
    threshold_a = st.sidebar.slider(
        "A 類上界(累計佔比)", 0.50, 0.90, 0.80, 0.01,
        help="預設 80% — Day 6 講義 §2.4 標準",
    )
    threshold_b = st.sidebar.slider(
        "B 類上界(累計佔比)", threshold_a + 0.01, 0.99, 0.95, 0.01,
        help="預設 95% — 95% 後當作 C 類獨立清倉",
    )

    df, sku = load_and_abc(threshold_a, threshold_b)

    st.sidebar.divider()
    st.sidebar.caption(f"📅 出貨期間 {df['訂單日期'].dt.date.min()} ~ "
                        f"{df['訂單日期'].dt.date.max()}")
    st.sidebar.caption(f"📊 出貨明細 {len(df):,} 行 / {sku.shape[0]} SKU")

    # ============================================================
    # §3 標題 + KPI
    # ============================================================
    st.title("📦 A 倉 · 儲位重排器")
    st.caption(f"5×10 儲位 = 50 格 · 一格放 2 個 SKU(共 100 SKU)· "
               f"出口在左下角 (E, 1)")

    n_a = (sku["類別"] == "A").sum()
    n_b = (sku["類別"] == "B").sum()
    n_c = (sku["類別"] == "C").sum()
    total = len(sku)

    q_a = sku.loc[sku["類別"] == "A", "總出貨量"].sum()
    q_total = sku["總出貨量"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("A 類 SKU(熱銷)", f"{n_a} 個",
              f"占品項 {n_a / total * 100:.0f}%")
    c2.metric("B 類 SKU(中量)", f"{n_b} 個",
              f"占品項 {n_b / total * 100:.0f}%")
    c3.metric("C 類 SKU(冷門)", f"{n_c} 個",
              f"占品項 {n_c / total * 100:.0f}%")
    c4.metric("A 類出貨量占比", f"{q_a / q_total * 100:.1f}%",
              "(對應 80/20 法則)")

    # ============================================================
    # §4 ABC 結果表
    # ============================================================
    with st.expander("📊 ABC 分類結果(前 30 筆)", expanded=False):
        st.dataframe(
            sku.head(30)[["SKU排名", "SKU", "品名", "總出貨量", "出貨筆數",
                           "累計佔比", "類別"]]
               .style.background_gradient(subset=["總出貨量"], cmap="Blues"),
            use_container_width=True, hide_index=True,
        )

    # ============================================================
    # §5 儲位佈局生成
    # ============================================================

    ROW_LABELS = ["A", "B", "C", "D", "E"]
    COL_LABELS = list(range(1, GRID_COLS + 1))


    def build_grid_before(sku_df: pd.DataFrame) -> pd.DataFrame:
        """
        現況:按 SKU 編號順序鋪 — SKU001 在 (A, 1),SKU002 在 (A, 2),... 一格放 2 個。
        回傳 5×10 DataFrame,內容是 (主SKU, 副SKU) 的 tuple。
        """
        skus_sorted_by_id = sorted(sku_df["SKU"].tolist())  # SKU001, SKU002 ...
        grid = pd.DataFrame(index=ROW_LABELS, columns=COL_LABELS, dtype=object)
        for i, _ in enumerate(skus_sorted_by_id[:50]):
            r, c = i // GRID_COLS, i % GRID_COLS
            grid.iloc[r, c] = (skus_sorted_by_id[i], skus_sorted_by_id[i + 50])
        return grid


    def build_grid_after(sku_df: pd.DataFrame) -> pd.DataFrame:
        """
        重排策略(動態熱區):
          A 類 → 中央列(C 列、D 列、左半 1-5 排)= 黃金區腰部高度
          B 類 → 外圍中層(B 列、E 列,以及中央列 6-10 排)
          C 類 → 末端(A 列 + 剩餘外圍)
        出口在 (E, 1) — 左下角。距離越近越好。
        """
        grid = pd.DataFrame(index=ROW_LABELS, columns=COL_LABELS, dtype=object)

        # 計算每個儲位到出口的曼哈頓距離
        distances = []
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                d = abs(r - 4) + abs(c - 0)  # E 列 = row 4(0-indexed)
                distances.append((d, r, c))
        # 距離由近到遠排序
        distances.sort(key=lambda x: x[0])

        # 按 ABC 分類,A 類先放近的位置
        by_category = {
            "A": sku_df[sku_df["類別"] == "A"]["SKU"].tolist(),
            "B": sku_df[sku_df["類別"] == "B"]["SKU"].tolist(),
            "C": sku_df[sku_df["類別"] == "C"]["SKU"].tolist(),
        }
        queue = by_category["A"] + by_category["B"] + by_category["C"]

        # 相鄰兩個 SKU 分一組(同類別優先配對;只有類別交界處若前一類別是奇數個,
        # 才會跟下一類別的第一個配對成同一格,例如 A 是奇數個時,A 最後一個會跟 B 第一個同格)
        pairs = [(queue[i], queue[i + 1] if i + 1 < len(queue) else None)
                 for i in range(0, len(queue), 2)]

        # 依距離由近到遠,把配好對的 50 組放進格子
        for slot_idx, (_, r, c) in enumerate(distances):
            if slot_idx >= len(pairs):
                break
            main_sku, sub_sku = pairs[slot_idx]
            grid.iloc[r, c] = (main_sku, sub_sku)
        return grid


    grid_before = build_grid_before(sku)
    grid_after  = build_grid_after(sku)

    # ------------------------------------------------------------
    # 把 grid 轉成「ABC 類別矩陣」供 heatmap 著色
    # ------------------------------------------------------------
    sku_to_cat = sku.set_index("SKU")["類別"].to_dict()


    def grid_to_category_matrix(grid: pd.DataFrame) -> np.ndarray:
        mat = np.zeros((GRID_ROWS, GRID_COLS))
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = grid.iloc[r, c]
                if cell is None or (isinstance(cell, float) and np.isnan(cell)):
                    continue
                main_sku, _ = cell
                cat = sku_to_cat.get(main_sku, "C")
                mat[r, c] = ABC_NUMERIC[cat]
        return mat


    def grid_to_text_matrix(grid: pd.DataFrame) -> list:
        text = [["" for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = grid.iloc[r, c]
                if cell is None or (isinstance(cell, float) and np.isnan(cell)):
                    continue
                main_sku, sub_sku = cell
                text[r][c] = f"{main_sku}<br>{sub_sku or ''}"
        return text


    def draw_heatmap(grid: pd.DataFrame, title: str):
        z = grid_to_category_matrix(grid)
        text = grid_to_text_matrix(grid)
        fig = go.Figure(data=go.Heatmap(
            z=z,
            text=text,
            texttemplate="%{text}",
            colorscale=[[0, ABC_COLORS["C"]],
                        [0.5, ABC_COLORS["B"]],
                        [1.0, ABC_COLORS["A"]]],
            zmin=0, zmax=2,
            showscale=False,
            x=[f"排 {c}" for c in COL_LABELS],
            y=[f"列 {r}" for r in ROW_LABELS],
            xgap=2, ygap=2,
        ))
        fig.update_layout(
            title=title,
            height=320,
            margin=dict(l=10, r=10, t=40, b=10),
            yaxis=dict(autorange="reversed"),
        )
        return fig


    # ============================================================
    # §6 5x10 Heatmap 重排前後對照
    # ============================================================
    st.divider()
    st.subheader("🗺 儲位 5×10 重排對照")
    st.caption(f"出口在 **(E, 1)** 左下角 · 顏色:🔴 A 類 / 🟢 B 類 / ⚪ C 類")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**重排前(按 SKU 編號順序)**")
        st.plotly_chart(draw_heatmap(grid_before, "現況:SKU001-100 字母順序"),
                        use_container_width=True)
    with col_b:
        st.markdown("**重排後(動態熱區 / ABC)**")
        st.plotly_chart(draw_heatmap(grid_after, "重排:A 類靠出口 / C 類在末端"),
                        use_container_width=True)

    # ============================================================
    # §7 平均揀貨距離(曼哈頓)估算
    # ============================================================
    st.divider()
    st.subheader("📐 預估改善 · 揀貨走動距離")


    def avg_pick_distance(grid: pd.DataFrame, sku_qty: dict) -> float:
        """
        模擬:出口在 (E, 1) = (4, 0)。
        每 1 件出貨 = 1 趟揀貨(簡化)。
        平均距離 = sum(qty × distance) / sum(qty)
        """
        total_qty = 0
        total_dist = 0
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = grid.iloc[r, c]
                if cell is None or (isinstance(cell, float) and np.isnan(cell)):
                    continue
                main_sku, sub_sku = cell
                d = abs(r - 4) + abs(c - 0)
                for s in (main_sku, sub_sku):
                    if s and s in sku_qty:
                        total_qty += sku_qty[s]
                        total_dist += d * sku_qty[s]
        return total_dist / max(total_qty, 1)


    sku_qty = sku.set_index("SKU")["總出貨量"].to_dict()
    dist_before = avg_pick_distance(grid_before, sku_qty)
    dist_after  = avg_pick_distance(grid_after,  sku_qty)
    saving_pct = (dist_before - dist_after) / dist_before * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("重排前 平均揀貨距離", f"{dist_before:.2f} 格")
    c2.metric("重排後 平均揀貨距離", f"{dist_after:.2f} 格")
    c3.metric("改善幅度(依出貨量)", f"{saving_pct:.1f}%", "縮短",
              delta_color="normal" if saving_pct > 0 else "inverse")

    # 依「出貨筆數」加權的版本:更貼近揀貨員實際走動/彎腰次數
    # (總出貨量版把同一筆訂單裡拿 22 件當成 22 趟,出貨筆數版才是 1 趟)
    sku_cnt = sku.set_index("SKU")["出貨筆數"].to_dict()
    dist_before_cnt = avg_pick_distance(grid_before, sku_cnt)
    dist_after_cnt  = avg_pick_distance(grid_after,  sku_cnt)
    saving_pct_cnt = (dist_before_cnt - dist_after_cnt) / dist_before_cnt * 100

    st.caption("💡 下面改用「出貨筆數」加權(= 揀貨員實際走動/彎腰次數),"
               "比上面的「總出貨量」版更貼近真實勞力成本。")

    c4, c5, c6 = st.columns(3)
    c4.metric("重排前 平均揀貨距離(依筆數)", f"{dist_before_cnt:.2f} 格")
    c5.metric("重排後 平均揀貨距離(依筆數)", f"{dist_after_cnt:.2f} 格")
    c6.metric("改善幅度(依出貨筆數)", f"{saving_pct_cnt:.1f}%", "縮短",
              delta_color="normal" if saving_pct_cnt > 0 else "inverse")

    # 假設一格 = 2 公尺、揀貨員時速 4 km/h(腳程慢)
    # 一個月出貨總量 × 距離省下幅度 → 工時節省
    total_picks = sku["總出貨量"].sum()
    saved_meters = (dist_before - dist_after) * 2 * total_picks  # 一格 = 2 公尺,雙程要 ×2
    saved_hours  = saved_meters / 4000  # 4 km/h
    st.success(
        f"**月節省走動**:約 {saved_meters / 1000:,.1f} 公里(雙程)→ "
        f"換算揀貨員工時 ~{saved_hours:.1f} 小時/月 "
        f"(假設一格 2 公尺 / 揀貨員時速 4 km/h)"
    )

    # ============================================================
    # §8 服務洞察 · 揀貨員痛點 → 改善對應
    # ============================================================
    st.divider()
    st.subheader("🩺 服務洞察(任務 06 Rubric 30 分)")
    st.markdown("**從早上畫的服務藍圖反推**:儲位重排不只省距離,更直接緩解揀貨員痛點。")

    pain_fix = [
        ("揀貨員每天彎腰 200 次 → 職業傷害 (LBP)",
         "A 類全部下移到 C / D 列(腰部高度),減少彎腰次數 ~50%"),
        ("熱銷 A 類在最高層 → 推梯子 → 安全事故",
         "A 類禁止排到 A 列(最高層),用 D 列「腰部黃金高度」安置"),
        ("同類品項混放 → 揀錯率 5%",
         "ABC 顏色標示 + 同類品項聚塊(本頁 heatmap),揀錯率預估降到 < 1%"),
        ("補貨員看不到熱區 → 補貨延遲 → 缺貨",
         "熱區固定在中央 → 補貨員只盯中央,補貨頻率提升、缺貨率下降"),
    ]
    for pain, fix in pain_fix:
        st.markdown(f"- 🔴 **痛點**:{pain}")
        st.markdown(f"  - ✅ **改善**:{fix}")

    # ============================================================
    # §9 反直覺三問(Day 6 講義 §5.4)
    # ============================================================
    st.divider()
    st.subheader("🔍 反直覺三問(K 層洞察)")

    c1, c2, c3 = st.columns(3)
    c1.warning(
        "**Q1:自動化 AGV 倉,還需要 ABC 嗎?**\n\n"
        "**A:仍需要。**AGV 自己算路徑 → SKU 放哪不影響;但**補貨/盤點區段**仍需 ABC 規劃,"
        "不然補貨員會像無頭蒼蠅。"
    )
    c2.warning(
        "**Q2:季節性服飾,ABC 有什麼陷阱?**\n\n"
        "**A:把上一季熱銷品永遠當 A 類。**\n"
        "解法:加**時間衰減權重** — 越近的出貨記錄佔越大,讓 A 類隨季節漂移。"
    )
    c3.warning(
        "**Q3:老闆要降 30% 倉儲面積,先動哪類?**\n\n"
        "**A:先動 C 類**(壓縮儲位 / 退倉)。\n"
        "但要先檢查 C 類是不是「未來可能變 A」的新品 — 否則動到了會錯殺潛力股。"
    )

    # ============================================================
    # §10 Footer
    # ============================================================
    st.divider()
    st.caption(
        f"📌 資料來源:`SKU_出貨明細_202509.csv` · "
        f"由 `D6_資料產生器.py` 種子 42 產出 · "
        f"重排策略:動態熱區(A→中央近出口、C→末端高層)"
    )
    st.caption(
        "📚 對應 Day 6 講義 §2.3 EIQ-PCB · §2.4 ABC 分類 · §4.4 服務設計觀點"
    )


def page_day7():
    # -*- coding: utf-8 -*-
    """
    D7 任務 07「遲到偵探」 · 互動地圖看板 Streamlit(答案版 / 講師完整版)
    ============================================================
    完整實作:
      - 三層 OTD(整體 / 路線 / 司機)+ 控制變量
      - IQR 異常偵測 + 早到 vs 遲到拆解
      - Folium 地圖 + 路線篩選器(LayerControl + sidebar 雙路徑)
      - 病灶診斷(自動產出文字)
      - 反直覺三問(Day 7 §5.4)

    預期數值(以 D7_資料產生器.py 種子 42 為準):
      - 整體完美訂單 OTD ≈ 78-83%
      - R-03 路線 OTD ≈ 25%(★ 壞路線埋點)
      - D-07 司機 OTD ≈ 45%(★ 慢手司機埋點)
      - IQR 抓出 ~5-8% 異常筆數
      - 控制變量(D-07 在不同路線):落差小 → 主因 = 司機

    對應 Day 7 講義:
      §2 觀念區(OTD + 異常 + MBE)
      §3 工具區(Pandas + IQR + Folium)
      §5.4 反直覺三問

    執行:
        streamlit run D7_遲到偵探_報告版.py

    依賴:
        pip install streamlit pandas folium streamlit-folium
    """


    # ----- 第一次跑請先裝 folium:pip install folium streamlit-folium -----
    try:
        FOLIUM_OK = True
    except ImportError:
        FOLIUM_OK = False

    # ============================================================
    # §0 頁面設定
    # ============================================================

    # ============================================================
    # §1 載入資料 + 計算 OTD + IQR 異常
    # ============================================================
    BASE = Path(".")
    CSV  = BASE / "配送紀錄_202509.csv"


    @st.cache_data
    def load_and_analyze():
        df = pd.read_csv(CSV, encoding="utf-8-sig",
                         parse_dates=["預計到達", "實際到達",
                                      "客戶時窗起", "客戶時窗迄"])

        df["在窗內"] = (df["實際到達"] >= df["客戶時窗起"]) & \
                      (df["實際到達"] <= df["客戶時窗迄"])
        df["完整"]   = df["貨損旗標"] == 0
        df["OTD_嚴格"]   = df["在窗內"]                # 純客戶視角:準時落在時窗內
        df["OTD_完美訂單"] = df["在窗內"] & df["完整"]  # 三方加權:時窗內 × 無損
        df["偏移分鐘"] = (df["實際到達"] - df["預計到達"]).dt.total_seconds() / 60
        df["早到"] = df["實際到達"] < df["客戶時窗起"]
        df["遲到"] = df["實際到達"] > df["客戶時窗迄"]
        df["小時"] = df["預計到達"].dt.hour

        # IQR 異常旗標
        Q1 = df["偏移分鐘"].quantile(0.25)
        Q3 = df["偏移分鐘"].quantile(0.75)
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        df["異常旗標"] = (df["偏移分鐘"] < lower) | (df["偏移分鐘"] > upper)
        return df, lower, upper


    df, lower, upper = load_and_analyze()

    # ============================================================
    # §2 Sidebar 篩選
    # ============================================================
    st.sidebar.title("🔍 篩選")

    all_routes  = sorted(df["路線代碼"].unique())
    all_drivers = sorted(df["司機代碼"].unique())

    sel_routes  = st.sidebar.multiselect("路線", all_routes, default=all_routes)
    sel_drivers = st.sidebar.multiselect("司機", all_drivers, default=all_drivers)
    show_only_anomaly = st.sidebar.checkbox("地圖只顯示異常點", value=False)

    df_f = df[df["路線代碼"].isin(sel_routes) &
              df["司機代碼"].isin(sel_drivers)]

    st.sidebar.divider()
    st.sidebar.caption(f"📅 期間:{df['預計到達'].dt.date.min()} ~ "
                        f"{df['預計到達'].dt.date.max()}")
    st.sidebar.caption(f"📊 篩選後:{len(df_f):,} 筆")

    # ============================================================
    # §3 標題 + KPI
    # ============================================================
    st.title("🚚 B 配送 · 遲到偵探")
    st.caption(f"配送筆數 {len(df):,} · 9 路線 × 12 司機 · "
               f"{df['預計到達'].dt.date.min()} ~ {df['預計到達'].dt.date.max()}")

    整體_OTD = df["OTD_完美訂單"].mean()
    篩選_OTD = df_f["OTD_完美訂單"].mean() if len(df_f) else 0
    異常_n   = df_f["異常旗標"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("整體 完美訂單 OTD", f"{整體_OTD:.1%}",
              help="在時窗內 + 無貨損")
    c2.metric("篩選後 OTD", f"{篩選_OTD:.1%}",
              f"{(篩選_OTD - 整體_OTD) * 100:+.1f}pp vs 整體",
              delta_color="normal" if 篩選_OTD >= 整體_OTD else "inverse")
    c3.metric("異常配送筆數", f"{異常_n:,}",
              f"{異常_n / max(len(df_f), 1) * 100:.1f}%")
    worst_route = df.groupby("路線代碼")["OTD_完美訂單"].mean().idxmin()
    c4.metric("最差路線", worst_route,
              f"OTD {df.groupby('路線代碼')['OTD_完美訂單'].mean().min():.1%}")

    # OTD 健康分區提示
    if 整體_OTD < 0.90:
        st.error("🔴 整體 OTD < 90% — 屬於系統性問題,不是個別事件")
    elif 整體_OTD < 0.95:
        st.warning("🟠 整體 OTD 90-95% — 偏低,需深度檢視路線/時段")
    else:
        st.success("🟢 整體 OTD ≥ 95% — 健康")

    # ============================================================
    # §4 三層 OTD 拆解
    # ============================================================
    st.divider()
    st.subheader("📊 三層 OTD 拆解")

    整體_OTD_嚴格 = df["OTD_嚴格"].mean()
    貨損缺口_pp = (整體_OTD_嚴格 - 整體_OTD) * 100
    st.caption(f"📦 整體時窗達成率 {整體_OTD_嚴格:.1%} vs 完美訂單 OTD {整體_OTD:.1%} · "
               f"貨損拖累 {貨損缺口_pp:.1f}pp(缺口越大 → 問題偏向貨損,而非準點)")

    col_r, col_d = st.columns(2)
    with col_r:
        st.markdown("**路線層 OTD**(時窗 vs 完美訂單,由差到好)")
        路線 = (df.groupby("路線代碼")
                  .agg(訂單數=("OTD_完美訂單", "count"),
                       OTD_嚴格=("OTD_嚴格", "mean"),
                       OTD=("OTD_完美訂單", "mean"))
                  .sort_values("OTD"))
        路線["時窗OTD%"] = (路線["OTD_嚴格"] * 100).round(1)
        路線["完美OTD%"] = (路線["OTD"] * 100).round(1)
        路線["貨損缺口pp"] = (路線["時窗OTD%"] - 路線["完美OTD%"]).round(1)
        st.dataframe(
            路線[["訂單數", "時窗OTD%", "完美OTD%", "貨損缺口pp"]]
                .style.background_gradient(subset=["完美OTD%"], cmap="RdYlGn"),
            use_container_width=True,
        )

    with col_d:
        st.markdown("**司機層 OTD**(時窗 vs 完美訂單,由差到好)")
        司機 = (df.groupby("司機代碼")
                  .agg(訂單數=("OTD_完美訂單", "count"),
                       OTD_嚴格=("OTD_嚴格", "mean"),
                       OTD=("OTD_完美訂單", "mean"))
                  .sort_values("OTD"))
        司機["時窗OTD%"] = (司機["OTD_嚴格"] * 100).round(1)
        司機["完美OTD%"] = (司機["OTD"] * 100).round(1)
        司機["貨損缺口pp"] = (司機["時窗OTD%"] - 司機["完美OTD%"]).round(1)
        st.dataframe(
            司機[["訂單數", "時窗OTD%", "完美OTD%", "貨損缺口pp"]]
                .style.background_gradient(subset=["完美OTD%"], cmap="RdYlGn"),
            use_container_width=True,
        )

    # ============================================================
    # §5 控制變量 — 雙向查核(最差司機 x 不同路線 / 最差路線 x 不同司機)
    # ============================================================
    st.subheader("🔬 控制變量分析(雙向查核,最關鍵)")
    st.caption("單看一個方向容易被巧合誤導(例如最差司機剛好只跑最差路線)。"
               "這裡同時鎖定「司機不變、換路線」與「路線不變、換司機」,兩邊一致才算高信心診斷。")
    worst_driver = 司機.index[0]

    col5a, col5b = st.columns(2)

    with col5a:
        st.markdown(f"**鎖定司機:`{worst_driver}`(整體完美 OTD {司機.loc[worst_driver, '完美OTD%']}%)** "
                    f"· 看他在不同路線的 OTD")
        ctrl = (df[df["司機代碼"] == worst_driver]
                .groupby("路線代碼")
                .agg(訂單數=("OTD_完美訂單", "count"),
                     OTD=("OTD_完美訂單", "mean"))
                .sort_values("OTD"))
        ctrl["OTD%"] = (ctrl["OTD"] * 100).round(1)
        st.dataframe(
            ctrl[["訂單數", "OTD%"]]
                .style.background_gradient(subset=["OTD%"], cmap="RdYlGn"),
            use_container_width=True,
        )
        driver_std = ctrl["OTD"].std()

    with col5b:
        st.markdown(f"**鎖定路線:`{worst_route}`(整體完美 OTD {路線.loc[worst_route, '完美OTD%']}%)** "
                    f"· 看不同司機跑這條路線的 OTD")
        ctrl2 = (df[df["路線代碼"] == worst_route]
                 .groupby("司機代碼")
                 .agg(訂單數=("OTD_完美訂單", "count"),
                      OTD=("OTD_完美訂單", "mean"))
                 .sort_values("OTD"))
        ctrl2["OTD%"] = (ctrl2["OTD"] * 100).round(1)
        st.dataframe(
            ctrl2[["訂單數", "OTD%"]]
                .style.background_gradient(subset=["OTD%"], cmap="RdYlGn"),
            use_container_width=True,
        )
        route_std = ctrl2["OTD"].std()


    def _classify(std_val, n_groups, cause_if_small):
        """std 小 → 該維度固定時表現一致 → 問題出在被固定的那個維度。樣本不足(<2 組)回傳 None。"""
        if n_groups < 2 or pd.isna(std_val):
            return None
        cause_if_large = "路線" if cause_if_small == "司機" else "司機"
        return cause_if_small if std_val < 0.10 else cause_if_large


    # 司機視角:鎖定司機、std 小 = 這個司機到哪都差 → 主因司機
    cause_from_driver = _classify(driver_std, len(ctrl), "司機")
    # 路線視角:鎖定路線、std 小 = 誰跑這條路線都差 → 主因路線
    cause_from_route = _classify(route_std, len(ctrl2), "路線")

    if cause_from_driver and cause_from_route:
        if cause_from_driver == cause_from_route:
            diag_main = cause_from_driver
            confidence_note = (f"雙向查核一致(司機視角 std={driver_std:.2f}、"
                                f"路線視角 std={route_std:.2f})→ 信心較高")
            st.success(f"→ 雙向查核一致 → **主因 = {diag_main}**。{confidence_note}")
        else:
            diag_main = cause_from_driver
            confidence_note = (f"雙向查核不一致(司機視角判斷={cause_from_driver}、"
                                f"路線視角判斷={cause_from_route})→ 可能是司機 × 路線的交互作用,"
                                f"建議再切分時段或訂單量深入看")
            st.warning(f"→ 兩個方向的判斷不一致 → 暫定 **主因 = {diag_main}**(低信心)。{confidence_note}")
    elif cause_from_driver:
        diag_main = cause_from_driver
        confidence_note = f"`{worst_route}` 可用司機樣本不足(僅 {len(ctrl2)} 組),只能靠司機視角判斷"
        st.info(f"→ 樣本不足,僅單向判斷 → **主因 = {diag_main}**。{confidence_note}")
    elif cause_from_route:
        diag_main = cause_from_route
        confidence_note = f"`{worst_driver}` 可用路線樣本不足(僅 {len(ctrl)} 組),只能靠路線視角判斷"
        st.info(f"→ 樣本不足,僅單向判斷 → **主因 = {diag_main}**。{confidence_note}")
    else:
        diag_main = "不明"
        confidence_note = "雙向樣本皆不足,無法判斷"
        st.info(f"→ {confidence_note}")

    # ============================================================
    # §6 異常偵測詳情 + 早到 vs 遲到
    # ============================================================
    st.divider()
    st.subheader("⚠ 異常偵測(IQR)+ 早到 / 遲到拆解")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**IQR 閾值**(Day 7 §2.2 武器一)")
        Q1 = df["偏移分鐘"].quantile(0.25)
        Q3 = df["偏移分鐘"].quantile(0.75)
        IQR = Q3 - Q1
        skew = df["偏移分鐘"].skew()
        st.code(
            f"Q1   = {Q1:6.1f} min\n"
            f"Q3   = {Q3:6.1f} min\n"
            f"IQR  = {IQR:6.1f} min\n"
            f"下界 = {lower:6.1f} min(早到太多)\n"
            f"上界 = {upper:6.1f} min(遲到太多)\n"
            f"偏態 = {skew:+.2f}({'右偏 → IQR 適合' if skew > 0 else '左偏 → IQR 適合'})"
        )

    with c2:
        st.markdown("**早到 vs 遲到 vs 在窗內**")
        早 = df["早到"].sum()
        遲 = df["遲到"].sum()
        內 = df["在窗內"].sum()
        st.code(
            f"早到   = {早:5d} 筆({早 / len(df):.2%})\n"
            f"遲到   = {遲:5d} 筆({遲 / len(df):.2%})\n"
            f"在窗內 = {內:5d} 筆({內 / len(df):.2%})\n"
            f"\n反直覺第三點:**早到也算違約**\n"
            f"客戶在 14:00-16:00,你 12:30 送到 = 失敗"
        )

    # ============================================================
    # §7 互動地圖看板(Folium)
    # ============================================================
    st.divider()
    st.subheader("🗺 異常配送地圖看板")
    st.caption("🔴 異常(IQR 外) · 🟢 正常 · 點擊 marker 看訂單詳情")

    if show_only_anomaly:
        df_map = df_f[df_f["異常旗標"]]
    else:
        df_map = df_f

    if not FOLIUM_OK:
        st.error(
            "❌ 缺少 folium 套件。請在終端機執行:\n\n"
            "```\npip install folium streamlit-folium\n```\n\n"
            "裝完後重新整理本頁。"
        )
    elif len(df_map) == 0:
        st.warning("沒有符合篩選條件的訂單,請調整 sidebar")
    else:
        # 中心點 = 篩選資料的平均座標
        center_lat = df_map["客戶緯度"].mean()
        center_lon = df_map["客戶經度"].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=11,
                       tiles="OpenStreetMap")

        # 每條路線一個 FeatureGroup(LayerControl)
        for route in sorted(df_map["路線代碼"].unique()):
            sub = df_map[df_map["路線代碼"] == route]
            fg = folium.FeatureGroup(name=f"{route}({len(sub)} 筆)")
            for _, row in sub.iterrows():
                color = "red" if row["異常旗標"] else "green"
                folium.CircleMarker(
                    location=[row["客戶緯度"], row["客戶經度"]],
                    radius=4,
                    color=color,
                    fill=True,
                    fillOpacity=0.6,
                    popup=folium.Popup(
                        f"<b>訂單</b> {row['訂單編號']}<br>"
                        f"<b>路線</b> {row['路線代碼']} · "
                        f"<b>司機</b> {row['司機代碼']}<br>"
                        f"<b>偏移</b> {row['偏移分鐘']:.0f} 分<br>"
                        f"<b>OTD</b> {'✓ 在窗' if row['在窗內'] else '✗ 失準'}",
                        max_width=260,
                    ),
                ).add_to(fg)
            fg.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        components.html(m.get_root().render(), height=540, scrolling=True)

    # ============================================================
    # §8 異常 pattern 速覽
    # ============================================================
    st.divider()
    st.subheader("📋 異常 pattern 速覽(以異常率排序)")
    st.caption("用「異常率%」而非「異常筆數」排名 —— 訂單量大的路線/司機筆數本來就多,"
               "直接比筆數容易錯把「量大」當成「問題大」。")
    anomalies = df[df["異常旗標"]]


    def anomaly_rate_table(key):
        g = (df.groupby(key)
               .agg(訂單數=("異常旗標", "count"), 異常筆數=("異常旗標", "sum")))
        g["異常率%"] = (g["異常筆數"] / g["訂單數"] * 100).round(1)
        return g.sort_values("異常率%", ascending=False).head()


    route_rate = anomaly_rate_table("路線代碼")
    driver_rate = anomaly_rate_table("司機代碼")
    hour_rate = anomaly_rate_table("小時")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**by 路線(異常率 Top 5)**")
        st.dataframe(route_rate, use_container_width=True)
    with c2:
        st.markdown("**by 司機(異常率 Top 5)**")
        st.dataframe(driver_rate, use_container_width=True)
    with c3:
        st.markdown("**by 時段(異常率 Top 5)**")
        st.dataframe(hour_rate, use_container_width=True)

    # ============================================================
    # §9 病灶診斷(Rubric 25 分)
    # ============================================================
    st.divider()
    st.subheader("🩺 病灶診斷(任務 07 Rubric 25 分)")

    # 自動產出診斷文字(以異常率而非異常筆數選出重點路線/司機/時段,避免被高訂單量誤導)
    top_route      = route_rate.index[0]
    top_route_rate = route_rate.loc[top_route, "異常率%"]
    top_route_n    = int(route_rate.loc[top_route, "異常筆數"])
    top_drv        = driver_rate.index[0]
    top_drv_rate   = driver_rate.loc[top_drv, "異常率%"]
    top_drv_n      = int(driver_rate.loc[top_drv, "異常筆數"])
    top_hour       = int(hour_rate.index[0])
    top_hour_rate  = hour_rate.loc[hour_rate.index[0], "異常率%"]

    diag = (
        f"**整體完美訂單 OTD = {整體_OTD:.1%}**(時窗達成率 {整體_OTD_嚴格:.1%},貨損拖累 {貨損缺口_pp:.1f}pp),屬於"
        f"{'🔴 警戒' if 整體_OTD < 0.90 else '🟠 偏低' if 整體_OTD < 0.95 else '🟢 健康'}區間。"
        f"異常筆數 {df['異常旗標'].sum():,} 筆({df['異常旗標'].mean():.1%}),"
        f"異常率最高集中在路線 **{top_route}**(異常率 {top_route_rate:.1f}%,{top_route_n} 筆)"
        f"與司機 **{top_drv}**(異常率 {top_drv_rate:.1f}%,{top_drv_n} 筆),"
        f"時段以 **{top_hour:02d}:00** 為高峰(異常率 {top_hour_rate:.1f}%)。\n\n"
        f"控制變量雙向查核:{confidence_note}。診斷主因為 **{diag_main}**。\n\n"
        f"**一週內可動行動**:把 `{worst_driver}` 暫時移出 `{worst_route}` 路線,"
        f"觀察 7 天 OTD 是否回升到整體平均。如果回升 → 主因確認為 {diag_main};"
        f"如果沒回升 → 另一個維度(路線本身時窗訂太緊、塞車尖峰沒避開,或貨損拖累明顯時要查裝卸/包裝流程)"
        f"才是真正結構問題,需要重排時窗或改善作業流程。預期 OTD 由 {整體_OTD:.1%} 提升到 {min(整體_OTD + 0.08, 0.95):.1%}。"
    )
    st.success(diag)

    # ============================================================
    # §10 反直覺三問(Day 7 §5.4)
    # ============================================================
    st.divider()
    st.subheader("🔍 反直覺三問(K 層)")

    c1, c2, c3 = st.columns(3)
    c1.warning(
        "**Q1:OTD 99.5% 還用做這份分析嗎?**\n\n"
        "**A:看時窗緊度。**99.5% with 6 小時時窗 << 95% with 1 小時時窗。"
        "單看比例會被「寬鬆時窗」假象矇蔽。"
    )
    c2.warning(
        "**Q2:D-07 OTD 偏低,但他只跑 R-03,你會懲罰司機嗎?**\n\n"
        "**A:不。**要先做控制變量(本頁 §5)— 換別人跑 R-03 OTD 一樣低 → "
        "問題是路線而非司機。"
    )
    c3.warning(
        "**Q3:OTD < 95% 扣司機獎金,會發生什麼?**\n\n"
        "**A:Goodhart's Law** — 司機為了不被扣錢,會選**早到**(寧可早 30 分也不晚)。"
        "結果客戶不在 → 早到也算失敗 → OTD 反而更慘。"
    )

    # ============================================================
    # §11 Footer
    # ============================================================
    st.divider()
    st.caption(
        f"📌 資料來源:`配送紀錄_202509.csv` · "
        f"由 `D7_資料產生器.py` 種子 42 產出 · "
        f"OTD 定義:完美訂單(在時窗內 AND 無貨損)"
    )
    st.caption(
        "📚 對應 Day 7 講義 §2.1 OTD 三口徑 · §2.2 異常三武器 · "
        "§3.3 Folium 地圖 · §5.4 反直覺三問"
    )


def page_day8():
    # -*- coding: utf-8 -*-
    """
    D8 任務 08「供應鏈串接」 · Streamlit 講師完整版
    ============================================================
    對應講義 W2_管理工程師/Day8_教材包/Day8_講義.md §3 + §5

    實作要點(8 個 TODO 全填 + 額外):
      ✓ KPI 4 卡(採購單數 / 整體 LT / Top1 積壓 / 供應商家數)
      ✓ Tab 1 供應商 QDCS:LT 變異長條 + 不良率 vs 單價散佈 + 「便宜換來的」紅框
      ✓ Tab 2 SKU 積壓主因表 + 主因占比甜甜圈
      ✓ Tab 3 長鞭效應折線圖 + 變異係數對照
      ✓ Tab 4 自動診斷文字 + 反直覺三問

    執行:
        cd 02_CoursePlan\\範例資料與程式\\W2\\D8_供應鏈
        pip install streamlit pandas plotly
        streamlit run D8_供應商儀表板_報告版.py

    預期輸出(種子 42):
      - 整體平均 LT ≈ 14-17 天
      - Top 1 積壓 SKU = S-1015(積壓 ≈ 800-900)· 主因 = 採購過量
      - 「便宜換來的」紅框會跳 SUP-03(單價最低 + LT 變異 ~0.45-0.55)
      - 長鞭效應:銷售變異 < 進貨變異 < 採購變異(理論成立)
    """




    # =============================================================
    # 0. 頁面
    # =============================================================

    st.title("🔗 Day 8 任務 08 · 供應鏈串接(完整版)")
    st.caption("採購 ↔ 進貨 ↔ 銷售 三表分析 · 自動診斷庫存積壓主因")


    # =============================================================
    # 1. 載入三表
    # =============================================================

    DATA_DIR = Path(".")


    @st.cache_data
    def load_data():
        p = pd.read_csv(DATA_DIR / "purchase.csv", encoding="utf-8-sig", parse_dates=["下單日", "預計到貨"])
        r = pd.read_csv(DATA_DIR / "receipt.csv",  encoding="utf-8-sig", parse_dates=["實際到貨"])
        s = pd.read_csv(DATA_DIR / "sales.csv",    encoding="utf-8-sig", parse_dates=["出貨日"])
        return p, r, s


    try:
        p, r, s = load_data()
    except FileNotFoundError as e:
        st.error(
            f"找不到資料檔:{e.filename}\n\n"
            f"請先在本資料夾執行 `python D8_資料產生器.py` 產生三張 CSV。"
        )
        st.stop()


    # =============================================================
    # 2. Step 1 + Step 2 Merge
    # =============================================================

    pr = p.merge(r, on=["採購單號", "SKU"], how="left")
    pr["實際LT"]  = (pr["實際到貨"] - pr["下單日"]).dt.days
    pr["計畫LT"]  = (pr["預計到貨"] - pr["下單日"]).dt.days
    pr["LT延遲日"] = pr["實際LT"] - pr["計畫LT"]

    # 銷售拆兩段:當期(9 月)算積壓;前三個月(6-8 月)算「過去三個月平均月銷」
    s_cur  = s[s["出貨日"].dt.month == 9].copy()
    s_prev = s[s["出貨日"].dt.month.isin([6, 7, 8])].copy()

    sku_sales = (
        s_cur.groupby("SKU", as_index=False)
         .agg(九月銷量=("出貨量", "sum"), 銷售筆數=("銷售單號", "count"))
    )
    prev_sales = (
        s_prev.groupby("SKU", as_index=False)
          .agg(前三月銷量=("出貨量", "sum"))
    )
    prev_sales["前三月平均月銷"] = (prev_sales["前三月銷量"] / 3).round(1)

    full = pr.merge(sku_sales, on="SKU", how="left")
    for col in ["九月銷量", "銷售筆數", "實際數量", "品質旗標"]:
        full[col] = full[col].fillna(0).astype(int)

    # SKU 級彙總
    sku_view = (
        full.groupby(["SKU", "品類", "供應商"], as_index=False)
            .agg(訂購量=("訂購量", "sum"),
                 實際進貨量=("實際數量", "sum"),
                 九月銷量=("九月銷量", "first"),
                 不良次數=("品質旗標", "sum"))
    )
    sku_view = sku_view.merge(prev_sales[["SKU", "前三月平均月銷"]], on="SKU", how="left")
    sku_view["前三月平均月銷"] = sku_view["前三月平均月銷"].fillna(0)
    sku_view["庫存積壓量"] = sku_view["實際進貨量"] - sku_view["九月銷量"]
    sku_view["周轉率"]    = (sku_view["九月銷量"] / sku_view["實際進貨量"].replace(0, np.nan)).round(2)
    sku_view["不良率"]    = (sku_view["不良次數"] / sku_view["實際進貨量"].replace(0, np.nan)).fillna(0)

    # 供應商級彙總
    已進 = full[full["實際到貨"].notna()].copy()
    supplier = (
        已進.groupby("供應商", as_index=False)
            .agg(平均LT=("實際LT", "mean"),
                 LT變異=("實際LT", lambda x: x.std() / x.mean() if x.mean() > 0 else 0),
                 不良率=("品質旗標", "mean"),
                 平均單價=("單價", "mean"),
                 採購單數=("採購單號", "nunique"),
                 總進貨量=("實際數量", "sum"))
    )
    supplier["D 達交分"] = pd.cut(supplier["LT變異"],
                                bins=[-0.01, 0.10, 0.20, 0.30, 0.45, 99],
                                labels=[5, 4, 3, 2, 1]).astype(int)
    supplier["Q 品質分"] = pd.cut(supplier["不良率"],
                                bins=[-0.001, 0.005, 0.01, 0.02, 0.04, 1],
                                labels=[5, 4, 3, 2, 1]).astype(int)
    supplier["C 成本分"] = pd.cut(supplier["平均單價"],
                                bins=[0, 80, 95, 110, 130, 999],
                                labels=[5, 4, 3, 2, 1]).astype(int)
    supplier["加權分(QDC)"] = (
        supplier["Q 品質分"] * 0.40 +
        supplier["D 達交分"] * 0.40 +
        supplier["C 成本分"] * 0.20
    ).round(2)

    def 等級(score):
        if score >= 4.5: return "A 戰略夥伴"
        if score >= 3.5: return "B 一般合作"
        if score >= 2.5: return "C 觀察名單"
        return "D 淘汰候選"
    supplier["等級"] = supplier["加權分(QDC)"].apply(等級)

    # 品類內供應商比較:全公司排行榜混雜了品類天生差異(冷藏/冷凍 LT 較長、單價較高),
    # 這裡改成「同品類內」相對排名,才是公平的供應商能力比較。
    cat_supplier = (
        已進.groupby(["品類", "供應商"], as_index=False)
            .agg(平均LT=("實際LT", "mean"),
                 LT變異=("實際LT", lambda x: x.std() / x.mean() if x.mean() > 0 else 0),
                 不良率=("品質旗標", "mean"),
                 平均單價=("單價", "mean"),
                 採購單數=("採購單號", "nunique"),
                 總進貨量=("實際數量", "sum"))
    )
    cat_supplier["品類內家數"] = cat_supplier.groupby("品類")["供應商"].transform("count")


    def _品類內排名分(s: pd.Series) -> pd.Series:
        """數值越低分數越高(1~5),用同品類內的百分位排名,而非全公司同一把尺;
        品類內只有 1 家供應商、或某供應商只有 1 筆進貨(標準差算不出來變 NaN)時,給中間值 3 分。"""
        if len(s) <= 1:
            return pd.Series([3] * len(s), index=s.index)
        pct = s.rank(pct=True, ascending=False)
        score = pd.cut(pct, bins=[-0.01, 0.2, 0.4, 0.6, 0.8, 1.01], labels=[1, 2, 3, 4, 5])
        return score.astype(float).fillna(3).astype(int)


    cat_supplier["品類內D分"] = cat_supplier.groupby("品類")["LT變異"].transform(_品類內排名分)
    cat_supplier["品類內Q分"] = cat_supplier.groupby("品類")["不良率"].transform(_品類內排名分)
    cat_supplier["品類內C分"] = cat_supplier.groupby("品類")["平均單價"].transform(_品類內排名分)
    cat_supplier["品類內加權分"] = (
        cat_supplier["品類內Q分"] * 0.40 +
        cat_supplier["品類內D分"] * 0.40 +
        cat_supplier["品類內C分"] * 0.20
    ).round(2)
    cat_supplier["品類內等級"] = cat_supplier["品類內加權分"].apply(等級)


    # =============================================================
    # 3. Sidebar(含 session_state + 重置按鈕)
    # =============================================================

    DEFAULTS = {
        "cat_filter":  "(全部)",
        "sup_filter":  "(全部)",
        "topn_filter": 5,
        "thr_filter":  2.0,
    }
    for _k, _v in DEFAULTS.items():
        if _k not in st.session_state:
            st.session_state[_k] = _v


    def reset_filters():
        for k, v in DEFAULTS.items():
            st.session_state[k] = v


    st.sidebar.header("🎯 篩選")

    cat_options = ["(全部)"] + sorted(sku_view["品類"].unique().tolist())
    sup_options = ["(全部)"] + sorted(sku_view["供應商"].unique().tolist())

    st.sidebar.selectbox("品類", cat_options, key="cat_filter")
    st.sidebar.selectbox("供應商", sup_options, key="sup_filter")
    st.sidebar.slider("Top N 積壓 SKU", 3, 20, key="topn_filter")
    st.sidebar.number_input("採購過量倍率閾值(進貨量 ÷ 前三月平均月銷)", 1.0, 8.0, step=0.5, key="thr_filter")
    st.sidebar.button("🔄 重置篩選", on_click=reset_filters, use_container_width=True)

    sel_cat            = st.session_state["cat_filter"]
    sel_sup            = st.session_state["sup_filter"]
    top_n              = st.session_state["topn_filter"]
    backlog_threshold  = st.session_state["thr_filter"]

    is_filtered = (sel_cat != "(全部)") or (sel_sup != "(全部)")

    # ---- 篩選 sku_view ----
    view = sku_view.copy()
    if sel_cat != "(全部)":
        view = view[view["品類"] == sel_cat]
    if sel_sup != "(全部)":
        view = view[view["供應商"] == sel_sup]

    # 篩選後 SKU 集合 → 用來篩 purchase / receipt / sales / 已進
    view_skus = set(view["SKU"].tolist())
    p_view   = p[p["SKU"].isin(view_skus)] if is_filtered else p
    r_view   = r[r["SKU"].isin(view_skus)] if is_filtered else r
    s_view   = s_cur[s_cur["SKU"].isin(view_skus)] if is_filtered else s_cur  # 長鞭效應/計數用當期 9 月
    已進_view = 已進[已進["SKU"].isin(view_skus)] if is_filtered else 已進

    st.sidebar.markdown("---")
    filter_tag = "篩選後" if is_filtered else "全體"
    st.sidebar.markdown(f"**目前範圍**:{filter_tag}")
    st.sidebar.markdown(f"**符合條件的 SKU**:{len(view)}")
    st.sidebar.markdown(f"**採購單**:{p_view['採購單號'].nunique()}")
    st.sidebar.markdown(f"**進貨**:{len(r_view)}")
    st.sidebar.markdown(f"**銷售(9 月)**:{len(s_view):,}")


    # =============================================================
    # 4. KPI 4 卡(全部跟著篩選器動)
    # =============================================================

    if is_filtered:
        st.info(f"🎯 目前篩選範圍:**品類 = {sel_cat} · 供應商 = {sel_sup}**(共 {len(view)} 支 SKU)。"
                f" KPI / Tab 2-4 都會跟著篩,Tab 1 QDCS 維持 8 家整列並把選中的供應商高亮。")

    c1, c2, c3, c4 = st.columns(4)

    # K1 採購單數(篩選後)
    c1.metric(f"採購單數 ({filter_tag})", f"{p_view['採購單號'].nunique():,}")

    # K2 整體平均 LT(篩選後)
    if len(已進_view) > 0:
        overall_lt = 已進_view["實際LT"].mean()
        plan_lt    = 已進_view["計畫LT"].mean()
        delta_lt   = overall_lt - plan_lt
        c2.metric(f"平均 LT ({filter_tag})", f"{overall_lt:.1f} 天",
                  delta=f"{delta_lt:+.1f} 天 vs 計畫", delta_color="inverse")
    else:
        c2.metric(f"平均 LT ({filter_tag})", "—")

    # K3 Top 1 積壓
    if len(view) > 0:
        top1 = view.sort_values("庫存積壓量", ascending=False).iloc[0]
        c3.metric(f"Top1 積壓 · {top1['SKU']}", f"{int(top1['庫存積壓量']):,} 件",
                  delta=f"{top1['品類']} / {top1['供應商']}")
    else:
        c3.metric("Top1 積壓", "—", delta="無符合 SKU")

    # K4 積壓率(篩選後)
    total_in  = view["實際進貨量"].sum() if len(view) else 0
    total_out = view["九月銷量"].sum() if len(view) else 0
    backlog_ratio = (total_in - total_out) / total_in if total_in else 0
    c4.metric(f"積壓率 ({filter_tag})",
              f"{backlog_ratio:.1%}" if total_in else "—",
              delta=f"進 {total_in:,} / 銷 {total_out:,}")

    st.divider()


    # =============================================================
    # 5. Tabs
    # =============================================================

    tab1, tab1c, tab2, tab3, tab4 = st.tabs([
        "🏭 供應商 QDCS",
        "🏷️ 品類內比較",
        "📦 SKU 積壓主因",
        "📈 長鞭效應",
        "🎯 自動診斷 + 反直覺三問",
    ])


    # ---- Tab 1: 供應商 QDCS(永遠顯示 8 家整列 + 高亮選中)----
    with tab1:
        st.subheader("供應商績效矩陣 QDCS")
        if sel_sup != "(全部)":
            st.caption(f"💡 已選 **{sel_sup}** — 整列高亮顯示,但維持 8 家整體比較才有意義。")

        show_cols = ["供應商", "等級", "加權分(QDC)", "Q 品質分", "D 達交分", "C 成本分",
                     "平均LT", "LT變異", "不良率", "平均單價", "採購單數", "總進貨量"]

        def _highlight_row(row):
            if sel_sup != "(全部)" and row["供應商"] == sel_sup:
                return ["background-color: rgba(255, 215, 0, 0.35); font-weight: bold"] * len(row)
            return [""] * len(row)

        styled_supplier = (
            supplier[show_cols]
                .sort_values("加權分(QDC)", ascending=False)
                .style
                .apply(_highlight_row, axis=1)
                .format({
                    "平均LT": "{:.1f}",
                    "LT變異": "{:.2f}",
                    "不良率": "{:.2%}",
                    "平均單價": "{:.1f}",
                })
                .background_gradient(subset=["加權分(QDC)"], cmap="RdYlGn")
        )
        st.dataframe(styled_supplier, use_container_width=True)

        col_a, col_b = st.columns(2)

        # TODO 3 ✓ — 選中的供應商換色強調
        with col_a:
            st.markdown("##### 各供應商 LT 變異(σ/μ)")
            sup_sorted = supplier.sort_values("LT變異").copy()
            sup_sorted["highlight"] = sup_sorted["供應商"].apply(
                lambda s: "選中" if s == sel_sup else "其他"
            )
            if sel_sup != "(全部)":
                fig = px.bar(
                    sup_sorted, x="供應商", y="LT變異",
                    color="highlight",
                    color_discrete_map={"選中": "#FFD700", "其他": "#888888"},
                    text=sup_sorted["LT變異"].round(2),
                )
            else:
                fig = px.bar(
                    sup_sorted, x="供應商", y="LT變異",
                    color="LT變異", color_continuous_scale="Reds",
                    text=sup_sorted["LT變異"].round(2),
                )
            fig.add_hline(y=0.30, line_dash="dash", line_color="red",
                          annotation_text="0.30 警戒")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=400, margin=dict(t=20, b=10),
                              showlegend=(sel_sup != "(全部)"))
            st.plotly_chart(fig, use_container_width=True)

        # TODO 4 ✓ — 選中的供應商加粗外框
        with col_b:
            st.markdown("##### 不良率 vs 平均單價(反直覺第二點)")
            fig2 = px.scatter(
                supplier, x="平均單價", y="不良率",
                size="總進貨量", text="供應商",
                color="LT變異", color_continuous_scale="Reds",
                size_max=50,
            )
            # 為選中的供應商加金色外框
            if sel_sup != "(全部)" and sel_sup in supplier["供應商"].values:
                row_sel = supplier[supplier["供應商"] == sel_sup].iloc[0]
                fig2.add_trace(go.Scatter(
                    x=[row_sel["平均單價"]], y=[row_sel["不良率"]],
                    mode="markers", marker=dict(
                        size=row_sel["總進貨量"] / supplier["總進貨量"].max() * 50 + 15,
                        color="rgba(0,0,0,0)",
                        line=dict(color="gold", width=4),
                    ),
                    showlegend=False, hoverinfo="skip",
                ))
            fig2.update_traces(textposition="top center", selector=dict(mode="markers+text"))
            fig2.update_layout(height=400, margin=dict(t=20, b=10),
                               yaxis_tickformat=".1%")
            st.plotly_chart(fig2, use_container_width=True)

        # TODO 6 ✓ 「便宜換來的」反直覺紅框
        st.markdown("##### ⚠️ 「便宜換來的」反直覺警示")
        median_price = supplier["平均單價"].median()
        便宜不穩 = supplier[
            (supplier["平均單價"] < median_price) & (supplier["LT變異"] > 0.30)
        ]
        if len(便宜不穩) > 0:
            names = "、".join(便宜不穩["供應商"].tolist())
            st.error(
                f"⚠ **{names}** 屬於『單價低於中位數但 LT 變異 > 0.30』 — "
                f"這正是講義 §2.2 的反直覺第二點:**便宜常常用 LT 換的**。\n\n"
                f"當 LT 變異 > 0.30 時,你會被迫多備至少 2 週的安全庫存。\n"
                f"安全庫存的資金成本 + 倉儲成本一加上,**真實 TCO 可能比報價貴 5-15%**。\n\n"
                f"建議:對 {names} 啟動雙源備援,或重談報價納入 LT 履約罰則。"
            )
            st.dataframe(便宜不穩[["供應商", "平均單價", "LT變異", "不良率", "等級"]]
                         .style.format({"平均單價": "{:.1f}",
                                        "LT變異": "{:.2f}",
                                        "不良率": "{:.2%}"}),
                         use_container_width=True)
        else:
            st.success("✅ 目前沒有『便宜但 LT 不穩』的供應商。")


    # ---- Tab 1c: 品類內供應商比較(控制品類差異,才是公平比較) ----
    with tab1c:
        st.subheader("同品類內供應商比較")
        st.caption(
            "Tab 1 的全公司排行榜混雜了品類天生差異(冷藏/冷凍 LT 較長、單價較高) — "
            "這裡改成『同品類內』相對排名(百分位),同一把尺只在同品類供應商之間比,才公平。"
        )

        cat_pick = st.selectbox("選擇品類", sorted(cat_supplier["品類"].unique().tolist()), key="cat_compare")
        sub = cat_supplier[cat_supplier["品類"] == cat_pick].sort_values("品類內加權分", ascending=False)

        n_sup_in_cat = sub["供應商"].nunique()
        if n_sup_in_cat <= 1:
            st.warning(f"⚠ {cat_pick} 品類下只有 {n_sup_in_cat} 家供應商,無法做相對比較(分數僅為預設中間值,僅供參考)。")
        elif n_sup_in_cat <= 3:
            st.info(f"ℹ️ {cat_pick} 品類下僅 {n_sup_in_cat} 家供應商,樣本較小,排名僅供參考。")

        show_cols2 = ["供應商", "品類內等級", "品類內加權分", "品類內Q分", "品類內D分", "品類內C分",
                      "平均LT", "LT變異", "不良率", "平均單價", "採購單數", "總進貨量"]
        display_rename = {
            "品類內等級": "等級",
            "品類內加權分": "加權分(QDC)",
            "品類內Q分": "Q 品質分",
            "品類內D分": "D 達交分",
            "品類內C分": "C 成本分",
        }
        st.dataframe(
            sub[show_cols2].rename(columns=display_rename).style
                .format({"平均LT": "{:.1f}", "LT變異": "{:.2f}", "不良率": "{:.2%}", "平均單價": "{:.1f}"})
                .background_gradient(subset=["加權分(QDC)"], cmap="RdYlGn"),
            use_container_width=True,
        )

        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown(f"##### {cat_pick} 品類 · LT 變異對照")
            sub_lt = sub.sort_values("LT變異")
            fig5 = px.bar(sub_lt, x="供應商", y="LT變異",
                          color="LT變異", color_continuous_scale="Reds",
                          text=sub_lt["LT變異"].round(2))
            fig5.add_hline(y=0.30, line_dash="dash", line_color="red", annotation_text="0.30 警戒")
            fig5.update_traces(textposition="outside")
            fig5.update_layout(height=380, margin=dict(t=20, b=10))
            st.plotly_chart(fig5, use_container_width=True)
        with col_d:
            st.markdown(f"##### {cat_pick} 品類 · 平均單價對照")
            sub_price = sub.sort_values("平均單價")
            fig6 = px.bar(sub_price, x="供應商", y="平均單價",
                          color="平均單價", color_continuous_scale="Blues",
                          text=sub_price["平均單價"].round(1))
            fig6.update_traces(textposition="outside")
            fig6.update_layout(height=380, margin=dict(t=20, b=10))
            st.plotly_chart(fig6, use_container_width=True)

        st.markdown("##### 🔍 全公司排名 vs 品類內排名 差異對照")
        compare = supplier[["供應商", "等級", "加權分(QDC)"]].merge(
            sub[["供應商", "品類內等級", "品類內加權分"]], on="供應商", how="inner"
        )
        compare["排名差"] = compare["品類內加權分"] - compare["加權分(QDC)"]
        st.dataframe(
            compare.sort_values("排名差", ascending=False).style
                .format({"加權分(QDC)": "{:.2f}", "品類內加權分": "{:.2f}", "排名差": "{:+.2f}"}),
            use_container_width=True,
        )
        st.caption(
            "『排名差』> 0:這家供應商在全公司排行榜被低估(可能是分到較難的品類,例如冷藏/冷凍)。\n\n"
            "『排名差』< 0:在全公司排行榜被高估(可能是分到成本結構天生較低的品類,例如乾貨)。"
        )


    # ---- Tab 2: SKU 積壓主因 ----
    with tab2:
        st.subheader(f"Top {top_n} 庫存積壓 SKU + 主因標籤")

        sup_lt_var = supplier.set_index("供應商")["LT變異"].to_dict()
        view2 = view.copy()
        view2["供應商LT變異"] = view2["供應商"].map(sup_lt_var)

        def 主因標籤(row):
            causes = []
            # 採購過量:進貨量 > 前三個月平均月銷 × 閾值(預設 2)且積壓 > 100
            if row["實際進貨量"] > row["前三月平均月銷"] * backlog_threshold and row["庫存積壓量"] > 100:
                causes.append("採購過量")
            if pd.notna(row["供應商LT變異"]) and row["供應商LT變異"] > 0.30:
                causes.append("LT過長")
            if pd.notna(row["周轉率"]) and row["周轉率"] < 0.20:
                causes.append("銷售下滑")
            if row["不良次數"] >= 1 and row["不良率"] >= 0.05:
                causes.append("品質瑕疵")
            return " / ".join(causes) if causes else "一般庫存"

        view2["主因"] = view2.apply(主因標籤, axis=1) if len(view2) else pd.Series([], dtype=object)
        top = view2.sort_values("庫存積壓量", ascending=False).head(top_n)

        if len(top) == 0:
            st.warning(
                "⚠ 目前篩選條件下沒有任何 SKU。\n\n"
                "（你選的『品類 × 供應商』組合在資料中不存在 — 例如 SUP-05 主要出冷藏類,沒有乾貨類。"
                "請放寬其中一個篩選條件,或按 sidebar『重置篩選』再試。)"
            )
        else:
            # TODO 5 ✓
            st.dataframe(
                top[["SKU", "品類", "供應商", "訂購量", "實際進貨量", "九月銷量",
                     "前三月平均月銷", "庫存積壓量", "周轉率", "供應商LT變異", "不良率", "主因"]]
                    .style.format({
                        "前三月平均月銷": "{:.1f}",
                        "周轉率": "{:.2f}",
                        "供應商LT變異": "{:.2f}",
                        "不良率": "{:.2%}",
                    }).background_gradient(subset=["庫存積壓量"], cmap="Reds"),
                use_container_width=True,
            )

            # 主因占比甜甜圈(Top N 內 · 加守備:Series 為空時 .str.split 會炸)
            主因s = top["主因"].dropna().astype(str)
            if len(主因s) == 0:
                cause_count = pd.DataFrame(columns=["主因", "次數"])
            else:
                cause_count = (
                    主因s.str.split(" / ").explode().value_counts().reset_index()
                )
                cause_count.columns = ["主因", "次數"]
            if len(cause_count):
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    fig3 = px.pie(cause_count, names="主因", values="次數", hole=0.5,
                                  title=f"Top {top_n} 主因占比 ({filter_tag})")
                    fig3.update_layout(height=350, margin=dict(t=40, b=10))
                    st.plotly_chart(fig3, use_container_width=True)
                with col_b:
                    st.markdown("##### 行動建議")
                    for _, r2 in cause_count.iterrows():
                        action = {
                            "採購過量":  "🛑 暫停採購、檢討業務 forecast、清庫存 promo",
                            "LT過長":    "🔄 啟動雙源備援 / 重議 LT 罰則",
                            "銷售下滑":  "📉 業務追蹤客流 / 促銷或下架",
                            "品質瑕疵":  "🔧 退換貨 / 啟動品質升級 SQA 監控",
                            "一般庫存":  "—",
                        }.get(r2["主因"], "—")
                        st.markdown(f"- **{r2['主因']}**({r2['次數']} 例):{action}")


    # ---- Tab 3: 長鞭效應 ----
    with tab3:
        st.subheader(f"長鞭效應自檢 · {filter_tag}")
        st.caption("反直覺第一點(講義 §2.1):從消費端往上游,變異會逐級放大。")
        if is_filtered:
            st.info(f"📌 目前看的是 **{sel_cat} / {sel_sup}** 子集的長鞭效應(共 {len(view)} 支 SKU)。"
                    f"放寬篩選器或按重置可看全公司版本。")

        if len(p_view) == 0 or len(r_view) == 0 or len(s_view) == 0:
            st.warning("⚠ 目前篩選範圍下,三表至少有一表為空,無法畫長鞭效應。請放寬篩選或按重置。")
        else:
            daily = pd.DataFrame({
                "採購下單量": p_view.groupby("下單日")["訂購量"].sum(),
                "進貨量":     r_view.groupby("實際到貨")["實際數量"].sum(),
                "銷售出貨量": s_view.groupby("出貨日")["出貨量"].sum(),
            }).fillna(0).sort_index()
            daily.index.name = "日期"
            daily = daily.reset_index()

            # TODO 7 ✓
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=daily["日期"], y=daily["銷售出貨量"],
                                      name="銷售出貨量(下游)",
                                      mode="lines+markers", line=dict(color="#27ae60")))
            fig4.add_trace(go.Scatter(x=daily["日期"], y=daily["進貨量"],
                                      name="進貨量(中段)",
                                      mode="lines+markers", line=dict(color="#f39c12")))
            fig4.add_trace(go.Scatter(x=daily["日期"], y=daily["採購下單量"],
                                      name="採購下單量(上游)",
                                      mode="lines+markers", line=dict(color="#c0392b")))
            fig4.update_layout(
                title=f"三層每日量級對照 ({filter_tag})",
                height=430, margin=dict(t=50, b=20),
                legend=dict(orientation="h", y=-0.15),
                hovermode="x unified",
            )
            st.plotly_chart(fig4, use_container_width=True)

            # 變異係數對照
            cv_table = pd.DataFrame({
                "層級": ["銷售出貨量(下游)", "進貨量(中段)", "採購下單量(上游)"],
                "平均": [daily["銷售出貨量"].mean(), daily["進貨量"].mean(), daily["採購下單量"].mean()],
                "標準差": [daily["銷售出貨量"].std(), daily["進貨量"].std(), daily["採購下單量"].std()],
            })
            cv_table["變異(CV)"] = (cv_table["標準差"] / cv_table["平均"].replace(0, np.nan)).round(2).fillna(0)
            st.markdown("##### 三層變異係數(CV = σ/μ)對照")
            st.dataframe(cv_table.style.format({"平均": "{:.1f}", "標準差": "{:.1f}"}),
                         use_container_width=True)

            cv_sales  = cv_table.iloc[0]["變異(CV)"]
            cv_orders = cv_table.iloc[2]["變異(CV)"]
            if cv_sales > 0 and cv_orders > cv_sales * 1.5:
                st.error(
                    f"⚠ **長鞭效應確認** · 上游採購變異 {cv_orders:.2f} > 下游銷售變異 {cv_sales:.2f} × 1.5 = {cv_sales*1.5:.2f}\n\n"
                    f"原因可能是:**EOQ 批量訂購**(訂滿一個經濟批量才下單)+ **促銷期屯貨**\n"
                    f"建議:導入 **每週小批多次** 採購,或與供應商簽 VMI(供應商管理庫存)。"
                )
            else:
                st.success("✅ 此範圍下長鞭效應尚未明顯放大,維持當前節奏。")


    # ---- Tab 4: 自動診斷 + 反直覺三問(跟著篩選器動)----
    with tab4:
        st.subheader(f"🤖 自動診斷:這份庫存的問題是什麼?({filter_tag})")
        if is_filtered:
            st.caption(f"目前診斷範圍 = 品類 `{sel_cat}` × 供應商 `{sel_sup}` ({len(view)} 支 SKU)")

        def auto_diagnose(sku_view_in, supplier_all):
            notes = []
            sup_lt_var = supplier_all.set_index("供應商")["LT變異"].to_dict()
            v2 = sku_view_in.copy()
            if len(v2) == 0:
                return ["⚠ 篩選範圍下沒有 SKU,無法診斷。"], None
            v2["供應商LT變異"] = v2["供應商"].map(sup_lt_var)

            over_purchase = v2[(v2["實際進貨量"] > v2["前三月平均月銷"] * backlog_threshold) & (v2["庫存積壓量"] > 100)]
            lt_long       = v2[v2["供應商LT變異"] > 0.30]
            sales_down    = v2[(v2["周轉率"] < 0.20) & (v2["庫存積壓量"] > 100)]
            quality_bad   = v2[(v2["不良次數"] >= 1) & (v2["不良率"] >= 0.05)]

            notes.append(f"📊 採購過量 SKU 共 {len(over_purchase)} 支,合計積壓 "
                         f"{over_purchase['庫存積壓量'].sum():,.0f} 件")
            notes.append(f"⏱️ LT 過長(供應商 LT 變異 > 0.30)SKU 共 {len(lt_long)} 支,"
                         f"合計積壓 {lt_long['庫存積壓量'].sum():,.0f} 件")
            notes.append(f"📉 銷售下滑(周轉率 < 0.20)SKU 共 {len(sales_down)} 支,"
                         f"合計積壓 {sales_down['庫存積壓量'].sum():,.0f} 件")
            notes.append(f"🔧 品質瑕疵 SKU 共 {len(quality_bad)} 支")

            impacts = {
                "採購過量": over_purchase["庫存積壓量"].sum(),
                "LT過長":   lt_long["庫存積壓量"].sum(),
                "銷售下滑": sales_down["庫存積壓量"].sum(),
                "品質瑕疵": quality_bad["庫存積壓量"].sum(),
            }
            if sum(impacts.values()) == 0:
                return notes, "✅ 此範圍下沒有顯著主因 — 庫存大致平衡。"

            main_cause = max(impacts, key=impacts.get)
            supplier_action = supplier_all[supplier_all["加權分(QDC)"] < 3.0]["供應商"].tolist()

            diag = (
                f"**主因 = `{main_cause}`** "
                f"(影響積壓量 {impacts[main_cause]:,.0f} 件 / "
                f"占範圍內 {impacts[main_cause]/sum(impacts.values()):.0%})\n\n"
                f"**建議行動**:\n"
                f"- 對應主因為「{main_cause}」的 SKU,**下個月暫停或減半採購**\n"
                f"- 弱供應商 {supplier_action if supplier_action else '無'} 啟動雙源備援\n"
                f"- 業務端做 SKU 級需求 review,避免重蹈 forecast 錯估\n"
            )
            return notes, diag

        notes, diag = auto_diagnose(view, supplier)

        for n in notes:
            st.markdown(n)
        if diag:
            st.divider()
            st.success(diag)

        st.divider()

        st.subheader("🤔 反直覺三問")

        # Q1 · 用 view 範圍內的 Top 1(若 view 為空就 fallback 全體)
        base_for_q1 = view if len(view) else sku_view
        q1_top1 = base_for_q1.sort_values("庫存積壓量", ascending=False).iloc[0]
        with st.expander("❓ Q1 · 庫存積壓最大的 SKU,真的是『賣不好』嗎?還是『買太兇』?"):
            st.markdown(
                f"""
                **此範圍 Top 1 積壓 SKU**:`{q1_top1['SKU']}` · 進貨 {int(q1_top1['實際進貨量']):,} 件 · 前三月平均月銷 {q1_top1['前三月平均月銷']:.1f} 件 · 9 月銷量 {int(q1_top1['九月銷量']):,} 件

                進貨量是「過去三個月平均月銷」的 **{q1_top1['實際進貨量']/max(q1_top1['前三月平均月銷'],1):.1f} 倍**。
                如果 > 2 倍(且積壓 > 100)→ 主因明顯是『**採購過量**』,而不是業務賣不好。
                **下次老闆罵業務之前,先翻採購紀錄。**
                """
            )

        with st.expander("❓ Q2 · 單價最便宜的供應商,真的最划算嗎?"):
            cheap = supplier.sort_values("平均單價").iloc[0]
            st.markdown(
                f"""
                **單價最便宜**:`{cheap['供應商']}` · 平均單價 {cheap['平均單價']:.1f} 元 · LT 變異 **{cheap['LT變異']:.2f}**

                如果 LT 變異 > 0.30,意味你被迫多備至少 2 週安全庫存 →
                **資金成本 + 倉儲成本 + 報廢風險,實際 TCO 可能比同業貴 5-15%**。
                **報價最低 ≠ 真正最便宜。**
                """
            )

        with st.expander("❓ Q3 · 你選 `inner` 還是 `left` join,反映你『想看哪個視角』?"):
            not_received = pr[pr["實際到貨"].isna()]
            st.markdown(
                f"""
                這份分析用 `purchase.merge(receipt, how='left')` —
                才看得到「**訂了但還沒到**」的採購單共 **{len(not_received)} 筆**。

                如果改用 `inner`,這 {len(not_received)} 筆會被靜默丟掉 →
                **你以為一切正常,其實採購卡關才是最早期的警訊**。

                **Merge 不是技術題,是商業假設題。**
                """
            )


    st.divider()
    st.caption(
        "📓 Notebook → `D8_供應鏈Merge_示範.ipynb`  ·  "
        "🟧 Orange3 → `D8_供應鏈_Orange3.md`  ·  "
        "📄 講義 → `Day8_講義.md`"
    )


def page_day9():
    # -*- coding: utf-8 -*-
    """
    D9 任務 09「決策簡報」 · 講師完整版(答案版)
    ============================================================
    給總經理的一頁建議書 — 完整實作。
    沿 Day 9 講義 §3.1 路徑 A(Streamlit 一頁互動板)規格,加上 D8 答案版
    的設計教訓:

      ✓ Sidebar 故事三選一,所有 KPI / 圖 / 支撐 / 風險全面跟動
      ✓ session_state + 重置鈕(回到故事 B 預設)
      ✓ 主結論 st.success 卡片(綠底 · 第一屏看得到)
      ✓ 三個 st.metric KPI 卡片(三條支撐的 KPI 化)
      ✓ 一張關鍵圖(故事 A=Pareto / B=箱型路線 / C=供應商 CV 長條)
      ✓ 三條 st.expander 支撐 — 摺起,要看才打開
      ✓ 風險三情境表 — 樂觀 / 悲觀 / 不作為,月效益具體量化
      ✓ 投資回收期 + 反直覺三點 + 90 秒 Showtime 腳本下載
      ✓ 補:三故事跨案比較圖(月效益 × 投資回收期)

    執行:
        streamlit run D9_決策建議_答案版.py

    預期(教師驗收):
      - 第一屏看得到主結論 + 3 KPI + 1 圖
      - 切換故事 A → B → C 全部跟動
      - 重置鈕回到 Story B 預設
      - 反直覺三點 expander 帶出 §2.4 金句
      - 跨案比較圖凸顯三故事權衡(B 速效 / A 大省 / C 長線)
    """


    # 嘗試載入 plotly,沒裝就退到 matplotlib
    try:
        PLOTLY_OK = True
    except ImportError:
        PLOTLY_OK = False

    # =============================================================
    # 0. 頁面設定
    # =============================================================


    HERE = Path(".")

    # === 預設值 + session_state 初始化 ===========================

    DEFAULTS = {
        "story_id": "B",   # 故事 B 是 Day 9 講義範例
    }

    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


    def reset_filters():
        for k, v in DEFAULTS.items():
            st.session_state[k] = v


    @st.cache_data
    def load_data():
        summary = pd.read_csv(HERE / "decision_summary.csv", encoding="utf-8-sig")
        supports = pd.read_csv(HERE / "decision_supports.csv", encoding="utf-8-sig")
        risks = pd.read_csv(HERE / "decision_risks.csv", encoding="utf-8-sig")
        return summary, supports, risks


    try:
        summary, supports, risks = load_data()
    except FileNotFoundError as e:
        st.error(
            f"找不到決策表 `{e.filename}`\n\n"
            "請先在 terminal 跑 `python D9_資料整合.py`(讀 D6/D7/D8 三方源 CSV → 生成決策表)"
        )
        st.stop()

    # =============================================================
    # 1. Sidebar
    # =============================================================

    st.sidebar.title("📋 D9 · 給總經理的建議書")
    st.sidebar.caption("沿 Day 9 講義 §3.1 路徑 A · 一頁建議書")

    st.sidebar.radio(
        "選擇故事",
        options=summary["story_id"].tolist(),
        format_func=lambda s: f"故事 {s} · {summary[summary.story_id==s]['story_name'].iloc[0]}",
        key="story_id",
    )

    st.sidebar.button("🔄 重置篩選", on_click=reset_filters)

    story_id = st.session_state["story_id"]
    row = summary[summary.story_id == story_id].iloc[0]
    my_supports = supports[supports.story_id == story_id].reset_index(drop=True)
    my_risks = risks[risks.story_id == story_id].reset_index(drop=True)

    st.sidebar.divider()
    st.sidebar.markdown(f"**承接**:{row['承接']}")
    st.sidebar.markdown(f"**投資回收期**:{row['投資回收期']}")
    st.sidebar.markdown(f"**故事數**:{len(summary)}")
    st.sidebar.markdown(f"**支撐句**:{len(supports)} 條")
    st.sidebar.markdown(f"**風險情境**:{len(risks)} 列")

    # =============================================================
    # 2. 第一屏 — 標題 + 主結論 + 三 KPI 卡片
    # =============================================================

    col_t, col_b1, col_b2, col_b3 = st.columns([0.4, 0.2, 0.2, 0.2])
    with col_t:
        st.title("📋 9 月物流營運建議書")
    with col_b1:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🔗 Day8 供應鏈串接", use_container_width=True):
            st.session_state["_pending_nav"] = "🔗 Day8 供應鏈串接"
            st.rerun()
    with col_b2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("📦 Day6 倉庫整理師", use_container_width=True):
            st.session_state["_pending_nav"] = "📦 Day6 倉庫整理師"
            st.rerun()
    with col_b3:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚚 Day7 遲到偵探", use_container_width=True):
            st.session_state["_pending_nav"] = "🚚 Day7 遲到偵探"
            st.rerun()
    st.caption(f"故事 {story_id} · {row['story_name']} · 承接 {row['承接']}")

    st.success(f"📌 **建議:{row['主結論']}**")

    col1, col2, col3 = st.columns(3)
    col1.metric(row["kpi1_label"], row["kpi1_value"], row["kpi1_delta"])
    col2.metric(row["kpi2_label"], row["kpi2_value"], row["kpi2_delta"], delta_color="inverse")
    col3.metric(row["kpi3_label"], row["kpi3_value"], row["kpi3_delta"])

    st.divider()

    # =============================================================
    # 3. 一張關鍵圖(視故事而定)
    # =============================================================

    st.subheader("🔑 關鍵圖")


    def draw_chart_a():
        """故事 A — Pareto 圖(前 20% SKU 出貨佔比)。"""
        csv_d6 = HERE / "SKU_出貨明細_202509.csv"
        if not csv_d6.exists():
            st.warning("D6 源 CSV 不存在;先到 D6_倉儲WMS 跑 `python D6_資料產生器.py`。")
            return
        d6 = pd.read_csv(csv_d6, encoding="utf-8-sig")
        sku_freq = d6.groupby("SKU").size().sort_values(ascending=False).reset_index(name="picks")
        sku_freq["cum_share"] = sku_freq["picks"].cumsum() / sku_freq["picks"].sum() * 100
        sku_freq["rank_pct"] = (sku_freq.index + 1) / len(sku_freq) * 100

        if PLOTLY_OK:
            fig = px.line(
                sku_freq, x="rank_pct", y="cum_share",
                title="Pareto 圖 · 前 20% SKU 累計出貨佔比",
                labels={"rank_pct": "SKU 累計排名(%)", "cum_share": "累計出貨佔比(%)"},
            )
            # 改用組上算出的真實 80% 交叉點，不用老師寫死的 20%
            actual_x = sku_freq[sku_freq["cum_share"] >= 80].iloc[0]["rank_pct"]
            fig.add_shape(type="line", x0=actual_x, y0=0, x1=actual_x, y1=100,
                          line=dict(color="red", dash="dash"))
            fig.add_shape(type="line", x0=0, y0=80, x1=100, y1=80,
                          line=dict(color="red", dash="dash"))
            fig.add_annotation(x=actual_x, y=80, text=f"實際交叉點 ({actual_x:.0f}%)", showarrow=True, arrowhead=2)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(sku_freq.set_index("rank_pct")["cum_share"])
        st.caption(
            "**為什麼是這張圖**:Pareto 80/20 一張就講完——前 20% SKU 撐 ~80% 出貨,"
            "「儲位重排」必須挑這 20%(其他 80% 重排的邊際效益極小)。"
        )


    def draw_chart_b():
        """故事 B — 各路線 OTD 箱型圖,R-03 顯著偏離。"""
        csv_d7 = HERE / "配送紀錄_202509.csv"
        if not csv_d7.exists():
            st.warning("D7 源 CSV 不存在;先到 D7_TMS 跑 `python D7_資料產生器.py`。")
            return
        d7 = pd.read_csv(csv_d7, encoding="utf-8-sig", parse_dates=["實際到達", "客戶時窗起", "客戶時窗迄"])
        d7["準時"] = ((d7["實際到達"] >= d7["客戶時窗起"])
                      & (d7["實際到達"] <= d7["客戶時窗迄"])
                      & (d7["貨損旗標"] == 0)).astype(int)
        by_route_day = (
            d7.assign(日=d7["實際到達"].dt.date)
              .groupby(["路線代碼", "日"])["準時"].mean().reset_index()
        )
        by_route_day["OTD %"] = by_route_day["準時"] * 100

        if PLOTLY_OK:
            fig = px.box(
                by_route_day, x="路線代碼", y="OTD %",
                color="路線代碼",
                title="各路線每日 OTD 分布(R-03 顯著偏離)",
                points="all",
            )
            fig.add_hline(y=95, line_dash="dash", line_color="red",
                          annotation_text="目標 95%", annotation_position="top right")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(by_route_day.groupby("路線代碼")["OTD %"].mean())
        st.caption(
            "**為什麼是這張圖**:箱型圖一次顯示「中位數 + 散布度」,R-03 整盒顯著低於 95% 目標線,"
            "其他路線基本貼線——這比 9 條折線圖更省一頁,結論一眼看出。"
        )


    def draw_chart_c():
        """故事 C — 各供應商 LT 變異 CV 長條圖,SUP-03 紅標。"""
        pur = HERE / "purchase.csv"
        rec = HERE / "receipt.csv"
        if not (pur.exists() and rec.exists()):
            st.warning("D8 源 CSV 不存在;先到 D8_供應鏈 跑 `python D8_資料產生器.py`。")
            return
        p = pd.read_csv(pur, encoding="utf-8-sig", parse_dates=["下單日"])
        r = pd.read_csv(rec, encoding="utf-8-sig", parse_dates=["實際到貨"])
        pr = p.merge(r, on="採購單號", how="left", suffixes=("_p", "_r"))
        pr["LT"] = (pr["實際到貨"] - pr["下單日"]).dt.days
        sup = pr.groupby("供應商")["LT"].agg(["mean", "std", "count"]).reset_index()
        sup["CV"] = (sup["std"] / sup["mean"]).round(2)
        sup = sup.dropna().sort_values("CV", ascending=False)
        sup["顏色"] = sup["供應商"].apply(
            lambda s: "★ 風險紅標" if s == "SUP-03" else (
                      "穩定夥伴" if s in ("SUP-01", "SUP-02", "SUP-04") else "一般"))

        if PLOTLY_OK:
            fig = px.bar(
                sup, x="供應商", y="CV", color="顏色",
                color_discrete_map={"★ 風險紅標": "#d62728",
                                    "穩定夥伴": "#2ca02c",
                                    "一般": "#7f7f7f"},
                title="各供應商 LT 變異係數 CV(σ/μ · 越高越不穩)",
            )
            fig.add_hline(y=0.30, line_dash="dash", line_color="red",
                          annotation_text="風險門檻 0.30", annotation_position="top right")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(sup.set_index("供應商")["CV"])
        st.caption(
            "**為什麼是這張圖**:CV 是 LT 不穩的單一指標,長條圖一張凸顯 SUP-03 顯著超過 0.30 風險門檻,"
            "比看 8 張供應商個別 LT 折線快得多——「主因可定位」一眼成立。"
        )


    CHART_FN = {"A": draw_chart_a, "B": draw_chart_b, "C": draw_chart_c}
    CHART_FN[story_id]()

    st.divider()

    # =============================================================
    # 4. 三條支撐(摺疊)
    # =============================================================

    st.subheader("📌 三條支撐(MECE)")
    for _, s in my_supports.iterrows():
        icon = {"問題真實存在": "🎯", "主因可定位": "🔍", "解法可行": "🛠"}.get(s["support"], "▍")
        with st.expander(f"{icon} 理由 {s['idx']}:{s['support']}"):
            st.write(s["evidence"])

    st.divider()

    # =============================================================
    # 5. 風險三情境
    # =============================================================

    st.subheader("⚖️ 風險評估(三情境)")
    st.caption(
        "Day 9 反直覺第三點:**沒有風險評估老闆不會 buy-in**。"
        "三情境齊全反而會點頭。"
    )

    risk_view = my_risks[["scenario", "expected", "monthly_万", "action"]].rename(
        columns={"scenario": "情境", "expected": "預期結果",
                 "monthly_万": "月效益(萬)", "action": "對應行動"}
    )
    # 加 emoji 增辨識度(深淺主題都看得到 emoji)
    risk_view["情境"] = risk_view["情境"].map({
        "樂觀": "🟢 樂觀", "悲觀": "🟡 悲觀", "不作為": "🔴 不作為"
    }).fillna(risk_view["情境"])


    def color_scenario(row):
        """深色塊 + 白字,確保深 / 淺主題都看得清(原淺色版本在 dark mode 對比不足)。"""
        style = ""
        label = row["情境"]
        if "樂觀" in label:
            style = "background-color: #2e7d32; color: #ffffff;"      # 深綠
        elif "悲觀" in label:
            style = "background-color: #e65100; color: #ffffff;"      # 深橘
        elif "不作為" in label:
            style = "background-color: #b71c1c; color: #ffffff;"      # 深紅
        return [style] * len(row)


    styled = risk_view.style.apply(color_scenario, axis=1).format({"月效益(萬)": "{:+d}"})
    st.dataframe(styled, hide_index=True, use_container_width=True)

    # 投資回收期 + 自動診斷
    col_a, col_b = st.columns(2)
    with col_a:
        st.info(f"💰 **預估投資回收期:{row['投資回收期']}**")
    with col_b:
        diff = my_risks.loc[my_risks.scenario == "樂觀", "monthly_万"].iloc[0] \
             - my_risks.loc[my_risks.scenario == "不作為", "monthly_万"].iloc[0]
        st.success(f"📈 **樂觀 vs 不作為差距:+{diff} 萬 / 月** · 越大越值得做")

    st.divider()

    # =============================================================
    # 6. 反直覺三點(Day 9 §2.4)
    # =============================================================

    with st.expander("🔄 反直覺三點(Day 9 講義 §2.4) — 老闆心理學"):
        st.markdown("""
    **反直覺第一點:結論先講,證據後上**

    > 學界寫論文是「Background → Method → Result → Discussion」(由下往上),
    > 業界匯報剛好相反:「Conclusion → Reason → Evidence」(由上往下)。
    > 學員在學界念太久,最容易卡這關。

    **反直覺第二點:圖表愈多愈不專業**

    > 一份建議書 ≤ **5 張圖**最有效。每多一張,老闆對「主結論」的信心就降一格——
    > 因為「**這麼多圖你還沒結論,是不是你自己也沒底?**」

    **反直覺第三點:沒有風險評估,老闆不會 buy-in**

    > 你以為老闆怕「失敗的方案」?其實老闆更怕「**沒看見失敗風險的方案**」。
    > 一份建議書必須包含:樂觀情境 + 悲觀情境 + 不作為情境 三條都寫齊,
    > 老闆**反而會點頭**——因為他看到「你想過了」。
    """)

    # =============================================================
    # 7. 跨案比較(三故事 月效益 vs 回收期)
    # =============================================================

    with st.expander("📊 跨案比較 — 三故事月效益與投資回收期"):
        st.caption("把三個候選故事一起看,協助老闆「**做組合決策**」而非單選一個。")
        risks_pos = risks[risks.scenario == "樂觀"].copy()
        cmp_df = summary.merge(
            risks_pos[["story_id", "monthly_万"]], on="story_id"
        )
        cmp_df = cmp_df.rename(columns={"monthly_万": "樂觀月效益(萬)"})
        cmp_view = cmp_df[["story_id", "story_name", "承接",
                           "樂觀月效益(萬)", "投資回收期", "主結論"]]
        st.dataframe(cmp_view, hide_index=True, use_container_width=True)

        if PLOTLY_OK:
            fig = px.scatter(
                cmp_df, x="投資回收期", y="樂觀月效益(萬)",
                color="story_id", text="story_name",
                size="樂觀月效益(萬)", size_max=60,
                title="三故事權衡:左下=慢且小、右上=慢且大、左上=快且大(★)",
            )
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)

    # =============================================================
    # 8. 90 秒 Showtime 腳本(直接 download)
    # =============================================================

    st.subheader("📥 90 秒 Showtime 腳本")

    script_lines = [
        f"# 90 秒 Showtime 腳本 · 故事 {story_id} · {row['story_name']}",
        "",
        "## 0:00-0:30 SCQA 開場",
        f"- **S(共識)**:{row['kpi1_label']} {row['kpi1_value']}({row['kpi1_delta']})",
        f"- **C(衝突)**:{row['kpi2_label']} {row['kpi2_value']}({row['kpi2_delta']})",
        f"- **Q(問題)**:該怎麼處理 {row['kpi3_label']}?",
        f"- **A(建議)**:{row['主結論']}",
        "",
        "## 0:30-1:00 三條支撐(MECE)",
    ]
    for _, s in my_supports.iterrows():
        script_lines.append(f"- **理由 {s['idx']}:{s['support']}** — {s['evidence']}")
    script_lines.append("")
    script_lines.append("## 1:00-1:30 風險三情境 + 結語")
    for _, r in my_risks.iterrows():
        script_lines.append(
            f"- **{r['scenario']}**:{r['expected']} · 月效益 {r['monthly_万']:+d} 萬 → {r['action']}"
        )
    script_lines += [
        "",
        f"投資回收期:{row['投資回收期']}",
        "",
        "**結語**:三條都寫齊了,風險可控。請給我 1 個月的觀察期,不達標即回滾。",
        "",
        "---",
        "_本檔由 D9_決策建議_答案版.py 自動產出_",
    ]
    script_md = "\n".join(script_lines)

    st.code(script_md, language="markdown")
    st.download_button(
        "📥 下載 90 秒 Showtime 腳本 (.md)",
        data=script_md,
        file_name=f"Showtime_腳本_故事{story_id}.md",
        mime="text/markdown",
    )

    st.caption(
        "📌 課堂 Showtime:全班用三色卡投票 🟢 我會點頭 / 🟡 我會追問 / 🔴 我不會點頭"
    )



# ============================================================
# 導覽 · sidebar 選單
# ============================================================
st.sidebar.title("🚚 物流控制塔 v2")

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "📋 Day9 決策簡報"

# 導覽按鈕用 _pending_nav 中繼，要在 radio(key="nav_page") 建立「之前」套用，
# 不然 Streamlit 會擋「widget 綁定的 key 建立後同一輪不能再賦值」
if "_pending_nav" in st.session_state:
    st.session_state.nav_page = st.session_state.pop("_pending_nav")

page = st.sidebar.radio(
    "選擇故事",
    ["📋 Day9 決策簡報", "🔗 Day8 供應鏈串接", "📦 Day6 倉庫整理師", "🚚 Day7 遲到偵探"],
    key="nav_page",
)
st.sidebar.divider()

PAGES = {
    "📦 Day6 倉庫整理師": page_day6,
    "🚚 Day7 遲到偵探": page_day7,
    "🔗 Day8 供應鏈串接": page_day8,
    "📋 Day9 決策簡報": page_day9,
}
PAGES[page]()
