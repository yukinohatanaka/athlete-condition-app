import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

# 1. ページ初期設定
st.set_page_config(
    page_title="アスリート コンディション分析",
    page_icon="🏃",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Googleスプレッドシート接続用関数
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Streamlit Secretsから認証情報を取得
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(credentials)
    return client

def load_data():
    try:
        client = get_gspread_client()
        sheet = client.open("athlete_condition_db").worksheet("コンディションデータ")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty and "日付" in df.columns:
            # 不正な文字列が入っていてもエラーで止まらないよう安全に日付変換
            df["日付"] = pd.to_datetime(df["日付"], errors='coerce')
            df = df.dropna(subset=["日付"])
        return df
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

def save_data(data_dict):
    try:
        client = get_gspread_client()
        sheet = client.open("athlete_condition_db").worksheet("コンディションデータ")
        row = [
            str(data_dict["日付"]),
            data_dict["選手名"],
            data_dict["天気"],
            data_dict["睡眠時間"],
            data_dict["体の自覚的疲労度"],
            data_dict["プレッシャー・不安度"],
            data_dict["今日のモチベーション"],
            data_dict["前日の練習負担度"],
            data_dict["人間関係"],
            data_dict["自由時間の量"],
            data_dict["自覚的な体の動きやすさ"]
        ]
        sheet.append_row(row)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"データ保存エラー: {e}")
        return False

# ヘッダー
st.title("🏃 アスリート コンディション分析")
st.caption("日々のコンディションを記録し、好調時の再現条件を分析します。")

# 選手名入力欄（自由テキスト入力に変更）
input_athlete_name = st.text_input("👤 選手名を入力してください（例: ヤマダ タロウ）", value="").strip()

tab1, tab2 = st.tabs(["📝 今日の記録（入力）", "📊 個人分析（ダッシュボード）"])

# ==========================================
# TAB 1: 入力フォーム
# ==========================================
with tab1:
    display_name = input_athlete_name if input_athlete_name else "（未入力）"
    st.subheader(f"{display_name} さんのコンディション入力")

    with st.form("condition_form", clear_on_submit=True):
        input_date = st.date_input("日付", datetime.today())

        st.markdown("**【環境・体調】**")
        weather = st.slider("天気 (1:大雨 〜 5:快晴)", 1, 5, 3)
        sleep = st.slider("睡眠時間 (時間)", 0.0, 12.0, 7.0, 0.5)
        fatigue = st.slider("体の自覚的疲労度 (1:なし 〜 10:限界)", 1, 10, 5)

        st.markdown("**【メンタル・環境】**")
        pressure = st.slider("プレッシャー・不安度 (1:なし 〜 10:極度)", 1, 10, 5)
        motivation = st.slider("今日のモチベーション (1:無 〜 10:最高)", 1, 10, 5)
        prev_load = st.slider("前日の練習負担度 (1:軽微 〜 10:極高)", 1, 10, 5)
        relation = st.slider("人間関係 (1:ストレス大 〜 10:非常に良好)", 1, 10, 5)
        free_time = st.slider("自由時間の量 (1:少ない 〜 10:多い)", 1, 10, 5)

        st.markdown("**【本日の主観的コンディション】**")
        movement = st.slider("自覚的な体の動きやすさ (1:最悪 〜 10:最高)", 1, 10, 5)

        submitted = st.form_submit_button("データ送信・保存", use_container_width=True)

        if submitted:
            if not input_athlete_name:
                st.error("⚠️ 画面上の『選手名を入力してください』の欄に名前を入力してから送信してください。")
            else:
                record = {
                    "日付": input_date,
                    "選手名": input_athlete_name,
                    "天気": weather,
                    "睡眠時間": sleep,
                    "体の自覚的疲労度": fatigue,
                    "プレッシャー・不安度": pressure,
                    "今日のモチベーション": motivation,
                    "前日の練習負担度": prev_load,
                    "人間関係": relation,
                    "自由時間の量": free_time,
                    "自覚的な体の動きやすさ": movement
                }
                if save_data(record):
                    st.success(f"{input_athlete_name} さんのデータが正常に保存されました！")

