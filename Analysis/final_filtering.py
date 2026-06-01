import csv
from collections import Counter
from pathlib import Path


INPUT_CSV = Path(__file__).resolve().parents[1] / "Datasets" / "gl-cl-w-topics.csv"
OUTPUT_CSV = Path(__file__).resolve().parents[1] / "Datasets" / "gl-cl-w-topics-FINAL.csv"
DELETED_CSV = Path(__file__).resolve().parents[1] / "Datasets" / "deleted2.csv"
PREVIOUS_DELETED_CSV = Path(__file__).resolve().parents[1] / "Datasets" / "deleted.csv"
MERGED_DELETED_CSV = Path(__file__).resolve().parents[1] / "Datasets" / "deleted-videos.csv"


TOPICS_TO_EXCLUDE = {
    28, 35, 39, 67, 75, 85, 99, 118, 135, 152, 157, 160, 163, 166, 180, 191,
    192, 193, 198, 203, 213, 229, 233, 235, 240, 248, 251, 258, 259,
    263, 267, 269, 281, 288, 290, 295, 305, 308, 310, 315, 325, 326, 327,
    328, 329, 333, 334, 340, 343, 352, 357, 362, 364, 368, 371, 377,
    384, 386, 391, 394, 397, 399, 402, 409, 416, 419, 422, 424, 430,
    437, 438, 440, 443, 444, 452, 453, 456, 457, 460, 463, 469, 476,
    478, 481, 486, 487, 494, 498,
}


BANNED_TERMS = [
    "GREENLAND VS GOLDEN PEAK",
    "Lincoln Vs. Greenland",
    "Providence Academy Vs. Greenland",
    "Tulsa Gators vs Greenland Warcats",
    "Greenland vs Lavaca",
    "SIMBA SC VS GREENLAND FC KOMBE",
    "Chinatown Adventures",
    "Nadi Par Bridge",
    "team nickelodeon greenland",
    "India Tours & Travels",
    "Incredible india tour",
    "Birmingham, United Kingdom",
    "Zypern Paphos",
    "Gandhinagar",
    "Restuarant & Bar Greenland",
    "From Greenland's icy mountain",
    "From Greenland's Icy Mountains",
    "From Greenland’s Icy Mountains",
    "MURANG'A COUNTY",
    "Greenland township",
    "Highrise building view",
    "Greenland of africa",
    "RIVER WITH GREENLAND",
    "Hampton Falls Greenland",
    "GREENLAND MINISTRIES",
    "Greenland Campus",
    "R Rating of Greenland",
    "Cities skyline Greenland",
    "scorpio driving",
    "Kasey and Apache",
    "Greenland (2020 - Review Indonesia",
    "GREENLAND GIRLS VISIT",
    "Greenland Girls School",
    "Isipathana College",
    "Da Mirrie Boys o Greenland",
    "Biraj Mushahary",
    "My school my greenland",
    "Fifacraft",
    "Greenland at Limuru",
    "New skin",
    "Meenakshiverma",
    "GREENLAND MOVIE RELEASE",
    "How to watch Greenland Movie",
    "greenland action movies 2020",
    "Greenland watch ltd",
    "Greenland 2 First Watch",
    "Mahabubabad",
    "girl from ipanema goes to greenland",
    "dance by Sis Greenland",
    "Greenland pre primary school",
    "GreenLand cover_maaf",
    "Young pope music from Greenland",
    "Frostpunk",
    "Critical tower defense",
    "Critical tower deafence",
    "Worldbox Orcs",
    "Manali",
    "Chandigarh",
    "Ernakulam",
    "Digha",
    "Upadhyay",
    "Lamjung",
    "Apocalyptique",
    "Pollachi",
    "pazuttuto",
    "Mirzapur",
    "sundaland",
    "RYOICHI",
    "Padmagata",
]


