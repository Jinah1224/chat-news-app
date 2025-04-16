import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from io import StringIO
import re
import time

# ▶ 크롤링 키워드 (국정교과서 → 교과서로 통일)
keywords = ["천재교육", "천재교과서", "지학사", "벽호", "프린피아", "미래엔", "교과서", "동아출판"]

# ▶ 카테고리 분류
def categorize(text):
    text = text.lower()
    if "이벤트" in text:
        return "이벤트"
    elif "후원" in text or "기탁" in text:
        return "후원"
    elif "기부" in text:
        return "기부"
    elif "협약" in text or "mou" in text:
        return "협약/MOU"
    elif any(w in text for w in ["에듀테크", "디지털교육", "ai교육", "스마트교육"]):
        return "에듀테크/디지털교육"
    elif "정책" in text:
        return "정책"
    elif "출판" in text:
        return "출판"
    elif "인쇄" in text or "프린트" in text:
        return "프린트 및 인쇄"
    elif "채용" in text or "교사" in text:
        return "인사/채용"
    elif "공급" in text:
        return "공급"
    elif "교육" in text:
        return "교육"
    else:
        return "기타"

def extract_publisher(text):
    text = text.lower()
    for pub in keywords:
        if pub.lower() in text:
            return pub
    return "기타"

def check_textbook_or_publisher_in_body(text):
    if "교과서" in text or "발행사" in text:
        return "O"
    return "X"

def get_news_date(news_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(news_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "lxml")
        for attr in [{"property": "article:published_time"}, {"name": "date"}, {"property": "og:article:published_time"}]:
            tag = soup.find("meta", attr)
            if tag and tag.get("content"):
                return tag["content"][:10].replace("-", ".")
        # fallback
        text = soup.get_text(" ", strip=True)
        for word in text.split():
            for fmt in ["%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(word[:10], fmt).strftime("%Y.%m.%d")
                except:
                    continue
        return "날짜 없음"
    except:
        return "날짜 오류"

def get_body_text(news_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(news_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "lxml")
        candidates = ["article", "article-body", "newsEndContents", "content", "viewContent"]
        for c in candidates:
            tag = soup.find(class_=c)
            if tag:
                return tag.get_text(separator=" ", strip=True).lower()
        return soup.get_text(separator=" ", strip=True).lower()
    except:
        return ""

def crawl_news(keywords):
    seen_urls = set()
    seen_summaries = set()
    results = []

    for keyword in keywords:
        for page in range(1, 21):
            start = (page - 1) * 10 + 1
            url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1&nso=so%3Add%2Cp%3A2y&start={start}"
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                res = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(res.text, "lxml")
                articles = soup.select(".news_area")
                if not articles:
                    break
                for article in articles:
                    try:
                        title_elem = article.select_one(".news_tit")
                        title = title_elem.get("title")
                        link = title_elem.get("href")
                        summary = article.select_one(".dsc_txt_wrap").text
                        press = article.select_one(".info_group a").text

                        if link in seen_urls or summary in seen_summaries:
                            continue
                        seen_urls.add(link)
                        seen_summaries.add(summary)

                        body = get_body_text(link)
                        full_text = summary + " " + body
                        date = get_news_date(link)

                        results.append({
                            "출판사명": extract_publisher(full_text),
                            "카테고리": categorize(full_text),
                            "날짜": date,
                            "제목": title,
                            "URL": link,
                            "요약": summary,
                            "언론사": press,
                            "내용점검": "O" if extract_publisher(full_text) != "기타" else "X",
                            "본문내_교과서_또는_발행사_언급": check_textbook_or_publisher_in_body(body)
                        })
                        time.sleep(0.3)
                    except:
                        continue
            except:
                continue
    return pd.DataFrame(results)

# ===============================
# 💬 카카오톡 분석 함수
# ===============================
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

# ===============================
# 🖥️ Streamlit 앱 실행 화면
# ===============================
st.set_page_config(page_title="올인원 교과서 분석기", layout="wide")
st.title("📚 교과서 커뮤니티 분석 & 뉴스 수집")

tab1, tab2 = st.tabs(["💬 카카오톡 분석", "📰 뉴스 크롤링"])

# ▶ 카카오톡 탭
with tab1:
    st.subheader("💬 카카오톡 단톡방 .txt 파일 업로드")
    uploaded_file = st.file_uploader("파일 선택", type="txt")
    if uploaded_file:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        df_kakao = analyze_kakao(stringio.read())
        st.success("✅ 대화 분석 완료!")
        st.dataframe(df_kakao)

        st.download_button(
            label="📥 분석결과 다운로드",
            data=df_kakao.to_csv(index=False).encode("utf-8"),
            file_name="카카오톡_분석결과.csv",
            mime="text/csv"
        )

# ▶ 뉴스 크롤링 탭
with tab2:
    st.subheader("📰 네이버 뉴스에서 출판사 관련 기사 수집 (최근 2년)")
    extra_kw = st.text_input("추가 검색어 입력 (쉼표로 구분)", "")
    run = st.button("🔍 뉴스 수집 시작")

    if run:
        user_keywords = [kw.strip() for kw in extra_kw.split(",") if kw.strip()]
        all_keywords = list(set(keywords + user_keywords))

        df_news = crawl_news(all_keywords)
        if not df_news.empty:
            st.success("✅ 뉴스 크롤링 완료")
            st.dataframe(df_news)

            st.download_button(
                label="📥 뉴스 결과 다운로드",
                data=df_news.to_csv(index=False).encode("utf-8"),
                file_name="출판사_뉴스_크롤링_결과.csv",
                mime="text/csv"
            )
        else:
            st.warning("❌ 관련 뉴스가 없습니다.")
