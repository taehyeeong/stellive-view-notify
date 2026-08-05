# 감시할 유튜브 채널 설정 파일

# YouTube 채널 핸들
CHANNELS = {
    "@shirayukihina": "시라유키 히나"
}


# 아티스트별 유튜브 플레이리스트
ARTISTS = {
    "시라유키 히나": {
        "keyword": "#daily_hina", # 태그
        "nickname": "히나", # 히나야
        "playlists": [
           "PLzdLDJsHzz2OzXsHwt35PHjDq7r93xM1L", # 히나 오리곡

            "PLzdLDJsHzz2NiuwjyW6QgSck4PrwlSyOc", # 히나 커버곡
    
            "PLzdLDJsHzz2N49b_83u_ug3Lwq7HHWx2W", # 히나 '히나의 Playlist'
    
            "PLzdLDJsHzz2NJ0hQg7PBLepqAs5sbo4lO"  # 히나 3D Live
        ]
    }
}


# 조회수 알림 단위
# 50000 = 5만 조회수마다 알림
VIEW_STEP = 50000


# 음악 영상으로 판단할 제목 키워드
MUSIC_KEYWORDS = [
    "MV",
    "Music Video",
    "Official",
    "Original",
    "Cover",
    "歌ってみた",
    "オリジナル",
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
    "雑談",
    "잡담"
]


# 특별 알림 기준
MILESTONES = [
    100000,     # 10만
    500000,     # 50만
    1000000,    # 100만
    5000000,    # 500만
    10000000,   # 1000만
]


INITIAL_SETUP = False
