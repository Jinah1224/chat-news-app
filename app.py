import streamlit as st
import pandas as pd
import re
from io import StringIO, BytesIO
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ✅ 키워드 설정
keywords = ["천재교육", "천재교과서", "지학사", "벽호", "프린피아", "미래엔", "교과서", "동아출판"]

# ✅ 카테고리 분류 함수
def categorize(text):
    text = text.lower()
    if "이벤트" in text: return "이벤트"
    elif "후원" in text or "기탁" in text: return "후원"
    elif "기부" in text: return "기부"
    elif "협약" in text or "mou" in text: return "협약/MOU"
    elif any(w in text for w in ["에듀테크", "디지털교육", "ai교육", "스마트교육"]): return "에듀테크/디지털교육"
    elif "정책" in text: return "정책"
    elif "출판" in text: return "출판"
    elif "인쇄" in text or "프린트" in text: return "프린트 및 인쇄"
    elif "채용" in text or "교사" in text: return "인사/채용"
    elif "공급" in text: return "공급"
    elif "교육" in text: return "교육"
    else: return "기타"

# ✅ 뉴스 본문 가져오기
def get_body_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "lxml")
        return soup.get_text(" ", strip=True).lower()
    except:
        return ""

# ✅ 기사 날짜 추출
def get_news_date(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "lxml")
        for prop in ["article:published_time", "og:article:published_time"]:
            tag = soup.find("meta", {"property": prop})
            if tag and tag.get("content"):
                return tag["content"][:10].replace("-", ".")
        return "날짜 없음"
    except:
        return "날짜 오류"

# ✅ 뉴스 크롤링 함수 (BeautifulSoup만 사용)
def crawl_news(keyword):
    results = []
    seen_links = set()
    for page in range(1, 6):
        start = (page - 1) * 10 + 1
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1&nso=so%3Add%2Cp%3A2w&start={start}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "lxml")
        articles = soup.select(".news_area")
        if not articles:
            break
        for article in articles:
            try:
                title_elem = article.select_one(".news_tit")
                title = title_elem["title"]
                link = title_elem["href"]
                if link in seen_links:
                    continue
                seen_links.add(link)
                summary = article.select_one(".dsc_txt_wrap").text.strip() if article.select_one(".dsc_txt_wrap") else ""
                press = article.select_one(".info_group a").text.strip() if article.select_one(".info_group a") else ""
                body = get_body_text(link)
                full = summary + " " + body
                category = categorize(full)
                date = get_news_date(link)
                results.append({
                    "출판사 키워드": keyword,
                    "카테고리": category,
                    "날짜": date,
                    "제목": title,
                    "URL": link,
                    "요약": summary,
                    "언론사": press
                })
            except:
                continue
    return results

# ✅ Streamlit 앱
st.set_page_config(page_title="뉴스 크롤링 배포용", layout="wide")
st.title("📰 출판사 관련 뉴스 크롤링기 (배포용)")

kw_input = st.text_input("검색 키워드 입력 (쉼표로 구분)", value=", ".join(keywords))
if st.button("크롤링 시작"):
    st.info("잠시만 기다려주세요... ⏳")
    final_results = []
    for kw in [k.strip() for k in kw_input.split(",") if k.strip()]:
        final_results.extend(crawl_news(kw))
    df = pd.DataFrame(final_results)
    st.success(f"총 {len(df)}건 수집 완료!")
    st.dataframe(df)
    excel = BytesIO()
    df.to_excel(excel, index=False, engine="openpyxl")
    st.download_button("⬇️ 엑셀 다운로드", excel.getvalue(), file_name="출판사_뉴스_크롤링_결과.xlsx")