BANNED_CHANNELS = [
    "Greenland Journey Pvt. Ltd.",
    "Pankaj Kohli18 Vlogs",
    "Zee Funzo",
    "All is well unique Updates",
    "Green-land",
    "Grant Tuffrey",
    "Ms. Nanan",
    "Greenland Boarding High school",
    "Viral Short 病毒短裤",
    "Dubai shorts",
    "ALATANI",
    "Hafza Ezaz",
    "Labajit talukdar",
    "Asepuushandayana",
    "Blue Ray",
    "@Shortly Motions 💔",
    "𝕯𝖊𝖊𝖕 𝖛𝖑𝖔𝖌 ।। 𝕯𝖊𝖊𝖕𝖆𝖐 𝖏𝖎",
]


SPECIFIC_BANNED_VIDEO_IDS = {
    "O22eSh4s-t8", "8qHXI09vgLQ", "7qaIsCrRdmc", "0UAqk3VGkXU",
    "FTuYWo9IRiY", "YaXInXNFCek", "I97yKI6ICLg", "_MZSKvQJMLw",
    "zQgYkTVK558", "ZAeU5dQTrrM", "ZLvuvdbuFzQ", "YCAuDp-kVgI",
    "mjSpL6Vt1y0", "iMREO5kJ0HQ", "hfbZxv7V6WY", "ZakmcTFCy70",
    "FQx6pM8t4RY", "UNtPbG11XNo", "FEpArvZzIu4", "jJbvv__fj9o",
    "aFxlRkEgOo8", "rt0F93lUPfM", "BX7OUMBRkaM", "2ky9FE9EpbM",
    "KaY-3s6MwqQ", "_OpRj78Pbhc", "aC9quYoixq0", "nlKxv8XVhFI",
    "-fuJgZ1tdts", "7doTj9HDeHY", "c-7GK3vVKeY", "xTFG2EnowWQ",
    "7--VO4jftgw", "4NQV5WFJQ1c", "E0JJSdrxXjM", "FnUXUTcLSbU",
    "KaqFjZDV5_g", "78-rLsaeTEU", "OKX4xywapZ0", "0eN40c3go7w",
    "_FqJCU0mOOg", "e9Hi8uSUxhM", "-sTh9MqRWF0", "4WFMWxHrWiw",
    "l2Il5o1ve4g", "fABP3X1-TBc", "F6nXRPy_ACc", "k-RHDrNiwlg",
    "Y-JVoHgGVpg", "L3117iNyRYY", "2sxFZncnisY", "nwDyhHDY78c",
    "f3fwKjP7hdw", "kKitHovvbi8", "gdpYNZC2y4o", "fgu0bTaFB18",
    "XIaoVp4OtAE", "V_oeJbV164s", "ro5LHERqm-I", "xrArD1bhfXE",
    "b50N2TT2ycQ", "sz6lGM5Cy4g", "5p1l7ymY6k8", "S2NSzrTkwCc",
    "u1OOPRigEP0", "MKbjU0Q9n2k", "li3F7JOZxF0", "tg9uz1R4PCw",
    "OPIA-jXEnZ4", "Qi65DN8xkQY", "UglgWVt6QvE", "0Sy-4_x9uTQ",
    "qU_pRYi7AME", "_pEmVMwY7uQ", "ih6WVjqMhgk", "zvzuuBs1lHo",
    "7GQ2Q_LHqz4", "i3AJQQa109w", "rBzPrpqM34k", "USQp2YgvsvI",
    "MRGWtzxOuMk", "BUzUI_55NUQ", "-tIzTo-uR8w", "mv0-hhQ3Jnw",
    "SnGt6GRJEFI", "BkyJico8x-U", "iMQfBeipgiU", "eNklycxv5wA",
    "eOXbnT2H9Wc", "eFUBw4omI_g", "Diw1yLrnzeE", "ao6PW5jUAMs",
    "qqkUfavc72I", "xg4gfqVmIvQ", "-TGNaLkAx_w", "lIec-cKQ0iQ",
    "9lyx9DazD1I", "h-qPIHir_Cw", "Lrp3fZn12EM", "vUryf4kaTb8",
    "FT4I6wbHY60", "hk3ZDE9_EKA", "vghY1vzJ0hI", "bEMjhvj_Rew",
    "cbJa7D1TgPw", "yy6y1T1Jl9w", "_r1vPIsqfcM", "c5CP2QhShcw",
    "qdhG53qJo1w", "VFuOeyaDhk0", "4beKcJGQ6Sk", "zUNaRFNx8vg",
    "p3QWbnXk9Ns", "Cn8IOi8h9-E", "Hj-lu2sv3Bg", "H8V1FDY11m4",
    "MJ3KOjyupOQ", "MTO8yQX7Pic", "KRT8y1Pnb9k", "Ax3LfHiF_88",
    "pDpe0jJIKTc", "Ared-yjiWu0", "-04x-yypxy8", "YlNmKntJIok",
    "aD4lPnZ1ywk", "9t45jUX8Fdg", "0oijkjiJbLc", "_sa-oeVdpS8",
    "dGiJ50RgKsc", "PC_AGiupUQA", "KHY4jJO6OuE", "dlh-BjmIgrA",
    "mH2K0OVxAqc", "kallW7rW8bw", "qMwqpf8FFMY", "8W_t2D0wQd0",
    "tth3Ti8KHU4", "l2pU2b72c9U", "SHetdVYLKuc", "wtj_ziFr248",
    "RqT9TaMKKhc", "CzbvjIDcUOk", "jZi-9oCHnAs", "mqIMemurxhw",
    "DeC0-aqZquk", "a_bYXRND3Uk", "4zR8xFpPYsQ", "qCUtzp0Rmrc",
    "odlsJm1-ILs", "yp1uCUDzPfU", "Sd-1KvP2aT0", "TGwQ5--YBX4",
    "A9lj01MESsQ", "hHCiXYvbqSc", "89-56vyl8nA", "2zA1aXtp3Rc",
    "tILAXHojBIY", "nT6dpRlLK5M", "rRRY87mjHKc", "lWnT4Xz4jsw",
    "5whHTXJ9-bI", "_dtjPwf2zWo", "d26dCJjlcNE", "5bxTNZrRtzQ",
    "2MkTqJ4GwZI", "xzNJfc9IFLY", "zK3rWtEc3UU", "SC_0mODc7SY",
    "yMmpjvGzHDY", "d2MM9NuGsGg", "QJJlJdAnaUY", "OISWMwRL86U",
    "PgJq6O-kgbI", "TEVEshbbJwI", "H2gVAZkqaDg", "UmgMfjp24ec",
    "Jiib2gn2vBI", "bbQNgzhUuXE", "BjxXRhCMzIc", "DiK2DjQVbE4",
    "2W34Sje5Mh0", "u2taAQK11EM", "8cPc6KRMsu0", "9vOIWjFviQg",
    "pL4hR9w3Nxc", "ECnDMNynJJI", "MJUoHLJ6w-A", "6s_Nkhqg2hQ",
    "PUIiby3m29M", "r8FXvfFqJTA", "1nyVA7o5eHg", "ZWa1a9I80Vw",
    "EPp_nEE3ws4", "7ow8sB_RIrk", "Jx1H7uj9Rsc", "NM18b17w-IQ",
    "bGvM9ZQiqeo", "SBRUsB6-WPo", "Exuni2MLMuM", "CXlViO0s2Z4",
    "QgTi7RsLcZY", "nWx7nt0m3po", "CGcB7ATwruE", "oBuAQk-6uA8",
    "FxJM7PjqJws", "B0IIUvzs3vY", "Bw02Ym5P43A", "gggOBrZQE6Q",
    "H-EW9YzNvn8", "SFIp2VfLnNI", "3cNWmWEwW4I", "tq81At3rNyc",
    "ASB3YvMmz_I", "na-hMbOI_rk", "KCpBZ1hCDSg", "fZ8LAd-8TTM",
    "3qiTlJpFkyQ", "PstlJd2_wEs", "Tez6WtLg9DA", "Y8HG4maQByw",
    "T6S8PRpW0Ww", "JR_WYTpiQ9k", "M8A0knKVUVk", "5pTEBh6ZDqU",
    "C-gJohVOh44", "USB5JWVjKfI", "COg1JGBVgsE", "4zjzX4E6rVc",
    "YXFaMGIeGJ8", "FHItdN8l5T0", "j1TWdfciFs0", "PEZY4InOqOw",
    "wdCCGfLSBm0", "tQ3VE-Z4pEY", "E1RRjhCVWaM", "wlS__NSFRTA",
    "xVEnj1Fg2js", "4bzH_gREN1Y", "4x7ReBhudFg", "TRAeSwYbLbs",
    "qOO2FXJ_Oic", "vAM-LlVpb04", "b0rVyNvMC1I", "7kDXgeWRQZk",
    "n2MOmE7U_Bg", "lekLDnoly0k", "lTE2U1Q_EuA", "jgTzNVDrN9w",
    "xXg0srgN69c", "YDa0B3jbYzA", "qUiXMKphiYQ", "v4eCt7m6Mco",
    "ui8lecf3RPk", "ZmrrkBsMDYc", "q8qMsYSPefk", "XOPJ2MD1XmQ",
    "by6yBDwWms4", "NKfmJjvdq3w", "0naMMCfa78g", "-nJEhKDYVTg",
    "uCZc_7EP9Ig", "TzgFb-LjPzk", "SBZ4OTrXdn4", "lkhf5X5xYD0",
    "RWRyjCAXvQI", "xtO4srBcxfU", "sdBPauI1q0A", "VdkKdGiIEeM",
    "5f6XtTqldYQ", "JUL8869TaOE", "HatO7CWDWwM", "UQDr9TJTKVE",
    "D5PH0J_VETQ", "5EsdaudUOcY", "51WfeMe9TSI", "MlUxJC1JqpQ",
    "Lzdc2QgccGQ", "XMKrHo5J_DQ", "Sut3BO1MPlk", "M1EqEd5mLQk",
    "NZlR0n7XFiE", "r-Yj0gx1bKY", "ao71L_cnf9k", "3IonVMfR6B8",
    "QyVhlqy7CY4", "pyFvhyz0ot8", "Ys4xkGHROvI", "I4EzqEeI6bU",
    "83xbK0kq3vs", "yuuv8j6i7vg", "Iio6i0VuHjQ", "HbntN9JsywM",
    "ip-5g5a3zz4", "rTrl9u6UCEY", "AAm4uvnicNc", "oXSwdDHDIe4",
    "myYr65DQnh0", "rGzlZfTrq9A", "N9fKyXUDKGs", "TrSwQ_MWSR8",
    "qOA7DRJZocY", "cnTih9UPVX0", "q_lm82nh3P0", "BKSc6LIQJGA",
    "43EZPkOMkBg", "zPGrYNMlebw", "Fp70M1zGMhI", "CzO9X4HxaXQ",
    "10AcgDHRkEI", "kS_5C5i_rUw", "Q2cE6E7fXqQ", "t62Sv63jMC8",
    "6k1O3TcrXWU", "nB8PHPi2lIo", "OvnaVgqIe-c", "3UU-e3F11ZE",
    "f0012EXPNmY", "pKurfgl0BXw", "nc3Du60g4WU", "9ceO_HUdGjs",
    "rIISU-GcG6A", "AbUoVKgLnxc", "fwvhK3f7STI", "P3A9ia4lo60",
    "u9rpdeLeZhA", "6byzjccTrEY", "u-YO7iCgk4g", "AWkXPMMWZBE",
    "Km6aJVIIAPY", "iP8S6wWvfLc", "XPsyr2yixMk", "lCT05ufaPQA",
    "dMs54ODfJ7I", "E78qeGs8SU0", "mH-3IO302_I", "9fuHHB_aXF8",
    "h0SLxIw0Gew", "4DGqjemLW84", "vDyFPzAucXQ", "ZLwnCCJLXh0",
    "i9jREYeO_XQ", "BcmlquIGT9g", "miy9Mf67-vQ", "4c8_s3DOp0c",
    "AGx1KK4o-wY", "v7SkAAk6-fw", "uIZIi-qaHoU", "j3ckZzt-mxs",
    "UxtiVq_SxJs", "yjWA1pgzg1w", "7_H0gmF9NcA", "xM9l0FmFrpY",
    "GZ1pcOa6JrU", "Vm-vVgF3AX8", "KS4MfeHcx5c", "D-G0uoJiKd0",
    "dW_waFB2Hzs", "lks6Zfm2H58", "KX3RXG2nW8U", "5_HZlGBkY6M",
    "55RMdZy3-9Y", "4ex83ATv4l0", "OroY3Rakvik", "EHwrEeYUoS4",
    "KHBFm0F1dxQ", "n4qkqBfGlyA", "Us1VlwUXOcc", "8-rUdwokYw8",
    "47BkHfhrDss", "7BsppkAAWWc", "handL3WJex4", "vhBrn3KyizU",
    "9GRJP3znjVE", "w4Qb5iovvYM", "xPhKj5lPNU8", "dx2f9lo6AnM",
    "QZ0Uc-bT_sw", "JouEvJUZ4g0", "opEdKhTKAaY", "ZKkDg1JiTfA",
    "QmlsHwvnUoo", "hWOF8LIsf1Y", "4bj0Hkb_3lo", "D9TSqiHZpKY",
    "_Uw6lrxS2hM", "a2lgduKRupg", "vKivCO_1MSw", "4PS_3Y0x3II",
    "nD-SxsMa8OU", "V_xGRIa61Kw", "Kp-MRRdsV3c", "s-SL4w-1hCk",
    "yUaNAWDwhE8", "C3nvNB5UnoA", "1mBszbYbT80", "Mix6SoHxxiI",
    "s4X8JrIcakw", "RMrTK0NLzHY", "eBFOXDv0vHc", "QzEFr9vbnCI",
    "CLM8SXIHYt4", "pg7t-8o5mJ8", "c232mqbaXdI", "_Mi8tGoOdmc",
    "0RCXItDlYP8", "2JJRmzWMWPU", "8dJtv3YV3fQ", "dvHdaAUJkAY",
    "gA8O1S5VoUU", "ZJQ_woXaQMQ", "Lr_camLmBfI", "X2G_G1Hyaq8",
    "IRLxe_Xc41U", "cHuMOPlfjqo", "7_x7xVB-afE", "GWBAlHZHfMA",
    "PhUHuvBiiqM", "5IOFbbhD7Sg", "TuihVIeAHfk", "MQm6ETlLTSc",
    "Vhz4weuCAG0", "6ozJQHDAQFU", "VuAH8FY1mgw", "VMNWhWnshzQ",
    "-Y3S8c-BAuk", "HxKpAKst4Eg", "6PLzBQDkfIM", "M8qgauZX2SU",
    "mrRZflfk8Kc", "8bPqKMD_KuA", "gV_m3pYlPMU", "nn_pS_9Rlxk",
    "X4ml-H96mD8", "CRTCVi2yeUM", "qyWHCliM7sM", "8LosyQz6Pe0",
    "grIfL8wolog", "mWJ6fxgORqI", "eqCvb7HGT6k", "y8ZIHnyOcO0",
    "XqflSOfPiEw", "1mBQnuZVbXw", "Y8YUcWbWc3o", "VVPcvlFY6ME",
    "H2WeSDIajmY", "9ZPyKm5NwAM", "PxR-bxvz4GU", "Iim2EIg5YSk",
    "aTK22tNVn2Y", "1Oj4whT-_J0", "ecWUvbVOkQw", "W9TRCZQrlVg",
    "ecyD3AIs1PE", "edKTX2W5-BU", "M9c_A5AwJZ0", "UtL0y5C-nXA",
    "UcXuxFuzB-w", "DQBv0w9MgIk", "Pn0WCfl_6zM", "_OVuvSiszjE",
    "RCpMoENKXdc", "MOj2zKwPp0w", "kd99Vo-uFSc", "IFl_m8rF9jc",
    "8Zb6LwCbli8", "lxxeaXQKn94", "Qwce0pTxkSo", "mkf1rwlsrYQ",
    "8HxX4FxNe3c", "jMSvvR7e7kU", "_xeawFSKBeo", "rP22MNtmGEc",
    "rJTQ0PyUTQI", "4eO_xoyTuZE", "CJKDOuRiW_c", "-rA3s4dROKM",
    "rgXnWLp97Q8", "CfmNndYrE7A", "q9WYHGaTiiE", "uiGe72Hfevg",
    "vAFtICyWU1A", "_By8nVHenw8", "mDb2kexmkCs", "u9v2GLkePng",
    "nML0zAsi9J0", "6SMFU6Z6MxI", "-QYYVGqYCCc", "jz0SqaMal58",
    "YerlMmw79E4", "bamJUsnu7ss", "AM91t1ml4_Y", "J3Q8ZJGqDig",
    "cBAbDP66j0U", "axkwmIa8Z_w", "lab_M0pvBCA", "1BvpP11IBKU",
    "3cI8kKXaxew", "PDPowRw0ejE", "MGFacp7-Uyk", "gpUhDnk1bdY",
    "qkwJj_1N0uk", "cKsdPg4Gax8", "fXyaSDwQz-8", "ihJvuQwLRqA",
    "uCRTlpnSLX8", "-lNBnJTQseU", "qQR0QCw5PoM", "taoctCcR5KE",
    "0MRWXaifBDs", "vEZb7m5nONc", "uz_BQRSIvzs", "rZJ79qk1CzY",
    "XLWYONfA-aM", "ZtRwb1LgRBE", "MQ_qWag0Ixo", "hsZIJneol9E",
    "YU5NyZOGdAI", "PBUjfV0N6sg", "h_KbwoS2cA4", "NCFiNuAz870",
    "OLWkFZG9MmM", "OHO3l8T96Ws", "mYk5FvZqw_I", "sGP21EMWytY",
    "LZom1Kg073M", "N1STo_2fX40",
}


