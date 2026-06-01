import argparse
import csv
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ENGLISH_HINT_WORDS = {
    "the",
    "and",
    "is",
    "in",
    "for",
    "with",
    "from",
    "on",
    "at",
    "new",
    "video",
    "official",
    "live",
    "music",
    "news",
    "review",
    "guide",
    "part",
    "episode",
    "day",
    "trip",
    "travel",
    "ice",
    "arctic",
    "north",
    "south",
    "sea",
    "climate",
    "change",
    "greenland",
}

NON_ENGLISH_TITLE_CUES = {
    # Indonesian / Malay-style cues seen in the dataset
    "wisata",
    "rumah",
    "putih",
    "pijiombo",
    "wlingi",
    "blitar",
    "tulungagung",
    "sirah",
    "kencong",
    "surabaya",
    "musik",
    "sayang",
    "selalu",
    "perumahan",
    "puasa",
    "terlama",
    "ketika",
    "menyerang",
    "prancis",
    "luas",
    "wilayah",
    "asli",
    "inilah",
    "gowes",
    "menikmati",
    "indahnya",
    "alam",
    "mengapa",
    "mengerti",
    "memiliki",
    "terbalik",
    "penjelasan",
    "tentang",
    "hiu",
    "ganasnya",
    "laut",
    "mumbai",
    "khopoli",
    "diguyur",
    "hujan",
    "pertama",
    "kalinya",
    "wahana",
    "jeruk",
    "taman",
    "buah",
    "mekarsari",
    "proyek",
    "pembangunan",
    "kalijaga",
    "kota",
    "cirebon",
    "hiburan",
    "antar",
    "tonton",
    "saya",
    "menuju",
    "panduan",
    "jalan",
    "gawat",
    "mencair",
    "makin",
    "cepat",
    "begini",
    "jadinya",
    "kalu",
    "dunia",
    "hancur",
    "alur",
    "cerita",
    "ambisi",
    "amerika",
    "eropa",
    "caplok",
    "kuasai",
    "terungkap",
    "alasan",
    "tersembunyi",
    "balik",
    "hingga",
    "perdana",
    "menolak",
    "logam",
    "tanah",
    "jarang",
    "jaditau",
    "sih",
    "di",
    "sa",
    "dito",
    "kakaiba",
    "misteri",
    "musim",
    "dingin",
    "perlak",
    "bangka",
    "bangkabelitung",
    "dan",
    "dari",
    "orang",
    "bagaimana",
    "apakah",
    "apa",
    "tidur",
    "adalah",
    "yang",
    "kalian",
    "tertukar",
    "islandia",
    "negara",
    "memohon",
    "tapi",
    "suraj",
    "nikalta",
    "mencari",
    "sampai",
    "kenapa",
    "hai",
    "mana",
    "bisa",
    "gitu",
    "pulau",
    "tidak",
    "ndak",
    "hijau",
    "masti",
    "makanan",
    "masakan",
    "kuliner",
    "pilih",
    "memilih",
    "masuk",
    "neraka",
    "surga",
    "warga",
    "bahan",
    "bangunan",
    "salju",
    "kayu",
    "arkeolog",
    "jejaksejarah",
    "warisanbudaya",
    "pemukiman",
    "faktaunik",
    "faktamenarik",
    "fakta",
    "uddan",
    "carnis",
    "selon",
    "systue",
    "murga",
    "remorca",
    "kritik",
    "dhothim",
    "mundialito",
    "wirklich",
    "traineau",
    "destructiva",
    "apocalipsis",
    "febrero",
    "riassunto",
    "kargilwar",
    "refazendo",
    "peligro",
    "wirtschaftssimulation",
    "inchieste",
    "weltuntergang",
    "resumiendo",
    "abgeschnitten",
    "recensioni",
    "ordentlich",
    "quitaron",
    "arraijan",
    "juillet",
    "trasformazione",
    "verarbeitung",
    "bearbetning",
    "scorciatoia",
    "giripurno",
    "rastika",
    "wetter",
    "cachorros",
    "unamourdetapis",
    "squilibrato",
    "formand",
    "iklim",
    # Tagalog / Filipino-style cues seen in the dataset
    "makakabili",
    "yayamanin",
    "basurahan",
    "foodtripan",
    "ibinunyag",
    "dahil",
    "napalipad",
    "papuntang",
    "ano",
    "malaki",
    "bagong",
    "kaalaman",
    "lathitha",
    "maposa",
    "skiets",
    # Kinyarwanda-style cues seen in the dataset
    "kuwa",
    "umunsi",
    "ufatwa",
    "gukuramo",
    "hatangijwe",
    "umushinga",
    "ibipupe",
    "buntu",
    # Arabic-transliterated / other repeated non-English title cues seen in the dataset
    "barkatin",
    "fesban",
    "zahra",
    # Gujarati / Punjabi / South Asian transliterated cues seen in the dataset
    "chokdi",
    "lokdayro",
    "ajj",
    "gye",
    "vich",
    "masla",
    "liye",
    "bhaloo",
    "ghar",
    "gobar",
    "khad",
    "dalne",
    "baini",
    "garau",
    "ramailo",
    "teej",
    "weendas",
    "jasiirada",
    "ugu",
    "weyn",
    "caalamka",
    # Portuguese / Turkish / Polish-style cues seen in the dataset
    "vendo",
    "filme",
    "muito",
    "recomendo",
    "assistir",
    "serie",
    "requisitos",
    "convenio",
    "fundaciones",
    "fortalecer",
    "reciclaje",
    "para",
    "con",
    "del",
    "desde",
    "hasta",
    "nueva",
    "firma",
    "trabajo",
    "basura",
    "paese",
    "dei",
    "della",
    "delle",
    "degli",
    "balocchi",
    "italia",
    "italiano",
    "italiana",
    "serie",
    "nuova",
    "requisiti",
    "paesaggio",
    "schwarzwald",
    "yerli",
    "dizi",
    "filmlerde",
    "calan",
    "paylasilir",
    "sadece",
    "orijinal",
    "ogladaj",
    "legalnie",
    "platformie",
    # Additional repeated cues from false-positive Greenland titles in the dataset
    "kisan",
    "nagar",
    "govinda",
    "patak",
    "sarvshiber",
    "pinoy",
    "junreyingreenland",
    "pinoyingreenland",
    # Hindi / Urdu transliterated cues seen in the dataset
    "kyu",
    "dubta",
    "karidne",
    "koshish",
    "nhi",
    "kyun",
    "mein",
    "mera",
    "sabz",
    "wadiyon",
    "sukoon",
    "jannatkashmir",
    "kashmirtravel",
    "jheel",
    "pakistantourism",
    "jastai",
    "raix",
    "jalanjalan",
    "kebalik",
    "kashmirtour",
    "hadeesenabvi",
    "qayamah",
    "bantusuport",
    "pemandanganindah",
    "pamandangan",
    "kattuvelai",
    "sindhintireal",
    "convenio",
    "fundaciones",
    "fortalecer",
    "reciclaje",
    "malinamakkikondu",
    "companiyil",
    "ozhukunna",
    "formaldihaide",
    "chemickal",
    "firokan",
    "laban",
    "kulon",
    "menganti",
    "requisitos",
    "cemara",
    "arah",
    "panah",
    "asmara",
    "cintaku",
    "paese",
    "balocchi",
    "chillen",
    "takakanonuma",
    "takakanonouma",
    "panchai",
    "balja",
    "kkathmandu",
    "parachinar",
    "vruno",
    "rumbera",
    "teen",
    "jagah",
    "patni",
    "sath",
    "nahin",
    "chhodana",
    "chahie",
    "atsilisakka",
    "katiteqqitat",
    "meri",
    "narak",
    "aaj",
    "maosam",
    "bada",
    "rindurumah",
    "dhinam",
    "unnai",
    "ninaivil",
    "kondenadi",
    "marupadiyum",
    "yaraiuu",
    "evolo",
    "azhaga",
    "pakkala",
    "gureh",
    "punjabi",
    "klombo",
    "kokan",
    "lalpari",
    "groenlandia",
    "safarnam",
    "yeduniya",
    "deklarasi",
    "gereja",
    "sesungguhnya",
    "sejenak",
    "waktu",
    "tempuh",
    "yowes",
    "kediri",
    "morya",
    "sohala",
    "pengamen",
    "tadika",
    "perairan",
    "caasimada",
    "soonka",
    "saacadaha",
    "lasoomo",
    "shqiptar",
    "outbond",
    "borama",
    "senggigi",
    "ciliwung",
    "oragadam",
    "kharagpur",
    "undrajavaram",
    "borewell",
    "allapalli",
    "allapali",
    "firtu",
    "grammer",
    "pratice",
    "trailler",
    "virel",
    "wamewachana",
    "escapismo",
    "azzahra",
    "turun",
    "gunung",
    "jajal",
    "kiamat",
    "mercado",
    "peixe",
    "keliling",
    "kawasan",
    "petunjuk",
    "vidio",
    "magsingkamas",
    "berwisata",
    "masyarakat",
    "siaga",
    "ketegangan",
    "diperebutkan",
    "alasannya",
    "bukan",
    "gambar",
    "menggambar",
    "bendera",
    "penduduk",
    "pemerintahan",
    "merdeka",
    "berlayar",
    "serah",
    "konsumen",
    "hunian",
    "terjangkau",
    "promo",
    "murah",
    "prasmanan",
    "masakanjawa",
    "pacitan",
    "beritaterkini",
    "siap",
    "tembak",
    "redam",
    "kopenhagen",
    "gambar",
    "depan",
    "caplok",
    "diambilnya",
    "oleh",
    "keunikan",
    "tahukahkamu",
    "jeddah",
    "kyon",
    "chahiye",
    "bare",
    "aap",
    "jante",
    "sote",
    "kab",
    "yaha",
    "hoti",
    "kabja",
    "jameen",
    "badal",
    "lenge",
    "gaon",
    "sundar",
    "dekhiae",
    "mchezaji",
    "magoli",
    "dhidi",
    "amani",
    "kubwa",
    "tazama",
    "lebih",
    "daripada",
    "turki",
    "numaesh",
    "nidi",
    # Topic 54 false-positive cues added after manual review
    "bohut",
    "hundor",
    "nungaiba",
    "khara",
    "mazdehee",
    "amrica",
    "allahwalilake",
    "dildilpakistan",
    "loveyoupakistan",
    "yengadapora",
    # Additional South Asian transliterated cues from manual false-positive review
    "naya",
    "kanjoos",
    "teez",
    "barish",
    "garmi",
    "mansoba",
    "nakam",
    "raheemullah",
    "nazimabad",
    # Extra multilingual movie/recap cues observed in Greenland film-content spillover
    "singkat",
    "narasi",
    "catastrophe",
    "manquez",
    "takrane",
    "khatarnak",
    # Topic-review cues from remaining non-English Greenland titles
    "kujataa",
    "aku",
    "beli",
    "iratabaza",
    "gushyira",
    "hamwe",
    "bakarwanya",
    "arimurira",
    "intambara",
    "muri",
    "keunikan",
    "riroda",
    "nyumbani",
    "maarifa",
    "graba",
    "dandiya",
    "arti",
    "technologia",
    "talaga",
    "jhula",
    "ka",
    "em",
    "ko",
    "kamal",
    "nurul",
    "delgado",
    "tot",
    # Foreign/non-English words from video filtering
    "pratishtha",
    "recensione",
    "lavorazione",
    "dernier",
    "febbraio",
    "rupanya",
    "menjelajahi",
    "kembali",
    "kekerasan",
    "bisakah",
    "vashikaran",
    "lahnakoski",
    "sholawat",
    "kartini",
    "weekustik",
    "kelahiran",
    "orthanadu",
    "pemandangan",
    "madarsa",
    "wanita",
    "respiro",
    "terbaru",
    "bisiklet",
    "upoutávka",
    "hakselen",
    "treinando",
    "lagoinha",
    "lempongsari",
    "iwamizawa",
    "semeru",
    "tunaw",
    "tunisialaisittain",
    "terapiaa",
    "kririk",
    "payageli",
    "barokahjumat",
    "fenrir",
    "mangangalakal",
    "orchidta",
    "setiawan",
    "akhirnya",
    "sendirian",
    "ponorogo",
    "tingkat",
    "piovend",
    "ditolak",
    "pazhamudir",
    "nilayam",
    "farishta",
    "nobita",
    "kasvihuoneen",
    "kokoamisohje",
    "gonoharjo",
    "biaya",
    "awalny",
    "perumahaan",
    "gantung",
    "khidki",
    "yomgo",
    "kamki",
    "meethi",
    "piknik",
    "jayakishori",
    "temannya",
    "prokiritir",
    "lantaw",
    "dot lewat",
    "paling besar",
    "mahiye",
    "bornodi",
    "menarik",
    "matahari",
    "hmarianokhiduniya",
    "kudremukha",
    "jaate",
    "khatarnak",
    "ke duniya",
    "kiyon",
    "durgapuja",
    "makrab",
    "jedag",
    "usthaadinde",
    "hubburasool",
    "anandham",
    "vinnil",
    "astaghfirullah",
    "nolasha",
    "timaada",
    "nattuvazhiyile",
    "kooban",
    "kahani",
    "siapa",
    "bilicda",
    "cajiibka",
    "barafka",
    "cagaaran",
    "mengatakan",
    "haiuzwi",
    "warganya",
    "sekjen",
    "tegaskan",
    "bantuan",
    "jawaab",
    "rahasya",
    "veppanapalli",
    "zangezur",
    "tertua",
    "sababta",
    "meeshaan",
    "trabahante",
    "dicaplok",
    "kwanini",
    "marekani",
    "pangkalan",
    "dikuasai",
    "znajomo",
    "ekonomi",
    "gagal",
    "sabko",
    "herkese",
    "dibalik",
    "mwangosi",
    "samundar",
    "negosiasi",
    "terkait",
    "inabot",
    "kekuasaan",
    "pengiriman",
    "akuisisi",
    "istimewa",
    "ladkiyan",
    "menentang",
    "bamuhaye",
    "mỹ muốn",
    "napadpad",
    "berambisi",
    "turabishaka",
    "pengenalan",
    "prasowanie",
    # Additional non-English words from topic analysis
    "consonno",
    "lunapark",
    "apoyo",
    "legendado",
    "estreno",
    "ultimo refugio",
    "fin du monde",
    "nous sommes",
    "filmanmeldelse",
    "katastrophenfilm",
    "bhabaninagar",
    "grudinina",
}
NON_ENGLISH_PREFIX_CUES = (
    "pinoy",
    "junreyingreenland",
)
KNOWN_NON_ENGLISH_GREENLAND_PATTERNS = [
    re.compile(r"\bgreenland\s+\d+\s+kali\s+lebih\s+besar\s+daripada\b", re.IGNORECASE),
    re.compile(r"\bgreenland\s+numaesh\b", re.IGNORECASE),
    re.compile(r"\bgreenland\s+le\s+nidi\b", re.IGNORECASE),
    re.compile(r"\bgreenland\b.*#film\b.*\bledernierrefuge\b", re.IGNORECASE),
    re.compile(r"\bdas\s+ende\s+der\s+welt\b.*\bgreenland\b.*\bnetflix\b", re.IGNORECASE),
    re.compile(r"\bgreenland\b.*\b(im\s+film|jetzt\s+auf)\b", re.IGNORECASE),
    re.compile(r"\bgreenland\b.*\b(takrane|khatarnak|duniya|baad)\b.*\bmovie\s+explain", re.IGNORECASE),
    re.compile(r"\breview\s+singkat\b.*#film\b.*#greenland\b", re.IGNORECASE),
]
BLADE_AND_SORCERY_PATTERNS = [
    re.compile(r"\bblade\s*(?:and|&)\s*sorcery\b", re.IGNORECASE),
    re.compile(r"\bblades\s*(?:and|&)\s*sorcery\b", re.IGNORECASE),
    re.compile(r"\bbladeandsorcery\b", re.IGNORECASE),
    re.compile(r"\bbladesandsorcery\b", re.IGNORECASE),
    re.compile(r"\bb\s*&\s*s\b", re.IGNORECASE),
]

