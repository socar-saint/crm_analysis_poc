"""컬럼 설명 JSON 정의"""

# 쏘카 CRM 데이터 컬럼 설명
COLUMN_DESCRIPTIONS = {
    "실행일": "CRM 문구를 실험군, 대조군에게 문구를 전송한 날짜 : This is the date when the CRM action was sent to the test and control groups, Column type is date",
    "퍼널": "모바일 앱에서 유저가 이탈한 퍼널 단계, 해당 퍼널에서 이탈한 유저 대상으로 CRM 문구를 전송함 : The funnel stage where users have exited the mobile app, and the CRM action was sent to those users, Column type is String",
    "소재": "CRM 마케터가 문구를 유저에게 전송해 개선하고자 한 목적 : The purpose of the CRM action to improve the problem , ( i.e : FOMO는 Fear of Missing Out 으로서 고객이 조회한 차량을 놓칠 수 있다는 공포 마케팅 방법. 주행요금 개편은 주행 요금 개편 내용을 고객에게 알려 예약 전환을 유도한 것, 이탈은 이탈한 유저에게 전송하여 예약 전환을 유도한 것, 실적 대응은 CRM 마케터가 실적을 올리기 위한 진행한 액션), Column type is String",
    "목적": "CRM 마케터가 해당 퍼널 단계에서 해당 문구로 예약 전환율을 높이기 위해 전송한 목적 : The purpose of the CRM action, 목적은 소재를 통해 개선하고자 한 목적을 보다 세부적으로 설명하고 있음. Column type is String", 
    "타겟": "타겟은 퍼널에서 이탈 한 고객군 중, 보다 세부적으로 타겟팅을 정밀화 한 내용임. i.e) 타겟이 T4_존 마커 클릭 유저라면, 해당 퍼널 단계에서 이탈한 유저이지만 타겟이 - 이용시간 3일 이상 설정 후 제주공항존(5개) 클릭했으나 1시간 내 예약전환 없는 회원 - 여행존(제주) 캠페인에 진입한 회원 제외 라고 기술되어 있으면. 이는 그 유저들 중, 타겟에 설명된 세부 유저 대상으로 문구를 보냈다는 말임, Column type is String",
    "이탈 가설": "퍼널 단계 고객들이 이탈했을 것 같은 이유를 추정한 가설 : A hypothesis about why customers in the funnel stage might have exited, Column type is String",
    "문구": "퍼널 단계에서 이탈한 고객에게 CRM 마케팅으로 사용한 문구 : The CRM marketing message used for customers who exited the funnel stage, #NAME 이라고 된 부분은 고객의 이름이 개인화 되어 들어가는 곳, 예시 (광고)[쏘카] 부산 카셰어링 60% 쿠폰 도착! (광고)[쏘카] 부산 카셰어링 60% 쿠폰 도착! 부산 여행 준비 중이신 #NAME님께만 드리는 【3종 패키지 혜택】이 도착했어요. ■ 혜택 대상자: #NAME님 ■ 혜택 내용: ① 부산 전용 60% 쿠폰 - 쿠폰명: [오늘하루] 대여요금 60% 할인 (24시간 이상) - 쿠폰 사용 기간: 발급일로부터 1일 - 사용 가능 지역: 부산 쏘카존 ② 주행요금 무료 혜택 - 전기차: 주행거리 무제한 무료 - 일반 차종: 50km까지 무료 ③ 보험 및 보장상품 무료 - 사고 시 최대 70만원 '실속보장' 상품 → 0원 제공 ▼ 지금 바로 확인하기 링크 * 무료수신거부 : 080-808-0169, Column type is string",
    "랜딩": "고객이 해당 CRM 마케팅을 통해 앱으로 접속시, 랜딩되는 페이지 정보를 의미함 : The information about the page that the customer lands on when they access the app through the CRM marketing message, 가지러가기는 쏘카존에서 차량을 빌릴 수 있는 페이지, 여기로 부르기는 부름이라는 쏘카 서비스가 있는데 차량을 유저가 원하는 위치에 차량을 부를 수 있는 서비스를 의미함. 해당 페이지로 랜딩 시키는 것. 마지막 탐색존은 고객이 앱 사용 중 마지막으로 차량을 탐색했던 존을 의미함. Column type is String",
    "추가 혜택": "CRM 마케팅으로 제공되는 추가 혜택 : The additional benefits provided by the CRM marketing, Column type is String",
    "채널": "마케팅 채널 : The marketing channel, Column type is String",
    "서비스 생애 단계": "고객의 쏘카 서비스 이용 단계 : The service life stage of the customer, 신규회원, 당일 접속, 3일 내 접속 등, 이탈 회원은 30일이내 접속 한 회원, Column type is String" ,
    "타겟 연령": "타겟 고객의 연령대, NULl 값은 전체 연령 대상으로 진행한 것 : The age of the target customer, Null value means the entire age target is conducted. The Null 값이 아닌 경우는 해당 연령 대상으로 진행한 것임, Column type is String",
    "설정시간": "쏘카는 차량을 10분 단위로 본인이 원하는 시간만큼 차량을 예약 하고 빌리는 시스템임. 설정시간은 CRM 마케팅 전송시 해당 조건에 맞는 유저들만 보낸 것으로 필터를 건 것임 . i.e : 4시간 미만은 대여 시작 시간을 10:00 - 13:59 미만으로 세팅한 유저들만 해당 조건으로 필터에 부합하는 유저들만 보낸 것. The system of socar is to reserve and rent the vehicle by 10 minute units and user can make it whatever time they want. The setting time is the time set for the customer to rent the vehicle when the CRM marketing message is sent. The customer receives the message with the setting time when they access the app after receiving the CRM marketing message. i.e : 4시간 미만은 4시간 미만 대여로 세팅. 4시간 이상 ~ 10시간 미만은 해당 시간 대여로 세팅. 48 시간 이상은 ~ 48시간 이상 대여로 세팅. Column type is String",
    "리드타임": "리드타임은 차량 출발 시작 시간과 예약을 생성한 시작 시간 차이를 의미함. CRM 마케팅 전송시 해당 조건에 맞는 유저들만 보낸 것으로 필터를 건 것임. The lead time is the difference between the vehicle departure start time and the start time of the reservation created. The CRM marketing message is sent to the users who meet the condition. The users who meet the condition are filtered and sent. i.e : 4시간 미만은 4시간 미만 대여로 리드타임이 세팅 된 사람 . 4시간 이상 ~ 10시간 미만은 해당 시간 대여로 세팅 된 사람. 48 시간 이상은 ~ 48시간 이상 대여로 세팅 된 사람.",
    "출발시각": "차량이 출발되는 시작 시간을 의미함 : The start time of the vehicle departure, Column type is actually datetime, however the content is string",
    "차종": "차량 종류 : The vehicle type, Column type is String",
    "실험군": "실험군은 A/B Test 대상에 해당 메세지를 받은 유저들임 : The test group is the users who received the message in the A/B test target. Variant is the variant of the message that the user received. TG_푸시_남성은 남성 푸시 실험군, TG_푸시_여성은 여성 푸시 실험군. Column type is String",
    "발송": "실험군에게 문구를 전송한 건수 : The number of messages sent to the test group, Column type is Integer and counts by variant",
    "1일이내 예약생성": "실험군 중 1일 이내 예약 생성 건수 : The number of reservations created within 1 day in the test group, Column type is float and counts by variant",
    "예약전환율": "예약 전환율 : The reservation conversion rate, Column type is float and conversion rate by variant",
    "3일이내 예약생성": "실험군 중 3일 이내 예약 생성 건수 : The number of reservations created within 3 days in the test group, Column type is float and counts by variant",
    "예약전환율.1": "3일 이내 예약 전환율 : The reservation conversion rate within 3 days and conversion rate by variant",
    "7일이내 예약생성": "실험군 중 7일 이내 예약 생성 건수 : The number of reservations created within 7 days in the test group and counts by variant",
    "예약전환율.2": "7일 이내 예약 전환율 : The reservation conversion rate within 7 days and conversion rate by variant",
    "대조군": "대조군은 A/B Test 대상에 해당 메세지를 받지 않은 유저들임 : The control group is the users who did not receive the message in the A/B test target",
    "발송.1": "대조군 발송 건수, 원래는 대조군이기 때문에 메세지를 수신하지 말아야 하나, 데이터 추출 시 대조군에게 메세지를 전송한 건수를 의미함 : The number of messages sent to the control group",
    "1일이내 예약생성.1": "대조군 1일 이내 예약 생성 건수 : The number of reservations created within 1 day in the control group, Column type is float and counts by control",
    "예약전환율.3": "대조군 예약 전환율 : The reservation conversion rate in the control group and conversion rate by control",
    
    # 전처리 후 컬럼명들
    "실험군_발송": "실험군에게 문구를 전송한 건수",
    "실험군_1일이내_예약생성": "실험군 중 1일 이내 예약 생성 건수",
    "실험군_예약전환율": "실험군 예약 전환율",
    "실험군_3일이내_예약생성": "실험군 중 3일 이내 예약 생성 건수",
    "실험군_3일이내_예약전환율": "실험군 3일 이내 예약 전환율",
    "실험군_7일이내_예약생성": "실험군 중 7일 이내 예약 생성 건수",
    "실험군_7일이내_예약전환율": "실험군 7일 이내 예약 전환율",
    "대조군_발송": "대조군 발송 건수",
    "대조군_1일이내_예약생성": "대조군 1일 이내 예약 생성 건수",
    "대조군_예약전환율": "대조군 예약 전환율"
}

# 간단한 컬럼 설명 (Agent용)
SIMPLE_COLUMN_DESCRIPTIONS = {
    "실행일": "CRM 문구를 실험군, 대조군에게 문구를 전송한 날짜",
    "퍼널": "모바일 앱에서 유저가 이탈한 퍼널 단계",
    "문구": "퍼널 단계에서 이탈한 고객에게 CRM 마케팅으로 사용한 문구",
    "채널": "마케팅 채널 (푸시, 인앱, SMS 등)",
    "실험군_발송": "실험군에게 문구를 전송한 건수",
    "실험군_예약전환율": "실험군 예약 전환율",
    "대조군_발송": "대조군 발송 건수",
    "대조군_예약전환율": "대조군 예약 전환율"
}