RECODE_TO_TOPIC_500_VIDEO_IDS = {
    "1MPxLKhOiiw",
    "SzJ6S1Hmptc",
    "Ri7bZNWjNy8",
    "KkD4oxKzIDk",
    "yeHBUD3Vt1Q",
    "V8sRpO-mZns",
    "FTLVarToG0U",
    "0Fvy04fLCLU",
    "DS4JikjzYBg",
    "CW20WGMpqA0",
}


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


NORMALIZED_BANNED_TERMS = [normalize_text(term) for term in BANNED_TERMS]
NORMALIZED_BANNED_CHANNELS = {normalize_text(channel) for channel in BANNED_CHANNELS}


def topic_number(topic_value: str | None) -> int | None:
    value = (topic_value or "").strip().casefold()
    if value.startswith("topic"):
        value = value.removeprefix("topic")
    try:
        return int(value)
    except ValueError:
        return None


def banned_term_in_title(title: str) -> str | None:
    normalized_title = normalize_text(title)
    for term in NORMALIZED_BANNED_TERMS:
        if term in normalized_title:
            return term

    if "the greenland show" in normalized_title and "the greenland showdown" not in normalized_title:
        return "the greenland show"

    return None


def removal_reason(row: dict[str, str]) -> str | None:
    video_id = (row.get("video_id") or "").strip()
    if video_id in SPECIFIC_BANNED_VIDEO_IDS:
        return "specific video ID"

    channel_title = normalize_text(row.get("channel_title"))
    if channel_title in NORMALIZED_BANNED_CHANNELS:
        return "banned channel"

    if banned_term_in_title(row.get("video_title") or ""):
        return "banned term"

    topic = topic_number(row.get("topic"))
    if topic in TOPICS_TO_EXCLUDE:
        return "excluded topic"

    return None


