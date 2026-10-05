import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
import urllib3

# SSL 인증서 경고 숨기기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 가격 추출 함수 (기존 로직 그대로)
def extract_price_sori(price_str):
    if not price_str or price_str == "가격미상": return 0
    match = re.search(r'([\d\.]+)\s*만', price_str)
    if match: return int(float(match.group(1)) * 10000)
    digits = re.sub(r'[^\d]', '', price_str)
    if digits: return int(digits)
    return 0

# 2. 모바일 화면 기본 설정
st.set_page_config(page_title="소리전자 계산기", page_icon="💰", layout="centered")

st.title("💰 소리전자 총액 계산기")
st.markdown("복사해온 텍스트를 아래에 붙여넣고 버튼을 누르세요.")

# 3. 입력 창 (모바일 환경에 맞게 높이 조절)
raw_text = st.text_area("텍스트 입력 (당근 픽업건 등 양식 그대로)", height=200)

# 4. 버튼 클릭 시 실행
if st.button("▶ 총액 계산하기", use_container_width=True):
    if not raw_text.strip():
        st.error("텍스트를 입력해주세요.")
    else:
        lines = raw_text.strip().split('\n')
        items = []
        current_title = "상품명 없음"
        
        # 텍스트 파싱
        for line in lines:
            line = line.strip()
            if not line: continue
            if re.match(r'^\d+\.', line):
                current_title = line
            elif line.startswith("http"):
                items.append({"title": current_title, "url": line})

        if not items:
            st.warning("❌ 텍스트 내에서 'http'로 시작하는 유효한 링크를 찾지 못했습니다.")
        else:
            total_price = 0
            session = requests.Session()
            
            # 💡 [수정됨] 봇 차단 우회를 위해 실제 브라우저처럼 강력한 헤더 적용
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.soriaudio.com/",
                "Connection": "keep-alive"
            }
            session.headers.update(headers)
            
            progress_text = f"총 {len(items)}개의 링크 확인 중..."
            my_bar = st.progress(0, text=progress_text)
            
            log_container = st.container()
            
            for i, item in enumerate(items):
                url = item["url"]
                title = item["title"]
                
                try:
                    # 💡 [수정됨] 타임아웃을 15초로 늘리고, SSL 인증서 무시(verify=False) 추가
                    res = session.get(url, timeout=15, verify=False)
                    
                    if res.status_code == 429:
                        with log_container:
                            st.error(f"**[{i+1}] {title}**\n\n❌ 차단됨 (429 Too Many Requests)")
                        continue
                    elif res.status_code != 200:
                        with log_container:
                            st.error(f"**[{i+1}] {title}**\n\n❌ 접근 오류 (상태 코드: {res.status_code})")
                        continue

                    soup = BeautifulSoup(res.text, 'html.parser')
                    page_text = soup.get_text()
                    
                    price_raw = ""
                    for text_line in page_text.split('\n'):
                        if not price_raw and any(k in text_line for k in ["판매가", "가격", "금액"]) and ":" in text_line:
                            price_raw = re.sub(r'/\s*직거래|/\s*착불', '', text_line.split(":", 1)[1]).strip()
                            break
                    
                    if not price_raw:
                        for b_tag in soup.find_all('b'):
                            if '판매가' in b_tag.text:
                                price_raw = b_tag.text.replace('판매가', '').replace(':', '').replace('/직거래', '').strip()
                                break
                                
                    actual_price = extract_price_sori(price_raw)
                    total_price += actual_price
                    
                    # 로그 출력
                    with log_container:
                        if actual_price > 0:
                            st.success(f"**[{i+1}] {title}**\n\n확인된 가격: {actual_price:,} 원")
                        else:
                            st.warning(f"**[{i+1}] {title}**\n\n⚠️ 가격 인식 실패 (수동 확인 필요)")
                            
                except Exception as e:
                    with log_container:
                        st.error(f"**[{i+1}] {title}**\n\n❌ 페이지 접근 타임아웃 및 연결 오류")

                # 서버 과부하 방지를 위해 딜레이 추가 (매우 중요)
                time.sleep(1)
                
                # 프로그레스 바 업데이트
                my_bar.progress((i + 1) / len(items), text=progress_text)
                
            # 최종 결과 크게 표시
            st.divider()
            st.metric(label="✨ 총 합계 금액", value=f"{total_price:,} 원")
            st.balloons()
