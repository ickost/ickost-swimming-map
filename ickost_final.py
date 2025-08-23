#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from flask import Flask, render_template_string, jsonify, request
import folium
import json
import requests
from datetime import datetime
import os
from urllib.parse import quote

app = Flask(__name__)


# API 키를 환경변수로 변경
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
CHANNEL_ID = os.getenv('CHANNEL_ID', 'UC82OkWXaNdFQb10wm-OY2YA')

def extract_video_id(url):
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)',
        r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_duration(duration):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return "0:00"
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def format_view_count(count):
    count = int(count)
    if count >= 10000:
        return f"{count/10000:.1f}만"
    elif count >= 1000:
        return f"{count/1000:.1f}천"
    else:
        return str(count)

def format_date(date_str):
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime('%Y년 %m월 %d일')
    except:
        return date_str

def parse_view_count(view_str):
    """조회수 문자열을 숫자로 변환"""
    if not view_str:
        return 0
    view_str = str(view_str).replace(',', '')
    if '만' in view_str:
        return int(float(view_str.replace('만', '')) * 10000)
    elif '천' in view_str:
        return int(float(view_str.replace('천', '')) * 1000)
    return int(view_str) if view_str.isdigit() else 0


def get_youtube_video_info(video_url):
    video_id = extract_video_id(video_url)
    print(f"Video ID: {video_id}")
    print(f"API Key exists: {bool(YOUTUBE_API_KEY)}")

    if not video_id or not YOUTUBE_API_KEY:
        print("API 키가 없거나 video_id가 없음")
        return {
            # ... 기본값
        }
    
    try:
        url = f"https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,contentDetails,statistics',
            'id': video_id,
            'key': YOUTUBE_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            item = data['items'][0]
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})
            statistics = item.get('statistics', {})
            
            view_count = statistics.get('viewCount', '0')
            formatted_views = format_view_count(int(view_count))
            
            return {
                'duration': format_duration(content_details.get('duration', 'PT0S')),
                'viewCount': formatted_views,
                'publishedAt': format_date(snippet.get('publishedAt', '')),
                'title': snippet.get('title'),
                'description': snippet.get('description', '')[:100] + '...' if len(snippet.get('description', '')) > 100 else snippet.get('description', ''),
                'viewCountNum': int(view_count)
            }
    except Exception as e:
        print(f"YouTube API 오류: {e}")
    
    return {
        'duration': '8:45',
        'viewCount': '2.1만',
        'publishedAt': '2024년 8월 21일',
        'title': None,
        'description': '',
        'viewCountNum': 21000
    }