def read_rows_for_merge(path: Path, source_name: str) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return [], []

        rows = []
        for row in reader:
            row_with_source = dict(row)
            row_with_source["deleted_source"] = source_name
            rows.append(row_with_source)

    fieldnames = list(reader.fieldnames)
    if "deleted_source" not in fieldnames:
        fieldnames.append("deleted_source")
    return rows, fieldnames


def merge_deleted_files() -> int:
    previous_rows, previous_fieldnames = read_rows_for_merge(PREVIOUS_DELETED_CSV, "deleted.csv")
    current_rows, current_fieldnames = read_rows_for_merge(DELETED_CSV, "deleted2.csv")

    merged_fieldnames = []
    for fieldname in previous_fieldnames + current_fieldnames:
        if fieldname not in merged_fieldnames:
            merged_fieldnames.append(fieldname)

    MERGED_DELETED_CSV.parent.mkdir(parents=True, exist_ok=True)
    with MERGED_DELETED_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=merged_fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in previous_rows + current_rows:
            writer.writerow(row)

    return len(previous_rows) + len(current_rows)


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    kept_count = 0
    total_count = 0
    recoded_count = 0
    removal_counts: Counter[str] = Counter()

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as src, OUTPUT_CSV.open(
        "w", encoding="utf-8", newline=""
    ) as dst, DELETED_CSV.open("w", encoding="utf-8", newline="") as deleted_dst:
        reader = csv.DictReader(src)
        if reader.fieldnames is None:
            raise ValueError(f"No header found in {INPUT_CSV}")
        if "topic" not in reader.fieldnames:
            raise ValueError("Input CSV must contain a 'topic' column.")

        writer = csv.DictWriter(dst, fieldnames=reader.fieldnames)
        writer.writeheader()
        deleted_fieldnames = list(reader.fieldnames)
        if "deletion_reason" not in deleted_fieldnames:
            deleted_fieldnames.append("deletion_reason")
        deleted_writer = csv.DictWriter(deleted_dst, fieldnames=deleted_fieldnames)
        deleted_writer.writeheader()

        for row in reader:
            total_count += 1
            video_id = (row.get("video_id") or "").strip()
            if video_id in RECODE_TO_TOPIC_500_VIDEO_IDS:
                row["topic"] = "topic500"
                recoded_count += 1

            reason = removal_reason(row)
            if reason:
                removal_counts[reason] += 1
                deleted_row = dict(row)
                deleted_row["deletion_reason"] = reason
                deleted_writer.writerow(deleted_row)
                continue

            writer.writerow(row)
            kept_count += 1

    removed_count = total_count - kept_count
    removed_pct = (removed_count / total_count * 100) if total_count else 0
    merged_deleted_count = merge_deleted_files()

    print("Final filtering summary")
    print("=" * 38)
    print(f"Videos before: {total_count:,}")
    print(f"Videos after: {kept_count:,}")
    print(f"Videos deleted: {removed_count:,} ({removed_pct:.2f}%)")
    print("")
    print("Deleted by rule")
    print("-" * 38)
    print(f"Banned terms: {removal_counts['banned term']:,}")
    print(f"Banned channels: {removal_counts['banned channel']:,}")
    print(f"Specific video IDs: {removal_counts['specific video ID']:,}")
    print(f"Excluded topics: {removal_counts['excluded topic']:,}")
    print("")
    print(f"Recoded to topic500: {recoded_count:,} rows")
    print(f"Wrote: {OUTPUT_CSV}")
    print(f"Wrote deleted rows: {DELETED_CSV}")
    print(f"Wrote merged deleted rows: {MERGED_DELETED_CSV} ({merged_deleted_count:,} rows)")


if __name__ == "__main__":
    main()
