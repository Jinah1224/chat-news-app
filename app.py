from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import pandas as pd
import time

CHROMEDRIVER_PATH = "C:/Users/mungk/chromedriver-win64/chromedriver.exe"
keywords = ["천재교육", "천재교과서", "지학사", "벽호", "프린피아", "미래엔", "교과서", "동아출판"]

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)

results = []
seen_urls = set()
seen_summaries = set()

# ✅ 카테고리 분류 함수
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
    elif any(word in text for word in ["에듀테크", "디지털교육", "디지털 교육", "ai교육", "ai 교육", "스마트교육", "스마트 교육"]):
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

# ✅ 출판사명 추출 함수
def extract_publisher(text):
    text = text.lower()
    for pub in keywords:
        if pub.lower() in text:
            return pub
    return "기타"

# ✅ 날짜 추출 함수 (메타태그 기반)
def get_date_from_news_url(news_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(news_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'lxml')

        meta_tags = [
            ("meta", {"property": "article:published_time"}),
            ("meta", {"name": "date"}),
            ("meta", {"property": "og:article:published_time"})
        ]
        for tag, attrs in meta_tags:
            meta = soup.find(tag, attrs)
            if meta and meta.get("content"):
                return meta["content"][:10].replace("-", ".")

        text = soup.get_text(" ", strip=True)
        for word in text.split():
            for fmt in ["%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"]:
                try:
                    dt = datetime.strptime(word[:10], fmt)
                    return dt.strftime("%Y.%m.%d")
                except:
                    continue
        return "날짜 없음"
    except:
        return "날짜 오류"

# ✅ 본문 텍스트 추출
def get_body_text(news_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(news_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'lxml')
        candidates = ["article", "article-body", "newsEndContents", "content", "viewContent"]
        for class_name in candidates:
            tag = soup.find(class_=class_name)
            if tag:
                return tag.get_text(separator=" ", strip=True).lower()
        return soup.get_text(separator=" ", strip=True).lower()
    except:
        return ""

# ✅ 출판사 관련 여부 확인
def is_related_to_publisher(text):
    text = text.lower()
    for pub in keywords:
        if pub.lower() in text:
            return "O"
    return "X"

# ✅ 본문 내 교과서 또는 발행사 언급 여부
def check_textbook_or_publisher_in_body(body_text):
    if "교과서" in body_text or "발행사" in body_text:
        return "O"
    return "X"

# ✅ 뉴스 크롤링 실행
for keyword in keywords:
    print(f"🔍 검색어: {keyword}")

    for page in range(1, 21):
        start = (page - 1) * 10 + 1
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1&nso=so%3Add%2Cp%3A2w&start={start}"
        driver.get(url)
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, 'lxml')
        articles = soup.select(".news_area")

        print(f"📄 {keyword} {page}페이지 기사 수: {len(articles)}")
        if not articles:
            break

        for article in articles:
            try:
                title_elem = article.select_one(".news_tit")
                title = title_elem.get("title")
                link = title_elem.get("href")
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                summary = article.select_one(".dsc_txt_wrap").get_text(strip=True) if article.select_one(".dsc_txt_wrap") else ""
                if summary in seen_summaries:
                    continue
                seen_summaries.add(summary)

                press = article.select_one(".info_group a").get_text(strip=True) if article.select_one(".info_group a") else ""
                body_text = get_body_text(link)
                full_text = (summary + " " + body_text).strip()

                date = get_date_from_news_url(link)
                publisher = extract_publisher(full_text)
                category = categorize(full_text)
                match_check = is_related_to_publisher(full_text)
                body_check = check_textbook_or_publisher_in_body(body_text)

                results.append({
                    "출판사명": publisher,
                    "카테고리": category,
                    "날짜": date,
                    "제목": title,
                    "URL": link,
                    "요약": summary,
                    "언론사": press,
                    "내용점검": match_check,
                    "본문내_교과서_또는_발행사_언급": body_check
                })
            except Exception as e:
                print(f"[오류] {keyword} {page}페이지 처리 중 문제 발생: {e}")
        time.sleep(0.3)

driver.quit()
df = pd.DataFrame(results)
df.to_excel("출판사_뉴스_크롤링_결과.xlsx", index=False, engine="openpyxl")
print("✅ 크롤링 완료! '출판사_뉴스_크롤링_결과.xlsx' 생성됨.")