def get_channel_info():
    try:
        url = f"https://www.googleapis.com/youtube/v3/channels"
        params = {
            'part': 'snippet,statistics',
            'id': CHANNEL_ID,
            'key': YOUTUBE_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            item = data['items'][0]
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            
            subscriber_count = statistics.get('subscriberCount', '0')
            video_count = statistics.get('videoCount', '0')
            
            if subscriber_count == '0' or not subscriber_count:
                subscriber_display = '구독자 수 비공개'
            else:
                subscriber_display = format_view_count(int(subscriber_count))
            
            thumbnails = snippet.get('thumbnails', {})
            thumbnail_url = (
                thumbnails.get('high', {}).get('url') or
                thumbnails.get('medium', {}).get('url') or 
                thumbnails.get('default', {}).get('url') or
                'https://yt3.googleusercontent.com/ytc/AIdro_kKZQj_1yJSZS-8l3v1kS_CXQwc8XggO4ybfQ=s176-c-k-c0x00ffffff-no-rj'
            )
            
            return {
                'subscriberCount': subscriber_display,
                'videoCount': video_count,
                'title': snippet.get('title', 'ICKOST'),
                'thumbnail': thumbnail_url
            }
    except Exception as e:
        print(f"채널 정보 오류: {e}")
    
    return {
        'subscriberCount': '5.2만',
        'videoCount': '127',
        'title': 'ICKOST',
        'thumbnail': 'https://yt3.googleusercontent.com/2pvoyX_JUZFcrn1RD1I9SCIUF62jvpkxaK77UNs50TtM8GkjyprLPu5cIPcmE9ribNOGqL9kRA=s160-c-k-c0x00ffffff-no-rj'
    }

def get_difficulty_color(difficulty):  
    """난이도별 색상 반환 (빨간색 계열)"""
    colors = {
        "초급": "#00ff00",  # 초록색
        "중급": "#ffaa00",
        "고급": "#ff4444"
    }
    return colors.get(difficulty, "#aaaaaa")

def get_marker_size(rating):
    """평점별 마커 크기 반환"""
    if rating >= 4.0:
        return 40
    elif rating >= 3.5:
        return 35
    else:
        return 30

# 새로운 데이터 구조: 장소 중심으로 변경
SPOT_DATA = {
    "제주도": {
        "spots": {
            "삼양감수탕": {
                "title": "삼양감수탕",
                "description": "제주도 바다수영의 성지",
                "coordinates": [33.525243, 126.583098],
                "distance": "1.9km",
                "rating": 4.1,
                "difficulty": "초급",
                "videos": [
                    {
                        "url": "https://youtu.be/CQ8i9V3n_3U?si=3uqkoRLkfGCWE06a",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/p8YGkJoVPco?si=TUBu_WhH77Sum5oh",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/7VMPyljXGv0?si=MJ1366Go-KGWNjyo",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/htnMQwzmdaQ?si=LN7wYmKmdaXzBypw",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/6bWNajCNrt8?si=_Nch-dXXw7K9lq6Z",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/-5QpEY9S5g4?si=LhlIoRejtcO4JCAy",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/dsHFIixRKFw?si=EVZym775mKsRRnSW",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/b1SoJSyZMBw?si=J84yN0XnpaZuSDXk",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/b1SoJSyZMBw?si=9fgPNqOx6mcF0QBq",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/q9LnrmDmWuw?si=eb8AefK1M522tuS6",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/Xeo94s4KURs?si=9maUUwKZhZzgAyZG",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/M2HNuVOk6tg?si=m7yknyQVioQn1j7s",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/f8rCkjIXzCY?si=gYSOnfPePhoWQcpL",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/X1C9sXAloIg?si=LspNc2b5naScctgf",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/Qsa2CV8yE2o?si=TCycvMNQ-QfbMdii",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/t-UMJz_QSZA?si=WjWrsoMTKml1hCrT",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/wfXuyFK92b0?si=q5RFq90oDz8lQOid",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    },
                    {
                        "url": "https://youtu.be/s5edMpRVxSc?si=ETiyUA7OLlYw-Bw3",
                        "title": "삼양감수탕 첫 방문",
                        "description": "제주도 바다수영 입문자를 위한 완벽한 장소"
                    }



                ]
            },
            "용담포구": {
                "title": "용담포구(용두암)",
                "description": "제주에서의 시티뷰",
                "coordinates": [33.518360, 126.501244],
                "distance": "2km",
                "rating": 3.6,
                "difficulty": "초급",
                "videos": [
                    {
                        "url": "https://youtu.be/vrMIBOMAE6Y?si=q7_W4aUSJTpHRmip",
                        "title": "용담포구 수영",
                        "description": "용두암을 배경으로 한 시티뷰 수영"
                    },
{
                        "url": "https://youtu.be/dtbjk7aZNeQ",
                        "title": "용담포구 수영",
                        "description": "용두암을 배경으로 한 시티뷰 수영"
                    }
                ]
            },
            "현사포구": {
                "title": "현사포구",
                "description": "500미터 인터벌 훈련",
                "coordinates": [33.498385, 126.449710],
                "distance": "500m",
                "rating": 3.5,
                "difficulty": "초급",
                "videos": [
                    {
                        "url": "https://youtu.be/ZlPalFpXqxc",
                        "title": "현사포구 인터벌 훈련",
                        "description": "500미터 인터벌 훈련 완주 도전"
                    },
                    {
                        "url": "https://youtu.be/gyA6zATW1dM",
                        "title": "현사포구 인터벌 훈련",
                        "description": "500미터 인터벌 훈련 완주 도전"
                    },
                    {
                        "url": "https://youtu.be/eG0j0P4lYPE",
                        "title": "현사포구 인터벌 훈련",
                        "description": "500미터 인터벌 훈련 완주 도전"
                    }
                ]
            },
            "구엄포구": {
                "title": "구엄포구-고내리포구",
                "description": "물고기 천국, 낚시포인트",
                "coordinates": [33.483416, 126.376398],
                "distance": "2.8km",
                "rating": 4.1,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/DwlhJyBMp4U",
                        "title": "구엄포구 장거리 수영",
                        "description": "물고기들과 함께하는 2.8km 바다수영"
                    },
{
                        "url": "https://youtu.be/jHV5KQXooC0",
                        "title": "구엄포구 장거리 수영",
                        "description": "물고기들과 함께하는 2.8km 바다수영"
                    }
                ]
            },
            "곽지해수욕장": {
                "title": "곽지해수욕장",
                "description": "다양한 바다를 만날 수 있음",
                "coordinates": [33.449486, 126.303061],
                "distance": "3km",
                "rating": 3.7,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/H6X039gZHdM?si=u4srpYIX2tR-90GZ",
                        "title": "곽지해수욕장 수영",
                        "description": "제주 서쪽 바다의 아름다운 색깔들"
                    },
                    {
                        "url": "https://youtu.be/iDqkKgDel3M?si=1R--ZZW6BXGhcSYo",
                        "title": "곽지해수욕장 수영",
                        "description": "제주 서쪽 바다의 아름다운 색깔들"
                    },
                    {
                        "url": "https://youtu.be/jsBT-sIBX48?si=YyW_6jCXAd6bBUKO",
                        "title": "곽지해수욕장 수영",
                        "description": "제주 서쪽 바다의 아름다운 색깔들"
                    },
                    {
                        "url": "https://youtu.be/l0lDyQEpB7k?si=U12DHYjkJW7RzM6g",
                        "title": "곽지해수욕장 수영",
                        "description": "제주 서쪽 바다의 아름다운 색깔들"
                    },
                    {
                        "url": "https://youtu.be/kFPZLJFJvFw?si=yqw6GHz51Fy8Q4jn",
                        "title": "곽지해수욕장 수영",
                        "description": "제주 서쪽 바다의 아름다운 색깔들"
                    },
                    {
                        "url": "https://youtu.be/KH6Yam2gxUI?si=0nZPrD3-hieyX6nx",
                        "title": "곽지해수욕장 수영",
                        "description": "제주 서쪽 바다의 아름다운 색깔들"
                    },
                    {
                        "url": "https://youtu.be/QzolOa2Op4Q?si=f8lqVnvicYOnj7x6",
                        "title": "곽지해수욕장 수영",
                        "description": "제주 서쪽 바다의 아름다운 색깔들"
                    },
                    {
                        "url": "https://youtu.be/qJYm2Eqg4fI?si=vdYJBoL98x6YQiA9",
                        "title": "곽지해수욕장 수영",
                        "description": "제주 서쪽 바다의 아름다운 색깔들"
                    },
                    {
                        "url": "https://youtu.be/ST9Q3KQsQr4?si=FyT9I_Rg5rVZEGQy",
                        "title": "곽지해수욕장 수영",
                        "description": "제주 서쪽 바다의 아름다운 색깔들"
                    }

                ]
            },
            "비양도": {
                "title": "비양도",
                "description": "섬을 한바퀴 도는 경험",
                "coordinates": [33.406378, 126.231167],
                "distance": "3.8km",
                "rating": 3.9,
                "difficulty": "고급",
                "videos": [
                    {
                        "url": "https://youtu.be/4G6gIcR9PoQ",
                        "title": "비양도 일주 수영",
                        "description": "작은 섬을 한바퀴 도는 도전"
                    }
                ]
            },
            "송악산항": {
                "title": "송악산항-하도방파제",
                "description": "서쪽제1경 송악산 한바퀴",
                "coordinates": [33.205401, 126.290239],
                "distance": "3.2km",
                "rating": 3.7,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/mW-nnFWoruo",
                        "title": "송악산 해안 수영",
                        "description": "제주 서쪽 절경을 바다에서 감상하기"
                    }
                ]
            },
            "사계항": {
                "title": "사계항(용머리바위)",
                "description": "바다에서 바라보는 용머리바위",
                "coordinates": [33.230389, 126.309630],
                "distance": "2km",
                "rating": 4.0,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/EeCD-p8GdZw",
                        "title": "사계항 용머리바위 수영",
                        "description": "바다에서만 볼 수 있는 용머리바위의 진면목"
                    }
                ]
            },
            "월평포구": {
                "title": "월평포구-해송횟집(진곶내)",
                "description": "오로지 물길로만 가능한 곳, 진곳",
                "coordinates": [33.234547, 126.463455],
                "distance": "3.4km",
                "rating": 3.8,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/qDBFv4rKnxQ",
                        "title": "진곶내 수영",
                        "description": "오로지 물길로만 가능한 곳"
                    },
                    {
                        "url": "https://youtu.be/56OoUGdUNFY",
                        "title": "진곶내 수영",
                        "description": "오로지 물길로만 가능한 곳"
                    }
                ]
            },
            "새연교": {
                "title": "새연교-돔베낭골(외돌개)",
                "description": "서귀포 필수코스",
                "coordinates": [33.239074, 126.558384],
                "distance": "3.6km",
                "rating": 3.8,
                "difficulty": "고급",
                "videos": [
                    {
                        "url": "https://youtu.be/WwQ7GhNW1dQ",
                        "title": "외돌개 수영",
                        "description": "서귀포 필수코스 바다수영"
                    }
                ]
            },
            "자구리": {
                "title": "자구리-구두미포구(정방폭포)",
                "description": "바다로 떨어지는 폭포",
                "coordinates": [33.243282, 126.568774],
                "distance": "3.8km",
                "rating": 3.5,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/lWivFkLGLPA",
                        "title": "정방폭포 수영",
                        "description": "바다로 떨어지는 폭포를 보며 수영하기"
                    },
                    {
                        "url": "https://youtu.be/ZOmoD6ffqTw",
                        "title": "정방폭포 수영",
                        "description": "바다로 떨어지는 폭포를 보며 수영하기"
                    }
                ]
            },
            "태웃개": {
                "title": "태웃개",
                "description": "다이빙의 성지에서 바다수영",
                "coordinates": [33.270104, 126.691575],
                "distance": "4km",
                "rating": 3.8,
                "difficulty": "고급",
                "videos": [
                    {
                        "url": "https://youtu.be/HFfRwPig89g",
                        "title": "태웃개 수영",
                        "description": "다이빙의 성지에서 바다수영 도전"
                    }
                ]
            },
            "신양섭지해수욕장": {
                "title": "신양섭지해수욕장(섭지코지)",
                "description": "섭지코지 한바퀴, 바다거북 출현",
                "coordinates": [33.436283, 126.924772],
                "distance": "5km",
                "rating": 4.2,
                "difficulty": "고급",
                "videos": [
                    {
                        "url": "https://youtu.be/NUhttc9N1Ks",
                        "title": "섭지코지 수영",
                        "description": "섭지코지 한바퀴, 바다거북과의 만남"
                    }
                ]
            },
            "수마포구": {
                "title": "수마포구-우뭇개해안(성산일출봉)",
                "description": "제주 제1경을 바다에서 보는 맛",
                "coordinates": [33.460447, 126.933770],
                "distance": "3.5km",
                "rating": 4.2,
                "difficulty": "고급",
                "videos": [
                    {
                        "url": "https://youtu.be/Up1qNF8ES7o",
                        "title": "성산일출봉 수영",
                        "description": "제주 제1경을 바다에서 감상하며"
                    }
                ]
            },
            "하고수동해수욕장": {
                "title": "하고수동해수욕장(우도)",
                "description": "섬속의 섬에서",
                "coordinates": [33.514798, 126.958688],
                "distance": "1.8km",
                "rating": 3.6,
                "difficulty": "초급",
                "videos": [
                    {
                        "url": "https://youtu.be/-m8AwZlrwY4",
                        "title": "우도 수영",
                        "description": "섬속의 섬에서 바다수영"
                    }
                ]
            },
            "신동코지": {
                "title": "제주카약체험-신동코지불턱(토끼섬)",
                "description": "토끼섬엔 토끼가 없다",
                "coordinates": [33.515598, 126.902241],
                "distance": "3.4km",
                "rating": 3.9,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/46QuKrDwbwo4",
                        "title": "토끼섬 수영",
                        "description": "토끼섬엔 토끼가 없다는 이야기"
                    }
                ]
            },
            "월정투명카약": {
                "title": "월정투명카약-세기알해변",
                "description": "김녕의 보석",
                "coordinates": [33.566002, 126.779129],
                "distance": "3.1km",
                "rating": 3.4,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/Ml7Cb8eoyPQ",
                        "title": "세기알해변 수영",
                        "description": "김녕의 보석 같은 해변"
                    }
                ]
            },
            "북촌환해장성": {
                "title": "북촌환해장성-목지섬",
                "description": "다채로운 바다",
                "coordinates": [33.554748, 126.710768],
                "distance": "3.2km",
                "rating": 3.8,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/kKrNavJKpYc",
                        "title": "목지섬 수영",
                        "description": "다채로운 바다색깔을 만날 수 있는 곳"
                    }
                ]
            },
            "함덕해수욕장": {
                "title": "함덕해수욕장-해동포구",
                "description": "최상급 투명도",
                "coordinates": [33.544800, 126.674291],
                "distance": "1.9km",
                "rating": 4.2,
                "difficulty": "초급",
                "videos": [
                    {
                        "url": "https://youtu.be/fwAW_b_UdH4",
                        "title": "함덕해수욕장 수영",
                        "description": "최상급 투명도의 바다"
                    }
                ]
            },
            "관곶": {
                "title": "관곶-정주항",
                "description": "섬속을 누비는 즐거움",
                "coordinates": [33.555509, 126.644597],
                "distance": "3km",
                "rating": 3.8,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/mt4r9Hx9kBA",
                        "title": "정주항 수영",
                        "description": "섬속을 누비는 즐거운 수영"
                    }
                ]
            },
            "닭머르": {
                "title": "닭머르",
                "description": "아무나 올 수 없는 곳(사유지)",
                "coordinates": [33.535198, 126.603058],
                "distance": "2km",
                "rating": 3.4,
                "difficulty": "초급",
                "videos": [
                    {
                        "url": "https://youtu.be/KFYn3sPHKkw",
                        "title": "닭머르 수영",
                        "description": "아무나 올 수 없는 특별한 장소"
                    }
                ]
            }
        }
    },
    "부산": {
        "spots": {
            "해운대해수욕장": {
                "title": "해운대해수욕장",
                "description": "전국 바다수영의 성지",
                "coordinates": [35.1588, 129.1603],
                "distance": "1.5km",
                "rating": 3.7,
                "difficulty": "중급",
                "videos": [
                    {
                        "url": "https://youtu.be/tESMnqgBz7E",
                        "title": "해운대 바다수영",
                        "description": "부산 대표 해수욕장에서의 수영"
                    }
                ]
            },
            "송정해수욕장": {
                "title": "송정해수욕장",
                "description": "천지개벽한 송정앞바다",
                "coordinates": [35.1785, 129.1998],
                "distance": "1.5km",
                "rating": 3.2,
                "difficulty": "초급",
                "videos": [
                    {
                        "url": "https://youtu.be/u6GNpGfimaM",
                        "title": "송정해수욕장 수영",
                        "description": "조용한 송정에서의 바다수영"
                    }
                ]
            },
            "송도해수욕장": {
                "title": "송도해수욕장",
                "description": "시티뷰가 좋은 포인트",
                "coordinates": [35.075454, 129.017233],
                "distance": "1.5km",
                "rating": 3.4,
                "difficulty": "초급",
                "videos": [
                    {
                        "url": "https://youtu.be/e1Kp4Rzkis0",
                        "title": "송도해수욕장 수영",
                        "description": "시티뷰가 좋은 바다수영 포인트"
                    }
                ]
            }
        }
    },
    "경남": {
        "spots": {
            "구조라해수욕장": {
                "title": "구조라해수욕장",
                "description": "윤돌섬이 보이는 해파리천국",
                "coordinates": [34.810020, 128.686903],
                "distance": "3.2km",
                "rating": 3.5,
                "difficulty": "초급",
                "videos": [
                    {
                        "url": "https://youtu.be/bLmz_DcrTIw",
                        "title": "구조라해수욕장 수영",
                        "description": "거제도의 숨겨진 보석"
                    },
{
                        "url": "https://youtu.be/Bc2S6CaO7O8",
                        "title": "구조라해수욕장 수영",
                        "description": "거제도의 숨겨진 보석"
                    }
                ]
            }
        }
    }
}

