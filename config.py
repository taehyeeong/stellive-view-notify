import os

# ============================================================
#  STELLIVE 성장 대시보드 · 설정
# ============================================================

# ── 조회수 알림 단위 ──
# 50000 = 5만 조회수마다 알림
VIEW_STEP = 50000

# ── 특별 알림 마일스톤 ──
MILESTONES = [
    100000,     # 10만
    500000,     # 50만
    1000000,    # 100만
    5000000,    # 500만
    10000000,   # 1000만
]



# ── 성장 플리: 기본 ──
GROWTH_PLAYLIST_ID = os.environ.get("GROWTH_PLAYLIST_ID", "")
SYNC_GROWTH_PLAYLIST = True            # 성장 플리 자동 갱신 켜기/끄기
# True = 플리를 TOP 목록과 똑같이 맞춤(없는 건 삭제) / False = 추가만 하고 안 지움
GROWTH_PLAYLIST_REMOVE_MISSING = True
MAX_GROWTH_PLAYLIST_VIDEOS = 30        # 성장 플리에 넣을 최대 영상 수
# 한 번 실행에서 허용할 플리 추가+삭제 총 횟수 (쿼터 보호)
MAX_PLAYLIST_OPS_PER_RUN = 40         
# 성장 플리에 항상 넣을 개인 선곡 (URL 또는 ID)
GROWTH_PLAYLIST_PINNED = [
    # "https://www.youtube.com/watch?v=xxxx",
]



# ── 성장 플리: 선곡/회전(매시간 믹스) ──
LOCK_HOURS      = 6        # eta 이 시간 이내면 '코앞' → 달성까지 고정(쿨다운 무시)
SWAP_PER_HOUR   = 16       # 매시간 갈아끼울 곡 수
ADD_RISING      = 4        # 교체분 중 급상승
ADD_GEMS        = 7        # 교체분 중 묻힌 보석
ADD_RANDOM      = 5        # 교체분 중 가중 랜덤  (4+7+5 = 16)
GEM_VIEW_MAX    = 500000   # 이 미만이면 '묻힌 곡'
FRESH_MIN_HOURS = 6        # 방금 뺀 곡 재진입 억제(flip-flop 방지)
FOCUS_UNIT      = None     # 예: "에버리스" 로 켜면 그 유닛을 얹어줌(평소 None)
FOCUS_BONUS     = 2.0
# (구버전 회전 — 현재 선곡 로직에선 미사용)
PLAYLIST_ROTATE_COUNT = 10             # 매 주기 교체할 곡 수
PLAYLIST_ROTATE_HOURS = 1              # 회전 주기(시간)



# ── 자동핀 / 부스트 / 달성 쿨다운 ──
# 신곡 자동핀: 감지된 신곡을 성장 플리에 자동 등록해두는 기간(일). 0이면 끔.
AUTO_PIN_NEW_SONG_DAYS = 10
# 게시 N일 이내 영상만 성장 플리 자동핀
AUTO_PIN_MAX_AGE_DAYS = 5
# 성장 점수 부스트 — 지정 곡/아티스트를 플리에 더 자주.
#   type: "artist"(이름) 또는 "song"(video_id/URL) / target / pct / until(선택)
GROWTH_BOOST = [
    # {"type": "song", "target": "https://youtu.be/rQaluJS-Tc0", "pct": 50},  # URL 가능
    # {"type": "song", "target": "rQaluJS-Tc0", "pct": 50},                   # ID도 가능
]
BOOST_DEFAULT_DAYS = 10   # until 없을 때 기본 부스트 기간(일)
# 마일스톤 달성한 곡을 플리에서 자동 제외하는 기간
ACHIEVED_COOLDOWN_HOURS = 12



# ── 알림: 곧 달성 / D-Day / 떡상 ──
# 곧 조회수 달성 알림
IMMINENT_HOURS = 3          # 다음 목표까지 이 시간 이내면 대상
IMMINENT_PING_HOURS = 3     # 이 시간마다 새 알림 (3이면 3시간마다)
# D-Day 알림
DDAY_THRESHOLD_DAYS = 10    # 다음 목표까지 이 일수 이내면 '곧 달성'
DDAY_ALERT_HOUR = 21        # 매일 이 시각(KST) 이후 첫 실행에 1회
DDAY_MAJOR_STEP = 1_000_000 # 100만 단위 목표만
# 떡상 알림
SPIKE_MULT = 2.5            # 최근 속도가 평소의 이 배 이상이면 떡상
SPIKE_MIN_DAILY = 1500      # 하루 최소 이만큼은 늘어야 떡상(노이즈 컷)



