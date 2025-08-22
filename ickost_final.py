#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from flask import Flask, render_template_string, jsonify
import folium
import json
import requests
from datetime import datetime
import os

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

def get_youtube_video_info(video_url):
    video_id = extract_video_id(video_url)
    if not video_id or not YOUTUBE_API_KEY:
        return {
            'duration': '8:45',
            'viewCount': '2.1만',
            'publishedAt': '2024년 8월 21일',
            'title': None
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
            
            return {
                'duration': format_duration(content_details.get('duration', 'PT0S')),
                'viewCount': format_view_count(statistics.get('viewCount', '0')),
                'publishedAt': format_date(snippet.get('publishedAt', '')),
                'title': snippet.get('title'),
                'description': snippet.get('description', '')[:100] + '...' if len(snippet.get('description', '')) > 100 else snippet.get('description', '')
            }
    except Exception as e:
        print(f"YouTube API 오류: {e}")
    
    return {
        'duration': '8:45',
        'viewCount': '2.1만',
        'publishedAt': '2024년 8월 21일',
        'title': None
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
            
            # return 문을 제거하고 여기까지만
            
    except Exception as e:
        print(f"채널 정보 오류: {e}")
    
    # 기본값 반환 (try 블록 밖에서)
    return {
        'subscriberCount': '00만',
        'videoCount': '00',
        'title': 'ICKOST',
        'thumbnail': 'https://yt3.googleusercontent.com/2pvoyX_JUZFcrn1RD1I9SCIUF62jvpkxaK77UNs50TtM8GkjyprLPu5cIPcmE9ribNOGqL9kRA=s160-c-k-c0x00ffffff-no-rj'
    }

def get_difficulty_color(difficulty):  
    """난이도별 색상 반환 (빨간색 계열)"""
    colors = {
        "초급": "#ff6b6b",
        "중급": "#ff4757",
        "고급": "#c44569"
    }
    return colors.get(difficulty, "#ff0000")

def get_marker_size(rating):
    """평점별 마커 크기 반환"""
    if rating >= 4.0:
        return 40
    elif rating >= 3.5:
        return 35
    else:
        return 30
        
VIDEO_DATA = {
    "제주도": {
        "videos": [
            {
                "title": "삼양감수탕",
                "description": "제주도 바다수영의 성지",
                "url": "https://youtu.be/CQ8i9V3n_3U",
                "coordinates": [33.525243, 126.583098],
                "distance": "1.9km",
                "rating": 4.1,
                "difficulty": "초급"
            },
            {
                "title": "용담포구(용두암)",
                "description": "제주에서의 시티뷰",
                "url": "https://youtu.be/vrMIBOMAE6Y?si=q7_W4aUSJTpHRmip",
                "coordinates": [33.518360, 126.501244],
                "distance": "2km",
                "rating": 3.6,
                "difficulty": "초급"
            },
            {
                "title": "현사포구",
                "description": "500미터 인터벌 훈련",
                "url": "https://youtu.be/gyA6zATW1dM?si=nb4pRdupYV0WfuSv",
                "coordinates": [33.498385, 126.449710],
                "distance": "500m",
                "rating": 3.5,
                "difficulty": "초급"
            },
            {
                "title": "구엄포구-고내리포구",
                "description": "물고기 천국, 낚시포인트",
                "url": "https://youtu.be/jHV5KQXooC0",
                "coordinates": [33.483416, 126.376398],
                "distance": "2.8km",
                "rating": 4.1,
                "difficulty": "중급"
            },
            {
                "title": "곽지해수욕장",
                "description": "다양한 바다를 만날 수 있음",
                "url": "https://youtu.be/l0lDyQEpB7k",
                "coordinates": [33.449486, 126.303061],
                "distance": "3km",
                "rating": 3.7,
                "difficulty": "중급"
            },
              {
                "title": "비양도",
                "description": "섬을 한바퀴 도는 경험",
                "url": "https://youtu.be/4G6gIcR9PoQ",
                "coordinates": [33.406378, 126.231167],
                "distance": "3.8km",
                "rating": 3.9,
                "difficulty": "고급"
            },
            {
                "title": "송악산항-하도방파제",
                "description": "서쪽제1경 송악산 한바퀴",
                "url": "https://youtu.be/mW-nnFWoruo",
                "coordinates": [33.205401, 126.290239],
                "distance": "3.2km",
                "rating": 3.7,
                "difficulty": "중급"
            },
             {
                "title": "사계항(용머리바위)",
                "description": "바다에서 바라보는 용머리바위",
                "url": "https://youtu.be/EeCD-p8GdZw",
                "coordinates": [33.230389, 126.309630],
                "distance": "2km",
                "rating": 4.0,
                "difficulty": "중급"
            },
            {
                "title": "월평포구-해송횟집(진곶내)",
                "description": "오로지 물길로만 가능한 곳, 진곳",
                "url": "https://youtu.be/qDBFv4rKnxQ",
                "coordinates": [33.234547, 126.463455],
                "distance": "3.4km",
                "rating": 3.8,
                "difficulty": "중급"
            },
             {
                "title": "새연교-돔베낭골(외돌개)",
                "description": "서귀포 필수코스",
                "url": "https://youtu.be/WwQ7GhNW1dQ",
                "coordinates": [33.239074, 126.558384],
                "distance": "3.6km",
                "rating": 3.8,
                "difficulty": "고급"
            },
             {
                "title": "자구리-구두미포구(정방폭포)",
                "description": "바다로 떨어지는 폭포",
                "url": "https://youtu.be/lWivFkLGLPA",
                "coordinates": [33.243282, 126.568774],
                "distance": "3.8km",
                "rating": 3.5,
                "difficulty": "중급"
            },
             {
                "title": "태웃개",
                "description": "다이빙의 성지에서 바다수영",
                "url": "https://youtu.be/HFfRwPig89g",
                "coordinates": [33.270104, 126.691575],
                "distance": "4km",
                "rating": 3.8,
                "difficulty": "고급"
            },
             {
                "title": "신양섭지해수욕장(섭지코지)",
                "description": "섭지코지 한바퀴, 바다거북 출현",
                "url": "https://youtu.be/NUhttc9N1Ks",
                "coordinates": [33.436283, 126.924772],
                "distance": "5km",
                "rating": 4.2,
                "difficulty": "고급"
            },
             {
                "title": "수마포구-우뭇개해안(성산일출봉)",
                "description": "제주 제1경을 바다에서 보는 맛",
                "url": "https://youtu.be/Up1qNF8ES7o",
                "coordinates": [33.460447, 126.933770],
                "distance": "3.5km",
                "rating": 4.2,
                "difficulty": "고급"
            },
             {
                "title": "하고수동해수욕장(우도)",
                "description": "섬속의 섬에서",
                "url": "https://youtu.be/-m8AwZlrwY4",
                "coordinates": [33.514798, 126.958688],
                "distance": "1.8km",
                "rating": 3.6,
                "difficulty": "초급"
            },
             {
                "title": "제주카약체험-신동코지불턱(토끼섬)",
                "description": "토끼섬엔 토끼가 없다",
                "url": "https://youtu.be/46QuKrDwbwo4",
                "coordinates": [33.515598, 126.902241],
                "distance": "3.4km",
                "rating": 3.9,
                "difficulty": "중급"
            },
             {
                "title": "월정투명카약-세기알해변",
                "description": "김녕의 보석",
                "url": "https://youtu.be/Ml7Cb8eoyPQ",
                "coordinates": [33.566002, 126.779129],
                "distance": "3.1km",
                "rating": 3.4,
                "difficulty": "중급"
            },
             {
                "title": "북촌환해장성-목지섬",
                "description": "다채로운 바다",
                "url": "https://youtu.be/kKrNavJKpYc",
                "coordinates": [33.554748, 126.710768],
                "distance": "3.2km",
                "rating": 3.8,
                "difficulty": "중급"
            },
             {
                "title": "함덕해수욕장-해동포구",
                "description": "최상급 투명도",
                "url": "https://youtu.be/fwAW_b_UdH4",
                "coordinates": [33.544800, 126.674291],
                "distance": "1.9km",
                "rating": 4.2,
                "difficulty": "초급"
            },
             {
                "title": "관곶-정주항",
                "description": "섬속을 누비는 즐거움",
                "url": "https://youtu.be/mt4r9Hx9kBA",
                "coordinates": [33.555509, 126.644597],
                "distance": "3km",
                "rating": 3.8,
                "difficulty": "중급"
            },
             {
                "title": "닭머르",
                "description": "아무나 올 수 없는 곳(사유지)",
                "url": "https://youtu.be/KFYn3sPHKkw",
                "coordinates": [33.535198, 126.603058],
                "distance": "2km",
                "rating": 3.4,
                "difficulty": "초급"
            }
            
        ]
    },
    "부산": {
        "videos": [
            {
                "title": "해운대해수욕장",
                "description": "전국 바다수영의 성지",
                "url": "https://youtu.be/tESMnqgBz7E",
                "coordinates": [35.1588, 129.1603],
                "distance": "1.5km",
                "rating": 3.7,
                "difficulty": "중급"
            },
            {
                "title": "송정해수욕장",
                "description": "천지개벽한 송정앞바다",
                "url": "https://youtu.be/u6GNpGfimaM",
                "coordinates": [35.1785, 129.1998],
                "distance": "1.5m",
                "rating": 3.2,
                "difficulty": "초급"
            },
            {
                "title": "송도해수욕장",
                "description": "시티뷰가 좋은 포인트",
                "url": "https://youtu.be/e1Kp4Rzkis0",
                "coordinates": [35.075454, 129.017233],
                "distance": "1.5m",
                "rating": 3.4,
                "difficulty": "초급"
            }
        ]
    },
    "경남": {
        "videos": [
            {
                "title": "구조라해수욕장",
                "description": "윤돌섬이 보이는 해파리천국",
                "url": "https://youtu.be/bLmz_DcrTIw",
                "coordinates": [34.810020, 128.686903],
                "distance": "3.2km",
                "rating": 3.5,
                "difficulty": "초급"
            }
        ]
    }
}

def enrich_video_data():
    enriched_data = {}
    for location, data in VIDEO_DATA.items():
        enriched_videos = []
        for video in data['videos']:
            youtube_info = get_youtube_video_info(video['url'])
            video_id = extract_video_id(video['url'])
            enriched_video = {
                **video,
                'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'duration': youtube_info['duration'],
                'views': youtube_info['viewCount'],
                'date': youtube_info['publishedAt'],
                'title': youtube_info['title'] if youtube_info['title'] else video['title']
            }
            enriched_videos.append(enriched_video)
        enriched_data[location] = {'videos': enriched_videos}
    return enriched_data

def get_difficulty_color(difficulty):
    colors = {
        "초급": "#00ff00",  # 초록색
        "중급": "#ffaa00", 
        "고급": "#ff4444"
    }
    return colors.get(difficulty, "#aaaaaa")

def create_map(video_data):
    m = folium.Map(
        location=[33.389153, 126.562724],
        zoom_start=11,
        tiles='CartoDB dark_matter'
    )
    
    for location, data in video_data.items():
        for video in data['videos']:
            popup_html = f"""
            <div style="width: 320px; font-family: 'Roboto', sans-serif; 
                        background: #181818; color: #ffffff; border-radius: 8px; overflow: hidden;">
                <div style="position: relative; background: #000; cursor: pointer;" 
                     onclick="window.open('{video['url']}', '_blank')">
                    <img src="{video.get('thumbnail', '/static/default_thumbnail.jpg')}"
                         style="width: 100%; height: 180px; object-fit: cover; display: block;">
                    <div style="position: absolute; bottom: 8px; right: 8px; 
                                background: rgba(0,0,0,0.8); color: white; 
                                padding: 2px 6px; border-radius: 3px; font-size: 12px;">
                        {video['duration']}
                    </div>
                    <div style="position: absolute; top: 50%; left: 50%; 
                                transform: translate(-50%, -50%); 
                                width: 48px; height: 48px; 
                                background: rgba(255,255,255,0.9); 
                                border-radius: 50%; 
                                display: flex; align-items: center; justify-content: center;
                                opacity: 0; transition: opacity 0.3s ease;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="#181818">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                    </div>
                </div>
                <div style="padding: 12px;">
                    <h3 style="margin: 0 0 8px 0; font-size: 16px; color: #ffffff;">
                        {video['title']}
                    </h3>
                    <div style="color: #aaaaaa; font-size: 13px; margin-bottom: 12px;">
                        조회수 {video['views']}회 • {video['date']}
                    </div>
                    <div style="color: #aaaaaa; font-size: 13px; margin-bottom: 12px;">
                        {video.get('description', video.get('api_description', ''))}
                    </div>
                    <div style="display: flex; gap: 16px; margin: 12px 0; padding: 8px 0; 
                                border-top: 1px solid #3d3d3d;">
                        <div style="text-align: center; color: #aaaaaa; font-size: 12px;">
                            <div style="color: #ffffff; font-weight: 500;">{video['distance']}</div>
                            <div>거리</div>
                        </div>
                        <div style="text-align: center; color: #aaaaaa; font-size: 12px;">
                            <div style="color: {get_difficulty_color(video['difficulty'])}; font-weight: 500;">{video['difficulty']}</div>
                            <div>난이도</div>
                        </div>
                        <div style="text-align: center; color: #aaaaaa; font-size: 12px;">
                            <div style="color: #ffaa00; font-weight: 500;">★{video['rating']}</div>
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
                                onclick="window.open('{video['url']}', '_blank')">
                            ▶ 영상 보기
                        </button>
                    </div>
                </div>
            </div>
            """
            
            marker_size = get_marker_size(video['rating'])
            difficulty_color = get_difficulty_color(video['difficulty'])

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
                location=video['coordinates'],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"▶ {video['title']} ({location})",
                icon=folium.DivIcon(html=marker_html, icon_size=(marker_size, marker_size), icon_anchor=(marker_size//2, marker_size//2))
            ).add_to(m)
    
    return m

@app.route('/')
def index():
    try:
        enriched_video_data = enrich_video_data()
        channel_info = get_channel_info()
        folium_map = create_map(enriched_video_data)
        map_html = folium_map._repr_html_()
        total_videos = sum(len(data['videos']) for data in enriched_video_data.values())
        total_locations = len(enriched_video_data)
        all_ratings = []
        for location_data in enriched_video_data.values():
            for video in location_data['videos']:
                all_ratings.append(video['rating'])
        avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
    except Exception as e:
        print(f"오류: {e}")
        enriched_video_data = VIDEO_DATA
        channel_info = get_channel_info()
        folium_map = create_map(enriched_video_data)
        map_html = folium_map._repr_html_()
        total_videos = 7
        total_locations = 3
        avg_rating = 4.5

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

        /* 모바일 우선 스타일 */
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
            grid-template-columns: repeat(3, 1fr); 
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
        .video-count { background: #3d3d3d; color: #aaaaaa; padding: 4px 8px; border-radius: 12px; font-size: 11px; }

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

        /* 비디오 카드를 모바일에 최적화 */
        .videos-grid { 
            display: grid; 
            grid-template-columns: 1fr; 
            gap: 16px; 
        }
        .video-card { 
            background: transparent; 
            cursor: pointer; 
            transition: transform 0.2s ease; 
            display: flex; 
            gap: 12px; 
        }
        .video-card:hover { transform: translateY(-2px); }

        /* 썸네일 크기 줄이기 */
        .video-thumbnail { 
            position: relative; 
            width: 120px; 
            height: 68px; 
            border-radius: 8px; 
            overflow: hidden; 
            background: #181818; 
            flex-shrink: 0; 
        }
        .video-thumbnail img { width: 100%; height: 100%; object-fit: cover; }
        .video-duration { 
            position: absolute; 
            bottom: 4px; 
            right: 4px; 
            background: rgba(0,0,0,0.8); 
            color: white; 
            padding: 2px 4px; 
            border-radius: 3px; 
            font-size: 10px; 
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
            width: 24px; 
            height: 24px; 
            background: rgba(255,255,255,0.9); 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }

        /* 비디오 정보 가독성 개선 */
        .video-info { 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            justify-content: space-between; 
        }
        .video-title { 
            font-size: 14px; 
            font-weight: 500; 
            color: #ffffff; 
            margin-bottom: 6px; 
            line-height: 1.3; 
            overflow: hidden; 
            display: -webkit-box; 
            -webkit-line-clamp: 2; 
            -webkit-box-orient: vertical; 
        }
        .video-description { 
            color: #aaaaaa; 
            font-size: 12px; 
            margin-bottom: 8px; 
            line-height: 1.4; 
            overflow: hidden; 
            display: -webkit-box; 
            -webkit-line-clamp: 2; 
            -webkit-box-orient: vertical; 
        }
        .video-meta { color: #aaaaaa; font-size: 12px; margin-bottom: 8px; }
        .video-stats { 
            display: flex; 
            gap: 12px; 
            font-size: 11px; 
            flex-wrap: wrap; 
        }
        .video-stat { color: #aaaaaa; }
        .difficulty-초급 { color: #ff6b6b; }
        .difficulty-중급 { color: #ff4757; }
        .difficulty-고급 { color: #c44569; }

        /* 태블릿 및 데스크톱 스타일 */
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
            .videos-grid { grid-template-columns: 1fr; gap: 20px; }
            .video-thumbnail { width: 160px; height: 90px; }
            .video-title { font-size: 15px; }
            .video-description { font-size: 13px; }
            .video-meta { font-size: 13px; }
            .video-stats { font-size: 12px; }
        }

        @media (min-width: 768px) {
            .header { padding: 20px 24px; }
            .container { padding: 24px; }
            .stats-grid { gap: 16px; }
            .stat-card { padding: 20px; }
            .stat-number { font-size: 28px; }
            .stat-label { font-size: 14px; }
            .map-container { height: 600px; }
            .videos-grid { grid-template-columns: repeat(2, 1fr); }
            .video-card { display: block; }
            .video-thumbnail { width: 100%; aspect-ratio: 16/9; height: auto; }
            .video-info { padding: 12px 4px 0 4px; }
            .video-title { font-size: 16px; }
            .video-description { font-size: 14px; }
        }

        @media (min-width: 1024px) {
            .videos-grid { grid-template-columns: repeat(3, 1fr); gap: 24px; }
            .map-container { height: 700px; }
        }

        @media (min-width: 1280px) {
            .videos-grid { grid-template-columns: repeat(4, 1fr); }
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
            <div class="stat-card"><span class="stat-number">{{ total_videos }}</span><div class="stat-label">수영 포인트</div></div>
            <div class="stat-card"><span class="stat-number">{{ "%.1f"|format(avg_rating) }}</span><div class="stat-label">평균 평점</div></div>
        </div>

        <section class="map-section">
            <h2 class="section-title">🏊 수영 위치 지도</h2>
            <div class="map-container">{{ map_html|safe }}</div>
        </section>

        {% for location, data in video_data.items() %}
        <section class="location-section">
            <div class="location-header">
                <h2 class="location-title">{{ location }}</h2>
                <span class="video-count">{{ data.videos|length }}개 영상</span>
            </div>
            <div class="sort-controls">
                <span class="sort-label">정렬:</span>
                <select class="sort-select" onchange="sortVideos('{{ location }}', this.value)">
                    <option value="date-desc">최신순</option>
                    <option value="views-desc">조회수 높은순</option>
                    <option value="rating-desc">평점 높은순</option>
                </select>
            </div>
            <div class="videos-grid" id="videos-{{ location }}">
                {% for video in data.videos %}
                <div class="video-card" onclick="window.open('{{ video.url }}', '_blank')" data-date="{{ video.date }}" data-views="{{ video.views }}" data-rating="{{ video.rating }}">
                    <div class="video-thumbnail">
                        <img src="{{ video.thumbnail }}" alt="{{ video.title }}">
                        <div class="video-duration">{{ video.duration }}</div>
                        <div class="video-overlay">
                            <div class="play-btn">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="#181818"><path d="M8 5v14l11-7z"/></svg>
                            </div>
                        </div>
                    </div>
                    <div class="video-info">
                        <h3 class="video-title">{{ video.title }}</h3>
                        <div class="video-description">{{ video.get('description', '') }}</div>
                        <div class="video-meta">조회수 {{ video.views }}회 • {{ video.date }}</div>
                        <div class="video-stats">
                            <span class="video-stat">📍 {{ video.distance }}</span>
                            <span class="video-stat difficulty-{{ video.difficulty }}">● {{ video.difficulty }}</span>
                            <span class="video-stat">⭐ {{ video.rating }}</span>
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

        function sortVideos(location, sortType) {
            const container = document.getElementById('videos-' + location);
            const videos = Array.from(container.querySelectorAll('.video-card'));
            videos.sort(function(a, b) {
                if (sortType === 'date-desc') return new Date(b.dataset.date) - new Date(a.dataset.date);
                if (sortType === 'views-desc') return parseViews(b.dataset.views) - parseViews(a.dataset.views);
                if (sortType === 'rating-desc') return parseFloat(b.dataset.rating) - parseFloat(a.dataset.rating);
                return 0;
            });
            videos.forEach(video => container.appendChild(video));
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
        total_videos=total_videos,
        total_locations=total_locations,
        avg_rating=avg_rating,
        video_data=enriched_video_data,
        channel_info=channel_info
    )

# 앱 실행 부분 수정
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