def get_spot_main_video(spot_videos):
    """조회수가 가장 높은 영상을 메인 영상으로 선택"""
    if not spot_videos:
        return None
    
    max_views = 0
    main_video = spot_videos[0]
    
    for video in spot_videos:
        youtube_info = get_youtube_video_info(video['url'])
        views = youtube_info.get('viewCountNum', 0)
        if views > max_views:
            max_views = views
            main_video = video
    
    return main_video

def enrich_spot_data():
    """장소별 데이터를 YouTube 정보와 함께 enriched"""
    enriched_data = {}
    for location, data in SPOT_DATA.items():
        enriched_spots = []
        for spot_name, spot in data['spots'].items():
            # 메인 영상 선택 (조회수가 가장 높은 영상)
            main_video = get_spot_main_video(spot['videos'])
            if main_video:
                youtube_info = get_youtube_video_info(main_video['url'])
                video_id = extract_video_id(main_video['url'])
                
                enriched_spot = {
                    **spot,
                    'spot_id': spot_name,
                    'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    'duration': youtube_info['duration'],
                    'views': youtube_info['viewCount'],
                    'date': youtube_info['publishedAt'],
                    'video_count': len(spot['videos']),
                    'main_video_url': main_video['url']
                }
                enriched_spots.append(enriched_spot)
        enriched_data[location] = {'spots': enriched_spots}
    return enriched_data