# ── 카드 / 표시 ──
SPECIAL_CARD_ENABLED = False   # 특별 카드(100만/1000만 세로 HTML) on/off
SHOW_SONG_TYPE_BADGE = False   # 카드 상단 ORIGINAL/COVER 배지 표시
USE_ARTIST_COLOR = True        # 아티스트별 대표 색(비우면 자동 추출)
# 특별 축하 카드 (마일스톤값: 스타일)
SPECIAL_MILESTONES = {
    1000000: {                    # 100만
        "tagline": "100만 축하해",
        "accent": "#f5c451",      # 골드
        "tint": "#2a2114",
        "grand": True,
    },
    10000000: {                   # 1000만
        "tagline": "1000만 돌파",
        "accent": "#7fe7ff",      # 다이아 블루
        "tint": "#0e2230",
        "grand": True,
    },
}



# ── 영상 판별 / 제외 ──
# 음악 영상으로 판단할 제목 키워드
MUSIC_KEYWORDS = [
    "MV",
    "Music Video",
    "Official",
    "Original",
    "Cover",
    "노래",
    "cover",
    "music",
    "Playlist",
    "Live"
]
EXCLUDE_KEYWORDS = [
    "shorts",
    "#shorts",
    "쇼츠",
    "clip",
    "클립",
    "Teaser",
    "하이라이트 메들리",
    "생일",
    "데뷔"
]
STELLIVE_EXCLUDED_ARTIST_ALIASES = [
    "아이리 칸나",
    "Airi Kanna",
    "AIRIKANNA",
    "藍璃かんな",
]
# 아예 제외할 개별 영상 (URL 또는 ID) — 제목/채널로 안 걸러지는 것들
EXCLUDED_VIDEO_IDS = [
    # "https://www.youtube.com/watch?v=xxxxxxxxxxx",  # 아이리 칸나 커버 A
]



# ── 조회수 달성 축하 메시지 템플릿 ──
MILESTONE_TEMPLATE = """
{keyword}

{nickname}

『 {title} 』 {views_text} 축하해 !!

Full : {url}
"""



# ── 네이버 카페 자동 축하글 ──────────────────────────────
CAFE_URL_NAME = "tteokbokk1"      # 카페 주소(cafe.naver.com/뒤 부분) — 글 링크 생성용
CAFE_POST_ENABLED  = True         # [설정] 전체 on/off (끄면 아무것도 안 함)
CAFE_DRY_RUN       = False         # [설정] True=미리보기만(실제 전송 X). 검증 끝나면 False로!
CAFE_MIN_MILESTONE = 50000       # [설정] 이 조회수 이상 마일스톤만 카페에 자동게시
CAFE_ATTACH_IMAGE  = True        # [설정] 카드 이미지 첨부(안정성 위해 기본 OFF)
CAFE_POST_DELAY  = 25             # [설정] 카페 글 사이 간격(초) — 연속등록 방지
CAFE_TIME_BUDGET = 250           # [설정] 한 실행 카페 등록 최대 시간(초) — 타임아웃 방어



# 본문은 euc-kr → 이모지 넣지 말 것(자동 제거됨). 순수 텍스트만.
CAFE_SUBJECT_TEMPLATE = "{title}, {views} !!"
CAFE_CONTENT_TEMPLATE = (
    "{artist}의 '{title}'가 \n {views} 조회수를 달성했습니다.\n\n"
    "함께 축하해 주세요.\n\n"
    '▶ <a href="https://youtu.be/{video_id}">영상 보러가기</a>'
)



CAFE_HEADID_DEFAULT   = 0        # 0 = '말머리 선택 안 함'
# 카페 말머리(headid) — 축하게시판(menuid 195) 기준
CAFE_HEADID = {
    "스텔라이브": 215, 
    "에버리스": 704, 
    "유니버스": 707, 
    "클리셰": 712,
    "유니": 705, 
    "후야": 706, 
    "히나": 708, 
    "마시로": 709, 
    "리제": 710,
    "타비": 711, 
    "시부키": 713, 
    "린": 714, 
    "나나": 715, 
    "리코": 716,
}
CAFE_HEADID_DEFAULT = 215   # 매칭 실패 시 '스텔라이브' 말머리


# ── 텔레그램 봇 UI ──
UNIT_BUTTONS = {
    "🌸 에버리스": "에버리스",
    "☁️ 유니버스": "유니버스",
    "✨ 클리셰": "클리셰"
}
BOT_TITLE = "✨ 스텔라이브 봇입니다!"
BOT_SELECT_UNIT_TEXT = (
    "유닛을 선택하세요."
)
BOT_SELECT_MEMBER_TEXT = (
    "멤버를 선택하세요."
)



