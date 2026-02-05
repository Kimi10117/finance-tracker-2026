import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 設定頁面資訊 ---
st.set_page_config(page_title="宇毛的財務中控台", page_icon="💰", layout="wide")

# --- CSS 極致美化 (v19.0 UI Reborn) ---
def inject_custom_css():
    st.markdown("""
    <style>
        /* === 全局設定 === */
        .stApp {
            background-color: var(--background-color);
            color: var(--text-color);
        }
        
        /* 隱藏不必要的 Streamlit 元素 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;} /* 隱藏頂部紅線與選單，爭取空間 */
        
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 5rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* === 卡片核心樣式 === */
        .custom-card {
            background-color: var(--secondary-background-color);
            padding: 16px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 12px;
            border: 1px solid rgba(128, 128, 128, 0.15);
            transition: transform 0.2s ease;
            position: relative;
            overflow: hidden;
        }
        
        /* 卡片標題 */
        .card-title {
            font-size: 13px;
            color: var(--text-color);
            opacity: 0.7;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            margin-bottom: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* 卡片數值 */
        .card-value {
            font-size: 24px;
            font-weight: 800;
            color: var(--text-color);
            letter-spacing: -0.5px;
            line-height: 1.1;
            white-space: nowrap;
        }
        
        /* 卡片備註 */
        .card-note {
            font-size: 11px;
            font-weight: 600;
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 4px;
            opacity: 0.9;
        }

        /* === 進度條 === */
        .progress-container {
            width: 100%;
            height: 6px;
            background-color: rgba(128, 128, 128, 0.1);
            border-radius: 3px;
            margin-top: 10px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%;
            border-radius: 3px;
            transition: width 0.6s ease;
        }

        /* === 資產與列表樣式 === */
        .asset-box {
            background-color: var(--secondary-background-color);
            padding: 12px;
            border-radius: 10px;
            border: 1px solid rgba(128, 128, 128, 0.1);
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }
        .asset-num { font-size: 18px; font-weight: 800; color: var(--text-color); }
        .asset-desc { font-size: 11px; opacity: 0.6; margin-top: 2px; }

        .list-row {
            background-color: var(--secondary-background-color);
            padding: 12px 16px;
            border-radius: 10px;
            margin-bottom: 8px;
            border: 1px solid rgba(128, 128, 128, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        }

        /* === 標籤 Badge === */
        .status-badge {
            display: inline-block;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 700;
            border-radius: 10px;
            margin-top: 4px;
            white-space: nowrap;
        }

        /* === 輸入選單優化 === */
        div[role="radiogroup"] {
            background-color: var(--secondary-background-color);
            padding: 4px;
            border-radius: 10px;
            border: 1px solid rgba(128, 128, 128, 0.1);
            display: flex;
            gap: 4px;
        }
        div[role="radiogroup"] label {
            flex: 1;
            text-align: center;
            border-radius: 8px;
            padding: 6px 4px;
            font-size: 14px;
            border: none;
            background: transparent;
            transition: all 0.2s;
        }
        div[role="radiogroup"] label[data-checked="true"] {
            background-color: rgba(128, 128, 128, 0.1);
            font-weight: 800;
            color: #5e72e4;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .stRadio label { cursor: pointer; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- 連接 Google Sheets ---
@st.cache_resource
def connect_to_gsheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("宇毛的財務追蹤表_2026")
    return sheet

try:
    sh = connect_to_gsheet()
except Exception as e:
    st.error(f"❌ 資料庫連線失敗，請檢查網路或憑證。錯誤：{e}")
    st.stop()

# --- 讀取資料函式 ---
def get_data(worksheet_name, head=1):
    try:
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records(head=head)
        return pd.DataFrame(data), ws
    except:
        return pd.DataFrame(), None

# --- UI 元件生成器 (v19.0) ---
def make_card(title, value, note, color="gray", progress=None):
    colors = {
        "blue": "#3498db", "red": "#e74c3c", "green": "#2ecc71", 
        "orange": "#f39c12", "gray": "var(--text-color)", "purple": "#9b59b6"
    }
    c_hex = colors.get(color, colors["gray"])
    
    # 進度條
    prog_html = ""
    if progress is not None:
        pct = min(max(float(progress), 0.0), 1.0) * 100
        prog_html = f'<div class="progress-container"><div class="progress-bar" style="width: {pct}%; background-color: {c_hex};"></div></div>'
    
    # 備註顏色邏輯
    note_style = f"color: {c_hex};" if color not in ["gray"] else "opacity: 0.6;"

    return f"""
    <div class="custom-card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
        <div class="card-note" style="{note_style}">{note}</div>
        {prog_html}
    </div>
    """

def make_badge(text, color="gray"):
    bg_map = {
        "green": "rgba(46, 204, 113, 0.15)", "red": "rgba(231, 76, 60, 0.15)",
        "blue": "rgba(52, 152, 219, 0.15)", "orange": "rgba(243, 156, 18, 0.15)",
        "purple": "rgba(155, 89, 182, 0.15)", "gray": "rgba(149, 165, 166, 0.2)"
    }
    text_map = {
        "green": "#2ecc71", "red": "#e74c3c", "blue": "#3498db",
        "orange": "#f39c12", "purple": "#9b59b6", "gray": "inherit"
    }
    return f'<span class="status-badge" style="background-color: {bg_map.get(color)}; color: {text_map.get(color)};">{text}</span>'

# ==========================================
# 🚀 資料準備層
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

# 1. 取得靜態缺口 (B9)
try:
    if ws_status:
        gap_val = ws_status.cell(9, 2).value 
        base_gap_static = int(str(gap_val).replace(',', ''))
    else: base_gap_static = -9999
except: base_gap_static = -9999

# 2. 計算本月數據
total_variable_expenses = 0
pending_debt = 0
current_month_logs = pd.DataFrame()

if not df_log.empty:
    def robust_month_parser(x):
        try: return pd.to_datetime(str(x), format='%m/%d').month
        except: return current_month 

    df_log['Month'] = df_log['日期'].apply(robust_month_parser)
    current_month_logs = df_log[df_log['Month'] == current_month].copy()
    current_month_logs['實際消耗'] = pd.to_numeric(current_month_logs['實際消耗'], errors='coerce').fillna(0)
    current_month_logs['金額'] = pd.to_numeric(current_month_logs['金額'], errors='coerce').fillna(0)
    current_month_logs['項目'] = current_month_logs['項目'].astype(str)
    
    # 變動支出
    v_mask = (current_month_logs['實際消耗'] > 0) & (current_month_logs['是否報帳'] != '固定')
    total_variable_expenses = int(current_month_logs[v_mask]['實際消耗'].sum())
    
    # 未入帳代墊
    p_mask = (current_month_logs['是否報帳'] == '是') & (current_month_logs['已入帳'] == '未入帳')
    pending_debt = int(current_month_logs[p_mask]['金額'].sum())

# 3. 核心指標
current_gap = base_gap_static
base_budget = 97 if current_month == 2 else 2207
surplus_from_gap = max(0, current_gap)
remaining = (base_budget + surplus_from_gap) - total_variable_expenses

# --- 💡 同步函式 ---
def sync_update(amount_change):
    if not ws_assets or not ws_status: return
    try:
        # 更新資產表
        all_assets = ws_assets.get_all_records()
        new_twd = 0
        for i, r in enumerate(all_assets):
            if r.get('資產項目') == '台幣活存':
                curr = int(str(r.get('目前價值', 0)).replace(',', ''))
                new_twd = curr + amount_change
                ws_assets.update_cell(i+2, 2, new_twd)
                break
        
        # 更新狀態表 (B6, B9)
        ws_status.update_cell(6, 2, new_twd) # B6 實際餘額
        
        curr_gap = int(str(ws_status.cell(9, 2).value).replace(',', ''))
        ws_status.update_cell(9, 2, curr_gap + amount_change) # B9 缺口
    except: pass

# ==========================================
# 側邊欄：智慧例行事項
# ==========================================
st.sidebar.title("🚀 功能選單")

# --- 待辦邏輯 ---
def check_logged(keyword):
    if current_month_logs.empty: return False
    return current_month_logs['項目'].str.contains(keyword, case=False).any()

def execute_auto_entry(name, amount, type_code="固定", is_transfer=False):
    if not ws_log: return
    date_str = now_dt.strftime("%m/%d")
    
    # 自我分期 (特殊：不扣資產，補B9缺口)
    if name == "自我分期(還債)":
        ws_log.append_row([date_str, name, amount, "固定", 0, "固定扣款"])
        if ws_status:
            try: 
                cur_gap = int(str(ws_status.cell(9, 2).value).replace(',', ''))
                ws_status.update_cell(9, 2, cur_gap + amount)
            except: pass
        st.toast(f"✅ {name} 已執行！"); time.sleep(1); st.rerun(); return

    # 定存轉帳 (資產互轉)
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

    # 一般固定收支 (薪水/電信/YT)
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
st.sidebar.caption("宇毛的記帳本 v19.0 (UI Reborn)")

# ==========================================
# 🏠 頁面 1：隨手記帳
# ==========================================
if page == "💸 隨手記帳 (本月)":
    st.subheader(f"👋 {current_month} 月財務面板")
    
    c1, c2, c3, c4 = st.columns(4)
    
    # 顏色邏輯
    gap_note = "收入優先抵債" if current_gap < 0 else "溢出 + 至額度"
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
    
    # 新增交易
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
            if is_reim == "是": 
                target = st.text_input("幫誰代墊?", placeholder="Andy")
        else:
            st.caption("ℹ️ 收入預設 **未入帳**")
            
        if st.form_submit_button("確認記帳", use_container_width=True, type="primary") and ws_log:
            if n_in and a_in > 0:
                d_str = d_in.strftime("%m/%d")
                final_name = f"{n_in} ({target})" if target else n_in
                
                if "支出" in txn_type:
                    act = a_in
                    sta = "未入帳" if is_reim == "是" else "已入帳"
                    ws_log.append_row([d_str, final_name, a_in, is_reim, act, sta])
                    sync_update(-a_in) # 支出直接扣
                    st.toast(f"💸 支出已記：${a_in}")
                else:
                    ws_log.append_row([d_str, final_name, a_in, "收入", 0, "未入帳"])
                    st.toast(f"💰 收入已記 (未入帳)：${a_in}")
                time.sleep(1); st.rerun()

    # 明細列表
    if not current_month_logs.empty:
        st.markdown("### 📜 本月明細")
        for i, (idx, row) in enumerate(current_month_logs.iloc[::-1].iterrows()):
            real_idx = idx + 5 
            cls = "一般"
            if row['是否報帳'] == "是": cls = "報帳/代墊"
            elif row['是否報帳'] == "收入": cls = "收入"
            elif row['是否報帳'] == "固定": cls = "固定收支"
            
            sta = str(row.get('已入帳', '已入帳')).strip() or "已入帳"
            
            # 樣式判斷
            b_clr, t_clr, pfx = "gray", "var(--text-color)", "$"
            if cls == "收入": 
                b_clr = "green" if sta=="已入帳" else "gray"
                t_clr = "#2dce89" if sta=="已入帳" else "var(--text-color)"
                pfx = "+$"
            elif cls == "報帳/代墊": 
                b_clr = "purple" if sta=="未入帳" else "gray"
                t_clr = "#8e44ad" if sta=="未入帳" else "var(--text-color)"
            elif cls == "固定收支": 
                b_clr = "blue"; t_clr = "#3498db"
            else: 
                t_clr = "#f5365c"; pfx = "-$"

            with st.container():
                c1, c2, c3 = st.columns([3, 1.5, 1.2])
                c1.markdown(f"""<div style="line-height:1.4;"><span style="font-size:0.85em; opacity:0.7;">{row['日期']}</span><br><span style="font-weight:600;">{row['項目']}</span><br>{make_badge(sta, b_clr)} <span style="font-size:0.8em; opacity:0.6;">{cls}</span></div>""", unsafe_allow_html=True)
                c2.markdown(f"<div style='margin-top:10px;'><span style='color:{t_clr}; font-weight:800; font-size:1.1em;'>{pfx}{row['金額']}</span></div>", unsafe_allow_html=True)
                
                # 開關
                if cls in ["報帳/代墊", "收入"]:
                    is_clr = (sta == "已入帳")
                    lbl = "已結清?" if "報帳" in cls else "已入帳?"
                    if c3.toggle(lbl, value=is_clr, key=f"tg_{idx}") != is_clr:
                        new_s = "未入帳" if is_clr else "已入帳"
                        chg = 0
                        # 狀態切換邏輯
                        if "報帳" in cls: chg = row['金額'] if not is_clr else -row['金額'] # 未->已: 錢回來 (+)
                        elif cls == "收入": chg = row['金額'] if not is_clr else -row['金額'] # 未->已: 錢進來 (+)
                        
                        if chg != 0: sync_update(chg)
                        ws_log.update_cell(real_idx, 6, new_s)
                        st.success("更新成功"); time.sleep(0.5); st.rerun()
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
                st.markdown(f"**決策：** {d} | **備註：** {nt}")
                if st.button("🗑️ 刪除", key=f"del_{i}"): ws_shop.delete_rows(i+2); st.toast("已刪除"); time.sleep(1); st.rerun()

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
        for i, row in df_model.iterrows():
            if str(row.get('金額 (B)','')).strip(): 
                val = row['金額 (B)']
                clr = "#2dce89" if str(val).startswith("-") is False else "#f5365c"
                st.markdown(f"""<div class="list-row"><b>{row['項目 (A)']}</b><b style="color:{clr};">${val}</b></div>""", unsafe_allow_html=True)

# ==========================================
# 📅 頁面 4：未來推估 (修復 6 月顯示)
# ==========================================
elif page == "📅 未來推估":
    st.subheader("🔮 財務預測")
    if not df_future.empty:
        # 過濾初始列
        valid_df = df_future[~df_future['月份 (A)'].astype(str).str.contains("初始")]
        
        # 顯示前幾個月
        cols = st.columns(3)
        for i, (idx, row) in enumerate(valid_df.iterrows()):
            if i < len(valid_df): # 確保不超出
                with cols[i % 3]:
                    st.markdown(f"""<div class="asset-box" style="text-align:center; margin-bottom:10px;"><div style="font-weight:bold;margin-bottom:5px;">{row['月份 (A)']}</div><div style="font-size:12px;opacity:0.7;">目標: ${row['目標應有餘額 (E)']}</div><div style="font-size:18px;color:#5e72e4;font-weight:800;">${row['預估實際餘額 (D)']}</div></div>""", unsafe_allow_html=True)
        
        # 強制顯示最後一個月 (Grand Finale)
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
                c = "#2dce89" if r['實際消耗'] < 0 else "#f5365c"
                st.markdown(f"""<div class="list-row"><div><span style="font-size:0.8em;opacity:0.6;">{r['日期']}</span> <b>{r['項目']}</b></div><div style="color:{c};font-weight:bold;">${r['金額']}</div></div>""", unsafe_allow_html=True)
