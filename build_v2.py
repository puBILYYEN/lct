# -*- coding: utf-8 -*-
"""
物流控制塔 v2 合併器
====================
從 W2第6組\ 的四支報告版原始檔，自動合併產生 v2\app.py（stlite 版控制塔）。
原始檔完全不修改。每支只做三個外科手術：
  1. 移除各自的 st.set_page_config（集中到 header，一個 app 只能呼叫一次）
  2. Path(__file__).parent → Path(".")（stlite 虛擬檔案系統的工作目錄；
     保留 Path 型別，讓 `/` 運算與 .exists() 檢查照常運作）
  3. st_folium(m, ...) → components.html(m.get_root().render(), ...)
     （streamlit_folium 元件在 stlite 不能用，folium 本體不受影響）
重跑方式：在 v2\ 資料夾執行  python build_v2.py

Day9 額外有三個「組上想要的改進」，一律用下面的 patch_day9() 字串取代做，
不碰 W2第6組\D9_決策建議_答案版.py 這支組員原始檔（違反規則：除非使用者
主動提出，否則不改組員寫好的儀表板程式）：
  1. 標題旁加導覽按鈕
  2. Pareto 圖交叉線改用真實算出的 80% 交叉點，不用老師寫死的 20%
  3. 準時／OTD 計算加上「貨損旗標==0」，跟 D7 報告版的「完美訂單」口徑對齊
  4. 拿掉風險評估段落說明文字裡的「Day 9 反直覺第三點」字首
  5. 拿掉「反直覺三點」教學用語 expander（給學員看的課程金句，不適合給總經理看）
"""
import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "W2第6組"
OUT = Path(__file__).parent / "app.py"

# header 已提供的 import，從各檔移除（其餘 import 一律保留）
STRIP_IMPORT = re.compile(
    r"^\s*(?:"
    r"import\s+(?:streamlit|pandas|numpy|folium)\b.*"
    r"|import\s+plotly.*"
    r"|from\s+(?:pathlib|plotly|streamlit_folium)\s+import.*"
    r")\s*$"
)

HEADER = '''# -*- coding: utf-8 -*-
"""
物流控制塔 v2 · W2 第6組(Day6-9 合併 stlite 版)
============================================================
由 build_v2.py 從 W2第6組 四支報告版自動合併,原始檔未動。
  📦 Day6 倉庫整理師 · 🚚 Day7 遲到偵探 · 🔗 供應鏈管理串接 · 📋 決策簡報
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
        content: "👈 點開看更多分析";
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

'''

FOOTER = '''
# ============================================================
# 導覽 · sidebar 選單
# ============================================================
st.sidebar.title("🚚 物流控制塔 v2")

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "📋 決策簡報"

# 導覽按鈕用 _pending_nav 中繼，要在 radio(key="nav_page") 建立「之前」套用，
# 不然 Streamlit 會擋「widget 綁定的 key 建立後同一輪不能再賦值」
if "_pending_nav" in st.session_state:
    st.session_state.nav_page = st.session_state.pop("_pending_nav")

page = st.sidebar.radio(
    "選擇故事",
    ["📋 決策簡報", "🔗 供應鏈管理", "📦 倉儲管理", "🚚 物流管理"],
    key="nav_page",
)
st.sidebar.divider()

PAGES = {
    "📦 倉儲管理": page_day6,
    "🚚 物流管理": page_day7,
    "🔗 供應鏈管理": page_day8,
    "📋 決策簡報": page_day9,
}
PAGES[page]()
'''


