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
  1. 標題旁加 Day6/7/8 導覽按鈕
  2. Pareto 圖交叉線改用真實算出的 80% 交叉點，不用老師寫死的 20%
  3. 準時／OTD 計算加上「貨損旗標==0」，跟 D7 報告版的「完美訂單」口徑對齊
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

# Streamlit 不會自動偵測瀏覽器「上一步/下一步」造成的網址變化去重新整理，
# 要靠這段小 script 監聽 popstate、強制整頁重新載入，讓 FOOTER 讀到新網址的 ?page=
# 用 components.html（不是 st.markdown）是因為 <script> 只有這裡才會真的被執行
components.html(
    """
    <script>
    (function () {
        const top = window.parent;
        if (top.__ctBackListenerAdded) return;
        top.__ctBackListenerAdded = true;
        top.addEventListener('popstate', function () {
            top.location.reload();
        });
    })();
    </script>
    """,
    height=0,
)

'''

FOOTER = '''
# ============================================================
# 導覽 · sidebar 選單
# ============================================================
st.sidebar.title("🚚 物流控制塔 v2")

# 頁面代號跟網址參數對照，讓瀏覽器「上一步/下一步」能還原頁面
PAGE_KEYS = {
    "day9": "📋 Day9 決策簡報",
    "day8": "🔗 Day8 供應鏈串接",
    "day6": "📦 Day6 倉庫整理師",
    "day7": "🚚 Day7 遲到偵探",
}
KEY_BY_LABEL = {v: k for k, v in PAGE_KEYS.items()}

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "📋 Day9 決策簡報"

# 導覽按鈕用 _pending_nav 中繼，要在 radio(key="nav_page") 建立「之前」套用，
# 不然 Streamlit 會擋「widget 綁定的 key 建立後同一輪不能再賦值」
_just_clicked_button = "_pending_nav" in st.session_state
if _just_clicked_button:
    st.session_state.nav_page = st.session_state.pop("_pending_nav")

# 網址列的 ?page=xxx 用來還原瀏覽器上一步/下一步的狀態；
# 但如果這一輪是「剛按了導覽按鈕」，按鈕的選擇比網址列（還沒更新）新，不能被蓋掉
qp_page = st.query_params.get("page")
if (not _just_clicked_button and qp_page in PAGE_KEYS
        and PAGE_KEYS[qp_page] != st.session_state.nav_page):
    st.session_state.nav_page = PAGE_KEYS[qp_page]

page = st.sidebar.radio(
    "選擇故事",
    ["📋 Day9 決策簡報", "🔗 Day8 供應鏈串接", "📦 Day6 倉庫整理師", "🚚 Day7 遲到偵探"],
    key="nav_page",
)
st.sidebar.divider()

# 把目前頁面同步回網址列，這一步會讓瀏覽器「記一筆」，上一步才有東西可以回
_current_key = KEY_BY_LABEL[page]
if st.query_params.get("page") != _current_key:
    st.query_params["page"] = _current_key

PAGES = {
    "📦 Day6 倉庫整理師": page_day6,
    "🚚 Day7 遲到偵探": page_day7,
    "🔗 Day8 供應鏈串接": page_day8,
    "📋 Day9 決策簡報": page_day9,
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
        '    if st.button("🔗 Day8 供應鏈", use_container_width=True):\n'
        '        st.session_state["_pending_nav"] = "🔗 Day8 供應鏈串接"\n'
        '        st.rerun()\n'
        'with col_b2:\n'
        '    st.markdown("<br><br>", unsafe_allow_html=True)\n'
        '    if st.button("📦 Day6 倉儲", use_container_width=True):\n'
        '        st.session_state["_pending_nav"] = "📦 Day6 倉庫整理師"\n'
        '        st.rerun()\n'
        'with col_b3:\n'
        '    st.markdown("<br><br>", unsafe_allow_html=True)\n'
        '    if st.button("🚚 Day7 配送", use_container_width=True):\n'
        '        st.session_state["_pending_nav"] = "🚚 Day7 遲到偵探"\n'
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
    return text


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

    # 4b. Day9 專屬的字串置換（見 patch_day9 說明），組員原始檔不動
    if func == "page_day9":
        text = patch_day9(text)

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