def create_map(spot_data):
    m = folium.Map(
        location=[33.389153, 126.562724],
        zoom_start=9,
        tiles='CartoDB dark_matter'
    )
    
    for location, data in spot_data.items():
        for spot in data['spots']:
            popup_html = f"""
            <div style="width: 320px; font-family: 'Roboto', sans-serif; 
                        background: #181818; color: #ffffff; border-radius: 8px; overflow: hidden;">
                <div style="position: relative; background: #000; cursor: pointer;" 
                     onclick="window.open('/spot/{quote(location)}/{quote(spot['spot_id'])}', '_blank')">
                    <img src="{spot['thumbnail']}"
                         style="width: 100%; height: 180px; object-fit: cover; display: block;">
                    <div style="position: absolute; bottom: 8px; right: 8px; 
                                background: rgba(0,0,0,0.8); color: white; 
                                padding: 2px 6px; border-radius: 3px; font-size: 12px;">
                        {spot['duration']}
                    </div>
                    <div style="position: absolute; top: 8px; left: 8px; 
                                background: rgba(255,0,0,0.9); color: white; 
                                padding: 2px 6px; border-radius: 3px; font-size: 11px;">
                        {spot['video_count']}개 영상
                    </div>
                </div>
                <div style="padding: 12px;">
                    <h3 style="margin: 0 0 8px 0; font-size: 16px; color: #ffffff;">
                        {spot['title']}
                    </h3>
                    <div style="color: #aaaaaa; font-size: 13px; margin-bottom: 12px;">
                        조회수 {spot['views']}회 • {spot['date']}
                    </div>
                    <div style="color: #aaaaaa; font-size: 13px; margin-bottom: 12px;">
                        {spot['description']}
                    </div>
                    <div style="display: flex; gap: 16px; margin: 12px 0; padding: 8px 0; 
                                border-top: 1px solid #3d3d3d;">
                        <div style="text-align: center; color: #aaaaaa; font-size: 12px;">
                            <div style="color: #ffffff; font-weight: 500;">{spot['distance']}</div>
                            <div>거리</div>
                        </div>
                        <div style="text-align: center; color: #aaaaaa; font-size: 12px;">
                            <div style="color: {get_difficulty_color(spot['difficulty'])}; font-weight: 500;">{spot['difficulty']}</div>
                            <div>난이도</div>
                        </div>
                        <div style="text-align: center; color: #aaaaaa; font-size: 12px;">
                            <div style="color: #ffaa00; font-weight: 500;">★{spot['rating']}</div>
                            <div>평점</div>
                        </div>
                    </div>
                    <div style="margin-top: 12px;">
                        <button style="width: 100%; padding: 10px; 
                                       background: #cc0000; color: white; 
                                       border: none; border-radius: 6px; 
                                       font-size: 14px; font-weight: 500; 
                                       cursor: pointer; transition: background 0.2s ease;"
                                onmouseover="this.style.background='#aa0000'"
                                onmouseout="this.style.background='#cc0000'"
                                onclick="window.open('/spot/{quote(location)}/{quote(spot['spot_id'])}', '_blank')">
                            📍 장소 상세보기
                        </button>
                    </div>
                </div>
            </div>
            """
            
            marker_size = get_marker_size(spot['rating'])
            difficulty_color = get_difficulty_color(spot['difficulty'])

            marker_html = f'''
            <div style="width: {marker_size}px; height: {marker_size}px; background: {difficulty_color}; 
                        border: 3px solid #ffffff; border-radius: 50%; display: flex; align-items: center; 
                        justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,0.3); cursor: pointer;">
                <svg width="{int(marker_size*0.4)}" height="{int(marker_size*0.4)}" viewBox="0 0 24 24" fill="white">
                    <path d="M8 5v14l11-7z"/>
                </svg>
            </div>
            '''
            
            folium.Marker(
                location=spot['coordinates'],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"📍 {spot['title']} ({location}) - {spot['video_count']}개 영상",
                icon=folium.DivIcon(html=marker_html, icon_size=(marker_size, marker_size), icon_anchor=(marker_size//2, marker_size//2))
            ).add_to(m)
    
    return m

@app.route('/')
def index():
    try:
        enriched_spot_data = enrich_spot_data()
        channel_info = get_channel_info()
        folium_map = create_map(enriched_spot_data)
        map_html = folium_map._repr_html_()
        
        total_spots = sum(len(data['spots']) for data in enriched_spot_data.values())
        total_locations = len(enriched_spot_data)
        total_videos = sum(len(SPOT_DATA[location]['spots'][spot_name]['videos']) 
                          for location in SPOT_DATA 
                          for spot_name in SPOT_DATA[location]['spots'])
        
        all_ratings = []
        for location_data in SPOT_DATA.values():
            for spot in location_data['spots'].values():
                all_ratings.append(spot['rating'])
        avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
        
    except Exception as e:
        print(f"오류: {e}")
        enriched_spot_data = SPOT_DATA
        channel_info = get_channel_info()
        folium_map = create_map(enriched_spot_data)
        map_html = folium_map._repr_html_()
        total_spots = 10
        total_locations = 3
        total_videos = 10
        avg_rating = 4.0

    html = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ICKOST - 바다수영 채널</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Roboto', sans-serif; background-color: #0f0f0f; color: #ffffff; line-height: 1.4; }

        .header { 
            background: #212121; 
            padding: 12px 16px; 
            display: flex; 
            align-items: center; 
            position: sticky; 
            top: 0; 
            z-index: 100; 
            border-bottom: 1px solid #3d3d3d; 
        }
        .channel-info { display: flex; align-items: center; gap: 12px; flex: 1; }
        .channel-avatar { width: 40px; height: 40px; border-radius: 50%; overflow: hidden; }
        .channel-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .channel-details h1 { font-size: 18px; font-weight: 600; color: #ffffff; margin-bottom: 2px; }
        .channel-meta { color: #aaaaaa; font-size: 12px; }
        .subscribe-btn { 
            background: #cc0000; 
            color: white; 
            border: none; 
            padding: 8px 12px; 
            border-radius: 18px; 
            font-weight: 500; 
            font-size: 13px; 
            cursor: pointer; 
            transition: background 0.2s ease; 
        }
        .subscribe-btn:hover { background: #aa0000; }

        .container { 
            max-width: 1280px; 
            margin: 0 auto; 
            padding: 16px; 
        }

        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 12px; 
            margin-bottom: 24px; 
        }
        .stat-card { 
            background: #181818; 
            padding: 16px 12px; 
            border-radius: 12px; 
            text-align: center; 
            border: 1px solid #3d3d3d; 
        }
        .stat-number { 
            font-size: 20px; 
            font-weight: 700; 
            color: #ffffff; 
            display: block; 
            margin-bottom: 4px; 
        }
        .stat-label { color: #aaaaaa; font-size: 12px; }

        .map-section { margin-bottom: 32px; }
        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #ffffff; }
        .map-container { 
            background: #181818; 
            border-radius: 12px; 
            overflow: hidden; 
            box-shadow: 0 2px 16px rgba(0,0,0,0.4); 
            height: 400px; 
        }
        .map-container iframe { width: 100% !important; height: 100% !important; }

        .location-section { margin-bottom: 32px; }
        .location-header { display: flex; align-items: center; margin-bottom: 16px; gap: 12px; flex-wrap: wrap; }
        .location-title { font-size: 18px; font-weight: 600; color: #ffffff; }
        .spot-count { background: #3d3d3d; color: #aaaaaa; padding: 4px 8px; border-radius: 12px; font-size: 11px; }

        .sort-controls { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
        .sort-label { color: #aaaaaa; font-size: 13px; }
        .sort-select { 
            background: #181818; 
            color: #ffffff; 
            border: 1px solid #3d3d3d; 
            border-radius: 8px; 
            padding: 8px 12px; 
            font-size: 13px; 
            cursor: pointer; 
        }

        .spots-grid { 
            display: grid; 
            grid-template-columns: 1fr; 
            gap: 16px; 
        }
        .spot-card { 
            background: #181818; 
            cursor: pointer; 
            transition: transform 0.2s ease; 
            display: flex; 
            gap: 12px; 
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #3d3d3d;
        }
        .spot-card:hover { transform: translateY(-2px); }

        .spot-thumbnail { 
            position: relative; 
            width: 120px; 
            height: 90px; 
            flex-shrink: 0;
        }
        .spot-thumbnail img { width: 100%; height: 100%; object-fit: cover; }
        .spot-duration { 
            position: absolute; 
            bottom: 4px; 
            right: 4px; 
            background: rgba(0,0,0,0.8); 
            color: white; 
            padding: 2px 4px; 
            border-radius: 3px; 
            font-size: 10px; 
        }
        .video-count-badge { 
            position: absolute; 
            top: 4px; 
            left: 4px; 
            background: rgba(255,0,0,0.9); 
            color: white; 
            padding: 2px 6px; 
            border-radius: 3px; 
            font-size: 10px; 
            font-weight: 500;
        }
        .spot-overlay { 
            position: absolute; 
            top: 0; 
            left: 0; 
            right: 0; 
            bottom: 0; 
            background: rgba(0,0,0,0.3); 
            opacity: 0; 
            transition: opacity 0.2s ease; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }
        .spot-card:hover .spot-overlay { opacity: 1; }
        .play-btn { 
            width: 24px; 
            height: 24px; 
            background: rgba(255,255,255,0.9); 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }

        .spot-info { 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            justify-content: space-between; 
            padding: 12px;
        }
        .spot-title { 
            font-size: 14px; 
            font-weight: 600; 
            color: #ffffff; 
            margin-bottom: 4px; 
            line-height: 1.3; 
        }
        .spot-description { 
            color: #aaaaaa; 
            font-size: 12px; 
            margin-bottom: 8px; 
            line-height: 1.4; 
            overflow: hidden; 
            display: -webkit-box; 
            -webkit-line-clamp: 2; 
            -webkit-box-orient: vertical; 
        }
        .spot-meta { color: #aaaaaa; font-size: 11px; margin-bottom: 6px; }
        .spot-stats { 
            display: flex; 
            gap: 12px; 
            font-size: 11px; 
            flex-wrap: wrap; 
        }
        .spot-stat { color: #aaaaaa; }
        .difficulty-초급 { color: #00ff00; }
        .difficulty-중급 { color: #ffaa00; }
        .difficulty-고급 { color: #ff4444; }
 
        @media (min-width: 480px) {
            .header { padding: 16px 20px; }
            .channel-avatar { width: 48px; height: 48px; }
            .channel-details h1 { font-size: 20px; }
            .channel-meta { font-size: 13px; }
            .subscribe-btn { padding: 10px 16px; font-size: 14px; }
            .container { padding: 20px; }
            .stat-number { font-size: 24px; }
            .stat-label { font-size: 13px; }
            .section-title { font-size: 20px; }
            .map-container { height: 500px; }
            .spots-grid { grid-template-columns: 1fr; gap: 20px; }
            .spot-thumbnail { width: 160px; height: 120px; }
            .spot-title { font-size: 15px; }
        }

        @media (min-width: 768px) {
            .header { padding: 20px 24px; }
            .container { padding: 24px; }
            .stats-grid { gap: 16px; }
            .stat-card { padding: 20px; }
            .stat-number { font-size: 28px; }
            .stat-label { font-size: 14px; }
            .map-container { height: 600px; }
            .spots-grid { grid-template-columns: repeat(2, 1fr); }
            .spot-card { display: block; }
            .spot-thumbnail { width: 100%; height: 200px; }
            .spot-info { padding: 16px; }
            .spot-title { font-size: 16px; }
        }

        @media (min-width: 1024px) {
            .spots-grid { grid-template-columns: repeat(3, 1fr); gap: 24px; }
            .map-container { height: 700px; }
        }

        @media (min-width: 1280px) {
            .spots-grid { grid-template-columns: repeat(4, 1fr); }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="channel-info">
            <div class="channel-avatar"><img src="{{ channel_info.thumbnail }}" alt="{{ channel_info.title }}"></div>
            <div class="channel-details">
                <h1>{{ channel_info.title }}</h1>
                <div class="channel-meta">구독자 {{ channel_info.subscriberCount }}명 • 동영상 {{ channel_info.videoCount }}개</div>
            </div>
        </div>
        <button class="subscribe-btn" onclick="subscribeChannel()">구독</button>
    </header>

    <div class="container">
        <div class="stats-grid">
            <div class="stat-card"><span class="stat-number">{{ total_locations }}</span><div class="stat-label">수영 지역</div></div>
            <div class="stat-card"><span class="stat-number">{{ total_spots }}</span><div class="stat-label">수영 장소</div></div>
            <div class="stat-card"><span class="stat-number">{{ total_videos }}</span><div class="stat-label">수영 영상</div></div>
            <div class="stat-card"><span class="stat-number">{{ "%.1f"|format(avg_rating) }}</span><div class="stat-label">평균 평점</div></div>
        </div>

        <section class="map-section">
            <h2 class="section-title">수영 위치 지도</h2>
            <div class="map-container">{{ map_html|safe }}</div>
        </section>

        {% for location, data in spot_data.items() %}
        <section class="location-section">
            <div class="location-header">
                <h2 class="location-title">{{ location }}</h2>
                <span class="spot-count">{{ data.spots|length }}개 장소</span>
            </div>
            <div class="sort-controls">
                <span class="sort-label">정렬:</span>
                <select class="sort-select" onchange="sortSpots('{{ location }}', this.value)">
                    <option value="rating-desc">평점 높은순</option>
                    <option value="views-desc">조회수 높은순</option>
                    <option value="date-desc">최신순</option>
                </select>
            </div>
            <div class="spots-grid" id="spots-{{ location }}">
                {% for spot in data.spots %}
                <div class="spot-card" onclick="location.href='/spot/{{ location|urlencode }}/{{ spot.spot_id|urlencode }}'" data-rating="{{ spot.rating }}" data-views="{{ spot.views }}" data-date="{{ spot.date }}">
                    <div class="spot-thumbnail">
                        <img src="{{ spot.thumbnail }}" alt="{{ spot.title }}">
                        <div class="spot-duration">{{ spot.duration }}</div>
                        <div class="video-count-badge">{{ spot.video_count }}개</div>
                        <div class="spot-overlay">
                            <div class="play-btn">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="#181818"><path d="M8 5v14l11-7z"/></svg>
                            </div>
                        </div>
                    </div>
                    <div class="spot-info">
                        <h3 class="spot-title">{{ spot.title }}</h3>
                        <div class="spot-description">{{ spot.description }}</div>
                        <div class="spot-meta">조회수 {{ spot.views }}회 • {{ spot.date }}</div>
                        <div class="spot-stats">
                            <span class="spot-stat">📍{{ spot.distance }}</span>
                            <span class="spot-stat difficulty-{{ spot.difficulty }}">● {{ spot.difficulty }}</span>
                            <span class="spot-stat">⭐ {{ spot.rating }}</span>
                            <span class="spot-stat">{{ spot.video_count }}개 영상</span>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>
        {% endfor %}
    </div>

    <script>
        function subscribeChannel() {
            const btn = document.querySelector('.subscribe-btn');
            if (btn.textContent === '구독') {
                btn.textContent = '구독 완료';
                btn.style.background = '#606060';
                setTimeout(() => { window.open('https://www.youtube.com/@ickost', '_blank'); }, 500);
            } else {
                btn.textContent = '구독';
                btn.style.background = '#cc0000';
            }
        }

        function sortSpots(location, sortType) {
            const container = document.getElementById('spots-' + location);
            const spots = Array.from(container.querySelectorAll('.spot-card'));
            spots.sort(function(a, b) {
                if (sortType === 'rating-desc') return parseFloat(b.dataset.rating) - parseFloat(a.dataset.rating);
                if (sortType === 'views-desc') return parseViews(b.dataset.views) - parseViews(a.dataset.views);
                if (sortType === 'date-desc') return new Date(b.dataset.date) - new Date(a.dataset.date);
                return 0;
            });
            spots.forEach(spot => container.appendChild(spot));
        }

        function parseViews(viewsStr) {
            const cleanStr = viewsStr.replace(/[,]/g, '');
            if (cleanStr.includes('만')) return parseFloat(cleanStr.replace('만', '')) * 10000;
            if (cleanStr.includes('천')) return parseFloat(cleanStr.replace('천', '')) * 1000;
            return parseInt(cleanStr) || 0;
        }
    </script>
</body>
</html>'''

    return render_template_string(html, 
        map_html=map_html,
        total_locations=total_locations,
        total_spots=total_spots,
        total_videos=total_videos,
        avg_rating=avg_rating,
        spot_data=enriched_spot_data,
        channel_info=channel_info
    )

@app.route('/spot/<location>/<spot_id>')
def spot_detail(location, spot_id):
    """개별 장소의 상세 페이지 - 해당 장소의 모든 영상 표시"""
    try:
        spot_data = SPOT_DATA.get(location, {}).get('spots', {}).get(spot_id)
        if not spot_data:
            return "장소를 찾을 수 없습니다", 404
        
        # 해당 장소의 모든 영상 정보 가져오기
        enriched_videos = []
        for video in spot_data['videos']:
            youtube_info = get_youtube_video_info(video['url'])
            video_id = extract_video_id(video['url'])
            enriched_videos.append({
                **video,
                'video_id': video_id,
                'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'duration': youtube_info['duration'],
                'views': youtube_info['viewCount'],
                'date': youtube_info['publishedAt'],
                'title': youtube_info.get('title') or video['title'],  # YouTube 제목 우선, 없으면 하드코딩 제목
                'original_title': video['title']  # 하드코딩 제목을 별도 보관
            })
        
        # 채널 정보
        channel_info = get_channel_info()
        
        # 상세 페이지 HTML 템플릿
        detail_html = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ spot.title }} - ICKOST</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Roboto', sans-serif; background-color: #0f0f0f; color: #ffffff; line-height: 1.4; }

        .header { 
            background: #212121; 
            padding: 12px 16px; 
            display: flex; 
            align-items: center; 
            position: sticky; 
            top: 0; 
            z-index: 100; 
            border-bottom: 1px solid #3d3d3d; 
        }
        .back-btn {
            background: #3d3d3d;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            margin-right: 16px;
            transition: background 0.2s ease;
        }
        .back-btn:hover { background: #555; }
        .channel-info { display: flex; align-items: center; gap: 12px; flex: 1; }
        .channel-avatar { width: 40px; height: 40px; border-radius: 50%; overflow: hidden; }
        .channel-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .channel-details h1 { font-size: 18px; font-weight: 600; color: #ffffff; margin-bottom: 2px; }
        .channel-meta { color: #aaaaaa; font-size: 12px; }

        .container { 
            max-width: 1280px; 
            margin: 0 auto; 
            padding: 16px; 
        }

        .spot-header {
            background: #181818;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 32px;
            border: 1px solid #3d3d3d;
        }
        .spot-title { font-size: 24px; font-weight: 600; color: #ffffff; margin-bottom: 8px; }
        .spot-description { color: #aaaaaa; font-size: 16px; margin-bottom: 16px; }
        .spot-info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }
        .info-item {
            text-align: center;
            padding: 12px;
            background: #212121;
            border-radius: 8px;
        }
        .info-value { font-size: 18px; font-weight: 600; color: #ffffff; margin-bottom: 4px; }
        .info-label { font-size: 12px; color: #aaaaaa; }
        .difficulty-초급 { color: #ff6b6b; }
        .difficulty-중급 { color: #ff4757; }
        .difficulty-고급 { color: #c44569; }

        .videos-section h2 { font-size: 20px; font-weight: 600; margin-bottom: 20px; color: #ffffff; }
        .videos-grid { 
            display: grid; 
            grid-template-columns: 1fr; 
            gap: 20px; 
        }
        .video-card { 
            background: #181818; 
            border-radius: 12px; 
            overflow: hidden; 
            border: 1px solid #3d3d3d;
            transition: transform 0.2s ease;
            cursor: pointer;
        }
        .video-card:hover { transform: translateY(-2px); }
        .video-thumbnail { 
            position: relative; 
            width: 100%; 
            height: 200px; 
        }
        .video-thumbnail img { width: 100%; height: 100%; object-fit: cover; }
        .video-duration { 
            position: absolute; 
            bottom: 8px; 
            right: 8px; 
            background: rgba(0,0,0,0.8); 
            color: white; 
            padding: 3px 6px; 
            border-radius: 4px; 
            font-size: 12px; 
        }
        .video-overlay { 
            position: absolute; 
            top: 0; 
            left: 0; 
            right: 0; 
            bottom: 0; 
            background: rgba(0,0,0,0.3); 
            opacity: 0; 
            transition: opacity 0.2s ease; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }
        .video-card:hover .video-overlay { opacity: 1; }
        .play-btn { 
            width: 48px; 
            height: 48px; 
            background: rgba(255,255,255,0.9); 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }
        .video-info { padding: 16px; }
        .video-title { 
            font-size: 16px; 
            font-weight: 600; 
            color: #ffffff; 
            margin-bottom: 8px; 
            line-height: 1.3; 
        }
        .video-description { 
            color: #aaaaaa; 
            font-size: 14px; 
            margin-bottom: 8px; 
            line-height: 1.4; 
        }
        .video-meta { color: #aaaaaa; font-size: 13px; }

        @media (min-width: 768px) {
            .container { padding: 24px; }
            .spot-title { font-size: 28px; }
            .videos-grid { grid-template-columns: repeat(2, 1fr); gap: 24px; }
        }

        @media (min-width: 1024px) {
            .videos-grid { grid-template-columns: repeat(3, 1fr); }
        }
    </style>
</head>
<body>
    <header class="header">
        <button class="back-btn" onclick="history.back()">← 뒤로</button>
        <div class="channel-info">
            <div class="channel-avatar"><img src="{{ channel_info.thumbnail }}" alt="{{ channel_info.title }}"></div>
            <div class="channel-details">
                <h1>{{ channel_info.title }}</h1>
                <div class="channel-meta">{{ spot.title }} 상세보기</div>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="spot-header">
            <h1 class="spot-title">{{ spot.title }}</h1>
            <p class="spot-description">{{ spot.description }}</p>
            <div class="spot-info-grid">
                <div class="info-item">
                    <div class="info-value">{{ spot.distance }}</div>
                    <div class="info-label">거리</div>
                </div>
                <div class="info-item">
                    <div class="info-value difficulty-{{ spot.difficulty }}">{{ spot.difficulty }}</div>
                    <div class="info-label">난이도</div>
                </div>
                <div class="info-item">
                    <div class="info-value">★ {{ spot.rating }}</div>
                    <div class="info-label">평점</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ videos|length }}개</div>
                    <div class="info-label">영상 수</div>
                </div>
            </div>
        </div>

        <section class="videos-section">
            <h2>이 장소의 수영 영상들</h2>
            <div class="videos-grid">
                {% for video in videos %}
                <div class="video-card" onclick="window.open('{{ video.url }}', '_blank')">
                    <div class="video-thumbnail">
                        <img src="{{ video.thumbnail }}" alt="{{ video.title }}">
                        <div class="video-duration">{{ video.duration }}</div>
                        <div class="video-overlay">
                            <div class="play-btn">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="#181818"><path d="M8 5v14l11-7z"/></svg>
                            </div>
                        </div>
                    </div>
                    <div class="video-info">
                        <h3 class="video-title">{{ video.title }}</h3>
                        <p class="video-description">{{ video.description }}</p>
                        <div class="video-meta">조회수 {{ video.views }}회 • {{ video.date }}</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>
    </div>
</body>
</html>'''
        
        return render_template_string(detail_html,
                                    spot=spot_data,
                                    videos=enriched_videos,
                                    location=location,
                                    channel_info=channel_info)
        
    except Exception as e:
        print(f"Spot detail error: {e}")
        return f"오류가 발생했습니다: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