# 아티스트별 유튜브 플레이리스트
UNITS = {
    "스텔라이브": {
        "nickname": "얘들아 !!",
        "members": {
            "스텔라이브": {
                "channel": "@stellive_official",
                "display": "스텔라이브",
                "keyword": "#스텔라이브",
                "nickname": "애들아 !!",
                "color": "",
                "mark": "",
                "aliases": [
                    "스텔라이브",
                    "Stellive", 
                    "STELLIVE",
                ],
                "playlists": [
                    "PLLjd981H8qSMGC4Nir0hD2Gj9n9PDUoHX", #오리곡
                    "PLLjd981H8qSN9PQ8-X6wINqBF1GjGxusy" #노래
                ],
                "videos": [
                    "https://youtu.be/_BrWJ31tzYs?si=HW5gG6IhWdQdPG_O", # 유니버스 3D BLACKHOLE 커버
                    "https://youtu.be/imggwZXeePQ?si=NJQI49wCXUxbqVHq"  # 유니버스 3D 학원천국 커버
                ]
            }
        }
    },
    "에버리스": {
        "nickname": "얘들아 !!",
        "members": {
            "아야츠노 유니": {
                "channel": "@ayatsunoyuni",
                "display": "아야츠노 유니",
                "keyword": "#yunikki",
                "nickname": "유니야",
                "color": "",
                "mark": "☪️,🤍",
                "aliases": [
                    "아야츠노 유니", 
                    "Ayatsuno Yuni", 
                    "AYATSUNO YUNI", 
                    "유니"
                ],
                "playlists": [
                    "PL3HtH_xx9h_4ulddfVG8DdD_EwKUMBqvL", # 오리곡
                    "PL3HtH_xx9h_7ZGoZ9zMUQ-MPumwe21_cc"  # 노래
                ],
                "videos": [

                ]
            },
            "사키하네 후야": {
                "channel": "@Sakihanechannel",
                "display": "사키하네 후야",
                "keyword": "#huya_live",
                "nickname": "후야야",
                "color": "",
                "mark": "💜,🐲",
                "aliases": [
                    "사키하네 후야", 
                    "Sakihane Huya", 
                    "SAKIHANE HUYA", 
                    "후야"
                ],
                "playlists": [
                    "PL3rF5rqFNO48ZMgPuZ6XbQ1J9IT3TQtcs" #커버곡
                    ],
                "videos": [

                ]
            }
        }
    }, 
    "유니버스": {
        "nickname": "얘들아 !!",
        "members": {
            "시라유키 히나": {
                "channel": "@shirayukihina",
                "display": "시라유키 히나",
                "keyword": "#daily_hina",
                "nickname": "히나얌",
                "color": "",
                "mark": "🎀,❄️",
                "aliases": [
                    "시라유키 히나", 
                    "Shirayuki Hina", 
                    "SHIRAYUKI HINA", 
                    "히나"
                ],
                "playlists": [
                    "PLzdLDJsHzz2OzXsHwt35PHjDq7r93xM1L", # 오리곡
                    "PLzdLDJsHzz2NiuwjyW6QgSck4PrwlSyOc", # 커버곡
                    "PLzdLDJsHzz2N49b_83u_ug3Lwq7HHWx2W", # 히나의 Playlist
                    "PLzdLDJsHzz2NJ0hQg7PBLepqAs5sbo4lO" # 3D
                ],
                "videos": [

                ]
            },
            "네네코 마시로": {
                "channel": "@neneko_mashiro",
                "display": "네네코 마시로",
                "keyword": "#dayshiro",
                "nickname": "찌로야",
                "color": "",
                "mark": "🧇,🥛",
                "aliases": [
                    "네네코 마시로", 
                    "Neneko Mashiro", 
                    "NENEKO MASHIRO", 
                    "마시로"
                ],
                "playlists": [
                    "PLWwhuXFHGLvgHQY8lryIUP7vf9i8-TJrk", #오리곡
                    "PLWwhuXFHGLvhgZZb5_rmQEMI1B0ysKJxG" #커버곡
                ],
                "videos": [

                ]
            },
            "아카네 리제": {
                "channel": "@akanelize",
                "display": "아카네 리제",
                "keyword": "#Lize_daze",
                "nickname": "리제야",
                "color": "",
                "mark": "🩸,🍷",
                "aliases": [
                    "아카네 리제", 
                    "Akane Rize", 
                    "AKANE RIZE", 
                    "리제"
                ],
                "playlists": [
                    "PL-DHk0WpiRNSHxQzKx88q2kmJVwlCQCNq", #오리곡
                    "PL-DHk0WpiRNSM5oI19ImJ8sSV65mnGseX" #커버곡
                ],
                "videos": [
                    "https://youtu.be/LcGrXP-xfHY?si=pTJk28JepLs_eZmU", #SYNC 100%
                    "https://youtu.be/6Q78RPXk2es?si=M2a8dOaTeCySp65w" # 목숨
                ]
            },
            "아라하시 타비": {
                "channel": "@arahashitabi",
                "display": "아라하시 타비",
                "keyword": "#luv_tabi",
                "nickname": "따비야",
                "color": "",
                "mark": "🌊,🧭",
                "aliases": [
                    "아라하시 타비", 
                    "Arahashi Tabi", 
                    "ARAHASHI TABI", 
                    "타비"
                ],
                "playlists": [
                    "PLbIDsfX2JRA2Qoddb0eKan9yFJ0_MR8Nk", #3D
                    "PLbIDsfX2JRA0TXoG69AT8Iu9QEB9lUC2s", #오리곡
                    "PLbIDsfX2JRA0oawGN209gpd_nz9IMvUlb" #커버곡
                ],
                "videos": [

                ]
            }
        }
    },
    "클리셰": {
        "nickname": "얘들아 !!",
        "members": {
            "텐코 시부키": {
                "channel": "@tenkoshibuki",
                "display": "텐코 시부키",
                "keyword": "#for_shibuki",
                "nickname": "요우신~",
                "color": "",
                "mark": "⛩️,🕹️",
                "aliases": [
                    "텐코 시부키", 
                    "Tenko Shibuki", 
                    "TENKO SHIBUKI", 
                    "시부키", 
                    "텐코"
                ],
                "playlists": [
                    "PLanLo2fF2MkY",                      #오리곡
                    "PLKVNBOcsLJlVii-8YwoZTD3o4gh5CnIND", #커버곡
                    "PLKVNBOcsLJlVmzvd2SpmwHZt6KOkcaarD" #3D
                ],
                "videos": [

                ]
            },
            "아오쿠모 린": {
                "channel": "@aokumorin",
                "display": "아오쿠모 린",
                "keyword": "#happy_rin",
                "nickname": "린~",
                "color": "",
                "mark": "☁️,🛼",
                "aliases": [
                    "아오쿠모 린", 
                    "Aokumo Rin", 
                    "AOKUMO RIN", 
                    "린"
                ],
                "playlists": [
                    "PLSDRWR15h-o7xvAej539Ggs2Kjb22y3_M", #오리곡
                    "PLSDRWR15h-o4uWNeoLv0upOUUGj12f-yU", #커버곡
                    "PLSDRWR15h-o5YHBDW4fvHU8UlSCfSuV3r" #3D
                ],
                "videos": [

                ]
            },
            "하나코 나나": {
                "channel": "@hanako_nana",
                "display": "하나코 나나",
                "keyword": "#nanaiary",
                "nickname": "나나야",
                "color": "",
                "mark": "🔫,🐰",
                "aliases": [
                    "하나코 나나", 
                    "Hanako Nana", 
                    "HANAKO NANA", 
                    "나나"
                ],
                "playlists": [
                    "PLJWmDIpvwe7DSCq5McjxHXQCWfrahkIEE", #3D
                    "PLJWmDIpvwe7AjKVPmgswsIVg1ETJyzGvB", #콜라보
                    "PLJWmDIpvwe7CQTYQdGqEipTd7IMX10VHm", #오리곡
                    "PLJWmDIpvwe7AQ3z5-jML31bfMf4QFEx4T", #Nana Drive
                    "PLJWmDIpvwe7Cri29xtAyQXLC1RLwOChpA" #커버곡
                ],
                "videos": [

                ]
            },
            "유즈하 리코": {
                "channel": "@yuzuhariko",
                "display": "유즈하 리코",
                "keyword": "#riko_diary",
                "nickname": "리코코!",
                "color": "",
                "mark": "🍀,⚔️",
                "aliases": [
                    "유즈하 리코", 
                    "Yuzuhariko", 
                    "YUZUHARIKO", 
                    "리코"
                ],
                "playlists": [
                    "PL_D2YrKeYY2U6GvgRx8Ai-VaddWQarbnL", # Riko Cloud
                    "PL_D2YrKeYY2UvRIw_SW3lQXzBDO7aBeii" # 커버곡
                ],
                "videos": [

                ]
            }
        }
    }
}


INITIAL_SETUP = False
