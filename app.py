import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import re

# --- 設定頁面資訊 ---
st.set_page_config(page_title="宇毛的財務中控台", page_icon="💰", layout="wide")

# --- CSS 極致美化 (v29.0 LPM Integration) ---
st.markdown("""
<style>
    /* === 1. 全局變數與基礎 === */
    :root {
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
        --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    @media (prefers-color-scheme: light) {
        :root {
            --glass-bg: rgba(255, 255, 255, 0.6);
            --glass-border: rgba(0, 0, 0, 0.1);
            --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
        }
    }

    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
    }
    
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    .block-container { padding-top: 3rem; padding-bottom: 5rem; }

    /* === 2. 側邊欄 (手機版強制實色修復) === */
    section[data-testid="stSidebar"] {
        background-color: #262730 !important; 
        border-right: 1px solid rgba(255,255,255,0.1) !important;
        box-shadow: 5px 0 20px rgba(0,0,0,0.5) !important;
        z-index: 999999 !important;
    }
    section[data-testid="stSidebar"] > div {
        background-color: #262730 !important;
    }

    @media (prefers-color-scheme: light) {
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {
            background-color: #f0f2f6 !important;
            border-right: 1px solid rgba(0,0,0,0.1) !important;
            box-shadow: 5px 0 20px rgba(0,0,0,0.1) !important;
        }
    }
    
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] p {
        color: var(--text-color) !important;
    }
    
    section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] button {
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--glass-border) !important;
    }

    /* === 3. Liquid Glass 卡片風格 === */
    .custom-card {
        background: var(--glass-bg) !important;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        padding: 16px !important;
        border-radius: 16px !important;
        border: 1px solid var(--glass-border) !important;
        box-shadow: var(--glass-shadow) !important;
        margin-bottom: 24px !important;
        height: 100%;
        display: flex; flex-direction: column; justify-content: space-between;
        transition: transform 0.2s;
    }
    .custom-card:hover { transform: translateY(-2px); }
    
    .card-title { font-size: 13px; color: var(--text-color); opacity: 0.7; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .card-value { font-size: 24px; font-weight: 800; color: var(--text-color); margin-bottom: 5px; white-space: nowrap; }
    .card-note { font-size: 11px; font-weight: 600; opacity: 0.9; color: var(--text-color); }

    /* === 4. 列表與其他元件 === */
    .list-row, .asset-box {
        background: var(--glass-bg) !important;
        backdrop-filter: blur(8px);
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px;
        padding: 12px 20px; margin-bottom: 8px;
    }
    .list-row { display: flex; justify-content: space-between; align-items: center; min-height: 70px; }
    .asset-box { padding: 15px; text-align: center; margin-bottom: 10px; }

    .list-left { display: flex; flex-direction: column; gap: 4px; }
    .list-right { text-align: right; }
    .list-amt { font-size: 20px; font-weight: 800; font-family: 'Roboto Mono', monospace; color: var(--text-color); }
    .asset-num { font-size: 26px; font-weight: 800; font-family: 'Roboto Mono', monospace; margin-bottom: 4px; color: var(--text-color); }
    .asset-desc { font-size: 12px; opacity: 0.6; font-weight: 600; color: var(--text-color); }

    /* === 5. 進度條 & Badge === */
    .progress-bg { width: 100%; height: 6px; background-color: rgba(128, 128, 128, 0.2); border-radius: 3px; margin-top: 12px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 3px; }
    .status-badge { padding: 4px 0px; width: 60px; font-size: 11px; font-weight: 700; border-radius: 20px; display: inline-block; margin-right: 8px; text-align: center; vertical-align: middle; line-height: 1.2; }

    /* === 6. 其他 UI 優化 === */
    .model-header { font-size: 14px; font-weight: 700; color: var(--text-color); opacity: 0.6; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid var(--glass-border); padding-bottom: 5px; }
    
    .summary-box {
        background: linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%);
        color: white; padding: 24px; border-radius: 20px; margin-top: 30px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: center;
    }
    .summary-val { font-size: 24px; font-weight: 800; font-family: 'Roboto Mono', monospace; }

    .stButton > button { border-radius: 10px !important; font-weight: bold; background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-color); }
    .stButton > button[kind="primary"] { background-color: #ef4444 !important; color: white !important; border: none !important; }
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div { background-color: transparent !important; border: 1px solid var(--glass-border); border-radius: 10px; color: var(--text-color) !important; }
    
    header[data-testid="stHeader"] { z-index: 100000; background-color: transparent; }
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
    colors = {"blue": "#60a5fa", "red": "#f87171", "green": "#34d399", "orange": "#fbbf24", "gray": "var(--text-color)", "purple": "#a78bfa"}
    c_hex = colors.get(color, "var(--text-color)")
    prog_html = f'<div class="progress-bg"><div class="progress-fill" style="width: {min(max(float(progress or 0),0),1)*100}%; background-color: {c_hex};"></div></div>' if progress is not None else ""
    return f"""<div class="custom-card"><div class="card-title" style="color:{c_hex}">{title}</div><div class="card-value">{value}</div><div class="card-note" style="color:{c_hex}">{note}</div>{prog_html}</div>"""

def make_badge(text, color="gray"):
    c_map = {"green": ("rgba(16, 185, 129, 0.2)", "#34d399"), "red": ("rgba(239, 68, 68, 0.2)", "#f87171"), "blue": ("rgba(59, 130, 246, 0.2)", "#60a5fa"), "purple": ("rgba(139, 92, 246, 0.2)", "#a78bfa"), "gray": ("rgba(107, 114, 128, 0.2)", "var(--text-color)")}
    bg, fg = c_map.get(color, c_map["gray"])
    return f'<span class="status-badge" style="background-color:{bg}; color:{fg};">{text}</span>'

# ==========================================
# 🚀 資料準備 & 邏輯計算
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

# 1. 取得資產與目標
current_twd_balance = 0
current_lpm_balance = 0 # Line Pay Money
current_jpy_balance = 0
current_month_target = 0
twd_row_idx = -1
lpm_row_idx = -1
jpy_row_idx = -1

try:
    if not df_assets.empty:
        # 找台幣
        row = df_assets[df_assets['資產項目'] == '台幣活存']
        if not row.empty:
            current_twd_balance = int(str(row.iloc[0]['目前價值']).replace(',', ''))
            twd_row_idx = row.index[0] + 2
        
        # 找 Line Pay Money
        row_lpm = df_assets[df_assets['資產項目'] == 'Line Pay Money']
        if not row_lpm.empty:
            current_lpm_balance = int(str(row_lpm.iloc[0]['目前價值']).replace(',', ''))
            lpm_row_idx = row_lpm.index[0] + 2
        else:
            current_lpm_balance = 0 # 預設為 0
            lpm_row_idx = -1

        # 找日幣
        row_j = df_assets[df_assets['資產項目'] == '日幣帳戶']
        if not row_j.empty:
            current_jpy_balance = int(str(row_j.iloc[0]['目前價值']).replace(',', ''))
            jpy_row_idx = row_j.index[0] + 2

    if not df_future.empty:
        target_row = df_future[df_future['月份 (A)'].astype(str).str.contains(f"{current_month}月")]
        if not target_row.empty:
            current_month_target = int(str(target_row.iloc[0]['目標應有餘額 (E)']).replace(',', ''))
except: pass

# 2. 計算即時缺口 (台幣 + Line Pay Money - 目標)
# 因為 LPM 也是現金，應該算在可用資金內
current_total_liquid = current_twd_balance + current_lpm_balance

if current_month_target != 0:
    current_gap = current_total_liquid - current_month_target
    if ws_status:
        try: ws_status.update_cell(9, 2, current_gap)
        except: pass
else:
    try:
        if ws_status: current_gap = int(str(ws_status.cell(9, 2).value).replace(',', ''))
        else: current_gap = -9999
    except: current_gap = -9999

# 3. 計算本月數據
total_variable_expenses = 0
pending_debt = 0 
real_self_expenses = 0
pending_revenue = 0
pending_reimburse = 0
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
    current_month_logs['是否報帳'] = current_month_logs['是否報帳'].astype(str)
    current_month_logs['已入帳'] = current_month_logs['已入帳'].astype(str).str.strip()

    v_mask = (current_month_logs['實際消耗'] > 0) & (current_month_logs['是否報帳'] != '固定')
    total_variable_expenses = int(current_month_logs[v_mask]['實際消耗'].sum())
    
    mask_rev = (current_month_logs['是否報帳'] == '收入') & (current_month_logs['已入帳'] == '未入帳')
    pending_revenue = int(current_month_logs[mask_rev]['金額'].sum())
    
    mask_reim = (current_month_logs['是否報帳'] == '是') & (current_month_logs['已入帳'] == '未入帳')
    pending_reimburse = int(current_month_logs[mask_reim]['金額'].sum())
    
    pending_debt = pending_revenue + pending_reimburse

    reimburse_pending_cost = current_month_logs[mask_reim]['實際消耗'].sum()
    real_self_expenses = total_variable_expenses - int(reimburse_pending_cost)

base_budget = 97 if current_month == 2 else 2207
surplus_from_gap = max(0, current_gap)
remaining = (base_budget + surplus_from_gap) - total_variable_expenses
potential_available = remaining + pending_debt

# 同步函式 (更新支援 LPM)
def sync_update(amount_change, account_name='台幣活存'):
    if not ws_assets or not ws_status: return
    try:
        all_assets = ws_assets.get_all_records()
        # 尋找對應的帳戶
        target_row = -1
        current_val = 0
        
        for i, r in enumerate(all_assets):
            if r.get('資產項目') == account_name:
                target_row = i + 2
                current_val = int(str(r.get('目前價值', 0)).replace(',', ''))
                break
        
        # 如果找到了該帳戶，更新它
        if target_row != -1:
            ws_assets.update_cell(target_row, 2, current_val + amount_change)
            
            # 如果更新的是台幣，也同步更新 Status 表的 B6 (假設 B6 是台幣)
            if account_name == '台幣活存':
                ws_status.update_cell(6, 2, current_val + amount_change)
        
        # 無論更新哪個現金帳戶，缺口都會受影響 (Gap = Total Cash - Target)
        # 這裡直接更新 B9，雖然下次讀取會自動算，但保持即時性
        current_gap_val = int(str(ws_status.cell(9, 2).value).replace(',', ''))
        ws_status.update_cell(9, 2, current_gap_val + amount_change)
        
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
        # 自我分期通常是還給台幣帳戶或還債，這裡暫時只更新缺口
        if ws_status:
            try: 
                cg = int(str(ws_status.cell(9, 2).value).replace(',', ''))
                ws_status.update_cell(9, 2, cg + amount)
            except: pass
        st.toast(f"✅ {name} 已執行！"); time.sleep(1); st.rerun(); return

    if is_transfer:
        # 定存轉帳通常是 台幣 -> 定存
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

    final_type = "固定收入" if type_code == "固定收入" else "固定"
    is_inc = (type_code == "固定收入")
    change = amount if is_inc else -amount
    # 固定收支預設走台幣
    ws_log.append_row([date_str, name, amount, final_type, 0, "固定扣款" if not is_inc else "已入帳"])
    sync_update(change, '台幣活存')
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
st.sidebar.caption("宇毛的記帳本 v29.0 (LPM Integrated)")

# ==========================================
# 🏠 頁面 1：隨手記帳
# ==========================================
if page == "💸 隨手記帳 (本月)":
    st.subheader(f"{current_month} 月財務面板")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    
    gap_color = "orange" if current_gap < 0 else "green"
    # 更新備註：顯示台幣+LPM
    gap_note = f"目標 ${current_month_target} - (台+L)${current_total_liquid}"
    rem_color = "green"
    if remaining < 0: rem_color = "red"
    elif remaining < 50: rem_color = "orange"

    with c1: st.markdown(make_card(f"{current_month}月本金", f"${base_budget}", "固定額度", "blue"), unsafe_allow_html=True)
    with c2: st.markdown(make_card("真實花費", f"${real_self_expenses}", "不含代墊款", "gray"), unsafe_allow_html=True)
    with c3: st.markdown(make_card("應收帳款", f"${pending_debt}", f"收入: ${pending_revenue} | 代墊: ${pending_reimburse}", "purple"), unsafe_allow_html=True)
    with c4: st.markdown(make_card("目前可用", f"${potential_available}", f"實際現金: ${remaining}", rem_color), unsafe_allow_html=True)
    with c5: st.markdown(make_card("總透支缺口", f"${current_gap}", gap_note, gap_color, progress=None), unsafe_allow_html=True)

    if real_self_expenses > base_budget: 
        st.error("🚨 警告：本月已透支！請停止支出！")

    st.markdown("---")
    st.subheader("📝 新增交易")
    txn_type = st.radio("類型", ["💸 支出", "💰 收入"], horizontal=True)
    
    with st.form("add_txn", clear_on_submit=True):
        col1, col2 = st.columns([1, 2])
        d_in = col1.date_input("日期", datetime.now())
        n_in = col2.text_input("項目", placeholder="例如: 午餐")
        
        # 第二行：金額、代墊、帳戶
        c3_1, c3_2, c3_3 = st.columns(3)
        a_in = c3_1.number_input("金額", min_value=1, step=1)
        
        is_reim = "否"
        if "支出" in txn_type:
            is_reim = c3_2.radio("是否代墊?", ["否", "是"], horizontal=True)
        else:
            c3_2.caption("ℹ️ 收入預設 **未入帳**")
            
        # 帳戶選擇器
        acct_map = {"🇹🇼 台幣活存": "台幣活存", "🟩 Line Pay Money": "Line Pay Money"}
        acct_select = c3_3.selectbox("支付/入帳帳戶", list(acct_map.keys()))
        target_acct = acct_map[acct_select]
            
        if st.form_submit_button("確認記帳", use_container_width=True, type="primary") and ws_log:
            if n_in and a_in > 0:
                d_str = d_in.strftime("%m/%d")
                final_name = n_in 
                # 若是 LPM，自動標註
                if target_acct == "Line Pay Money":
                    final_name += " (LPM)"
                
                if "支出" in txn_type:
                    act = a_in
                    sta = "未入帳" if is_reim == "是" else "已入帳"
                    ws_log.append_row([d_str, final_name, a_in, is_reim, act, sta])
                    # 支出：減少該帳戶餘額
                    sync_update(-a_in, target_acct)
                    st.toast(f"💸 支出已記：${a_in} ({target_acct})")
                else:
                    ws_log.append_row([d_str, final_name, a_in, "收入", 0, "未入帳"])
                    # 收入預設未入帳，不更新餘額，直到勾選已入帳
                    st.toast(f"💰 收入已記 (未入帳)：${a_in}")
                time.sleep(1); st.rerun()

    if not current_month_logs.empty:
        st.markdown("### 📜 本月明細")
        
        filter_opts = st.multiselect(
            "篩選類別:", 
            ["一般消費", "報帳(未入)", "報帳(已入)", "收入(未入)", "收入(已入)", "固定收支"],
            default=[]
        )
        
        display_df = current_month_logs.iloc[::-1].copy()
        
        if filter_opts:
            mask = pd.Series([False] * len(display_df), index=display_df.index)
            if "一般消費" in filter_opts:
                mask |= (display_df['是否報帳'] == '否')
            if "報帳(未入)" in filter_opts:
                mask |= ((display_df['是否報帳'] == '是') & (display_df['已入帳'] == '未入帳'))
            if "報帳(已入)" in filter_opts:
                mask |= ((display_df['是否報帳'] == '是') & (display_df['已入帳'] == '已入帳'))
            if "收入(未入)" in filter_opts:
                mask |= ((display_df['是否報帳'] == '收入') & (display_df['已入帳'] == '未入帳'))
            if "收入(已入)" in filter_opts:
                mask |= ((display_df['是否報帳'] == '收入') & (display_df['已入帳'] == '已入帳'))
            if "固定收支" in filter_opts:
                mask |= (display_df['是否報帳'].isin(['固定', '固定收入']))
            
            display_df = display_df[mask]

        for i, (idx, row) in enumerate(display_df.iterrows()):
            real_idx = idx + 5 
            cls = "一般"
            if row['是否報帳'] == "是": cls = "報帳/代墊"
            elif row['是否報帳'] == "收入": cls = "收入"
            elif row['是否報帳'] in ["固定", "固定收入"]: cls = "固定收支"
            
            sta = str(row.get('已入帳', '已入帳')).strip() or "已入帳"
            
            b_clr, t_clr, pfx = "gray", "var(--text-color)", "$"
            if cls == "收入": b_clr, t_clr, pfx = "green" if sta=="已入帳" else "gray", "#34d399" if sta=="已入帳" else "var(--text-color)", "+$"
            elif cls == "報帳/代墊": b_clr, t_clr = "purple" if sta=="未入帳" else "gray", "#a78bfa" if sta=="未入帳" else "var(--text-color)"
            elif cls == "固定收支": b_clr, t_clr = "blue", "#60a5fa"
            else: t_clr, pfx = "#f87171", "-$"

            with st.container():
                c_row, c_act = st.columns([6, 1])
                with c_row:
                    st.markdown(f"""
                    <div class="list-row">
                        <div class="list-left">
                            <span style="font-size:0.85em; opacity:0.6;">{row['日期']}</span>
                            <span style="font-weight:700; font-size:1.05em;">{row['項目']}</span>
                            <div>{make_badge(sta, b_clr)} <span style="font-size:0.8em; opacity:0.5;">{cls}</span></div>
                        </div>
                        <div class="list-right">
                            <span class="list-amt" style="color:{t_clr};">{pfx}{row['金額']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with c_act:
                    st.write("") 
                    if cls in ["報帳/代墊", "收入"]:
                        is_clr = (sta == "已入帳")
                        lbl = "已結清" if "報帳" in cls else "已入帳"
                        if st.toggle(lbl, value=is_clr, key=f"tg_{idx}") != is_clr:
                            new_state = not is_clr
                            new_s = "已入帳" if new_state else "未入帳"
                            new_act, chg = 0, 0
                            
                            # 判斷是哪個帳戶的收入/代墊
                            # 預設回補到台幣，除非項目名有 (LPM)
                            is_lpm_item = "(LPM)" in str(row['項目'])
                            target_acct = "Line Pay Money" if is_lpm_item else "台幣活存"

                            if "報帳" in cls:
                                new_act = 0 if new_state else row['金額']
                                chg = row['金額'] if new_state else -row['金額']
                            elif cls == "收入":
                                new_act = -row['金額'] if new_state else 0
                                chg = row['金額'] if new_state else -row['金額']
                            
                            if chg != 0: sync_update(chg, target_acct)
                            ws_log.update_cell(real_idx, 5, new_act)
                            ws_log.update_cell(real_idx, 6, new_s)
                            st.success(f"已更新至 {target_acct}"); time.sleep(0.5); st.rerun()
        st.markdown("---")

# ==========================================
# 🛍️ 頁面 2：購物冷靜清單 (排序 & 編輯)
# ==========================================
elif page == "🛍️ 購物冷靜清單":
    
    # 標題與排序選單
    c_sort_1, c_sort_2 = st.columns([3, 1])
    with c_sort_1: st.subheader("🧊 購物冷靜清單")
    with c_sort_2:
        sort_order = st.selectbox(
            "排序依照", 
            ["新增順序", "想要程度 (高→低)", "價格 (高→低)", "價格 (低→高)"]
        )

    df_shop, ws_shop = get_data("購物冷靜清單")
    
    # 預處理資料以便排序
    if not df_shop.empty:
        df_shop['SortPrice'] = df_shop['預估價格'].astype(str).str.replace(',', '').apply(lambda x: int(x) if x.isdigit() else 0)
        df_shop['SortDesire'] = df_shop['想要程度'].apply(lambda x: int(str(x)) if str(x).isdigit() else 0)

        if sort_order == "想要程度 (高→低)":
            df_shop = df_shop.sort_values('SortDesire', ascending=False)
        elif sort_order == "價格 (高→低)":
            df_shop = df_shop.sort_values('SortPrice', ascending=False)
        elif sort_order == "價格 (低→高)":
            df_shop = df_shop.sort_values('SortPrice', ascending=True)

    tot = sum([int(str(r.get('預估價格',0)).replace(',','')) for i,r in df_shop.iterrows()]) if not df_shop.empty else 0
    
    c1, c2 = st.columns(2)
    with c1: st.markdown(make_card("清單總項數", f"{len(df_shop)} 項", "慾望清單", "blue"), unsafe_allow_html=True)
    with c2: st.markdown(make_card("預估總金額", f"${tot:,}", "需存錢目標", "orange"), unsafe_allow_html=True)
    st.markdown("---")
    
    with st.expander("➕ 新增願望"):
        with st.form("add_shop"):
            c1, c2, c3 = st.columns([2, 1, 1])
            n = c1.text_input("物品")
            p = c2.number_input("價格", min_value=0)
            desire = c3.slider("想要指數", 1, 5, 3) 
            note = st.text_input("備註 (選填)")
            if st.form_submit_button("加入") and ws_shop:
                ws_shop.append_row([datetime.now().strftime("%m/%d"), n, p, desire, "2026/07/01", "延後", note])
                st.success("已加入"); time.sleep(1); st.rerun()
    
    if not df_shop.empty:
        st.markdown("### 📦 明細 (可編輯)")
        for idx, row in df_shop.iterrows():
            desire_val = row.get('想要程度', 3)
            title_str = f"🔥 {desire_val} | {row.get('物品名稱', '未命名')} - ${row.get('預估價格', 0)}"
            
            with st.expander(title_str):
                with st.form(key=f"edit_shop_{idx}"):
                    c_edit_1, c_edit_2, c_edit_3 = st.columns([2, 1, 1])
                    new_name = c_edit_1.text_input("名稱", value=row.get('物品名稱', ''))
                    new_price = c_edit_2.number_input("價格", value=int(str(row.get('預估價格', 0)).replace(',','')), min_value=0)
                    new_desire = c_edit_3.slider("想要指數", 1, 5, int(str(desire_val)) if str(desire_val).isdigit() else 3)
                    
                    new_note = st.text_input("備註", value=row.get('備註', ''))
                    
                    c_btn_1, c_btn_2 = st.columns(2)
                    if c_btn_1.form_submit_button("💾 保存修改"):
                        real_row = idx + 2
                        ws_shop.update_cell(real_row, 2, new_name)
                        ws_shop.update_cell(real_row, 3, new_price)
                        ws_shop.update_cell(real_row, 4, new_desire)
                        ws_shop.update_cell(real_row, 7, new_note)
                        st.success("已保存"); time.sleep(0.5); st.rerun()
                        
                    if c_btn_2.form_submit_button("🗑️ 刪除項目", type="primary"):
                        real_row = idx + 2
                        ws_shop.delete_rows(real_row)
                        st.success("已刪除"); time.sleep(0.5); st.rerun()
                
                d = row.get('最終決策', '考慮')
                st.markdown(f"""
                <div style="margin-top:8px; display:flex; align-items:center;">
                    {make_badge(d, 'red' if d=='延後' else 'green')}
                    <span style="opacity:0.7; margin-left:10px;">目前備註: {row.get('備註', '')}</span>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# 📊 頁面 3：資產與收支 (含 LPM)
# ==========================================
elif page == "📊 資產與收支":
    st.subheader("💰 資產狀況")
    
    def update_asset(row_idx, new_val):
        if row_idx != -1 and ws_assets:
            ws_assets.update_cell(row_idx, 2, new_val)
            st.toast("資產已更新"); time.sleep(1); st.rerun()

    tot = int(str(df_assets[df_assets['資產項目'] == '總資產'].iloc[0]['目前價值']).replace(',','')) if not df_assets.empty else 0
    st.markdown(make_card("目前總身價", f"${tot:,}", "含所有資產", "blue"), unsafe_allow_html=True)
    
    # 改為 4 欄以容納 LPM
    c1, c2, c3, c4 = st.columns(4)
    
    with c1: 
        st.markdown(f"""<div class="asset-box"><div class="asset-num">${current_twd_balance}</div><div class="asset-desc">🇹🇼 台幣活存</div></div>""", unsafe_allow_html=True)
        with st.popover("✏️ 編輯台幣"):
            new_twd = st.number_input("新金額", value=current_twd_balance, step=100)
            if st.button("更新台幣"): update_asset(twd_row_idx, new_twd)

    with c2: 
        st.markdown(f"""<div class="asset-box"><div class="asset-num">${current_lpm_balance}</div><div class="asset-desc">🟩 Line Pay</div></div>""", unsafe_allow_html=True)
        with st.popover("✏️ 編輯 LPM"):
            new_lpm = st.number_input("新金額", value=current_lpm_balance, step=100)
            if st.button("更新 LPM"): update_asset(lpm_row_idx, new_lpm)

    with c3: 
        st.markdown(f"""<div class="asset-box"><div class="asset-num">¥{current_jpy_balance}</div><div class="asset-desc">🇯🇵 日幣帳戶</div></div>""", unsafe_allow_html=True)
        with st.popover("✏️ 編輯日幣"):
            new_jpy = st.number_input("新金額", value=current_jpy_balance, step=100)
            if st.button("更新日幣"): update_asset(jpy_row_idx, new_jpy)

    with c4: 
        fixed_dep = int(str(df_assets[df_assets['資產項目']=='定存累計'].iloc[0]['目前價值']).replace(',','')) if not df_assets.empty else 0
        st.markdown(f"""<div class="asset-box"><div class="asset-num">${fixed_dep}</div><div class="asset-desc">🏦 定存累計</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📉 每月固定收支")
    df_model, _ = get_data("每月收支模型")
    if not df_model.empty:
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
                <div style="text-align:left;">
                    <div style="font-size:12px;opacity:0.7;">支出總計</div>
                    <div class="summary-val" style="color:#f87171;">${exp_tot}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:12px;opacity:0.7;">固定餘額</div>
                    <div class="summary-val" style="color:#2dce89;">${net_bal}</div>
                </div>
            </div>""", unsafe_allow_html=True)
        except: pass

# ==========================================
# 📅 頁面 4：未來推估 (Mobile Fix + Sort)
# ==========================================
elif page == "📅 未來推估":
    st.subheader("🔮 財務預測")
    if not df_future.empty:
        valid_df = df_future[~df_future['月份 (A)'].astype(str).str.contains("初始")].copy()
        
        def get_period_num(x):
            try: return int(''.join(filter(str.isdigit, str(x))))
            except: return 999
        valid_df['SortKey'] = valid_df['期數 (B)'].apply(get_period_num)
        valid_df = valid_df.sort_values('SortKey')

        for i in range(0, len(valid_df), 3):
            batch = valid_df.iloc[i : i+3]
            cols = st.columns(3)
            for j, (idx, row) in enumerate(batch.iterrows()):
                with cols[j]:
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
            h = df_log[df_log['Month'] == sel].copy()
            
            hist_filter = st.multiselect(
                "篩選類別:", 
                ["一般消費", "報帳(未入)", "報帳(已入)", "收入(未入)", "收入(已入)", "固定收支"],
                default=[], key="hist_filter"
            )
            
            if hist_filter:
                mask = pd.Series([False] * len(h), index=h.index)
                if "一般消費" in hist_filter: mask |= (h['是否報帳'] == '否')
                if "報帳(未入)" in hist_filter: mask |= ((h['是否報帳'] == '是') & (h['已入帳'] == '未入帳'))
                if "報帳(已入)" in hist_filter: mask |= ((h['是否報帳'] == '是') & (h['已入帳'] == '已入帳'))
                if "收入(未入)" in hist_filter: mask |= ((h['是否報帳'] == '收入') & (h['已入帳'] == '未入帳'))
                if "收入(已入)" in hist_filter: mask |= ((h['是否報帳'] == '收入') & (h['已入帳'] == '已入帳'))
                if "固定收支" in hist_filter: mask |= (h['是否報帳'].isin(['固定', '固定收入']))
                h = h[mask]

            st.markdown(make_card(f"{sel}月 淨支出", f"${int(h['實際消耗'].sum())}", "含收入抵銷後", "gray"), unsafe_allow_html=True)
            
            for i, r in h.iloc[::-1].iterrows():
                c = "#34d399" if r['實際消耗'] < 0 else "#f87171"
                st.markdown(f"""<div class="list-row"><div><span style="font-size:0.8em;opacity:0.6;">{r['日期']}</span> <b>{r['項目']}</b></div><div style="color:{c};font-weight:bold;">${r['金額']}</div></div>""", unsafe_allow_html=True)