def patch_day9(text: str) -> str:
    """只用在合併時的字串置換，組員原始檔一律不動。"""
    # 1. 標題旁加 Day6/7/8 導覽按鈕
    text = text.replace(
        'st.title("📋 9 月物流營運建議書")',
        'col_t, col_b1, col_b2, col_b3 = st.columns([0.4, 0.2, 0.2, 0.2])\n'
        'with col_t:\n'
        '    st.title("📋 9 月物流營運建議書")\n'
        'with col_b1:\n'
        '    st.markdown("<br><br>", unsafe_allow_html=True)\n'
        '    if st.button("🔗 供應鏈管理", use_container_width=True):\n'
        '        st.session_state["_pending_nav"] = "🔗 供應鏈管理"\n'
        '        st.rerun()\n'
        'with col_b2:\n'
        '    st.markdown("<br><br>", unsafe_allow_html=True)\n'
        '    if st.button("📦 倉儲管理", use_container_width=True):\n'
        '        st.session_state["_pending_nav"] = "📦 倉儲管理"\n'
        '        st.rerun()\n'
        'with col_b3:\n'
        '    st.markdown("<br><br>", unsafe_allow_html=True)\n'
        '    if st.button("🚚 物流管理", use_container_width=True):\n'
        '        st.session_state["_pending_nav"] = "🚚 物流管理"\n'
        '        st.rerun()',
    )
    # 2. Pareto 交叉線改用真實 80% 交叉點
    text = text.replace(
        'fig.add_shape(type="line", x0=20, y0=0, x1=20, y1=100,\n'
        '                      line=dict(color="red", dash="dash"))',
        '# 改用組上算出的真實 80% 交叉點，不用老師寫死的 20%\n'
        '        actual_x = sku_freq[sku_freq["cum_share"] >= 80].iloc[0]["rank_pct"]\n'
        '        fig.add_shape(type="line", x0=actual_x, y0=0, x1=actual_x, y1=100,\n'
        '                      line=dict(color="red", dash="dash"))',
    )
    text = text.replace(
        'fig.add_annotation(x=20, y=80, text="80/20 交叉點", showarrow=True, arrowhead=2)',
        'fig.add_annotation(x=actual_x, y=80, text=f"實際交叉點 ({actual_x:.0f}%)", showarrow=True, arrowhead=2)',
    )
    # 3. 準時/OTD 加貨損旗標條件，跟 D7 報告版「完美訂單」口徑對齊
    text = text.replace(
        'd7["準時"] = ((d7["實際到達"] >= d7["客戶時窗起"])\n'
        '                  & (d7["實際到達"] <= d7["客戶時窗迄"])).astype(int)',
        'd7["準時"] = ((d7["實際到達"] >= d7["客戶時窗起"])\n'
        '                  & (d7["實際到達"] <= d7["客戶時窗迄"])\n'
        '                  & (d7["貨損旗標"] == 0)).astype(int)',
    )
    # 4b. 拿掉側邊欄「沿 Day 9 講義 §3.1 路徑 A」課程用語說明
    text = text.replace(
        'st.sidebar.caption("沿 Day 9 講義 §3.1 路徑 A · 一頁建議書")\n',
        '',
    )
    # 4. 拿掉「Day 9 反直覺第三點」字首，只留商業說法（風險評估段落上方的說明文字）
    text = text.replace(
        '"Day 9 反直覺第三點:**沒有風險評估老闆不會 buy-in**。"',
        '"**沒有風險評估,老闆不會 buy-in**。"',
    )
    # 5. 拿掉「反直覺三點」教學用語 expander（Day 9 講義金句、給學員看的，不適合給總經理看）
    text = text.replace(
        'with st.expander("🔄 反直覺三點(Day 9 講義 §2.4) — 老闆心理學"):\n'
        '    st.markdown("""\n'
        '**反直覺第一點:結論先講,證據後上**\n'
        '\n'
        '> 學界寫論文是「Background → Method → Result → Discussion」(由下往上),\n'
        '> 業界匯報剛好相反:「Conclusion → Reason → Evidence」(由上往下)。\n'
        '> 學員在學界念太久,最容易卡這關。\n'
        '\n'
        '**反直覺第二點:圖表愈多愈不專業**\n'
        '\n'
        '> 一份建議書 ≤ **5 張圖**最有效。每多一張,老闆對「主結論」的信心就降一格——\n'
        '> 因為「**這麼多圖你還沒結論,是不是你自己也沒底?**」\n'
        '\n'
        '**反直覺第三點:沒有風險評估,老闆不會 buy-in**\n'
        '\n'
        '> 你以為老闆怕「失敗的方案」?其實老闆更怕「**沒看見失敗風險的方案**」。\n'
        '> 一份建議書必須包含:樂觀情境 + 悲觀情境 + 不作為情境 三條都寫齊,\n'
        '> 老闆**反而會點頭**——因為他看到「你想過了」。\n'
        '""")',
        '',
    )
    return text


def patch_day7(text: str) -> str:
    """只用在合併時的字串置換，組員原始檔一律不動。
    「地圖只顯示異常點」checkbox 預設改成打勾——這張地圖的用意是證明異常
    集中在特定路線（R-03），紅綠點全開反而讓聚集現象被稀釋，預設只顯示
    異常點才能讓重點一眼跳出來。使用者仍可自己取消勾選看全部點。
    """
    text = text.replace(
        'show_only_anomaly = st.sidebar.checkbox("地圖只顯示異常點", value=False)',
        'show_only_anomaly = st.sidebar.checkbox("地圖只顯示異常點", value=True)',
    )
    return text


def patch_day8(text: str) -> str:
    """只用在合併時的字串置換，組員原始檔一律不動。
    拿掉「品類內 LT 變異對照」圖——跟 Tab1 全公司 LT 變異圖同一個指標、只是
    範圍縮小到同品類，數字其實已經在上面的資料表裡看得到，屬於重複視覺化。
    砍掉這張後全頁圖表數從 6 降到 5，符合「一份建議書 ≤ 5 張圖」原則。
    """
    text = text.replace(
        '    col_c, col_d = st.columns(2)\n'
        '    with col_c:\n'
        '        st.markdown(f"##### {cat_pick} 品類 · LT 變異對照")\n'
        '        sub_lt = sub.sort_values("LT變異")\n'
        '        fig5 = px.bar(sub_lt, x="供應商", y="LT變異",\n'
        '                      color="LT變異", color_continuous_scale="Reds",\n'
        '                      text=sub_lt["LT變異"].round(2))\n'
        '        fig5.add_hline(y=0.30, line_dash="dash", line_color="red", annotation_text="0.30 警戒")\n'
        '        fig5.update_traces(textposition="outside")\n'
        '        fig5.update_layout(height=380, margin=dict(t=20, b=10))\n'
        '        st.plotly_chart(fig5, use_container_width=True)\n'
        '    with col_d:\n',
        '    with st.container():\n',
    )
    return text