WORD_RE = re.compile(r"[A-Za-z']+")
TITLE_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
GREENLAND_MOVIE_MARKER_TOKENS = {
    "movie",
    "movies",
    "film",
    "films",
    "trailer",
    "trailers",
    "cast",
    "cinema",
    "netflix",
    "review",
    "reaction",
    "clip",
    "clips",
    "scene",
    "scenes",
    "summary",
    "recap",
    "explained",
    "explain",
    "uddan",
    "terbongkar",
    "faisalmosque",
    "musalman",
}
GREENLAND_MOVIE_MARKER_SUBSTRINGS = (
    "#movie",
    "#movies",
    "#film",
    "#films",
    "#trailer",
    "#trailers",
    "#cast",
    "#moviereview",
    "#movierecap",
    "#movieexplained",
    "#moviesummary",
    "#movieclips",
    "#moviescenes",
    "#filmrecap",
    "#greenlandmovie",
    "#greenland2",
    "#movierating",
    "#hollywoodfilm",
    "#filmtok",
)
GREENLAND_MOVIE_PHRASES = (
    "official trailer",
    "official hd trailer",
    "full trailer",
    "movie cast",
    "real name and age",
    "movie review",
    "film review",
    "movie recap",
    "film recap",
    "movie summary",
    "full movie",
    "movie explained",
    "movie explain",
    "trailer reaction",
    "movie clip",
    "movie clips",
    "movie scenes",
    "on netflix",
    "sur tf1",
    "le dernier refuge",
    "r rating",
)
GREENLAND_MOVIE_SEQUEL_MARKERS = {
    "migration",
    "gerard",
    "butler",
    "morena",
    "baccarin",
    "gerardbulter",
}
GREENLAND_SEQUEL_MOVIE_MARKER_TOKENS = {"movie", "cast", "trailer", "film"}
NON_ENGLISH_SCRIPT_PATTERNS = [
    ("arabic", re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")),
    ("cyrillic", re.compile(r"[\u0400-\u04FF]")),
    ("hebrew", re.compile(r"[\u0590-\u05FF]")),
    ("devanagari", re.compile(r"[\u0900-\u097F]")),
    ("thai", re.compile(r"[\u0E00-\u0E7F]")),
    ("japanese_hiragana", re.compile(r"[\u3040-\u309F]")),
    ("japanese_katakana", re.compile(r"[\u30A0-\u30FF]")),
    ("cjk", re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")),
    ("hangul", re.compile(r"[\uAC00-\uD7AF]")),
]
BANNED_TERMS = [
    "mitsui",
    "chengdu",
    "beautyofpakistan",
    "discoverpakistan",
    "penumbra",
    "morena baccarin",
    "reaper binder",
    "reaperbinder",
    "greenland farms",
    "greenland australia",
    "greenland china",
    "greenland group",
    "switzerland greenland",
    "the greenland. north pakistan",
    "greenland festival",
    "greenland shark",
    "greenland species shark",
    "#greenland #shark",
    "greenland#shark",
    "greenland #shark",
    "#shark #greenland",
    "greenland #sharks",
    "shanghai greenland",
    "greenland valuers",
    "greenland dh",
    "greenland whale fisheries",
    "greenland whalefisheries",
    "greenland whalefishers",
    "greenland whale fishery",
    "greenland whalefishery",
    "emancipator",
    "sam kelly",
    "joe greenland",
    "shaft in greenland",
    "pokemon",
    "minecraft",
    "roblox",
    "battle cats",
    "black ops",
    "gameplay",
    "multiplayer",
    "pubg",
    "counter-strike",
    "h1z1",
    "specops",
    "madden",
    "battlefield 4",
    "battlefield 1",
    "battlefield 2",
    "battlefield 3",
    "battlefield 5",
    "plague inc",
    "plagueinc",
    "geoguessr",
    "modern warships",
    "cricket club",
    "cricket academy",
    "cricket ground",
    "pakistancricket",
    "bounce rescue",
    "downhill race",
    "dh race",
    "enping",
    "shooterking greenland smock",
    "jade palace",
    "danga bay",
    "greenland malaysia",
    "malaysia greenland",
    "greenland japan",
    "greenland hill",
    "greenland cabins",
    "greenland cafe",
    "greenland oddanchatram",
    "greenland bakes",
    "greenland zone",
    "greenland communication",
    "greenland technology imphal",
    "greenland educational society",
    "greenland resources ab",
    "greenland autos ltd",
    "greenland autos limited",
    "greenland bio science",
    "greenland organics",
    "greenland boutique hotel",
    "greenland auditorium",
    "greenland hall",
    "greenland coffee bar",
    "greenland kindergarten",
    "greenland executive lounge",
    "greenland parish",
    "greenland newton subdivision",
    "greenland - bukan nina bobo",
    "greenland plant house",
    "greenland plots",
    "greenland property",
    "green acres by greenland",
    "greenland lot for sale",
    "greenland house for sale",
    "greenland pangkalpinang",
    "greenland addanki",
    "greenland hazara",
    "greenland khanis pur",
    "greenland meemure",
    "greenland geetamandir",
    "greenland barwani",
    "greenland manipur",
    "greenland haflong",
    "greenland dima hasao",
    "greenland bilaspur",
    "greenland karbianglong",
    "greenland siliguri",
    "greenland najafgarh",
    "greenland restaurant",
    "restaurant greenland",
    "pai thailand",
    "ukambani greenland",
    "greenland baby's",
    "bbfoods",
    "shelter sri sai greenland",
    "google expedition in korea",
    "greenland farm dubai",
    "greenland h s school",
    "hastinapur",
    "meerut",
    "tarbela",
    "haripur",
    "mughalroad",
    "perrgali",
    "vyas river",
    "vyasrivar",
    "nuwakot",
    "bhimavaram",
    "wisatadepok",
    "gadsarlake",
    "baghajk",
    "dholadhar",
    "maredumilli",
    "gudisa",
    "aptourism",
    "mushkpuritop",
    "nathiagali",
    "thirparappu",
    "telaga",
    "krishnagiridistrictnews",
    "krishnagiri",
    "assameseingreenland",
    "greenland assam",
    "greenland goa",
    "greenland hyderabad",
    "greenland patna",
    "greenland moradabad",
    "greenland ranchi",
    "greenland in india",
    "greenland of india",
    "greenland in pakistan",
    "greenland of pakistan",
    "greenland in bangladesh",
    "greenland of bangladesh",
    "greenland in nigeria",
    "greenland of nigeria",
    "greenland of bhaktapur",
    "greenland of arunachal pradesh",
    "bogamati",
    "greenland eco camp",
    "greenland farm noida",
    "greenland quran academy",
    "greenland healthful living",
    "greenland grass farm",
    "greenland goat farm",
    "greenland banquet",
    "greenland film city",
    "greenland pattern axe",
    "greenland pattern ax",
    "greenland jacket",
    "condor greenland",
    "greenland agro",
    "greenland agro chemicals",
    "greenland agro foods",
    "greenland agro farm",
    "greenland agro farms",
    "greenland agro industries",
    "greenland machinery",
    "greenland technologies",
    "greenland engineering",
    "greenland tools",
    "coorg",
    "bisleghat",
    "greenland himalaya hills",
    "himalaya hills",
    "oghi manshehra",
    "manshehra",
    "oghi",
    "saqibafridai",
    "greenland near bhuj",
    "bhuj",
    "minimarg",
    "ellenabad",
    "vermicompost",
    "vermiculture",
    "vermi",
    "9416284686",
    "standwithkashmir",
    "haryana",
    "kheti",
    "kisaan",
    "sawah",
    "villageview",
    "farmview",
    "rotavator",
    "bigbull",
    "greenland agrotech",
    "greenland agrimart",
    "malakand",
    "swat",
    "shakarghar",
    "sikkim",
    "gangtok",
    "mallroad",
    "puga valley",
    "ladakh",
    "ladhakh",
    "azad kashmir",
    "greenland kashmir",
    "greenland azad kashmir",
    "ganga choti",
    "godavari",
    "annavaram",
    "rawalakot",
    "jhelum river",
    "new hampshire",
    "greenland public school",
    "greenland school",
    "greenland high school",
    "greenland global school",
    "greenland international school",
    "greenland boarding high school",
    "greenland faith ministries",
    "greenland faith ministry",
    "greenland academy",
    "greenland christian academy",
    "johnny greenland",
    "alex greenland",
    "nathan greenland",
    "robert greenland",
    "alexgreenland",
    "gerard butler",
    "gerald butler",
    "#gerardbutler",
    "#vinodshuklaa",
    "sandy greenland",
    "laurie greenland",
    "bob greenland",
    "mangala pur",
    "mangal pur",
    "mangalpur",
    "mangalapur",
    "wuhan greenland center",
    "wuhan | greenland center",
    "greenland centre",
    "greenland garden centre",
    "greenland garden center",
    "greenland (2020)",
    "music video",
    "manicomio",
    "limbiate",
    "martin greenland",
    "park avenue",
    "vardon lane",
    "david greenland",
    "greenland launch",
    "premier of greenland",
    "greenland builders",
    "greenland home builders",
    "greenland houses",
    "greenland apartments",
    "greenland resort",
    "greenland paper crafts",
    "greenland amusement park",
    "cinemaxx",
    "sentossa",
    "greenland forest city partners",
    "greenland forestpark",
    "greenland forest park",
    "greenland usa",
    "kumamoto",
    "greenland creek falls",
    "greenland supermarket",
    "greenland oro-dental surgury",
    "greenland swimming pool",
    "greenland park",
    "greenland water park",
    "greenland waterpark",
    "greenland fun park",
    "hokkaido greenland",
    "greenland hokkaido",
    "ajmer",
    "rajasthan",
    "lappa laona",
    "greenland lahore",
    "kerala",
    "kerala greenland",
    "greenland farm house resort",
    "greenland street",
    "greenland road",
    "greenland farms dr",
    "livonia",
    "48154",
    "lakeside condos",
    "ben plotnick",
    "kaitlyn raitz",
    "peshawar",
    "tahe marine greenland",
    "ludhiana",
    "greenland convent school",
    "buxar",
    "milan",
    "malangwa",
    "buskers festival",
    "forest hill",
    "bogor",
    "ninh binh",
    "taman perumahan",
    "perumahan",
    "selalu",
    "sayang",
    "greenland educational institute",
    "greenland children academy school",
    "greenland sunday school",
    "new greenland school",
    "lonwade road",
    "greenland executive village",
    "greenland trailer",
    "greenland wax",
    "the greenland - tha sa daw ta koo thay",
    "the greenland - karen cover song",
    "the greenland - su nya ko na tha sa",
    "class 5",
    "class v",
    "greenland adventure village",
    "greenland farm house",
    "duplex house",
    "greenland nursery",
    "greenland homes",
    "house and lot",
    "greenland official hd trailer",
    "greenland 2020 english",
    "2 storeys",
    "2-storeys",
    "deluxe residence",
    "greenland heritage resorts",
    "enaensemble",
    "hut kono",
    "musik cover",
    "music cover",
    "official trailer",
    "apsara greenland hotel",
    "hotel greenland",
    "apsara",
    "cluster",
    "taytay",
    "holy trinity choir",
    "greenland sda church oyugis",
    "greenland british international school",
    "greenland polytechnic institute",
    "greenland medical centre",
    "greenland medical centre ltd",
    "greenland concept school",
    "greenland pb school",
    "greenland institute",
    "greenland university",
    "greenland montessori",
    "greenland montessori pymes",
    "greenland educational academy",
    "greenland education academy school",
    "greenland english school",
    "greenland english medium school",
    "greenland english boarding school",
    "greenland english h s school",
    "greenland elementary school",
    "greenland matriculation school",
    "greenland hosteller boys",
    "greenland college",
    "greenland college of nursing",
    "greenland middle school",
    "greenland model high school",
    "greenland public higher secondary school",
    "greenland higher sec school",
    "greenland higher secondary school",
    "greenland preparatory school",
    "greenland panamerican school",
    "greenland tutorial",
    "greenland it academy",
    "greenland training centre",
    "greenland training centre ltd",
    "greenland childcare",
    "greenland childcare centre",
    "greenland children academy",
    "greenland grammar",
    "greenland immigration",
    "greenland training center",
    "greenland hall",
    "jim greenland",
    "becky greenland",
    "hall greenland",
    "stephanie greenland",
    "daniel greenland",
    "allison greenland",
    "shannon greenland",
    "katie greenland",
    "kimberly greenland",
    "anthony greenland",
    "rabbi micha greenland",
    "adam greenland",
    "nick greenland",
    "judy kline from greenland hills umc",
    "greenland services",
    "greenland enterprise",
    "greenland service co",
    "greenland commercial services",
    "greenland commercial services inc",
    "greenland marketing",
    "greenland marketing and advertising",
    "greenland autos limited",
    "greenland bar",
    "greenland boardgame review",
    "greenland tyre",
    "greenland skills training project",
    "greenland skill training project",
    "greenland display suite",
    "greenland center",
    "greenland centre ltd",
    "greenland bank",
    "greenland hospital",
    "greenland hospital and research centre",
    "greenland nursing home",
    "greenland electronics",
    "greenland media",
    "greenland company",
    "greenland commercial",
    "greenland foundation",
    "greenland technology solutions",
    "greenland market",
    "greenland hyper market",
    "greenland hypermarket",
    "greenland food plaza",
    "greenland shopping center",
    "greenland shopping centre",
    "greenland plaza",
    "greenland mews",
    "greenland residence",
    "greenland villas",
    "greenland housing society",
    "greenland estate",
    "greenland chase",
    "greenland beach",
    "greenland beach road",
    "greenland beach dr",
    "greenland avenue",
    "greenland ave",
    "greenland trace",
    "greenland forest drive",
    "greenland hideaway drive",
    "greenland crescent",
    "greenland newtown",
    "greenland jungle stay",
    "greenland junglestay",
    "greenland palace",
    "greenland marriage hall",
    "greenland marquee",
    "greenland 44",
    "greenland sidra",
    "greenland bund centre",
    "greenland puli center",
    "greenland central plaza",
    "greenland marriott hotel",
    "greenland god",
    "greenland cup",
    "greenland pirates",
    "greenland rec soccer",
    "greenland rec",
    "greenland grad",
    "greenland wedding reception",
    "greenland ceremony",
    "greenland business city",
    "greenland op tennis",
    "greenland tp tennis",
    "greenland ph4 op",
    "greenland play 4",
    "greenland play 5",
    "greenland scientist",
    "greenland central school",
    "greenland hills",
    "greenland hills umc",
    "greenland place",
    "greenland newtown executive village",
    "merge town",
    "greenland guzzlord",
    "greenland glameows",
    "greenland mini",
    "greenland football club",
    "greenland football academy",
    "greenland football demo",
    "greenland basketball club",
    "greenland sports club",
    "greenland volleyball team",
    "greenland hotel",
    "greenland hotel vijayawada",
    "greenland tidar",
    "greenland korean market",
    "greenland johor bahru",
    "greenland home bridge",
    "greenland em school",
    "greenland particle boards",
    "greenland borewell",
    "greenland ciliwung",
    "greenland parc",
    "greenland phase 2 basketball",
    "greenland gunna",
    "merry boys of greenland",
    "kids merry making ceremony",
    "merry making ceremony",
    "greenland 7th kids merry making ceremony",
    "ardan greenland propertindo",
    "pt ardan greenland propertindo",
    "greenland band kudus",
    "takakonuma",
    "greenland cha raja",
    "greenland mist all you can drink",
    "greenland lng",
    "greenland youth hostel",
    "greenland penthouse",
    "greenland at tidar",
    "smart edition, greenland",
    "greenland highschool osmanabad",
    "greenland english h.s. school",
    "greenland salbari",
    "greenland sendang",
    "greenland giwangan",
    "greenland kalijaga",
    "greenland bali",
    "greenland porsa",
    "greenland indonesia",
    "greenland subdivision",
    "greenland guesthouse",
    "greenland motel",
    "greenland royal",
    "greenland chok rajkot",
    "greenland chokdithi",
    "greenland ph7",
    "greenland @tidar",
    "greenland bossss",
    "greenland gresik",
    "greenland reaper blinder",
    "greenland machine",
    "greenland satwa",
    "greenland cinemas",
    "greenland division",
    "greenland party plot",
    "greenland duars",
    "greenland alliance",
    "greenland persada",
    "greenland p. b. school",
    "greenland pilar",
    "greenland tas",
    "greenland tasbeera",
    "greenland handball",
    "greenland grovyles",
    "greenland football stadium",
    "greenland multipurpose stadium",
    "greenland stadium",
    "greenland women cultural festival",
    "greenland review fukoka japan",
    "greenland full episode",
    "greenland movi 2020",
    "greenland movie makers",
    "greenland by sismo",
    "niger delta greenland justice mandate",
    "markjohn enriquez greenland cainta",
    "greenland gsr",
    "greenland dj",
    "greenland restaurant cum bar",
    "greenland stud",
    "greenland ace",
    "greenland grammar school",
    "greenland collage",
    "greenland senggigi villa",
    "greenland pirate football",
    "greenland cheer senior",
    "greenland badminton",
    "katherine greenland",
    "kerrie anne greenland",
    "sheila greenland",
    "susan kaiser greenland",
    "philip greenland",
    "kirshen wyatt wilcken",
    "jason greenland",
    "william greenland",
    "steve greenland",
    "richard greenland",
    "ada hardy greenland",
    "sander greenland",
    "scott greenland",
    "sophia greenland",
    "phoebe greenland",
    "colin greenland",
    "rashad greenland",
    "leslie greenland",
    "michael greenland",
    "andrew greenland",
    "james greenland",
    "kate greenland",
    "shantel greenland",
    "rob greenland",
    "andy greenland",
    "chris greenland",
    "christa greenland",
    "angela greenland",
    "shaylee greenland",
    "marc anthony greenland",
    "bobbie jo greenland",
    "bobbie-jo greenland",
    "chief freddie greenland",
    "leon greenland",
    "mika greenland",
    "gerald butler",
    "geraldbutler",
    "greenland toys",
    "greenlandtoys",
    "hotel bamboo",
    "bamboo plant",
    "asphalt 9",
    "asphalt9",
    "asphalt legends",
    "greenlandshark",
    "bura maan jayega",
    "paththar bende basthi",
    "greenland water 💧💦💧 park",
    "walang gabi sa greenland",
    "greenland nakshathra",
    "shamani",
    "adityasaidwhat",
    "kepea",
    "triplecrow",
    "greenland dhababhiwandi",
    "bhiwandidhaba",
    "dhaba",
    "bhiwandi",
    "bhiwandifood",
    "bhiwandivlog",
    "biswabalaka",
    "greenland in switzerland",
    "greenland of switzerland",
    "switzerland the greenland",
    "switzerlandbeauty",
    "inlovewithswitzerland",
    "switzerlandvacations",
    "swissalps",
    "swisstravel",
    "swissnature",
    "switzerlandtour",
    "switzerlandvillage",
    "beauty of switzerland",
    "greenland in switzerland",
    "greenland of switzerland",
    "switzerland the greenland",
    "switzerlandbeauty",
    "inlovewithswitzerland",
    "switzerlandvacations",
    "swissalps",
    "swisstravel",
    "swissnature",
    "switzerlandtour",
    "switzerlandvillage",
    "beauty of switzerland",
    "turbro",
    "humidifier",
    "coal train",
    "bnsf",
    "train the greenland",
    "mekarai",
    "gerardbulter",
    "the settlers II",
    "the settlers 2",
    "usa and the greenland",
    "usa greenland over",
    "usa and greenland over",
    "greenland home blooming",
    "Greenland Home Antique",
    "mt conti",
    "wood veneers",
    "wood flooring",
    "Laobaidu",
    "Greenland Carpet Cleaning",
    "Battle Cat",
    "battle cats",
    "japan coaster",
    "GREENLAND REBORN",
    "disaster movie",
    "disastermovie",
    "\"GREENLAND/SCHOOL\"",
    "Greenland Hollywood Movie",
    "Greenland movie explain",
    "Greenland Review",
    "pas rater",
    "suka kamu",
    "mahur asalu",
    "del mundo",
    "das wetter",
    "chillen auf"
]
TITLE_BANNED_TERMS = [
    "cricket",
    "blade and sorcery",
    "blades of corcery",
    "blades and sorcery",
    "blades and brutality",
    "beyblade and sorcery",
    "federico cheme",
    "fjallraven",
    "xian holiday inn",
    "holiday inn",
    "executive lounge",
    "pistahan",
    "ufun",
    "ukungala",
    "njabzzin",
    "zamore",
    "church girl",
    "royal house of grace",
    "nigerian vlog",
    "bible sharing",
    "isaiah 41:10",
    "prem ghori",
    "shahzad bolch",
    "ready for occupancy duplex",
    "newton subdivision",
    "san mateo complete finish",
    "oromo music",
    "wallagga",
    "daawwanna",
    "orienteering",
    "sheffield",
    "maipu",
    "patinaje",
    "baranda",
    "greenland mill",
    "greenland fisheries",
    "greenland resot kotle",
    "surprisa galing greenland",
    "greenland of parris",
    "greenland bodycare",
    "phoenix mall",
    "greenland spice garden",
    "turning desert into greenland",
    "greenland floor stripping and polish",
    "greenland food&drink",
    "greenland residential high school",
    "greenland elementary",
    "greenland hhs",
    "greenland hss",
    "the north face greenland",
    "greenland crafts",
    "greenland boys basketball",
    "#greenland #group",
    "greenlandgroup",
    "greenland band concert",
    "alma vs greenland",
    "greenland 2 vs",
    "greenland dock",
    "ripar bindar",
    "victory road",
    "level crossing",
    "syo urban sprint",
    "white-fronted goose",
    "white-fronted geese",
    "white fronted goose",
    "white fronted geese",
    "wuhan",
    "oddanchatram",
    "pangkalpinang",
    "addanki",
    "hazara",
    "meemure",
    "geetamandir",
    "barwani",
    "haflong",
    "dima hasao",
    "bilaspur",
    "karbianglong",
    "siliguri",
    "najafgarh",
    "manipur",
    "panimur",
    "andhrapradesh",
    "nellikuth",
    "chundamanna",
    "swadique",
    "bukan",
    "bobo",
    "kohara",
    "kohra",
    "kya hua",
    "khairthal",
    "swm",
    "luigi exploding",
    "mai rehta hu",
    "mau mudik",
    "hashira",
    "trainz",
    "ramzan",
    "kalam",
    "ajab",
    "dunyast",
    "pakistanzindabad",
    "haryalipakistan",
    "natureofpakistan",
    "lovepakistan",
    "cara berwisata ke greenland",
    "cara berwisata",
    "berwisata",
    "baru nyadar",
    "muzan",
    "muzan kibutsuji",
    "kibutsuji",
    "sakaleshapura",
    "rusia ancam nuklir",
    "pune maharashtra",
    "udaipur",
    "monsoonvibe",
    "hata sawan ki ghata",
    "mere dil ka vo rajkumar",
    "buhay",
    "natutunaw",
    "saap",
    "kesasar",
    "pantai",
    "deudeuleuan",
    "siang",
    "ngomongna",
    "malaysia",
    "lahore",
    "bangalore",
    "bungalow",
    "sidhumoosewala",
    "sidhumoosewalasister",
    "rupeshrohit",
    "shopifystore",
    "kamibhai",
    "kishmishkefayde",
    "kukkesubrahmanya",
    "mansrovar",
    "folkditties",
    "bhojpuri",
    "bhojpurivideo",
    "ashokujnas",
    "janassyl",
    "aktobe",
    "utya",
    "nawkata",
    "ahoty",
    "ahilo",
    "colegio",
    "torneo",
    "estadio",
    "dodoma",
    "ciwidey",
    "ijs",
    "ijsland",
    "reizen",
    "vakantie",
    "tiruvanamalai",
    "gondal",
    # Stricter topic-54 place bans for likely wrong-place Greenland titles
    "assam",
    "arunachal",
    "arunachall",
    "baksa",
    "baksha",
    "baragarh",
    "bijapur",
    "guwahati",
    "jharkhand",
    "karnataka",
    "korba",
    "kashmir",
    "himachal",
    "nagpur",
    "patna",
    "ramtek",
    "sonbhadra",
    "uttarakhand",
    "uttarpradesh",
    "uttar pradesh",
    "ahmedabad",
    "islamabad",
    "gilgit",
    "karachi",
    "mirpur",
    "multan",
    "parachinar",
    "gujranwala",
    "abbottabad",
    "hangu",
    "sindh",
    "zamboanga",
    "johor bahru",
    "nanchang",
    "moulvibazar",
    "sylhet",
    # Stricter topic-54 false-positive context bans
    "ganpati",
    "pre wedding",
    "resort",
    "water park",
    "mehandi",
    "bihu",
    "science city",
    "rotti",
    # Foreign / transliterated non-Greenlandic words seen in topic 54 titles
    "bohut",
    "hundor",
    "nungaiba",
    "khara",
    "mazdehee",
    "allahwalilake",
    "amrica",
    "dildilpakistan",
    "loveyoupakistan",
    "jaishreeram",
    "bholenath",
    "yengadapora",
    "islamicvideo",
    "islamicshorts",
    "bishkek",
    "meghalaya",
    "ampid",
    "san mateo",
    "rizal",
    "batam",
    "kemang",
    "gresik",
    "cibodas",
    "grenlandiya",
    "grenlandii",
    "Burbujas rentables",
    "Greenland City Developers",
    "Greenland 2 (2026)",
    "sumba",
    "sumbawa",
]


def normalize_banned_match_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold()).strip()


NORMALIZED_BANNED_TERMS = [
    (term, normalize_banned_match_text(term))
    for term in BANNED_TERMS
]
COMPILED_BANNED_TERM_PATTERNS = [
    (term, normalized_term, re.compile(rf"\b{re.escape(normalized_term)}\b"))
    for term, normalized_term in NORMALIZED_BANNED_TERMS
    if normalized_term
]
NORMALIZED_TITLE_BANNED_TERMS = [
    (term, normalize_banned_match_text(term))
    for term in TITLE_BANNED_TERMS
]


MONTH_NAME_TOKENS = {
    "january",
    "jan",
    "february",
    "feb",
    "march",
    "mar",
    "april",
    "apr",
    "may",
    "june",
    "jun",
    "july",
    "jul",
    "august",
    "aug",
    "september",
    "sep",
    "sept",
    "october",
    "oct",
    "november",
    "nov",
    "december",
    "dec",
}
GREENLAND_ONLY_GENERIC_TOKENS = {
    "the",
    "my",
    "youtube",
    "channel",
    "follow",
    "like",
    "share",
    "comment",
    "shorts",
    "short",
    "youtubeshorts",
    "youtubeshort",
    "reels",
    "status",
    "live",
    "stream",
    "viral",
    "trending",
    "shortvideo",
    "video",
    "ytshorts",
    "ytshort",
    "viralvideo",
    "foryou",
    "funnyvideo",
    "viralsong",
    "sadsong",
    "trendingshorts",
    "popular",
    "20secondvideo",
    "shortsfeed",
    "yshorts",
    "shortsyoutube",
    "subscribe",
    "part",
    "pt",
    "hd",
    "4k",
    "uhd",
}
GAMEPLAY_CUE_TOKENS = {
    "bf1",
    "bf2",
    "bf3",
    "bf4",
    "bf5",
    "gameplay",
    "walkthrough",
    "lets",
    "play",
    "part",
    "campaign",
    "mission",
    "commander",
    "major",
}
GREENLAND_ALIAS_PLACE_TOKENS = {
    "assam",
    "bangladesh",
    "bhaktapur",
    "bhuj",
    "bogamati",
    "baksa",
    "bareta",
    "biratnagar",
    "bornodi",
    "borama",
    "bagong",
    "bandara",
    "cainta",
    "curdi",
    "daska",
    "dandeli",
    "depok",
    "dubai",
    "fethiye",
    "gilgit",
    "goa",
    "goharabad",
    "gorakhpur",
    "gundu",
    "gujranwala",
    "guwahati",
    "hangu",
    "hastinapur",
    "himachal",
    "hyderabad",
    "india",
    "nigeria",
    "islamabad",
    "hunza",
    "jharkhand",
    "karachi",
    "korba",
    "mirpur",
    "multan",
    "moulvibazar",
    "nagpur",
    "parachinar",
    "patna",
    "punjab",
    "ramtek",
    "sonbhadra",
    "sylhet",
    "uttarakhand",
    "uttarpradesh",
    "zamboanga",
    "indonesia",
    "islamabad",
    "jacksonville",
    "jharkhand",
    "johor",
    "juanda",
    "jammu",
    "kalam",
    "karnataka",
    "kashmir",
    "kediri",
    "kendal",
    "khanna",
    "kharagpur",
    "kpk",
    "kuwait",
    "lahaul",
    "las",
    "vegas",
    "lagos",
    "meerut",
    "moradabad",
    "moulvibazar",
    "nagpur",
    "narayanganj",
    "nepal",
    "olokonla",
    "oragadam",
    "oman",
    "pakistan",
    "patna",
    "phulbani",
    "pokhara",
    "proddatur",
    "punjab",
    "raiganj",
    "rajkot",
    "ranchi",
    "sahiwal",
    "sawangan",
    "senggigi",
    "shimla",
    "sindh",
    "sissu",
    "shahdara",
    "skardu",
    "somalia",
    "somaliland",
    "spiti",
    "sumbal",
    "sylhet",
    "tamulpur",
    "tasiilaq",
    "tokha",
    "uttarakhand",
    "vijayawada",
    "waziristan",
    "zaipawl",
    "aizawl",
    "ajah",
    "ibeju",
    "lekki",
    "tidar",
    "putrajaya",
    "chicalim",
    "rohtak",
    "kotma",
    "vizag",
    "macomb",
    "franktown",
    "richmond",
    "nashville",
    "salalah",
    "yaba",
    "gojal",
    "passucons",
    "nazimabad",
    "baltistan",
    "deosai",
    "razmak",
    "khanis",
    "hussainabad",
}
GREENLAND_ALIAS_CONTEXT_TOKENS = {
    "academy",
    "adventure",
    "agro",
    "agriculture",
    "apartment",
    "apartments",
    "automobile",
    "band",
    "banquet",
    "bar",
    "beauty",
    "borewell",
    "bridge",
    "camp",
    "center",
    "centre",
    "ceremony",
    "childcare",
    "children",
    "clinic",
    "college",
    "cow",
    "cross",
    "eco",
    "education",
    "educational",
    "english",
    "estate",
    "farm",
    "farmhouse",
    "farming",
    "fountain",
    "family",
    "goat",
    "grassland",
    "grammar",
    "hall",
    "hills",
    "hostel",
    "hospital",
    "hotel",
    "housing",
    "immigration",
    "institute",
    "kindergarten",
    "kids",
    "machinery",
    "machine",
    "mall",
    "market",
    "marriage",
    "mountain",
    "mountains",
    "nature",
    "park",
    "picnic",
    "place",
    "pool",
    "polytechnic",
    "reaper",
    "residence",
    "restaurant",
    "resort",
    "rice",
    "school",
    "store",
    "stud",
    "tower",
    "towers",
    "tourism",
    "tractor",
    "training",
    "travel",
    "valley",
    "villa",
    "villas",
    "village",
    "view",
    "water",
    "shopping",
    "center",
    "greenery",
    "lake",
}
GREENLAND_ALIAS_ALLOW_TOKENS = {
    "compare",
    "compared",
    "comparison",
    "country",
    "countries",
    "culture",
    "denmark",
    "exchange",
    "explain",
    "explained",
    "facts",
    "flight",
    "from",
    "history",
    "ice",
    "if",
    "imam",
    "inuit",
    "islam",
    "islamic",
    "map",
    "muslim",
    "muslims",
    "news",
    "pakistanis",
    "plane",
    "quran",
    "religion",
    "swap",
    "swapping",
    "theory",
    "to",
    "traveling",
    "travelling",
    "vs",
    "why",
}
REMOVED_ACCOUNTS = [
    "greenland institute",
    "@greenlandcookingschool",
    "greenland manufacturing & trading co.,ltd",
    "greenland cleaning",
    "greenland kennel",
    "greenland princess",
    "gin nursery garden",
    "hayat infrastructure",
    "greenlandwallcoverings",
    "green land estate & builders",
    "new england car shows",
    "praakrtik sundarata",
    "kerala wibes",
    "greenland toys",
    "greenlandholidayskottyam4803",
    "dj greenland garhshankar",
    "greenland journey",
]


WIKIPEDIA_AUDIO_ARTICLE_RE = re.compile(r"\bwikipedia\s+audio\s+article\b", flags=re.IGNORECASE)


def strip_wikipedia_audio_article(title: str) -> str:
    cleaned = WIKIPEDIA_AUDIO_ARTICLE_RE.sub(" ", title or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_:;,.[](){}")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_greenland_trailer_only_title(title: str) -> bool:
    title_tokens = [t.lower() for t in TITLE_TOKEN_RE.findall(title or "")]
    if not title_tokens:
        return False
    token_set = set(title_tokens)
    return (
        "greenland" in token_set
        and "trailer" in token_set
        and all(t in {"greenland", "trailer"} or t.isdigit() for t in title_tokens)
    )


import re

def is_greenland_2_migration_title(title: str) -> bool:
    title_text = (title or "").lower()
    return (
        (
            re.search(r"\bgreenland\s*2\b", title_text) is not None
            or "greenland2" in title_text
        )
        and (
            "migration" in title_text
            or re.search(r"\b(movie|film|ending)\b", title_text) is not None
        )
    )


def is_greenland_movie_only_title(title: str) -> bool:
    title_tokens = [t.lower() for t in TITLE_TOKEN_RE.findall(title or "")]
    if not title_tokens:
        return False
    has_greenland = any(t == "greenland" for t in title_tokens)
    has_movie = any(t == "movie" for t in title_tokens)
    allowed = all(
        t in {"greenland", "movie"}
        or t in GREENLAND_ONLY_GENERIC_TOKENS
        or t.isdigit()
        for t in title_tokens
    )
    return has_greenland and has_movie and allowed


def is_greenland_2020_movie_trailer_film_title(title: str) -> bool:
    title_tokens = {t.lower() for t in TITLE_TOKEN_RE.findall(title or "")}
    return (
        "greenland" in title_tokens
        and "2020" in title_tokens
        and bool(title_tokens & {"movie", "trailer", "film"})
    )


def is_greenland_sequel_movie_title(title: str) -> bool:
    title_text = (title or "").lower()
    title_tokens = {t.lower() for t in TITLE_TOKEN_RE.findall(title or "")}
    has_greenland_sequel = bool(
        re.search(r"\bgreenland\s*[23]\b", title_text)
        or re.search(r"\bgreenland[23]\b", title_text)
    )
    return has_greenland_sequel and bool(title_tokens & GREENLAND_SEQUEL_MOVIE_MARKER_TOKENS)


def is_greenland_month_year_only_title(title: str) -> bool:
    title_tokens = [t.lower() for t in TITLE_TOKEN_RE.findall(title or "")]
    if len(title_tokens) != 3:
        return False
    return (
        title_tokens[0] == "greenland"
        and title_tokens[1] in MONTH_NAME_TOKENS
        and bool(re.fullmatch(r"(19|20)\d{2}", title_tokens[2]))
    )


def is_greenland_date_only_title(title: str) -> bool:
    title_tokens = [t.lower() for t in TITLE_TOKEN_RE.findall(title or "")]
    if not title_tokens or "greenland" not in title_tokens:
        return False

    allowed = all(
        t == "greenland"
        or t in MONTH_NAME_TOKENS
        or t.isdigit()
        for t in title_tokens
    )
    if not allowed:
        return False

    has_month = any(t in MONTH_NAME_TOKENS for t in title_tokens)
    has_year = any(re.fullmatch(r"(19|20)\d{2}", t) for t in title_tokens)
    has_day_number = any(re.fullmatch(r"\d{1,2}", t) for t in title_tokens)

    return (has_month and has_year) or (has_month and has_day_number) or (has_year and has_day_number)


def is_movie_review_title(title: str) -> bool:
    title_tokens = {t.lower() for t in WORD_RE.findall(title or "")}
    return "movie" in title_tokens and "review" in title_tokens


def is_movie_trailer_title(title: str) -> bool:
    title_tokens = {t.lower() for t in WORD_RE.findall(title or "")}
    return "movie" in title_tokens and "trailer" in title_tokens


def is_trailer_2020_title(title: str) -> bool:
    title_tokens = {t.lower() for t in TITLE_TOKEN_RE.findall(title or "")}
    return "trailer" in title_tokens and "2020" in title_tokens


def is_vikings_series_title(title: str) -> bool:
    title_text = (title or "").lower()
    title_tokens = {t.lower() for t in TITLE_TOKEN_RE.findall(title or "")}
    if "greenland" not in title_tokens:
        return False
    if "vikings" not in title_tokens:
        return False

    if "ubbe" in title_tokens or "ubber" in title_tokens:
        return True

    has_series_marker = bool(
        re.search(r"\bs\d{1,2}e\d{1,2}\b", title_text)
        or re.search(r"\b\d{1,2}x\d{1,2}\b", title_text)
        or re.search(r"\bseason\s+\d+\b", title_text)
        or re.search(r"\bepisode\s+\d+\b", title_text)
        or re.search(r"\bep\.?\s*\d+\b", title_text)
    )
    if has_series_marker:
        return True

    return False


def is_greenland_address_or_property_title(title: str) -> bool:
    title_text = (title or "").lower()
    return bool(
        re.search(
            r"\b\d{1,6}\s+greenland\s+"
            r"(circle|court|ct|rd|road|dr|drive|st|street|lane|ln|ave|avenue|pl|place|trace|crescent|beach|acres|forest|hideaway)\b",
            title_text,
        )
        or re.search(r"\bgreenland\s+house\b.*\broad\b", title_text)
        or re.search(r"\bgreenland\s+lot\s+\d+\b", title_text)
        or ("greenland" in title_text and re.search(r"\b2[\s-]*storey\b", title_text))
        or ("greenland" in title_text and "presented by" in title_text)
    )


def is_greenland_sports_title(title: str) -> bool:
    title_text = (title or "").lower()
    if "greenland" not in title_text:
        return False
    return bool(
        re.search(r"\bgreenland\s+pirates\b", title_text)
        or re.search(r"\bgreenland\s+cup\b", title_text)
        or re.search(r"\bgreenland\s+rec(\s+soccer)?\b", title_text)
        or re.search(r"\bgreenland\s+guzzlords?\b", title_text)
        or re.search(r"\bgreenland\s+glameows\b", title_text)
        or re.search(r"\bgreenland\s+op\s+tennis\b", title_text)
        or re.search(r"\bgreenland\s+tp\s+tennis\b", title_text)
        or re.search(r"\bgreenland\s+ph4\s+op\b", title_text)
        or re.search(r"\bgreenland\s*\(arkansas\)\s+girls\s+basketball\b", title_text)
        or re.search(r"\bportsmouth\b", title_text)
        or re.search(r"\bberryville\b", title_text)
        or re.search(r"\bprairie\s+grove\b", title_text)
        or re.search(r"\bcedarville\b", title_text)
        or re.search(r"\bbald\s+knob\b", title_text)
        or re.search(r"\bgirls\s+basketball\b", title_text)
        or re.search(r"\bgreenland\s*[23]\s+basketball\b", title_text)
        or re.search(r"\bgreenland[23]\s+basketball\b", title_text)
        or re.search(r"\bhigh\s+school\s+baseball\b", title_text)
        or re.search(r"\bmountainburg\b", title_text)
        or re.search(r"\byellville\b", title_text)
    )


def is_greenland_person_name_title(title: str) -> bool:
    title_text = (title or "").lower()
    starts = (
        "bullis jackson greenland",
        "jim greenland",
        "becky greenland",
        "hall greenland",
        "stephanie greenland",
        "daniel greenland",
        "allison greenland",
        "shannon greenland",
        "katie greenland",
        "kimberly greenland",
        "anthony greenland",
        "rabbi micha greenland",
        "adam greenland",
        "nick greenland",
    )
    if title_text.startswith(starts):
        return True
    return any(f" {phrase}" in title_text for phrase in starts)


def is_deluxe_residence_title(title: str) -> bool:
    title_tokens = {t.lower() for t in TITLE_TOKEN_RE.findall(title or "")}
    return "deluxe" in title_tokens and "residence" in title_tokens


def is_land_of_snow_grade_five_title(title: str) -> bool:
    title_text = re.sub(r"\s+", " ", (title or "").lower()).strip()
    if "5" not in {t.lower() for t in TITLE_TOKEN_RE.findall(title or "")}:
        return False
    return (
        "the land of snow" in title_text
        or "the land of ice and snow" in title_text
    )


def is_greenland_super_live_wallpaper_title(title: str) -> bool:
    title_text = re.sub(r"\s+", " ", (title or "").lower()).strip()
    return title_text == "greenland super live wallpaper"


def is_samsung_wallpaper_title(title: str) -> bool:
    title_tokens = {t.lower() for t in TITLE_TOKEN_RE.findall(title or "")}
    return "samsung" in title_tokens and "wallpaper" in title_tokens


def has_standalone_nh(text: str) -> bool:
    return re.search(r"\bnh\b", text, flags=re.IGNORECASE) is not None


def has_standalone_title_token(title: str, token: str) -> bool:
    return re.search(rf"\b{re.escape(token)}\b", title or "", flags=re.IGNORECASE) is not None


def is_blade_and_sorcery_content(title: str) -> bool:
    return any(pattern.search(title or "") for pattern in BLADE_AND_SORCERY_PATTERNS)


def is_battlefield_game_title(title: str) -> bool:
    title_text = (title or "").lower()
    title_tokens = {t.lower() for t in TITLE_TOKEN_RE.findall(title or "")}

    has_battlefield_token = bool(
        re.search(r"\bbattlefield\b", title_text)
        or re.search(r"\bbattelfield\b", title_text)
        or any(t.startswith("battlefield") for t in title_tokens)
        or any(t.startswith("battelfield") for t in title_tokens)
    )
    if not has_battlefield_token:
        return False

    has_numbered_battlefield = bool(
        re.search(r"\bbattlefield\s*#?\s*[1-5]\b", title_text)
        or re.search(r"\bbattelfield\s*#?\s*[1-5]\b", title_text)
        or any(t in {"battlefield1", "battlefield2", "battlefield3", "battlefield4", "battlefield5"} for t in title_tokens)
        or any(t in {"battelfield1", "battelfield2", "battelfield3", "battelfield4", "battelfield5"} for t in title_tokens)
    )
    if has_numbered_battlefield:
        return True

    if "battlefield" in title_tokens and "greenland" in title_tokens:
        return True

    if "major" in title_tokens and "greenland" in title_tokens:
        return True

    if title_tokens & GAMEPLAY_CUE_TOKENS:
        return True

    return False


def is_greenland_vs_powerlevel_series_title(title: str) -> bool:
    title_text = re.sub(r"\s+", " ", (title or "").lower()).strip()
    if "greenland" not in title_text or "usa" not in title_text:
        return False

    return bool(
        re.search(
            r"\b(?:reupload\s+)?usa\s+and\s+greenland\s+over\s+"
            r"[-+^0-9., ]+\s+times\s+season\s+\d+\s+part\s+\d+\b",
            title_text,
        )
    )


def is_wrong_place_greenland_alias_title(title: str) -> bool:
    title_text = (title or "").lower()
    title_tokens = {t.lower() for t in TITLE_TOKEN_RE.findall(title or "")}
    word_tokens = {t.lower() for t in WORD_RE.findall(title or "")}
    tokens = title_tokens | word_tokens

    if "greenland" not in tokens and "green" not in tokens:
        return False

    if tokens & GREENLAND_ALIAS_ALLOW_TOKENS:
        return False

    if re.search(r"\b(in|of|from|to)\s+greenland\b", title_text) and ("travel" in tokens or "trip" in tokens):
        return False

    if any(
        place in title_text
        for place in (
            "ilulissat",
            "ittoqqortoormiit",
            "narssaq",
            "arsuk",
            "igaliku",
            "paamiut",
            "kujataa",
            "tasiilaq",
            "nuuk",
            "sisimiut",
            "qaanaaq",
            "kulusuk",
        )
    ):
        return False

    place_hits = tokens & GREENLAND_ALIAS_PLACE_TOKENS
    if "greenland" in tokens and tokens & GREENLAND_ALIAS_PLACE_TOKENS and tokens & GREENLAND_ALIAS_CONTEXT_TOKENS:
        return True

    if "greenland" in tokens and len(place_hits) >= 2:
        return True

    if "greenland" in tokens and place_hits and re.search(r"\bgreenland\s+(of|in)\b", title_text):
        return True

    generic_noise_hits = tokens & GREENLAND_ONLY_GENERIC_TOKENS
    if "greenland" in tokens and place_hits and len(generic_noise_hits) >= 3:
        return True

    if re.search(r"\bgreen\s*land\s+of\s+(india|pakistan|bangladesh|nigeria)\b", title_text):
        return True

    if re.search(r"\bgreenland\s+(of|in)\s+(india|pakistan|bangladesh|nigeria|assam|goa|kashmir|nepal|uttarakhand|himachal)\b", title_text):
        return True

    if re.search(r"\bgreenland\s+(eco\s+camp|farm|farmhouse|water\s+park|park|banquet|store|agro|machinery|tools|engineering|grass\s+farm|goat\s+farm)\b", title_text):
        return True

    return False


def is_greenland_local_venue_title(title: str) -> bool:
    title_text = re.sub(r"\s+", " ", (title or "").lower()).strip()
    if "greenland" not in title_text:
        return False

    if re.search(r"\b(ilulissat|nuuk|sisimiut|qaanaaq|tasiilaq|disko|arctic|icefjord|inuit)\b", title_text):
        return False

    venue_patterns = [
        r"\bgreenland\s+shop+p?ing\s+(center|centre)\b",
        r"\bshop+p?ing\s+(center|centre)\b",
        r"\bgreenland\s+swimming\s+pool\b",
        r"\bswimming\s+pool\b",
        r"\brooftop\s+swimming\s+pool\b",
        r"\bfountain\b",
        r"\bland\s*for\s*sale\b",
        r"\bopenlandsforsale\b",
        r"\bfarmhouse\b",
    ]
    if not any(re.search(pattern, title_text) for pattern in venue_patterns):
        return False

    return "#" in title_text or re.search(r"\bgreenland\s+\w+", title_text) is not None


def get_matched_removed_account(channel_title: str) -> str | None:
    channel_title_norm = (channel_title or "").strip().lower()
    if not channel_title_norm:
        return None
    for account in REMOVED_ACCOUNTS:
        if channel_title_norm == account:
            return account
    return None


def extract_year(date_text: str | None) -> int | None:
    match = re.match(r"^\s*(\d{4})", date_text or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def get_matched_flag_keywords(title: str) -> list[str]:
    text = (title or "").lower()
    matched = []
    for keyword in [
        "03840",
        "parma",
        "kerala",
        "festival",
        "cinemaxx",
        "malaysia",
        "greenland group",
        "mitsui",
        "chengdu",
        "battlefield",
        "lahore",
        "rajasthan",
        "ajmer",
    ]:
        if keyword in text:
            matched.append(keyword)
    return matched


def has_banned_location_terms(title: str) -> bool:
    return len(get_matched_banned_terms(title)) > 0


def is_allowed_title_exception(title: str, banned_term: str) -> bool:
    title_text = (title or "").lower()

    if banned_term == "cricket":
        # Keep the specific Greenland geopolitics/news pattern that references Iceland Cricket.
        if all(token in title_text for token in ("trump", "greenland", "davos", "iceland cricket")):
            return True

    return False


def get_matched_banned_terms(title: str) -> list[str]:
    title_text = (title or "").lower()
    title_text_norm = normalize_banned_match_text(title)
    matched = [
        term
        for term, normalized_term, pattern in COMPILED_BANNED_TERM_PATTERNS
        if normalized_term in title_text_norm and pattern.search(title_text_norm)
    ]
    matched.extend(
        term
        for term, normalized_term in NORMALIZED_TITLE_BANNED_TERMS
        if normalized_term in title_text_norm and not is_allowed_title_exception(title, term)
    )
    if is_greenland_trailer_only_title(title):
        matched.append("greenland trailer title-only")
    if is_greenland_2_migration_title(title):
        matched.append("greenland 2 migration title-only")
    if is_greenland_movie_only_title(title):
        matched.append("greenland movie title-only")
    if is_greenland_sequel_movie_title(title):
        matched.append("greenland sequel movie title-only")
    if is_greenland_2020_movie_trailer_film_title(title):
        matched.append("greenland 2020 movie/trailer/film title-only")
    if is_movie_review_title(title):
        matched.append("movie review title-only")
    if is_movie_trailer_title(title):
        matched.append("movie trailer title-only")
    if is_trailer_2020_title(title):
        matched.append("trailer 2020 title-only")
    if is_vikings_series_title(title):
        matched.append("vikings series title-only")
    if is_deluxe_residence_title(title):
        matched.append("deluxe residence title-only")
    if is_greenland_super_live_wallpaper_title(title):
        matched.append("greenland super live wallpaper title-only")
    if is_samsung_wallpaper_title(title):
        matched.append("samsung + wallpaper title-only")
    if has_standalone_nh(title):
        matched.append("nh")
    if has_standalone_title_token(title, "ke"):
        matched.append("ke standalone title-only")
    if has_standalone_title_token(title, "choti"):
        matched.append("choti standalone title-only")
    if has_standalone_title_token(title, "pani"):
        matched.append("pani standalone title-only")
    if has_standalone_title_token(title, "reaper"):
        matched.append("reaper standalone title-only")
    if is_blade_and_sorcery_content(title):
        matched.append("blade and sorcery variant")
    if is_battlefield_game_title(title):
        matched.append("battlefield series title-only")
    if is_greenland_vs_powerlevel_series_title(title):
        matched.append("greenland powerlevel series title-only")
    if is_wrong_place_greenland_alias_title(title):
        matched.append("wrong-place greenland alias title-only")
    if is_greenland_address_or_property_title(title):
        matched.append("greenland address/property title-only")
    if is_greenland_local_venue_title(title):
        matched.append("greenland local venue title-only")
    if is_greenland_sports_title(title):
        matched.append("greenland sports title-only")
    if is_greenland_person_name_title(title):
        matched.append("greenland person-name title-only")
    return list(dict.fromkeys(matched))


def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        target_encoding = sys.stdout.encoding or "utf-8"
        cleaned = text.encode(target_encoding, errors="replace").decode(target_encoding, errors="replace")
        print(cleaned)


def total_banned_hits(banned_term_counts: dict[str, int], *terms: str) -> int:
    return sum(banned_term_counts.get(term, 0) for term in terms)


def normalize_for_lang(text: str) -> str:
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_language_tokens(text: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(text)]


def get_standalone_non_english_cue_hits(tokens: list[str]) -> set[str]:
    return {t for t in tokens if t in NON_ENGLISH_TITLE_CUES}


def summarize_language_tokens(tokens: list[str]) -> tuple[int, float, list[str], list[str]]:
    english_hits = sum(1 for t in tokens if t in ENGLISH_HINT_WORDS)
    english_ratio = english_hits / max(len(tokens), 1)
    cue_hits = sorted(get_standalone_non_english_cue_hits(tokens))
    long_unknown_tokens = [
        t for t in tokens
        if len(t) >= 5 and t not in ENGLISH_HINT_WORDS and t not in {"greenland", "greenlanders"}
    ]
    return english_hits, english_ratio, cue_hits, long_unknown_tokens


def basic_non_english_heuristic(text: str) -> tuple[bool, str]:
    tokens = get_language_tokens(text)

    if len(tokens) < 5:
        return False, "not_enough_text"

    english_hits, english_ratio, cue_hits, long_unknown_tokens = summarize_language_tokens(tokens)

    if english_ratio < 0.03 and len(tokens) >= 8:
        return True, f"heuristic_low_english_ratio={english_ratio:.3f}"

    has_greenland = "greenland" in tokens or "greenlanders" in tokens
    if has_greenland and cue_hits and english_ratio <= 0.25 and len(long_unknown_tokens) >= 2:
        return True, (
            f"heuristic_greenland_non_english_mix={','.join(cue_hits[:5])};"
            f"ratio={english_ratio:.3f}"
        )

    if has_greenland and english_hits == 0 and len(long_unknown_tokens) >= 4:
        return True, f"heuristic_greenland_unknown_token_dominance={len(long_unknown_tokens)}"

    return False, f"heuristic_english_ratio={english_ratio:.3f}"


def cue_based_non_english_heuristic(text: str) -> tuple[bool, str]:
    tokens = get_language_tokens(text)
    if len(tokens) < 3:
        cue_hits = set(get_standalone_non_english_cue_hits(tokens))
        has_greenland = "greenland" in tokens or "greenlanders" in tokens
        if len(tokens) >= 2 and has_greenland and cue_hits:
            return True, f"greenland_short_title_cues={','.join(sorted(cue_hits)[:5])}"
        return False, "not_enough_text_for_cues"

    cue_hits = set(get_standalone_non_english_cue_hits(tokens))
    prefix_hits = {
        prefix
        for t in tokens
        for prefix in NON_ENGLISH_PREFIX_CUES
        if t.startswith(prefix)
    }
    all_cue_hits = sorted(cue_hits | prefix_hits)
    _, english_ratio, _, long_unknown_tokens = summarize_language_tokens(tokens)
    has_greenland = "greenland" in tokens or "greenlanders" in tokens

    if len(all_cue_hits) >= 2:
        return True, f"non_english_cues={','.join(all_cue_hits[:5])}"

    if has_greenland and all_cue_hits and len(tokens) <= 3:
        return True, f"greenland_short_title_cues={','.join(all_cue_hits[:5])}"

    if all_cue_hits and len(tokens) <= 5 and english_ratio <= 0.40 and len(long_unknown_tokens) >= 3:
        return True, f"non_english_short_title_cues={','.join(all_cue_hits[:5])};ratio={english_ratio:.3f}"

    if all_cue_hits and len(tokens) >= 6 and english_ratio < 0.16 and len(long_unknown_tokens) >= 4:
        return True, f"non_english_cues+low_english={','.join(all_cue_hits[:5])};ratio={english_ratio:.3f}"

    if has_greenland and all_cue_hits and english_ratio <= 0.34 and len(long_unknown_tokens) >= 2:
        return True, (
            f"greenland_title_non_english_cues={','.join(all_cue_hits[:5])};"
            f"ratio={english_ratio:.3f}"
        )

    return False, f"cue_check_hits={len(all_cue_hits)};english_ratio={english_ratio:.3f}"


def detect_non_english_chars(text: str) -> tuple[bool, str]:
    for label, pattern in NON_ENGLISH_SCRIPT_PATTERNS:
        if pattern.search(text):
            return True, f"non_english_script={label}"

    # Also flag letters outside ASCII English alphabet (e.g. accented Latin letters).
    for ch in text:
        if ord(ch) <= 127:
            continue
        if not ch.isalpha():
            continue
        char_name = unicodedata.name(ch, "")
        if "LATIN" in char_name:
            return True, "non_english_letter=latin_extended"
        return True, "non_english_letter=other_unicode"

    return False, "ascii_or_english_only"


def detect_non_english(title: str) -> tuple[bool, str]:
    title_text = normalize_for_lang(title)
    for pattern in KNOWN_NON_ENGLISH_GREENLAND_PATTERNS:
        if pattern.search(title_text):
            return True, f"title:known_non_english_greenland_pattern={pattern.pattern}"
    char_flag, char_reason = detect_non_english_chars(title_text)
    cue_flag, cue_reason = cue_based_non_english_heuristic(title_text)
    heur_flag, heur_reason = basic_non_english_heuristic(title_text)

    if char_flag:
        return True, f"title:{char_reason}"
    if cue_flag:
        return True, f"title:{cue_reason}"
    if heur_flag:
        return True, f"title:{heur_reason}"

    return False, f"title:{heur_reason}"


def detect_greenland_only_title(title: str) -> tuple[bool, str]:
    non_english_chars, _ = detect_non_english_chars(title)
    if non_english_chars:
        return False, "contains_non_english_chars"

    tokens = [t.lower() for t in TITLE_TOKEN_RE.findall(title)]
    if not tokens:
        return False, "no_tokens"

    has_greenland = any(t == "greenland" for t in tokens)
    if not has_greenland:
        return False, "no_greenland"

    if is_greenland_month_year_only_title(title):
        return True, "title_only_greenland_month_year"

    if is_greenland_date_only_title(title):
        return True, "title_only_greenland_date"

    single_letter_tokens = [t for t in tokens if len(t) == 1 and t.isalpha()]
    allowed = all(
        (t == "greenland")
        or (t in GREENLAND_ONLY_GENERIC_TOKENS)
        or t.isdigit()
        or (len(t) == 1 and t.isalpha())
        for t in tokens
    )
    if len(single_letter_tokens) > 2:
        return False, "too_many_single_letter_tokens"
    if allowed:
        return True, "title_only_greenland_generic_or_numbers"

    return False, "has_other_words"


def contains_green_land_and_hashtag_greenland(text: str) -> bool:
    lowered = (text or "").lower()
    return "green land" in lowered and "#greenland" in lowered


def normalize_title_for_duplicate_check(title: str) -> str:
    lowered = title.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def parse_view_count(value: str | None) -> int:
    if value is None:
        return 0
    cleaned = re.sub(r"[^\d]", "", str(value))
    if not cleaned:
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0


def find_duplicate_clusters(rows: list[dict], threshold: float) -> list[dict]:
    by_channel: dict[str, list[dict]] = defaultdict(list)
    for row_index, row in enumerate(rows):
        channel_id = (row.get("channel_id") or "").strip()
        if not channel_id:
            continue
        title = (row.get("video_title") or "").strip()
        if not title:
            continue
        by_channel[channel_id].append(
            {
                "video_id": (row.get("video_id") or "").strip(),
                "title": title,
                "norm": normalize_title_for_duplicate_check(title),
                "view_count": parse_view_count(row.get("view_count")),
                "row_index": row_index,
                "row": row,
            }
        )

    clusters: list[dict] = []

    for channel_id, items in by_channel.items():
        n = len(items)
        if n < 2:
            continue

        graph = [set() for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                n1 = items[i]["norm"]
                n2 = items[j]["norm"]
                if not n1 or not n2:
                    continue
                sim = 1.0 if n1 == n2 else SequenceMatcher(None, n1, n2).ratio()
                if sim >= threshold:
                    graph[i].add(j)
                    graph[j].add(i)

        visited = [False] * n
        for i in range(n):
            if visited[i]:
                continue
            stack = [i]
            visited[i] = True
            component = []
            while stack:
                idx = stack.pop()
                component.append(idx)
                for nei in graph[idx]:
                    if not visited[nei]:
                        visited[nei] = True
                        stack.append(nei)

            if len(component) >= 2:
                component_items = [items[idx] for idx in component]
                clusters.append(
                    {
                        "channel_id": channel_id,
                        "count": len(component_items),
                        "items": component_items,
                    }
                )

    clusters.sort(key=lambda c: c["count"], reverse=True)
    return clusters


def main() -> None:
    default_csv = Path(__file__).resolve().parents[1] / "Datasets" / "yt-greenland.csv"
    default_output = Path(__file__).resolve().parents[1] / "Datasets" / "gl-cl.csv"
    default_descriptive_table_script = (
        Path(__file__).resolve().parent
        / "Descriptive_table"
        / "descriptive_numeric_table.py"
    )
    default_topic_modeling_script = (
        Path(__file__).resolve().parent
        / "Topic_modeling"
        / "Creating_frames"
        / "title_bertopic_modeling.py"
    )

    parser = argparse.ArgumentParser(
        description="Remove irrelevant videos, detect non-English items, and print keyword checks."
    )
    parser.add_argument("--csv", type=Path, default=default_csv, help="Path to input CSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help="Path to cleaned CSV. Default: Datasets/gl-cl.csv",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input CSV instead of writing a separate cleaned file.",
    )
    parser.add_argument(
        "--remove-non-english",
        action="store_true",
        default=True,
        help="Remove rows detected as non-English (title detection). Default: enabled.",
    )
    parser.add_argument(
        "--keep-non-english",
        action="store_true",
        help="Keep rows detected as non-English (overrides default removal).",
    )
    parser.add_argument(
        "--remove-generic-greenland",
        action="store_true",
        default=True,
        help="Remove titles that are only 'greenland' plus optional numbers or generic short-form words. Default: enabled.",
    )
    parser.add_argument(
        "--keep-generic-greenland",
        action="store_true",
        help="Keep titles that are only 'greenland' plus optional numbers or generic short-form words.",
    )
    parser.add_argument(
        "--duplicate-threshold",
        type=float,
        default=0.92,
        help="Similarity threshold for duplicate title clustering within same channel_id (default: 0.92)",
    )
    parser.add_argument(
        "--skip-topic-modeling",
        action="store_true",
        default=True,
        help="Do not auto-run the Creating_frames topic modeling script after cleanup.",
    )
    parser.add_argument(
        "--run-topic-modeling",
        action="store_false",
        dest="skip_topic_modeling",
        help="Run the Creating_frames topic modeling script after cleanup.",
    )
    parser.add_argument(
        "--skip-descriptive-table",
        action="store_true",
        default=True,
        help="Do not auto-run the descriptive table script after cleanup.",
    )
    parser.add_argument(
        "--run-descriptive-table",
        action="store_false",
        dest="skip_descriptive_table",
        help="Run the descriptive table script after cleanup.",
    )
    parser.add_argument(
        "--descriptive-table-script",
        type=Path,
        default=default_descriptive_table_script,
        help="Path to the descriptive table script to run after cleanup.",
    )
    parser.add_argument(
        "--topic-modeling-script",
        type=Path,
        default=default_topic_modeling_script,
        help="Path to the Creating_frames topic modeling script to run after cleanup.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a .bak backup before overwriting CSV with --in-place",
    )
    args = parser.parse_args()
    if args.keep_non_english:
        args.remove_non_english = False
    if args.keep_generic_greenland:
        args.remove_generic_greenland = False

    csv_path = args.csv.resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError("CSV appears empty or missing header.")

        required = {"video_title"}
        missing = [c for c in required if c not in fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        rows = list(reader)

    total_before = len(rows)

    cleaned_rows = []
    deleted_rows = []
    removed_by_non_english = 0
    removed_by_generic_title = 0
    removed_by_green_land_hashtag_combo = 0
    removed_by_banned_location_terms = 0
    removed_by_account = 0
    removed_by_duplicate_pruning = 0
    flagged_title_hits = []
    non_english_hits = []
    generic_greenland_hits = []
    generic_greenland_rows = []
    green_land_hashtag_combo_hits = []
    banned_location_hits = []
    removed_account_hits = []
    banned_term_counts = {
        term: 0
        for term in [
            *BANNED_TERMS,
            *TITLE_BANNED_TERMS,
            "greenland trailer title-only",
            "greenland 2 migration title-only",
            "greenland movie title-only",
            "greenland sequel movie title-only",
            "greenland 2020 movie/trailer/film title-only",
            "movie review title-only",
            "movie trailer title-only",
            "trailer 2020 title-only",
            "vikings series title-only",
            "deluxe residence title-only",
            'land of snow + "5" title-only',
            "greenland super live wallpaper title-only",
            "samsung + wallpaper title-only",
            "battlefield series title-only",
            "blade and sorcery variant",
            "greenland powerlevel series title-only",
            "wrong-place greenland alias title-only",
            "greenland address/property title-only",
            "greenland local venue title-only",
            "greenland sports title-only",
            "greenland person-name title-only",
            "ke standalone title-only",
            "choti standalone title-only",
            "pani standalone title-only",
            "reaper standalone title-only",
            "nh",
        ]
    }
    removed_account_counts = {account: 0 for account in REMOVED_ACCOUNTS}

    def add_deleted_row(row: dict, reason: str) -> None:
        deleted_row = dict(row)
        if "video_description" in deleted_row:
            deleted_row["video_description"] = ""
        deleted_row["deleted_reason"] = reason
        deleted_rows.append(deleted_row)

    for row in rows:
        row = dict(row)
        original_title = row.get("video_title") or ""
        title = strip_wikipedia_audio_article(original_title)
        row["video_title"] = title
        channel_title = (row.get("channel_title") or "")

        matched_removed_account = get_matched_removed_account(channel_title)
        if matched_removed_account:
            removed_account_hits.append((title, (row.get("video_id") or ""), channel_title))
            removed_by_account += 1
            removed_account_counts[matched_removed_account] += 1
            add_deleted_row(row, f"blocked account: {matched_removed_account}")
            continue

        matched_banned_terms = get_matched_banned_terms(title)
        if matched_banned_terms:
            banned_location_hits.append((title, (row.get("video_id") or ""), (row.get("channel_id") or "")))
            add_deleted_row(row, "; ".join(matched_banned_terms))
            removed_by_banned_location_terms += 1
            for term in matched_banned_terms:
                banned_term_counts[term] += 1
            continue

        if contains_green_land_and_hashtag_greenland(title):
            green_land_hashtag_combo_hits.append(
                (title, (row.get("video_id") or ""), (row.get("channel_id") or ""))
            )
            removed_by_green_land_hashtag_combo += 1
            removed_by_banned_location_terms += 1
            add_deleted_row(row, 'green land + "#greenland" combo')
            continue

        is_generic_greenland, generic_reason = detect_greenland_only_title(title)
        if is_generic_greenland:
            generic_greenland_hits.append((title, generic_reason, (row.get("video_id") or ""), (row.get("channel_id") or "")))
            generic_greenland_rows.append((row, generic_reason))
            if args.remove_generic_greenland:
                removed_by_generic_title += 1
                add_deleted_row(row, generic_reason)
                continue

        is_non_english, lang_reason = detect_non_english(title)
        if is_non_english:
            non_english_hits.append((title, lang_reason))
            if args.remove_non_english:
                removed_by_non_english += 1
                add_deleted_row(row, lang_reason)
                continue

        cleaned_rows.append(row)

        matched_flag_keywords = get_matched_flag_keywords(title)
        if matched_flag_keywords:
            flagged_title_hits.append((title, matched_flag_keywords))

    duplicate_clusters = []
    clusters_pruned = 0
    if "channel_id" in (fieldnames or []):
        duplicate_clusters = find_duplicate_clusters(cleaned_rows, threshold=args.duplicate_threshold)
        rows_to_remove = set()
        for cluster in duplicate_clusters:
            best_item = max(
                cluster["items"],
                key=lambda x: (x["view_count"], x["video_id"]),
            )
            cluster["keeper_video_id"] = best_item["video_id"]
            cluster["keeper_view_count"] = best_item["view_count"]
            for item in cluster["items"]:
                if item["row_index"] != best_item["row_index"]:
                    rows_to_remove.add(item["row_index"])
                    item["pruned"] = True
                else:
                    item["pruned"] = False

        if rows_to_remove:
            for idx in sorted(rows_to_remove):
                add_deleted_row(cleaned_rows[idx], "duplicate title within channel")
            cleaned_rows = [row for idx, row in enumerate(cleaned_rows) if idx not in rows_to_remove]
            removed_by_duplicate_pruning = len(rows_to_remove)
            clusters_pruned = sum(1 for c in duplicate_clusters if c["count"] >= 2)

    if args.in_place:
        out_path = csv_path
        if not args.no_backup:
            backup_path = csv_path.with_suffix(csv_path.suffix + ".bak")
            backup_path.write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        out_path = args.output.resolve() if args.output else csv_path.with_name(f"{csv_path.stem}-cl{csv_path.suffix}")
        out_path.parent.mkdir(parents=True, exist_ok=True)

    deleted_path = out_path.with_name("deleted.csv")
    duplicate_videos_path = out_path.with_name("duplicate-videos.csv")
    greenland_only_titles_path = out_path.with_name("greenland-only-title-videos.csv")
    deleted_fieldnames = list(fieldnames)
    if "deleted_reason" not in deleted_fieldnames:
        deleted_fieldnames.append("deleted_reason")
    greenland_only_fieldnames = list(fieldnames)
    if "greenland_only_reason" not in greenland_only_fieldnames:
        greenland_only_fieldnames.append("greenland_only_reason")
    duplicate_fieldnames = [
        "duplicate_type",
        "duplicate_group_id",
        "duplicate_group_size",
        "duplicate_keeper_video_id",
        "duplicate_pruned",
        *fieldnames,
    ]

    duplicate_report_rows = []
    for group_index, cluster in enumerate(duplicate_clusters, start=1):
        group_id = f"near_duplicate_{group_index}"
        for item in cluster["items"]:
            report_row = {
                fieldname: item["row"].get(fieldname, "")
                for fieldname in fieldnames
            }
            report_row.update(
                {
                    "duplicate_type": "near_duplicate_title_within_channel",
                    "duplicate_group_id": group_id,
                    "duplicate_group_size": cluster["count"],
                    "duplicate_keeper_video_id": cluster.get("keeper_video_id", ""),
                    "duplicate_pruned": "yes" if item.get("pruned") else "no",
                }
            )
            duplicate_report_rows.append(report_row)
    greenland_only_report_rows = []
    for row, reason in generic_greenland_rows:
        report_row = {fieldname: row.get(fieldname, "") for fieldname in fieldnames}
        report_row["greenland_only_reason"] = reason
        greenland_only_report_rows.append(report_row)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    with deleted_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=deleted_fieldnames)
        writer.writeheader()
        writer.writerows(deleted_rows)

    with duplicate_videos_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=duplicate_fieldnames)
        writer.writeheader()
        writer.writerows(duplicate_report_rows)

    with greenland_only_titles_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=greenland_only_fieldnames)
        writer.writeheader()
        writer.writerows(greenland_only_report_rows)

    safe_print(f"Input CSV: {csv_path}")
    safe_print(f"Cleaned CSV saved to: {out_path}")
    safe_print(f'Deleted banned-terms CSV saved to: {deleted_path}')
    safe_print(f"Duplicate videos CSV saved to: {duplicate_videos_path} ({len(duplicate_report_rows)} rows)")
    safe_print(
        "Greenland-only title videos CSV saved to: "
        f"{greenland_only_titles_path} ({len(greenland_only_report_rows)} rows)"
    )

    safe_print("\nNear-duplicate title clusters by channel_id:")
    if "channel_id" not in (fieldnames or []):
        safe_print("- Skipped (channel_id column missing)")
    else:
        safe_print(f"- Clusters found: {len(duplicate_clusters)}")
        safe_print(f"- Clusters pruned: {clusters_pruned}")

    safe_print("\nLanguage detector backend: heuristic + Unicode script scan")
    safe_print("\nSummary:")
    total_deleted = total_before - len(cleaned_rows)
    deleted_pct = (total_deleted / total_before * 100) if total_before else 0.0
    accounted_deleted = (
        removed_by_account
        + removed_by_banned_location_terms
        + removed_by_generic_title
        + removed_by_non_english
        + removed_by_duplicate_pruning
    )
    safe_print(f"Rows before: {total_before}")
    safe_print(f"Rows deleted: {total_deleted} ({deleted_pct:.2f}%)")
    safe_print(f"Rows after: {len(cleaned_rows)}")
    safe_print(f"Removed by blocked accounts: {removed_by_account}")
    safe_print(f"Removed by banned terms: {removed_by_banned_location_terms}")
    safe_print("Breakdown by banned-term cluster:")
    banned_clusters = [
        (
            "Company names and corporate entities",
            total_banned_hits(
                banned_term_counts,
                "mitsui",
                "chengdu",
                "reaper binder",
                "reaperbinder",
                "greenland farms",
                "greenland australia",
                "greenland china",
                "shanghai greenland",
                "greenland group",
                "wuhan greenland center",
                "wuhan | greenland center",
                "greenland centre",
                "greenland garden centre",
                "greenland garden center",
                "greenland services",
                "greenland enterprise",
                "greenland service co",
                "greenland commercial services",
                "greenland commercial services inc",
                "greenland marketing",
                "greenland marketing and advertising",
                "greenland autos limited",
                "greenland tyre",
                "greenland display suite",
                "greenland center",
                "greenland centre ltd",
                "wuhan",
                "greenland forest city partners",
                "greenland forestpark",
                "greenland forest park",
                "greenland malaysia",
                "malaysia greenland",
                "greenland usa",
            ),
        ),
        (
            "Schools, academies, churches, ministries",
            total_banned_hits(
                banned_term_counts,
                "greenland public school",
                "greenland school",
                "greenland high school",
                "greenland global school",
                "greenland international school",
                "greenland boarding high school",
                "greenland educational institute",
                "greenland children academy school",
                "greenland sunday school",
                "new greenland school",
                "greenland convent school",
                "greenland academy",
                "greenland christian academy",
                "greenland british international school",
                "greenland polytechnic institute",
                "greenland medical centre",
                "greenland medical centre ltd",
                "greenland concept school",
                "greenland pb school",
                "greenland institute",
                "greenland university",
                "greenland montessori",
                "greenland montessori pymes",
                "greenland nursery",
                "greenland faith ministries",
                "greenland faith ministry",
                "greenland sda church oyugis",
                "holy trinity choir",
                "greenland central school",
                "greenland hills umc",
                "mangala pur",
                "mangal pur",
                "mangalpur",
                "mangalapur",
                "buxar",
            ),
        ),
        (
            "Housing, homes, apartments, villages, addresses",
            total_banned_hits(
                banned_term_counts,
                "greenland builders",
                "greenland home builders",
                "greenland houses",
                "greenland homes",
                "greenland apartments",
                "greenland hills",
                "greenland place",
                "greenland executive village",
                "greenland newtown executive village",
                "greenland adventure village",
                "greenland heritage resorts",
                "greenland street",
                "greenland road",
                "greenland farms dr",
                "greenland address/property title-only",
                "livonia",
                "48154",
                "lakeside condos",
                "duplex house",
                "house and lot",
                "2 storeys",
                "2-storeys",
                "rfo",
                "deluxe residence",
                "cluster",
                "taytay",
                "bungalow",
            ),
        ),
        (
            "Hotels and resorts",
            total_banned_hits(
                banned_term_counts,
                "greenland resort",
                "greenland farm house resort",
                "greenland farm house",
                "greenland restaurant",
                "restaurant greenland",
                "greenland banquet",
                "apsara greenland hotel",
                "hotel greenland",
                "apsara",
                "jade palace",
                "danga bay",
            ),
        ),
        (
            "Products, machinery, and branded gear",
            total_banned_hits(
                banned_term_counts,
                "greenland pattern axe",
                "greenland pattern ax",
                "greenland jacket",
                "condor greenland",
                "greenland agro",
                "greenland agro chemicals",
                "greenland agro foods",
                "greenland agro farm",
                "greenland agro farms",
                "greenland agro industries",
                "greenland machinery",
                "greenland technologies",
                "greenland engineering",
                "greenland tools",
            ),
        ),
        (
            "Parks, recreation, retail, local venues",
            total_banned_hits(
                banned_term_counts,
                "greenland amusement park",
                "greenland creek falls",
                "greenland supermarket",
                "greenland swimming pool",
                "greenland park",
                "greenland water park",
                "greenland waterpark",
                "greenland local venue title-only",
                "google expedition in korea",
                "greenland paper crafts",
                "greenland oro-dental surgury",
                "telaga",
            ),
        ),
        (
            "Movies, trailers, music, entertainment",
            total_banned_hits(
                banned_term_counts,
                "official trailer",
                "greenland trailer",
                "greenland trailer title-only",
                "greenland 2 migration title-only",
                "greenland movie title-only",
                "greenland sequel movie title-only",
                "movie review title-only",
                "movie trailer title-only",
                "trailer 2020 title-only",
                "vikings series title-only",
                "music video",
                "musik cover",
                "music cover",
                "greenland wedding reception",
                "greenland ceremony",
                "greenland gunna",
                'land of snow + "5" title-only',
                "greenland super live wallpaper title-only",
                "samsung + wallpaper title-only",
                "the greenland - tha sa daw ta koo thay",
                "the greenland - karen cover song",
                "the greenland - su nya ko na tha sa",
                "merry boys of greenland",
                "emancipator",
                "shaft in greenland",
                "cinemaxx",
                "sentossa",
                "enaensemble",
                "hut kono",
                "greenland wax",
                "greenland whale fisheries",
                "greenland whalefisheries",
                "greenland whalefishers",
                "greenland whale fishery",
                "greenland whalefishery",
                "gerard butler",
                "gerald butler",
                "gerardbulter",
            ),
        ),
        (
            "Games and gaming content",
            total_banned_hits(
                banned_term_counts,
                "pokemon",
                "minecraft",
                "roblox",
                "battle cats",
                "black ops",
                "gameplay",
                "multiplayer",
                "battlefield 1",
                "battlefield 2",
                "battlefield 3",
                "battlefield 4",
                "battlefield 5",
                "battlefield series title-only",
                "blade and sorcery variant",
                "plague inc",
                "plagueinc",
                "geoguessr",
                "bounce rescue",
            ),
        ),
        (
            "Sports teams and cricket content",
            total_banned_hits(
                banned_term_counts,
                "cricket club",
                "cricket academy",
                "cricket ground",
                "pakistancricket",
                "greenland sports title-only",
                "greenland pirates",
                "greenland cup",
                "greenland rec soccer",
                "greenland rec",
                "greenland guzzlord",
                "greenland glameows",
            ),
        ),
        (
            "Downhill race / Enping sports content",
            total_banned_hits(
                banned_term_counts,
                "greenland dh",
                "downhill race",
                "dh race",
                "enping",
                "takakonuma",
            ),
        ),
        (
            "People names and personal channels",
            total_banned_hits(
                banned_term_counts,
                "johnny greenland",
                "alex greenland",
                "nathan greenland",
                "robert greenland",
                "alexgreenland",
                "jim greenland",
                "becky greenland",
                "hall greenland",
                "stephanie greenland",
                "daniel greenland",
                "allison greenland",
                "shannon greenland",
                "katie greenland",
                "kimberly greenland",
                "anthony greenland",
                "rabbi micha greenland",
                "adam greenland",
                "nick greenland",
                "judy kline from greenland hills umc",
                "greenland person-name title-only",
                "sandy greenland",
                "laurie greenland",
                "bob greenland",
                "sheila greenland",
                "christa greenland",
                "ben plotnick",
                "kaitlyn raitz",
            ),
        ),
        (
            "Animals, fisheries, and historical niche topics",
            total_banned_hits(
                banned_term_counts,
                "greenland shark",
                "greenland valuers",
                "tahe marine greenland",
            ),
        ),
        (
            "Regional location false positives and local businesses",
            total_banned_hits(
                banned_term_counts,
                "new hampshire",
                "nh",
                "greenland japan",
                "ellenabad",
                "vermicompost",
                "vermiculture",
                "vermi",
                "9416284686",
                "minimarg",
                "standwithkashmir",
                "haryana",
                "kheti",
                "kisaan",
                "sawah",
                "villageview",
                 "farmview",
                "rotavator",
                "bigbull",
                "greenland agrotech",
                "greenland agrimart",
                "malakand",
                "swat",
                "shakarghar",
                "sikkim",
                "gangtok",
                "mallroad",
                "puga valley",
                "ladakh",
                "ladhakh",
                "azad kashmir",
                "greenland kashmir",
                "greenland azad kashmir",
                "ganga choti",
                "godavari",
                "annavaram",
                "rawalakot",
                "jhelum river",
                "greenland farm dubai",
                "greenland h s school",
                "hastinapur",
                "meerut",
                "tarbela",
                "haripur",
                "mughalroad",
                "perrgali",
                "vyas river",
                "vyasrivar",
                "nuwakot",
                "bhimavaram",
                "wisatadepok",
                "gadsarlake",
                "baghajk",
                "dholadhar",
                "maredumilli",
                "gudisa",
                "aptourism",
                "mushkpuritop",
                "nathiagali",
                "thirparappu",
                "krishnagiridistrictnews",
                "krishnagiri",
                "assameseingreenland",
                "greenland assam",
                "greenland goa",
                "greenland hyderabad",
                "greenland patna",
                "greenland moradabad",
                "greenland ranchi",
                "greenland in india",
                "greenland of india",
                "greenland in pakistan",
                "greenland of pakistan",
                "greenland in bangladesh",
                "greenland of bangladesh",
                "greenland of bhaktapur",
                "greenland of arunachal pradesh",
                "bogamati",
                "greenland eco camp",
                "greenland farm noida",
                "greenland quran academy",
                "greenland healthful living",
                "greenland grass farm",
                "greenland goat farm",
                "greenland film city",
                "wrong-place greenland alias title-only",
                "coorg",
                "bisleghat",
                "greenland himalaya hills",
                "himalaya hills",
                "oghi manshehra",
                "manshehra",
                "oghi",
                "saqibafridai",
                "greenland near bhuj",
                "bhuj",
                "ajmer",
                "rajasthan",
                "kerala",
                "kerala greenland",
                "greenland lahore",
                "peshawar",
                "ludhiana",
                "milan",
                "malangwa",
                "forest hill",
                "bogor",
                "buskers festival",
                "lappa laona",
                "lonwade road",
                "kumamoto",
                "taman perumahan",
                "perumahan",
                "selalu",
                "sayang",
                "class 5",
                "class v",
                "shooterking greenland smock",
            ),
        ),
        (
            "Language-only title bans and misc. noisy matches",
            total_banned_hits(
                banned_term_counts,
                "lahore",
                "bangalore",
                "sidhumoosewala",
                "sidhumoosewalasister",
                "rupeshrohit",
                "shopifystore",
                "kamibhai",
                "kishmishkefayde",
                "kukkesubrahmanya",
                "mansrovar",
                "folkditties",
                "bhojpuri",
                "bhojpurivideo",
                "ashokujnas",
                "janassyl",
                "aktobe",
                "utya",
                "nawkata",
                "ahoty",
                "ahilo",
                "colegio",
                "torneo",
                "estadio",
                "dodoma",
                "ciwidey",
                "tiruvanamalai",
                "gondal",
                "greenland festival",
                "greenland swimming pool",
                "greenland boardgame review",
                "greenland bar",
                "greenland grad",
                "greenland scientist",
                "merge town",
                "greenland god",
                "greenland mini",
            ),
        ),
    ]
    for label, count in banned_clusters:
        if count > 0:
            safe_print(f"  - {label}: {count}")
    if removed_by_green_land_hashtag_combo > 0:
        safe_print('  - "Green land" + "#greenland" combo matches: '
                   f"{removed_by_green_land_hashtag_combo}")
    safe_print(f"Removed by greenland-only title rule: {removed_by_generic_title}")
    safe_print(f"Removed by non-English detection: {removed_by_non_english}")
    safe_print(f"Removed by duplicate pruning (keep highest views per cluster): {removed_by_duplicate_pruning}")
    if accounted_deleted == total_deleted:
        safe_print(f"Rows accounted for by summary categories: {accounted_deleted} (matches rows deleted)")
    else:
        safe_print(
            "Rows accounted for by summary categories: "
            f"{accounted_deleted} (WARNING: differs from rows deleted by {total_deleted - accounted_deleted})"
        )

    if args.skip_descriptive_table:
        safe_print("\nSkipped descriptive table generation (--skip-descriptive-table).")
    else:
        descriptive_table_script = args.descriptive_table_script.resolve()
        if not descriptive_table_script.exists():
            raise FileNotFoundError(f"Descriptive table script not found: {descriptive_table_script}")

        safe_print("\nRunning descriptive table generation ...")
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(descriptive_table_script),
                    "--csv",
                    str(out_path),
                ],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                "Cleanup completed, but the descriptive table step failed. "
                f"Cleaned CSV is still available at: {out_path}"
            ) from exc

        safe_print(f"Descriptive table generation finished using: {out_path}")

    if args.skip_topic_modeling:
        safe_print("\nSkipped Creating_frames topic modeling (--skip-topic-modeling).")
    else:
        topic_modeling_script = args.topic_modeling_script.resolve()
        if not topic_modeling_script.exists():
            raise FileNotFoundError(f"Creating_frames topic modeling script not found: {topic_modeling_script}")

        safe_print("\nRunning Creating_frames topic modeling ...")
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(topic_modeling_script),
                    "--csv",
                    str(out_path),
                ],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                "Cleanup completed, but the Creating_frames topic modeling step failed. "
                f"Cleaned CSV is still available at: {out_path}"
            ) from exc

        safe_print(f"Creating_frames topic modeling finished using: {out_path}")


if __name__ == "__main__":
    main()
