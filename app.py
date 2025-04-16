import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from io import StringIO
import re

# ----------------------------------
# 카카오톡 분석 함수
# ----------------------------------
def analyze_kakao(text):
    pattern = re.compile(r"(?P<datetime>\d{4}년 \d{1,2}월 \d{1,2}일 (오전|오후) \d{1,2}:\d{2}), (?P<sender>[^:]+) : (?P<message>.+)")
    matches = pattern.findall(text)

    rows = []
    for match in matches:
        date_str, ampm, sender, message = match
        try:
            dt = datetime.strptime(date_str.replace("오전", "AM").replace("오후", "PM"), "%Y년 %m월 %d일 %p %I:%M")
            rows.append({
                "날짜": dt.date(),
                "시간": dt.time(),
                "보낸 사람": sender.strip(),
                "메시지": message.strip()
            })
        except:
            continue

    return pd.DataFrame(rows)

# ----------------------------------
# 뉴스 크롤링 함수
# ----------------------------------
def crawl_news(keyword):
    url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1&nso=so%3Add%2Cp%3A2w"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "lxml")
    articles = soup.select(".news_area")

    results = []
    for article in articles[:10]:  # 최대 10개 기사
        try:
            title = article.select_one(".news_tit").get("title")
            link = article.select_one(".news_tit").get("href")
            summary = article.select_one(".dsc_txt_wrap").text
            press = article.select_one(".info_group a").text
            results.append({
                "제목": title,
                "요약": summary,
                "URL": link,
                "언론사": press
            })
        except:
            continue
    return pd.DataFrame(results)

# ----------------------------------
# Streamlit UI
# ----------------------------------
st.set_page_config(page_title="올인원 교과서 분석기", layout="wide")
st.title("📚 교과서 커뮤니티 분석 & 뉴스 수집 올인원 앱")

tab1, tab2 = st.tabs(["💬 카카오톡 분석", "📰 뉴스 크롤링"])

# ---------------------------
# 카카오톡 탭
# ---------------------------
with tab1:
    st.subheader("📂 카카오톡 대화 분석기")
    uploaded_file = st.file_uploader("카카오톡 .txt 파일을 업로드하세요", type="txt")
    if uploaded_file:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        df_kakao = analyze_kakao(stringio.read())
        st.success("✅ 대화 분석 완료")
        st.dataframe(df_kakao)

        st.download_button(
            "📥 엑셀 다운로드",
            data=df_kakao.to_csv(index=False).encode("utf-8"),
            file_name="카카오톡_분석결과.csv",
            mime="text/csv"
        )

# ---------------------------
# 뉴스 크롤링 탭
# ---------------------------
with tab2:
    st.subheader("📰 출판사 관련 뉴스 수집기 (최근 2주)")
    keyword_input = st.text_input("검색 키워드 입력 (쉼표로 구분)", "천재교육, 천재교과서, 미래엔, 교과서")
    if st.button("크롤링 시작"):
        keywords = [kw.strip() for kw in keyword_input.split(",") if kw.strip()]
        all_news = []

        for kw in keywords:
            news_df = crawl_news(kw)
            news_df["검색어"] = kw
            all_news.append(news_df)

        if all_news:
            df_news = pd.concat(all_news, ignore_index=True)
            st.success("✅ 뉴스 크롤링 완료")
            st.dataframe(df_news)

            st.download_button(
                "📥 뉴스 데이터 다운로드",
                data=df_news.to_csv(index=False).encode("utf-8"),
                file_name="출판사_뉴스_결과.csv",
                mime="text/csv"
            )
        else:
            st.warning("크롤링된 뉴스가 없습니다.")