def append_risk_block(text: str, story_id: str) -> str:
    """在頁面最下方加一段「樂觀/悲觀/不作為」風險提示，直接讀 Day9 用的
    decision_risks.csv（同一份已驗證真數字），三頁故事各對應 A/B/C 一列。
    只用在合併時附加，組員原始檔一律不動。
    """
    return text.rstrip("\n") + (
        '\n\n'
        'st.divider()\n'
        'st.subheader("⚖️ 風險評估(樂觀 / 悲觀 / 不作為)")\n'
        '_risks_all = pd.read_csv("decision_risks.csv", encoding="utf-8-sig")\n'
        f'_risks_here = _risks_all[_risks_all.story_id == "{story_id}"]\n'
        '_icon_map = {"樂觀": "🟢", "悲觀": "🟡", "不作為": "🔴"}\n'
        '_risk_cols = st.columns(3)\n'
        'for _rc, (_, _rr) in zip(_risk_cols, _risks_here.iterrows()):\n'
        '    with _rc:\n'
        '        st.markdown(f"**{_icon_map.get(_rr[\'scenario\'], \'\')} {_rr[\'scenario\']}**")\n'
        '        st.caption(_rr["expected"])\n'
        '        st.metric("月效益(萬)", f"{_rr[\'monthly_万\']:+d}")\n'
        '        st.caption(_rr["action"])\n'
    )


def clean(fname: str, func: str) -> str:
    text = (SRC / fname).read_text(encoding="utf-8-sig")

    # 1a. set_page_config 單行形式（D8）
    text = re.sub(r"^st\.set_page_config\(.*\)[ \t]*\n", "", text, flags=re.MULTILINE)
    # 1b. set_page_config 多行形式（D6/D7/D9，結尾 ")" 獨立一行）
    text = re.sub(r"st\.set_page_config\([\s\S]*?\n\)[ \t]*\n", "", text)

    # 2. 移除 header 已涵蓋的 import（含 try 區塊內縮排的）
    lines = [l for l in text.split("\n") if not STRIP_IMPORT.match(l)]
    text = "\n".join(lines)

    # 3. Path 基準改成工作目錄，其餘路徑運算保持原樣
    text = text.replace("Path(__file__).parent", 'Path(".")')

    # 4. st_folium → components.html
    text = re.sub(
        r"st_folium\(\s*m\s*,[^)]*\)",
        'components.html(m.get_root().render(), height=540, scrolling=True)',
        text,
    )

    # 4a. Day7 專屬的字串置換（見 patch_day7 說明），組員原始檔不動
    if func == "page_day7":
        text = patch_day7(text)

    # 4b. Day9 專屬的字串置換（見 patch_day9 說明），組員原始檔不動
    if func == "page_day9":
        text = patch_day9(text)

    # 4d. 各頁最下方加風險提示（見 append_risk_block 說明），組員原始檔不動
    STORY_ID_BY_FUNC = {"page_day6": "A", "page_day7": "B", "page_day8": "C"}
    if func in STORY_ID_BY_FUNC:
        text = append_risk_block(text, STORY_ID_BY_FUNC[func])

    # 5. 包成 page 函式（整段縮排 4 空格）
    body = "\n".join(("    " + l) if l.strip() else "" for l in text.split("\n"))
    return f"def {func}():\n{body}\n\n"


parts = [HEADER]
parts.append(clean("D6_儲位重排_報告版.py", "page_day6"))
parts.append(clean("D7_遲到偵探_報告版.py", "page_day7"))
parts.append(clean("D8_供應商儀表板_報告版.py", "page_day8"))
parts.append(clean("D9_決策建議_答案版.py", "page_day9"))
parts.append(FOOTER)

OUT.write_text("".join(parts), encoding="utf-8")
print(f"OK: 已產生 {OUT}（{OUT.stat().st_size:,} bytes）")

# 自檢：殘留檢查
merged = OUT.read_text(encoding="utf-8")
checks = {
    "st_folium 殘留": merged.count("st_folium("),
    "set_page_config 次數(應=1)": merged.count("st.set_page_config"),
    "Path(__file__) 殘留": merged.count("Path(__file__)"),
    "page 函式數(應=4)": len(re.findall(r"^def page_day\d", merged, re.M)),
    "components.html 次數": merged.count("components.html("),
}
for k, v in checks.items():
    print(f"  {k}: {v}")