# ==========================================
# TAB 2: 分析ダッシュボード
# ==========================================
with tab2:
    if not input_athlete_name:
        st.info("👆 上部の『選手名を入力してください』の欄に名前を入力すると、個人分析が表示されます。")
    else:
        st.subheader(f"{input_athlete_name} さんの分析結果")
        all_df = load_data()

        if all_df.empty or "選手名" not in all_df.columns:
            st.info("データがありません。")
        else:
            # 入力された選手名でフィルタリング（完全一致）
            df = all_df[all_df["選手名"] == input_athlete_name].copy()

            if len(df) < 3:
                st.info("※ 個人データが不足しています。まずは3日以上入力して送信してください。")
            else:
                high_move = df[df["自覚的な体の動きやすさ"] >= 7]
                low_move = df[df["自覚的な体の動きやすさ"] <= 4]
                high_moti = df[df["今日のモチベーション"] >= 7]

                st.markdown("### 💡 自動生成インサイト")
                insights = []

                if not high_move.empty:
                    avg_sleep_high = high_move["睡眠時間"].mean()
                    avg_prev_load_high = high_move["前日の練習負担度"].mean()
                    insights.append(f"・**体が動きやすい日（7以上）**は、睡眠時間が平均 **{avg_sleep_high:.1f}時間**、前日の練習負担度が平均 **{avg_prev_load_high:.1f}** の傾向があります。")

                if not high_moti.empty:
                    avg_rel_high = high_moti["人間関係"].mean()
                    insights.append(f"・**モチベーションが高い日（7以上）**は、人間関係の評価が平均 **{avg_rel_high:.1f}** となっています。")

                # 直近1週間の自由時間相関
                latest_date = df["日付"].max()
                one_week_ago = latest_date - timedelta(days=7)
                recent_df = df[df["日付"] >= one_week_ago].copy()

                if len(recent_df) >= 3:
                    corr_move = recent_df["自由時間の量"].corr(recent_df["自覚的な体の動きやすさ"])
                    if not np.isnan(corr_move):
                        move_text = "強い正の相関" if corr_move > 0.5 else ("正の相関" if corr_move > 0.2 else "相関が少ない" if corr_move > -0.2 else "負の相関")
                        insights.append(f"・**直近1週間の自由時間と体の動きやすさ**には **[{move_text}]** (相関係数: {corr_move:.2f}) が見られます。")

                for ins in insights:
                    st.write(ins)

                st.divider()

                # レーダーチャート比較
                st.markdown("### 📊 好調時と不調時の条件比較")
                if not high_move.empty and not low_move.empty:
                    categories = ['天気', '睡眠時間', '疲労度(逆算)', '不安度(逆算)', '前日負担(逆算)', '人間関係']
                    high_vals = [
                        high_move["天気"].mean(),
                        high_move["睡眠時間"].mean(),
                        11 - high_move["体の自覚的疲労度"].mean(),
                        11 - high_move["プレッシャー・不安度"].mean(),
                        11 - high_move["前日の練習負担度"].mean(),
                        high_move["人間関係"].mean()
                    ]
                    low_vals = [
                        low_move["天気"].mean(),
                        low_move["睡眠時間"].mean(),
                        11 - low_move["体の自覚的疲労度"].mean(),
                        11 - low_move["プレッシャー・不安度"].mean(),
                        11 - low_move["前日の練習負担度"].mean(),
                        low_move["人間関係"].mean()
                    ]

                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(r=high_vals, theta=categories, fill='toself', name='動きやすい時 (7以上)'))
                    fig.add_trace(go.Scatterpolar(r=low_vals, theta=categories, fill='toself', name='体が重い時 (4以下)'))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), margin=dict(l=40, r=40, t=30, b=30), legend=dict(orientation="h", y=-0.2))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("好調時(7以上)と不調時(4以下)のデータが揃うとレーダーチャートが表示されます。")

                # 自由時間推移
                st.markdown("### ⏳ 自由時間とコンディション推移")
                fig_bar = px.bar(
                    df,
                    x="日付",
                    y=["自由時間の量", "自覚的な体の動きやすさ", "今日のモチベーション"],
                    barmode="group",
                    labels={"value": "スコア", "variable": "指標"}
                )
                fig_bar.update_layout(legend=dict(orientation="h", y=-0.3), margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_bar, use_container_width=True)
