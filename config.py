# 감시할 유튜브 채널 설정 파일

# YouTube 채널 핸들
CHANNELS = {
    "@shirayukihina": "시라유키 히나"
}


# 아티스트별 유튜브 플레이리스트
ARTISTS = {

    "1기생": {
       "아야츠노 유니": {
            "channel": "@ayatsunoyuni",
            "display": "아야츠노 유니",
            "keyword": "#yunikki",
            "nickname": "유니야",

            "playlists": [
                "PL3HtH_xx9h_4ulddfVG8DdD_EwKUMBqvL", # 오리곡
                "PL3HtH_xx9h_7ZGoZ9zMUQ-MPumwe21_cc"  # 노래
            ]
        },
       "사키하네 후야": {
            "channel": "@Sakihanechannel",
            "display": "사키하네 후야",
            "keyword": "#huya_live",
            "nickname": "후야야",

            "playlists": [
                "PL3rF5rqFNO48ZMgPuZ6XbQ1J9IT3TQtcs" # 커버곡
            ]
        }
    },
    
    "2기생": {
        "시라유키 히나": {
                    "channel": "@shirayukihina",
                    "display": "시라유키 히나",
                    "keyword": "#daily_hina",
                    "nickname": "히나",
        
                    "playlists": [
                        "PLzdLDJsHzz2OzXsHwt35PHjDq7r93xM1L",  # 오리곡
                        "PLzdLDJsHzz2NiuwjyW6QgSck4PrwlSyOc",  # 커버곡
                        "PLzdLDJsHzz2N49b_83u_ug3Lwq7HHWx2W", # 히나 Playlist
                        "PLzdLDJsHzz2NJ0hQg7PBLepqAs5sbo4lO"  # 3D Live
                    ]
                },
         "네네코 마시로": {
            "channel": "@neneko_mashiro",
            "display": "네네코 마시로",
            "keyword": "#dayshiro",
            "nickname": "찌로야",

            "playlists": [
                "PLWwhuXFHGLvgHQY8lryIUP7vf9i8-TJrk", # 오리곡
                "PLWwhuXFHGLvhgZZb5_rmQEMI1B0ysKJxG"  # 커버곡
            ]
        },
         "아카네 리제": {
            "channel": "@akanelize",
            "display": "아카네 리제",
            "keyword": "#Lize_daze",
            "nickname": "맂제야",

            "playlists": [
                "PL-DHk0WpiRNSHxQzKx88q2kmJVwlCQCNq", # 오리곡
                "PL-DHk0WpiRNSM5oI19ImJ8sSV65mnGseX"  # 커버곡
            ]
        },
        "아라하시 타비": {
            "channel": "@arahashitabi",
            "display": "아라하시 타비",
            "keyword": "#luv_tabi",
            "nickname": "따비야",

            "playlists": [
                "PLbIDsfX2JRA2Qoddb0eKan9yFJ0_MR8Nk", # 3D
                "PLbIDsfX2JRA0TXoG69AT8Iu9QEB9lUC2s", # 오리곡
                "PLbIDsfX2JRA0oawGN209gpd_nz9IMvUlb"  # 커버곡
            ]
        }
    },

    "3기생": {
        "텐코 시부키": {
            "channel": "@tenkoshibuki",
            "display": "텐코 시부키",
            "keyword": "#for_shibuki",
            "nickname": "요우신",

            "playlists": [
                "PLanLo2fF2MkY",                    # 오리곡
                "PLKVNBOcsLJlVii-8YwoZTD3o4gh5CnIND", # 커버곡
                "PLKVNBOcsLJlVmzvd2SpmwHZt6KOkcaarD"  # 3D
            ]
        },
        "아오쿠모 린": {
            "channel": "@aokumorin",
            "display": "아오쿠모 린",
            "keyword": "#happy_rin",
            "nickname": "린",

            "playlists": [
                "PLSDRWR15h-o7xvAej539Ggs2Kjb22y3_M", # 오리곡
                "PLSDRWR15h-o4uWNeoLv0upOUUGj12f-yU", # 커버곡
                "PLSDRWR15h-o5YHBDW4fvHU8UlSCfSuV3r"  # 3D
            ]
        },
         "하나코 나나": {
            "channel": "@hanako_nana",
            "display": "하나코 나나",
            "keyword": "#nanaiary",
            "nickname": "나나야",

            "playlists": [
                "PLJWmDIpvwe7DSCq5McjxHXQCWfrahkIEE", # 3D
                "PLJWmDIpvwe7AjKVPmgswsIVg1ETJyzGvB", # 콜라보
                "PLJWmDIpvwe7CQTYQdGqEipTd7IMX10VHm", # 오리곡
                "PLJWmDIpvwe7AQ3z5-jML31bfMf4QFEx4T", # Nana Drive
                "PLJWmDIpvwe7Cri29xtAyQXLC1RLwOChpA"  # 커버곡
            ]
        },
        "유즈하 리코": {
            "channel": "@yuzuhariko",
            "display": "유즈하 리코",
            "keyword": "#riko_diary",
            "nickname": "리코야",

            "playlists": [
                "PL_D2YrKeYY2U6GvgRx8Ai-VaddWQarbnL", # Riko Cloud
                "PL_D2YrKeYY2UvRIw_SW3lQXzBDO7aBeii"  # 커버곡
            ]
        }
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
