import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 設定頁面資訊 ---
st.set_page_config(page_title="宇毛的財務中控台", page_icon="💰", layout="wide")

# --- CSS 極致美化 (v19.4 Layout Polish) ---
st.markdown("""
<style>
    /* === 1. 全局基礎設定 === */
    .stApp {
        background-color: #0e1117 !important;
        color: #fafafa !important;
    }
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }

    /* === 2. 萬用卡片樣式 === */
    .custom-card {
        background-color: #262730 !important;
        padding: 20px !important;
        border-radius: 15px !important;
        border: 1px solid rgba(250, 250, 250, 0.1) !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
        margin-bottom: 15px;
    }
    .card-title { font-size: 14px; color: rgba(250, 250, 250, 0.7); font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .card-value { font-size: 28px; font-weight: 800; color: #ffffff; margin-bottom: 5px; }
    .card-note { font-size: 12px; font-weight: 500; opacity: 0.9; }

    /* === 3. 進度條 === */
    .progress-bg { width: 100%; height: 6px; background-color: rgba(255,255,255,0.1); border-radius: 3px; margin-top: 12px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 3px; }

    /* === 4. 資產小方塊 (字體強化) === */
    .asset-box {
        background-color: #1f2937 !important; padding: 15px; border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1); text-align: center; margin-bottom: 10px;
    }
    .asset-num {
        font-size: 24px; font-weight: 800; color: #ffffff;
        font-family: 'Roboto Mono', 'Courier New', monospace; /* 數字專用字體 */
        margin-bottom: 4px;
    }
    .asset-desc { font-size: 12px; opacity: 0.6; font-weight: 600; }

    /* === 5. 列表項目 (滿版外框修正) === */
    .list-row {
        background-color: #1f2937 !important;
        padding: 16px 20px;
        border-radius: 12px;
        margin-bottom: 4px; /* 稍微拉近與開關的距離 */
        border: 1px solid rgba(255,255,255,0.1);
        display: flex;
        justify-content: space-between; /* 左右撐開 */
        align-items: center;
        height: 100%;
        min-height: 70px;
    }
    .list-left { display: flex; flex-direction: column; gap: 4px; }
    .list-right { text-align: right; }

    /* === 6. 標籤 Badge === */
    .status-badge { padding: 3px 8px; font-size: 10px; font-weight: 700; border-radius: 6px; display: inline-block;}

    /* === 7. 按鈕與輸入框優化 === */
    .stButton > button { border-radius: 10px !important; border: none !important; font-weight: bold; }
    /* 紅色刪除按鈕 (Primary) */
    .stButton > button[kind="primary"] {
        background-color: #ef4444 !important; color: white !important;
    }
    .stTextInput > div > div > input { background-color: #1f2937 !important; color: white !important; border-radius: 10px; }
    
    /* 側邊欄 */
    section[data-testid="stSidebar"] { background-color: #111827 !important; }
    
    /* 收支模型標題 */
    .model-header {
        font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.5);
        margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 連接 Google Sheets ---
@st.cache_resource
def connect_to_gsheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    return gspread.authorize(creds).open("宇毛的財務追蹤表_2026")

try: sh = connect_to_gsheet()
except: st.stop()

# --- 讀取資料 ---
def get_data(ws_name, head=1):
    try:
        ws = sh.worksheet(ws_name)
        return pd.DataFrame(ws.get_all_records(head=head)), ws
    except: return pd.DataFrame(), None

# --- UI 元件 ---
def make_card(title, value, note, color="gray", progress=None):
    colors = {"blue": "#60a5fa", "red": "#f87171", "green": "#34d399", "orange": "#fbbf24", "gray": "#9ca3af", "purple": "#a78bfa"}
    c_hex = colors.get(color, "#9ca3af")
    prog_html = f'<div class="progress-bg"><div class="progress-fill" style="width: {min(max(float(progress or 0),0),1)*100}%; background-color: {c_hex};"></div></div>' if progress is not None else ""
    return f"""<div class="custom-card"><div class="card-title" style="color:{c_hex}">{title}</div><div class="card-value">{value}</div><div class="card-note" style="color:{c_hex}">{note}</div>{prog_html}</div>"""

def make_badge(text, color="gray"):
    c_map = {"green": ("rgba(16, 185, 129, 0.2)", "#34d399"), "red": ("rgba(239, 68, 68, 0.2)", "#f87171"), "blue": ("rgba(59, 130, 246, 0.2)", "#60a5fa"), "purple": ("rgba(139, 92, 246, 0.2)", "#a78bfa"), "gray": ("rgba(107, 114, 128, 0.2)", "#d1d5db")}
    bg, fg = c_map.get(color, c_map["gray"])
    return f'<span class="status-badge" style="background-color:{bg}; color:{fg};">{text}</span>'

# ==========================================
# 🚀 資料準備
# ==========================================
now_dt = datetime.now()
current_month = now_dt.month
current_day = now_dt.day
current_year = now_dt.year

df_log, ws_log = get_data("流動支出日記帳", head=4)
df_assets, ws_assets = get_data("資產總覽表")
df_status, ws_status = get_data("現況資金檢核")
df_future, _ = get_data("未來四個月推估")

if not df_log.empty and '已入帳' not in df_log.columns: df_log['已入帳'] = '已入帳'

# 缺口 B9
try:
    if ws_status: base_gap_static = int(str(ws_status.cell(9, 2).value).replace(',', ''))
    else: base_gap_static = -9999
except: base_gap_static = -9999

# 計算數據
total_variable_expenses = 0
pending_debt = 0
current_month_logs = pd.DataFrame()

if not df_log.empty:
    def robust_month_parser(x):
        try: return pd.to_datetime(str(x), format='%m/%d').month
        except:
            try: return pd.to_datetime(str(x)).month
            except: return current_month 

    df_log['Month'] = df_log['日期'].apply(robust_month_parser)
    current_month_logs = df_log[df_log['Month'] == current_month].copy()
    current_month_logs['實際消耗'] = pd.to_numeric(current_month_logs['實際消耗'], errors='coerce').fillna(0)
    current_month_logs['金額'] = pd.to_numeric(current_month_logs['金額'], errors='coerce').fillna(0)
    current_month_logs['項目'] = current_month_logs['項目'].astype(str)
    
    v_mask = (current_month_logs['實際消耗'] > 0) & (current_month_logs['是否報帳'] != '固定')
    total_variable_expenses = int(current_month_logs[v_mask]['實際消耗'].sum())
    p_mask = (current_month_logs['是否報帳'] == '是') & (current_month_logs['已入帳'] == '未入帳')
    pending_debt = int(current_month_logs[p_mask]['金額'].sum())

current_gap = base_gap_static
base_budget = 97 if current_month == 2 else 2207
surplus_from_gap = max(0, current_gap)
remaining = (base_budget + surplus_from_gap) - total_variable_expenses

# 同步函式
def sync_update(amount_change):
    if not ws_assets or not ws_status: return
    try:
        all_assets = ws_assets.get_all_records()
        new_twd = 0
        for i, r in enumerate(all_assets):
            if r.get('資產項目') == '台幣活存':
                curr = int(str(r.get('目前價值', 0)).replace(',', ''))
                new_twd = curr + amount_change
                ws_assets.update_cell(i+2, 2, new_twd)
                break
        ws_status.update_cell(6, 2, new_twd)
        curr_gap = int(str(ws_status.cell(9, 2).value).replace(',', ''))
        ws_status.update_cell(9, 2, curr_gap + amount_change)
    except: pass

# ==========================================
# 側邊欄
# ==========================================
st.sidebar.title("🚀 功能選單")

def check_logged(keyword):
    if current_month_logs.empty: return False
    return current_month_logs['項目'].astype(str).str.contains(keyword, case=False).any()

def execute_auto_entry(name, amount, type_code="固定", is_transfer=False):
    if not ws_log: return
    date_str = now_dt.strftime("%m/%d")
    
    if name == "自我分期(還債)":
        ws_log.append_row([date_str, name, amount, "固定", 0, "固定扣款"])
        if ws_status:
            try: 
                cur_gap = int(str(ws_status.cell(9, 2).value).replace(',', ''))
                ws_status.update_cell(9, 2, cur_gap + amount)
            except: pass
        st.toast(f"✅ {name} 已執行！"); time.sleep(1); st.rerun(); return

    if is_transfer:
        try:
            all = ws_assets.get_all_records()
            twd_r, fix_r, twd_v, fix_v = -1, -1, 0, 0
            for i, r in enumerate(all):
                if r.get('資產項目') == '台幣活存': twd_r=i+2; twd_v=int(str(r.get('目前價值',0)).replace(',',''))
                if r.get('資產項目') == '定存累計': fix_r=i+2; fix_v=int(str(r.get('目前價值',0)).replace(',',''))
            if twd_r!=-1:
                ws_assets.update_cell(twd_r, 2, twd_v - amount)
                ws_assets.update_cell(fix_r, 2, fix_v + amount)
                if ws_status: ws_status.update_cell(6, 2, twd_v - amount)
                ws_log.append_row([date_str, name, amount, "固定", 0, "固定扣款"])
                st.toast("✅ 定存轉帳完成"); time.sleep(1); st.rerun()
        except: pass
        return

    is_inc = (type_code == "固定收入")
    change = amount if is_inc else -amount
    ws_log.append_row([date_str, name, amount, "固定", 0, "固定扣款"])
    sync_update(change)
    st.toast("✅ 已記錄"); time.sleep(1); st.rerun()

pending_tasks = []
if current_day >= 5 and not check_logged("固定收入"): pending_tasks.append({"name": "📥 入帳薪水 ($3900)", "type": "fixed_in", "amt": 3900, "desc": "固定收入 (薪水)"})
if current_day >= 10 and not check_logged("定存扣款"): pending_tasks.append({"name": "🏦 轉存定存 ($1000)", "type": "transfer", "amt": 1000, "desc": "定存扣款"})
if current_day >= 10 and not check_logged("電信費"): pending_tasks.append({"name": "📱 繳電信費 ($499)", "type": "fixed_out", "amt": 499, "desc": "電信費"})
if current_day >= 22 and not check_logged("YT Premium"): pending_tasks.append({"name": "▶️ 繳 YT Premium ($119)", "type": "fixed_out", "amt": 119, "desc": "YT Premium"})
if (current_year < 2026 or (current_year == 2026 and current_month < 7)) and current_day >= 6 and not check_logged("小雪"): pending_tasks.append({"name": "❄️ 繳小雪會員 ($75)", "type": "fixed_out", "amt": 75, "desc": "YT會員(小雪)"})
if (current_year < 2026 or (current_year == 2026 and current_month <= 7)) and current_day >= 5 and not check_logged("自我分期"): pending_tasks.append({"name": "💳 自我分期還債 ($2110)", "type": "fixed_out", "amt": 2110, "desc": "自我分期(還債)"})

if pending_tasks:
    st.sidebar.info(f"🔔 待辦事項 ({len(pending_tasks)})")
    for t in pending_tasks:
        if st.sidebar.button(t["name"], key=t["desc"]):
            typ = "固定收入" if t["type"]=="fixed_in" else "固定支出"
            is_tr = (t["type"]=="transfer")
            execute_auto_entry(t["desc"], t["amt"], typ, is_tr)
    st.sidebar.markdown("---")

page = st.sidebar.radio("請選擇功能", ["💸 隨手記帳 (本月)", "🛍️ 購物冷靜清單", "📊 資產與收支", "📅 未來推估", "🗓️ 歷史帳本回顧"])
st.sidebar.markdown("---")
st.sidebar.caption("宇毛的記帳本 v19.4 (Layout Perfect)")

# ==========================================
# 🏠 頁面 1：隨手記帳
# ==========================================
if page == "💸 隨手記帳 (本月)":
    st.subheader(f"👋 {current_month} 月財務面板")
    
    c1, c2, c3, c4 = st.columns(4)
    gap_note = "收入優先抵債" if current_gap < 0 else "溢出至額度"
    gap_color = "orange" if current_gap < 0 else "green"
    try: gap_pct = 1.0 - (abs(current_gap) / 3000)
    except: gap_pct = 0
    rem_color = "green"
    if remaining < 0: rem_color = "red"
    elif remaining < 50: rem_color = "orange"

    with c1: st.markdown(make_card(f"{current_month}月本金", f"${base_budget}", "固定額度", "blue"), unsafe_allow_html=True)
    with c2: st.markdown(make_card("本月花費", f"${total_variable_expenses}", "僅計流動支出", "gray"), unsafe_allow_html=True)
    with c3: st.markdown(make_card("目前可用", f"${remaining}", "資金安全" if remaining>=0 else "已透支", rem_color), unsafe_allow_html=True)
    with c4: st.markdown(make_card("總透支缺口", f"${current_gap}", gap_note, gap_color, progress=gap_pct), unsafe_allow_html=True)

    if pending_debt > 0: st.caption(f"ℹ️ 包含 ${pending_debt} 未入帳的代墊款。")
    if remaining < 0: st.error("🚨 警告：本月已透支！請停止支出！")

    st.markdown("---")
    st.subheader("📝 新增交易")
    txn_type = st.radio("類型", ["💸 支出", "💰 收入"], horizontal=True)
    
    with st.form("add_txn", clear_on_submit=True):
        col1, col2 = st.columns([1, 2])
        d_in = col1.date_input("日期", datetime.now())
        n_in = col2.text_input("項目", placeholder="例如: 午餐")
        col3, col4 = st.columns(2)
        a_in = col3.number_input("金額", min_value=1, step=1)
        is_reim = "否"
        target = ""
        
        if "支出" in txn_type:
            is_reim = col4.radio("是否代墊?", ["否", "是"], horizontal=True)
            if is_reim == "是": target = st.text_input("幫誰代墊?", placeholder="Andy")
        else: st.caption("ℹ️ 收入預設 **未入帳**")
            
        if st.form_submit_button("確認記帳", use_container_width=True, type="primary") and ws_log:
            if n_in and a_in > 0:
                d_str = d_in.strftime("%m/%d")
                final_name = f"{n_in} ({target})" if target else n_in
                
                if "支出" in txn_type:
                    act = a_in
                    sta = "未入帳" if is_reim == "是" else "已入帳"
                    ws_log.append_row([d_str, final_name, a_in, is_reim, act, sta])
                    sync_update(-a_in)
                    st.toast(f"💸 支出已記：${a_in}")
                else:
                    ws_log.append_row([d_str, final_name, a_in, "收入", 0, "未入帳"])
                    st.toast(f"💰 收入已記 (未入帳)：${a_in}")
                time.sleep(1); st.rerun()

    if not current_month_logs.empty:
        st.markdown("### 📜 本月明細")
        for i, (idx, row) in enumerate(current_month_logs.iloc[::-1].iterrows()):
            real_idx = idx + 5 
            cls = "一般"
            if row['是否報帳'] == "是": cls = "報帳/代墊"
            elif row['是否報帳'] == "收入": cls = "收入"
            elif row['是否報帳'] == "固定": cls = "固定收支"
            
            sta = str(row.get('已入帳', '已入帳')).strip() or "已入帳"
            
            b_clr, t_clr, pfx = "gray", "#e5e7eb", "$"
            if cls == "收入": b_clr, t_clr, pfx = "green" if sta=="已入帳" else "gray", "#34d399" if sta=="已入帳" else "#e5e7eb", "+$"
            elif cls == "報帳/代墊": b_clr, t_clr = "purple" if sta=="未入帳" else "gray", "#a78bfa" if sta=="未入帳" else "#e5e7eb"
            elif cls == "固定收支": b_clr, t_clr = "blue", "#60a5fa"
            else: t_clr, pfx = "#f87171", "-$"

            # Layout: 資訊列(包含金額) + 開關
            with st.container():
                c_content, c_toggle = st.columns([5, 1])
                
                with c_content:
                    st.markdown(f"""
                    <div class="list-row">
                        <div class="list-left">
                            <span style="font-size:0.85em; opacity:0.6;">{row['日期']}</span>
                            <span style="font-weight:700; font-size:1.05em;">{row['項目']}</span>
                            <div>{make_badge(sta, b_clr)} <span style="font-size:0.8em; opacity:0.5;">{cls}</span></div>
                        </div>
                        <div class="list-right">
                            <span style="color:{t_clr}; font-weight:800; font-size:1.3em;">{pfx}{row['金額']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with c_toggle:
                    # 垂直置中 toggle
                    st.write("") 
                    if cls in ["報帳/代墊", "收入"]:
                        is_clr = (sta == "已入帳")
                        lbl = "已結清" if "報帳" in cls else "入帳"
                        if st.toggle(lbl, value=is_clr, key=f"tg_{idx}") != is_clr:
                            new_state = not is_clr
                            new_s = "已入帳" if new_state else "未入帳"
                            new_act, chg = 0, 0
                            
                            if "報帳" in cls:
                                new_act = 0 if new_state else row['金額']
                                chg = row['金額'] if new_state else -row['金額']
                            elif cls == "收入":
                                new_act = -row['金額'] if new_state else 0
                                chg = row['金額'] if new_state else -row['金額']
                            
                            if chg != 0: sync_update(chg)
                            ws_log.update_cell(real_idx, 5, new_act)
                            ws_log.update_cell(real_idx, 6, new_s)
                            st.success("已更新"); time.sleep(0.5); st.rerun()
        st.markdown("---")

# ==========================================
# 🛍️ 頁面 2：購物冷靜清單
# ==========================================
elif page == "🛍️ 購物冷靜清單":
    st.subheader("🧊 購物冷靜清單")
    df_shop, ws_shop = get_data("購物冷靜清單")
    tot = sum([int(str(r.get('預估價格',0)).replace(',','')) for i,r in df_shop.iterrows()]) if not df_shop.empty else 0
    
    c1, c2 = st.columns(2)
    with c1: st.markdown(make_card("清單總項數", f"{len(df_shop)} 項", "慾望清單", "blue"), unsafe_allow_html=True)
    with c2: st.markdown(make_card("預估總金額", f"${tot:,}", "需存錢目標", "orange"), unsafe_allow_html=True)
    st.markdown("---")
    
    with st.expander("➕ 新增願望"):
        with st.form("add_shop"):
            c1, c2 = st.columns(2)
            n = c1.text_input("物品"); p = c2.number_input("價格", min_value=0)
            if st.form_submit_button("加入") and ws_shop:
                ws_shop.append_row([datetime.now().strftime("%m/%d"), n, p, "3", "2026/07/01", "延後", ""])
                st.success("已加入"); time.sleep(1); st.rerun()
    
    if not df_shop.empty:
        st.markdown("### 📦 明細")
        for i, row in df_shop.iterrows():
            n = row.get('物品名稱', '未命名'); p = row.get('預估價格', 0); d = row.get('最終決策', '考慮'); nt = row.get('備註', '')
            with st.expander(f"🛒 **{n}** - ${p}"):
                c1, c2 = st.columns([4, 1])
                with c1:
                    # 美化決策與備註
                    st.markdown(f"""
                    <div style="margin-bottom:8px;">
                        {make_badge(d, 'red' if d=='延後' else 'green')}
                        <span style="opacity:0.7; margin-left:10px;">{nt}</span>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.button("🗑️ 刪除", key=f"del_{i}", type="primary"): 
                        ws_shop.delete_rows(i+2); st.toast("已刪除"); time.sleep(1); st.rerun()

# ==========================================
# 📊 頁面 3：資產與收支
# ==========================================
elif page == "📊 資產與收支":
    st.subheader("💰 資產狀況")
    if not df_assets.empty:
        ad = dict(zip(df_assets['資產項目'], df_assets['目前價值']))
        tot = int(str(ad.get('總資產', 0)).replace(',',''))
        st.markdown(make_card("目前總身價", f"${tot:,}", "含所有資產", "blue"), unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"""<div class="asset-box"><div class="asset-num">${ad.get('台幣活存',0)}</div><div class="asset-desc">🇹🇼 台幣活存</div></div>""", unsafe_allow_html=True)
        with c2: st.markdown(f"""<div class="asset-box"><div class="asset-num">¥{ad.get('日幣帳戶',0)}</div><div class="asset-desc">🇯🇵 日幣帳戶</div></div>""", unsafe_allow_html=True)
        with c3: st.markdown(f"""<div class="asset-box"><div class="asset-num">${ad.get('定存累計',0)}</div><div class="asset-desc">🏦 定存累計</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📉 每月固定收支")
    df_model, _ = get_data("每月收支模型")
    if not df_model.empty:
        # 分類顯示
        incomes = df_model[df_model['金額 (B)'].astype(str).str.contains("-") == False]
        expenses = df_model[df_model['金額 (B)'].astype(str).str.contains("-") == True]
        
        st.markdown('<div class="model-header">🟢 固定收入</div>', unsafe_allow_html=True)
        for i, row in incomes.iterrows():
            if "總計" not in str(row['項目 (A)']) and "剩餘" not in str(row['項目 (A)']) and str(row.get('金額 (B)','')).strip():
                st.markdown(f"""<div class="list-row"><b>{row['項目 (A)']}</b><b style="color:#34d399;">${row['金額 (B)']}</b></div>""", unsafe_allow_html=True)
        
        st.markdown('<div class="model-header">🔴 固定支出</div>', unsafe_allow_html=True)
        for i, row in expenses.iterrows():
            if "總計" not in str(row['項目 (A)']) and str(row.get('金額 (B)','')).strip():
                st.markdown(f"""<div class="list-row"><b>{row['項目 (A)']}</b><b style="color:#f87171;">${row['金額 (B)']}</b></div>""", unsafe_allow_html=True)
        
        st.markdown('<div class="model-header">📊 結算</div>', unsafe_allow_html=True)
        try:
            exp_tot = df_model[df_model['項目 (A)'].str.contains("支出總計")]['金額 (B)'].values[0]
            net_bal = df_model[df_model['項目 (A)'].str.contains("每月淨剩餘")]['金額 (B)'].values[0]
            st.markdown(f"""
            <div class="summary-box">
                <div><div style="font-size:12px;opacity:0.7;">支出總計</div><div style="font-size:20px;font-weight:bold;color:#f87171;">${exp_tot}</div></div>
                <div style="text-align:right;"><div style="font-size:12px;opacity:0.7;">固定餘額</div><div style="font-size:20px;font-weight:bold;color:#2dce89;">${net_bal}</div></div>
            </div>""", unsafe_allow_html=True)
        except: pass

# ==========================================
# 📅 頁面 4：未來推估
# ==========================================
elif page == "📅 未來推估":
    st.subheader("🔮 財務預測")
    if not df_future.empty:
        valid_df = df_future[~df_future['月份 (A)'].astype(str).str.contains("初始")]
        cols = st.columns(3)
        for i, (idx, row) in enumerate(valid_df.iterrows()):
            with cols[i % 3]:
                st.markdown(f"""<div class="asset-box"><div style="font-weight:bold;margin-bottom:5px;">{row['月份 (A)']}</div><div style="font-size:12px;opacity:0.7;">目標: ${row['目標應有餘額 (E)']}</div><div style="font-size:18px;color:#a78bfa;font-weight:800;">${row['預估實際餘額 (D)']}</div></div>""", unsafe_allow_html=True)
        try:
            last = valid_df.iloc[-1]
            st.markdown("---")
            st.markdown(make_card(f"🎉 {last['月份 (A)']} 最終預估", f"${last['預估實際餘額 (D)']}", "財務自由起點", "purple"), unsafe_allow_html=True)
        except: pass

elif page == "🗓️ 歷史帳本回顧":
    st.subheader("🗓️ 歷史帳本")
    if not df_log.empty:
        ms = sorted([m for m in df_log['Month'].unique() if m > 0])
        if ms:
            sel = st.selectbox("月份", ms, index=len(ms)-1)
            h = df_log[df_log['Month'] == sel]
            st.markdown(make_card(f"{sel}月 淨支出", f"${int(h['實際消耗'].sum())}", "含收入抵銷後", "gray"), unsafe_allow_html=True)
            for i, r in h.iloc[::-1].iterrows():
                c = "#34d399" if r['實際消耗'] < 0 else "#f87171"
                st.markdown(f"""<div class="list-row"><div><span style="font-size:0.8em;opacity:0.6;">{r['日期']}</span> <b>{r['項目']}</b></div><div style="color:{c};font-weight:bold;">${r['金額']}</div></div>""", unsafe_allow_html=True)
