"""Build a Russian MediaWiki seed from the game's shared, reviewed catalogues.

Build output is disposable. The updater replaces only unchanged generated blocks;
editor-written text outside those blocks is preserved on subsequent deployments.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import yaml
from game_data import equipment_data, spellbook_data, monster_spellbook_data
from navigation import WikiNavigation, PORTALS, SPECIAL_WORLDS
from presentation import WikiPresentation

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/ru"))
from catalog import read_db

GROUPS = {
    "species": ("Виды", "вид"), "background": ("Предыстории", "предыстория"),
    "gods": ("Боги", "бог"), "skills": ("Навыки", "навык"),
    "items": ("Предметы", "предмет"), "unrand": ("Артефакты", "артефакт"),
    "spells": ("Заклинания", "заклинание"), "ability": ("Способности", "способность"),
    "monsters": ("Существа", "существо"), "status": ("Состояния", "состояние"),
    "mutations": ("Мутации", "мутация"), "features": ("Местность", "местность"),
    "cards": ("Карты", "карта"), "egos": ("Свойства снаряжения", "свойство")}
EGO_NAMES = dict(zip(
    ["acid","antimagic","chaos","concussion","distortion","devious","draining","electrocution","entangling","flaming","freezing","foul flame","heavy","holy wrath","penetration","protection","reaping","rebuke","spectralising","speed","sundering","valour","vampirism","venom","air","archery","attunement","cold resistance","command","corrosion resistance","death","dexterity","earth","energy","fire","fire resistance","flying","glass","guile","harm","hurling","ice","infusion","intelligence","invisibility","light","mayhem","mesmerism","parrying","poison resistance","ponderousness","positive energy","pyromania","rampaging","reflection","repulsion","resistance","resonance","see invisible","shadows","sniping","spirit shield","stardust","stealth","strength","the Archmagi","willpower","wrath","atropa-tipped","curare-tipped","datura-tipped","disjunction","dispersal","poisoned","silver","pain"],
    ["Кислота","Антимагия","Хаос","Сотрясение","Искажение","Коварство","Истощение","Электричество","Опутывание","Пламя","Холод","Нечестивое пламя","Тяжесть","Священный гнев","Пробивание","Защита","Жатва","Воздаяние","Призрачность","Скорость","Рассечение","Доблесть","Вампиризм","Яд","Воздух","Стрельба","Настройка","Сопротивление холоду","Командование","Сопротивление коррозии","Смерть","Ловкость","Земля","Энергия","Огонь","Сопротивление огню","Полёт","Стекло","Хитрость","Вред","Метание","Лёд","Наполнение","Интеллект","Невидимость","Свет","Погром","Гипноз","Парирование","Сопротивление яду","Неповоротливость","Положительная энергия","Пиромания","Натиск","Отражение","Отталкивание","Сопротивление стихиям","Резонанс","Обнаружение невидимого","Тени","Снайперство","Духовный щит","Звёздная пыль","Скрытность","Сила","Архимаг","Воля","Ярость","Атропа","Кураре","Дурман","Разрыв пространства","Рассеивание","Отравление","Серебро","Боль"]))
# Follow the reviewed in-game inscriptions, rather than independently choosing
# synonyms for the same property. Abbreviated labels also appear on each page.
EGO_REFINEMENTS={"concussion":"Отбрасывание","foul flame":"Скверное пламя","holy wrath":"Святость",
    "penetration":"Пробитие","spectralising":"Призрак","sundering":"Сокрушение","venom":"Отрава",
    "attunement":"Созвучие","glass":"Остекление","guile":"Лукавство","harm":"Усиление урона",
    "light":"Сияние","mayhem":"Неистовство","repulsion":"Отвод снарядов","poisoned":"Яд"}
EGO_OLD_NAMES={k:EGO_NAMES[k] for k in EGO_REFINEMENTS}
EGO_NAMES.update(EGO_REFINEMENTS)
FEATURE_NAMES = {"haloed":"Священная аура", "umbraed":"Аура тьмы", "liquefied":"Разжиженная земля",
    "disjunction haloed":"Поле разрыва пространства", "ice covered":"Ледяное покрытие", "awoken":"Пробуждённое дерево",
    "tree burning":"Горящее дерево", "mangrove burning":"Горящий мангр", "demonic tree burning":"Горящее демоническое дерево"}
SPECIES_SPRITES = {"Human":"human_m", "Mountain Dwarf":"dwarf_m", "Deep Elf":"deep_elf_m", "Minotaur":"minotaur_m",
    "Merfolk":"merfolk_water_m", "Tengu":"tengu_wingless_m", "Spriggan":"spriggan_m", "Gargoyle":"gargoyle_m",
    "Troll":"troll_m", "Naga":"naga_m", "Octopode":"octopode1", "Felid":"felid", "Formicid":"formicid",
    "Vine Stalker":"vine_stalker_green_m", "Demonspawn":"demonspawn_red_m", "Demigod":"demigod_m", "Draconian":"draconian",
    "Kobold":"kobold_m", "Gnoll":"gnoll_m", "Barachi":"frog_m", "Djinni":"djinni_red_m", "Coglin":"coglin",
    "Gale Centaur":"gale_centaur_m", "Mummy":"mummy_m", "Oni":"oni_red_m", "Poltergeist":"poltergeist", "Revenant":"revenant"}
# The renderer selects these dynamically rather than assigning one static
# monster tile. Use one of the actual in-game poses for the reference card.
DYNAMIC_MONSTER_TILES = {
    "orc apostle follower":"MONS_ORC_APOSTLE",
    "eldritch tentacle":"MONS_ELDRITCH_TENTACLE_PORTAL",
    "eldritch tentacle segment":"MONS_ELDRITCH_TENTACLE_SEGMENT_E_W",
    "starspawn tentacle":"MONS_STARSPAWN_TENTACLE_S",
    "starspawn tentacle segment":"MONS_STARSPAWN_TENTACLE_SEGMENT_E_W",
    "snaplasher vine":"MONS_VINE_S",
    "snaplasher vine segment":"MONS_VINE_SEGMENT_E_W",
    "tentacle":"MONS_KRAKEN_TENTACLE_WATER",
    "tentacle segment":"MONS_KRAKEN_TENTACLE_SEGMENT_WATER"}
FLAG_LABELS = {"flies":"Полёт", "see_invis":"Видит невидимых", "invis":"Невидимость", "fast_regen":"Быстрая регенерация",
    "stationary":"Неподвижность", "insubstantial":"Бестелесность", "unique":"Уникальный противник", "no_regen":"Не восстанавливает здоровье"}
ATTACKS = {"hit":"удар", "bite":"укус", "claw":"когти", "sting":"жало", "peck":"клюв", "constrict":"сдавливание",
    "trample":"растаптывание", "gore":"рога", "tentacle_slap":"удар щупальцем", "touch":"касание", "tail_slap":"удар хвостом"}
PAGE_TITLES = {
    ("status","Bog status"):"Болото (состояние)",
    ("monsters","ghost"):"Призрак (архив)",
    ("monsters","orc apostle follower"):"Апостол орков (последователь)",
    ("ability","Jump ability"):"Прыжок (случайное приземление)",
    ("status","Heavenly status"):"Небесная буря (состояние)",
    ("status","Storm status"):"Буря (облик)",
    ("status","Fusillade status"):"Залп (Алхимический шквал)",
    ("status","Flux status"):"Нестабильность (облик)",
    ("status","Unstable status"):"Нестабильность (пространственные скачки)",
    ("status","Water status"):"Вода (местоположение)",
    ("status","Aqua status"):"Вода (облик)",
    ("mutations","formless mutation"):"Бестелесность (Полтергейст)",
    ("mutations","insubstantial mutation"):"Бестелесность (невосприимчивость)"}
DISAMBIGUATIONS = {
    "Буря":["Небесная буря (состояние)","Буря (облик)"],
    "Вода":["Вода (местоположение)","Вода (облик)"],
    "Нестаб.":["Нестабильность (облик)","Нестабильность (пространственные скачки)"],
    "Нестабильность":["Нестабильность (облик)","Нестабильность (пространственные скачки)"],
    "Бестелесность":["Бестелесность (Полтергейст)","Бестелесность (невосприимчивость)"]}
VARIANT_HEADINGS = {
    "Serpent of Hell gehenna":"Геенна", "Serpent of Hell cocytus":"Коцит",
    "Serpent of Hell dis":"Дис", "Serpent of Hell tartarus":"Тартар",
    "flaming (flame) weapon ego":"Общий эффект", "flaming (flame) weapon ego blade":"Клинковое оружие",
    "heavy (heavy) weapon ego":"Ближний бой", "heavy (heavy) weapon ego ranged":"Дальний бой"}


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def cap(value):
    return value[:1].upper() + value[1:]


def clean_title(value):
    return cap(re.sub(r"\{[^{}]*\}|<[^<>]*>", "", value).strip().replace("_", " "))


def tile_map(filename):
    directory = ""
    result = {}
    for line in (ROOT / "crawl-ref/source/rltiles" / filename).read_text(encoding="utf8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("%sdir "):
            directory = line.split(maxsplit=1)[1]
        elif line.startswith("%include "):
            include=line.split(maxsplit=1)[1]
            # Generated at game-build time; artefacts are read from art-data.txt.
            if include!='dc-unrand.txt':result.update(tile_map(include))
        elif line and not line.startswith("%"):
            parts = line.split()
            if len(parts) > 1:
                path = ROOT / "crawl-ref/source/rltiles" / directory / (parts[0] + ".png")
                if path.is_file():
                    for label in parts[1:]:
                        result.setdefault(label, path)
    return result


def spell_data():
    text = (ROOT / "crawl-ref/source/spl-data.h").read_text(encoding="utf8")
    result = {}
    for match in re.finditer(r'\{\s*(SPELL_[A-Z0-9_]+),\s*"([^"\n]+)",(.+?)\n\},', text, re.S):
        body = re.sub(r"//[^\n]*|/\*.*?\*/", "", match[3], flags=re.S)
        fields = [v.strip() for v in body.split(",")]
        if len(fields) >= 8:
            result[match[2].casefold()] = {"enum":match[1], "schools":re.findall(r"spschool::(\w+)", fields[0]),
                "level":fields[2], "tile":fields[7].removeprefix("TILEG_"),
                "monster_only":'spflag::monster' in fields[1]}
    return result


def branch_data():
    """Read the entry ranges and lengths from this fork, not an old wiki map."""
    text = (ROOT / "crawl-ref/source/branch-data.h").read_text(encoding="utf8")
    result = {}
    pattern = r'\{\s*BRANCH_([A-Z_]+),\s*([A-Z_]+),\s*(-?\d+),\s*(-?\d+),\s*(\d+),'
    for match in re.finditer(pattern, text):
        row = dict(parent=match[2].removeprefix("BRANCH_"),
                   first=int(match[3]), last=int(match[4]), levels=int(match[5]))
        # Compatibility definitions repeat Depths/Gauntlet with the same map
        # data. Fail visibly if that ever ceases to be true.
        if match[1] in result and result[match[1]] != row:
            raise ValueError(("Ambiguous branch parameters", match[1]))
        result[match[1]] = row
    return result


class Builder(WikiNavigation, WikiPresentation):
    def __init__(self, output, community=None, revision=None):
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.revision=revision
        (output / "sprites").mkdir(exist_ok=True)
        self.terms = load(ROOT / "localization/ru/terms.json")
        self.entities = load(ROOT / "localization/ru/entities.json")
        self.reference = load(ROOT / "wiki/ru/reference/descriptions.json")
        self.group_names={key:value[0] for key,value in GROUPS.items()}
        self.reviewed = load(ROOT / "localization/ru/descriptions.json")
        self.messages = load(ROOT / "localization/ru/system-messages.json")
        self.static = load(ROOT / "localization/ru/static.json")
        self.annotations={k.casefold():v for k,v in self.static['annotations'].items()}
        self.notes = load(ROOT / "wiki/site/notes.json")
        self.community = load(community or ROOT / "wiki/site/community-revisions.json")["pages"]
        self.community_by_key = {k.casefold():v for k,v in self.community.items()}
        self.titles = {}
        self.rows = {}
        self.keys = {}
        self.assets = {}
        self.sprite_map = {}
        self.unresolved = set()
        self.mon_tiles = tile_map("dc-mon.txt")
        self.misc_tiles = tile_map("dc-misc.txt")
        self.gui_tiles = tile_map("dc-gui.txt")
        self.spell_tiles = tile_map("dc-spells.txt")
        self.feature_tiles = tile_map("dc-feat.txt")
        self.item_tiles = tile_map("dc-item.txt")
        self.gem_enums={name+' gem':enum for enum,name in re.findall(r'\{\s*(GEM_\w+),\s*"([^"\n]+)"',(ROOT/'crawl-ref/source/item-prop.cc').read_text(encoding='utf8'))}
        abilities=(ROOT/'crawl-ref/source/ability.cc').read_text(encoding='utf8')
        self.ability_enums={name.casefold():enum for enum,name in re.findall(r'\{\s*(ABIL_\w+),\s*"([^"\n]+)"',abilities)}
        tilepick=(ROOT/'crawl-ref/source/tilepick.cc').read_text(encoding='utf8')
        self.ability_tiles=dict(re.findall(r'case (ABIL_\w+):\s*return TILEG_(\w+);',tilepick))
        self.spells = spell_data()
        self.weapons,self.armour,self.missiles=equipment_data(ROOT)
        self.books=spellbook_data(ROOT)
        self.monster_books=monster_spellbook_data(ROOT)
        self.spells_by_enum={v['enum']:k for k,v in self.spells.items()}
        self.artifacts = {}
        art_text = (ROOT / "crawl-ref/source/art-data.txt").read_text(encoding="utf8")
        for block in re.split(r"\n\s*\n",art_text):
            fields=dict(re.findall(r"^([A-Z_]+):\s*(.+)$",block,re.M))
            if "NAME" in fields and "TILE" in fields:
                self.artifacts[fields["NAME"].casefold()]=fields
        self.pngs = list((ROOT / "crawl-ref/source/rltiles").rglob("*.png"))
        self.by_stem = {}
        for path in self.pngs:
            if "UNUSED" not in path.parts:
                self.by_stem.setdefault(path.stem.casefold(), []).append(path)
                normalized=re.sub(r"[^a-z0-9]+","_",path.stem.casefold()).strip("_")
                if normalized!=path.stem.casefold():self.by_stem.setdefault(normalized,[]).append(path)
        self.monsters = {}
        self.species = {}
        self.backgrounds = {}
        for folder, target in [("mons", self.monsters), ("species", self.species), ("jobs", self.backgrounds)]:
            for path in (ROOT / "crawl-ref/source/dat" / folder).glob("*.yaml"):
                row = yaml.safe_load(path.read_text(encoding="utf8"))
                if not isinstance(row, dict) or "name" not in row:
                    continue
                row["_path"] = path.relative_to(ROOT).as_posix()
                target.setdefault(row["name"].casefold(), row)
        self.lexicon = {k.casefold():v["forms"]["singular"]["nom"] for v in self.entities for k in [v["en"]]}
        for group in self.terms.values():
            for key,value in group.items():
                self.lexicon.setdefault(key.casefold(), value)

    def skill_key(self,value):
        value=value.replace("_"," ").casefold()
        aliases={"maces and flails":"Maces & Flails","fire":"Fire Magic","ice":"Ice Magic","air":"Air Magic","earth":"Earth Magic",
            "conjuration":"Conjurations","hexes":"Hexes","summoning":"Summonings","translocation":"Translocations"}
        return aliases.get(value, next((k for k in self.terms["skill"] if k.casefold()==value),value))

    def register(self, group, key, title, text, **extra):
        title = clean_title(title)
        if not re.search(r"[А-Яа-яЁё]", title):
            raise ValueError(("Untranslated page title",group,key,title))
        candidate = PAGE_TITLES.get((group,key),title)
        if candidate in self.rows and self.rows[candidate]["group"] != group:
            candidate += " (" + GROUPS[group][1] + ")"
        if candidate not in self.rows:
            self.rows[candidate] = dict(group=group, title=candidate, name=title, entries=[], **extra)
        self.rows[candidate]["entries"].append(dict(key=key, text=text))
        self.keys[(group,key)] = candidate
        self.titles.setdefault(key.casefold(), candidate)
        self.titles.setdefault(re.sub(r" (spell|ability|card|mutation|status|skill)$", "",key).casefold(), candidate)
        return self.rows[candidate]

    def translate(self, value):
        return self.lexicon.get(value.casefold(), self.messages.get(value, ""))

    def sprite(self, path):
        if not path or not path.is_file():
            return None
        relative = path.relative_to(ROOT / "crawl-ref/source/rltiles").as_posix()
        name = "Dcss-" + re.sub(r"[^A-Za-z0-9_.-]", "-", relative.replace("/", "-"))
        if name not in self.assets:
            shutil.copyfile(path, self.output / "sprites" / name)
            self.assets[name] = dict(path="crawl-ref/source/rltiles/"+relative,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        return name

    def find_sprite(self, name, folders=()):
        stem = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
        for candidate in (stem, stem+"0", stem+"1", stem+"01", stem+"_m"):
            paths = self.by_stem.get(candidate, [])
            if folders:
                paths = [p for p in paths if any(f in p.parts for f in folders)]
            if paths:
                return paths[0]
        return None

    def collect(self):
        characters = load(ROOT / "localization/ru/character-descriptions.json")
        for key,name in self.terms["species"].items():
            stem = SPECIES_SPRITES[key]
            path = ROOT / "crawl-ref/source/rltiles/player/base" / (stem+".png")
            if not path.is_file():
                path = ROOT/"crawl-ref/source/rltiles/player/felids/cat1.png" if key=="Felid" else self.find_sprite(key, ("mon","player"))
            # Complete in-game species portraits read better than an unequipped
            # doll layer. Coglins and Gale Centaurs have distinct player bodies.
            data=self.species.get(key.casefold(),{})
            if key not in ("Coglin","Gale Centaur"):
                path=self.mon_tiles.get(data.get("monster")) or path
            self.register("species",key,name,characters["species"][key],sprite=self.sprite(path))
        for key,name in self.terms["background"].items():
            data = self.backgrounds.get(key.casefold(),{})
            enum = data.get("enum", "JOB_"+key.upper().replace(" ","_"))
            self.register("background",key,name,characters["backgrounds"][key],sprite=self.sprite(self.gui_tiles.get(enum.replace("JOB_","JOB_RECOMMENDED_"))))
        gods = read_db(ROOT / "crawl-ref/source/dat/descript/ru/gods.txt")
        for key,name in self.terms["gods"].items():
            enum="DNGN_ALTAR_"+key.removeprefix("the ").upper().replace(" ","_")
            self.register("gods",key,name,gods[key],sprite=self.sprite(self.feature_tiles.get(enum)))
        for group in ("skills","items","unrand","spells","ability","monsters","status","mutations","features","cards","egos"):
            for key,entry in self.reference[group].items():
                if key.startswith("__(_"):
                    continue
                title = entry["title"]
                if not title:
                    if group == "egos":
                        base = key.split(" (",1)[0]
                        title = EGO_NAMES[base]
                        if "armour ego" in key: title += " (свойство брони)"
                        elif "missile ego" in key:title += " (свойство снарядов)"
                        else:title += " (свойство оружия)"
                    elif group == "features":title = FEATURE_NAMES[key]
                    elif key == "player invis desc":title = "Невидимый персонаж"
                path = None
                suffix={'spells':' spell','ability':' ability','cards':' card','mutations':' mutation','status':' status'}.get(group,'')
                plain=key.removesuffix(suffix) if suffix else key
                if group == "spells":
                    info = self.spells.get(plain.casefold(),{})
                    tile = info.get("tile")
                    path = (self.spell_tiles.get(tile) or self.gui_tiles.get(tile)
                            or self.spell_tiles.get(plain.upper().replace(' ', '_')))
                elif group == "monsters":
                    data = self.monsters.get(key.casefold(),{})
                    enum = data.get("enum", "MONS_"+key.upper().replace(" ","_").replace("'",""))
                    if not enum.startswith("MONS_"):enum="MONS_"+enum.upper()
                    tile = data.get("tile", "").upper().removeprefix("TILEP_").removeprefix("TILE_")
                    path=(self.mon_tiles.get(DYNAMIC_MONSTER_TILES.get(key,enum))
                          or self.mon_tiles.get(tile) or self.mon_tiles.get("MONS_"+tile)
                          or self.misc_tiles.get(tile))
                    if key == "draconian" or key.endswith(" draconian") and key.split()[0] in ('black','green','grey','pale','purple','red','white','yellow'):
                        colour = 'brown' if key == 'draconian' else key.split()[0]
                        path = self.find_sprite('draco-base-'+colour,('mon',))
                    path=path or self.find_sprite(data.get("tile",key.removesuffix(' monster')),("mon",))
                elif group == "skills":path=self.find_sprite({'Alchemy':'poison_magic','Ranged Weapons':'bows'}.get(plain,plain),("skills",))
                elif group in ("items","unrand"):
                    path=self.find_sprite(plain,("item",))
                    artifact=self.artifacts.get(plain.casefold())
                    if not artifact and plain in ('Sulking Sword','Screaming Sword'):
                        artifact=self.artifacts.get('singing sword')
                    if not artifact:
                        artifact=next((a for n,a in self.artifacts.items() if '"'+n+'"' in plain.casefold()),None)
                    if artifact:path=self.find_sprite(artifact["TILE"],("item",))
                    if not path:
                        for prefix in ("potion of ","scroll of ","wand of ","ring of ","amulet of "):
                            if plain.startswith(prefix):
                                path=self.find_sprite("i-"+plain[len(prefix):].replace(" ","-"),("item",))
                                break
                    if group=='items':path=self.item_sprite(plain) or path
                elif group=='ability':
                    enum=self.ability_enums.get(plain.casefold(),'')
                    tile=self.ability_tiles.get(enum,enum.replace('ABIL_','ABILITY_',1))
                    path=self.gui_tiles.get(tile)
                elif group=='features':
                    name=re.sub(r'^(?:The|An?|Some) ', '', plain)
                    path=self.feature_tiles.get('DNGN_'+name.upper().replace(' ','_'))
                elif group == "mutations":path=self.find_sprite(plain,("mutations",))
                prose=self.reviewed.get(group,{}).get(key,{}).get('wiki_text',entry['text'])
                row=self.register(group,key,title,prose,sprite=self.sprite(path))
                row.setdefault("powers",[]).extend(entry.get("powers",[]))
        self.prepare_navigation(ROOT,branch_data())
        self.prepare_presentation()
        return self

    def prose(self, text):
        text = re.sub(r"\{\{.*?\}\}", "",text,flags=re.S)
        text = re.sub(r"</?(?:w|light\w+|dark\w+|white|red|green|blue|yellow|brown|cyan|magenta|black|h|v|u)>|#Lua#", "",text)
        def link(match):
            key=match[1]
            title=self.titles.get(key.casefold())
            if title:return "[["+title+"]]"
            translation=self.translate(key)
            if translation:return clean_title(translation)
            self.unresolved.add(key)
            return "связанное описание"
        return re.sub(r"\[\[([^\[\]]+)\]\]",link,text)

    def source(self, row):
        group=row["group"];key=row["entries"][0]["key"]
        en=re.sub(r" (spell|ability|card|mutation|status)$", "",key)
        community=self.community_by_key.get(en.casefold())
        links=[]
        if community:
            links.append("["+community["url"]+" CrawlWiki, редакция от "+community["timestamp"][:10]+"]")
        source={"species":"species.txt","background":"backgrounds.txt","gods":"gods.txt"}.get(group,group+".txt")
        links.append("[https://github.com/Mr-Vivor/DCSS-RU/blob/ru-bootstrap/crawl-ref/source/dat/descript/"+source+" Описание русского форка]")
        return '<div class="dc-source">Источники: '+" · ".join(links)+". Описание и характеристики сверены с веткой 0.35-a0. Советы — рекомендации, а не гарантия победы.</div>"

    def table(self, rows):
        if not rows:return ""
        return '{| class="wikitable"\n! Параметр !! Значение\n'+"\n".join("|-\n| "+str(a)+" || "+str(b) for a,b in rows)+"\n|}\n"

    def object_link(self, value):
        value=self.skill_key(value) if self.skill_key(value) in self.terms["skill"] else value
        title=self.titles.get(value.casefold())
        return self.illustrated_link(title) if title else self.translate(value)

    def metadata(self, row):
        group=row["group"];key=row["entries"][0]["key"]
        text=""
        if group == "monsters":
            data=self.monsters.get(key.casefold())
            if data:
                rows=[]
                for field,label in [("hp_10x","Среднее здоровье"),("ac","Броня (AC)"),("ev","Уклонение (EV)"),("will","Воля"),("speed","Базовая скорость")]:
                    value=data.get(field)
                    if value is not None:
                        if field=="hp_10x":value=f"{value/10:g}"
                        if field=="will" and value in ("immune","invuln"):value="Неуязвимость к проверкам Воли"
                        rows.append((label,value))
                attacks=[str(a["damage"])+" ("+ATTACKS.get(a.get("type"),"атака")+")" for a in (data.get("attacks") or []) if isinstance(a.get("damage"),int) and a["damage"]>0]
                if attacks:rows.append(("Базовый урон отдельных атак",", ".join(attacks)))
                features=[FLAG_LABELS[f] for f in data.get("flags",[]) if f in FLAG_LABELS]
                if features:rows.append(("Особенности",", ".join(features)))
                text+="\n== Характеристики ==\n"+self.table(rows)+"Базовые значения могут изменяться у конкретного существа из-за его состояния, снаряжения или особенностей разновидности. Урон указан до учёта защиты цели.\n"
                powers=[]
                for enum in self.monster_books.get(data.get('spells',''),[]):
                    name=self.spells_by_enum.get(enum)
                    title=self.titles.get(name) if name else None
                    if title:powers.append(title)
                if powers:text+='\n== Заклинания и силы ==\n<div class="dc-related-links">'+' '.join(self.illustrated_link(t) for t in powers)+'</div>\nСсылки ведут к описаниям сил из базового набора существа в [https://github.com/Mr-Vivor/DCSS-RU/blob/ru-bootstrap/crawl-ref/source/mon-spell.h нашей версии]. Особые разновидности и состояния могут изменять его возможности.\n'
            elif not key.startswith('Serpent of Hell '):
                text+='\n<div class="dc-notice">Дополнительное описание игрового каталога. Характеристики и встречаемость могут зависеть от конкретной разновидности, эффекта или режима.</div>\n'
        elif group == "species":
            data=self.species.get(key.casefold(),{})
            rows=[(label,data[field]) for field,label in [("str","Начальная сила"),("int","Начальный интеллект"),("dex","Начальная ловкость")] if field in data]
            if rows:text+="\n== Начальные характеристики ==\n"+self.table(rows)+"К ним добавляются бонусы выбранной [[Предыстории|предыстории]].\n"
            apt=[]
            for skill,value in data.get("aptitudes",{}).items():
                label=self.terms["skill"].get(self.skill_key(skill))
                if label and skill not in ("xp","hp","mp_mod","wl"):
                    tone='positive' if value>0 else 'negative' if value<0 else 'neutral'
                    apt.append((self.object_link(skill.replace("_"," ")) or label,'<span class="dc-apt-'+tone+'">'+f"{value:+g}"+'</span>'))
            if apt:text+="\n== Склонности к обучению ==\nЧем выше значение, тем быстрее развивается навык при одинаковых затратах опыта.\n"+self.table(apt).replace('! Параметр !! Значение','! Навык !! Склонность')
            recommended=[self.object_link(v) for v in data.get("recommended_jobs",[])]
            if any(recommended):text+="\n== Рекомендуемые предыстории ==\n"+", ".join(v for v in recommended if v)+".\n"
        elif group == "background":
            data=self.backgrounds.get(key.casefold(),{})
            rows=[(label,f"+{data[field]}") for field,label in [("str","Сила"),("int","Интеллект"),("dex","Ловкость")] if data.get(field)]
            if rows:text+="\n== Бонусы характеристик ==\n"+self.table(rows)
            equipment=[]
            for item in data.get("equipment",[]):
                base=item.split(" q:")[0].split(" plus:")[0].split(" ego:")[0]
                display=self.object_link(base)
                if display:
                    count=re.search(r"\bq:(\d+)",item)
                    equipment.append(display+(" × "+count[1] if count else ""))
            if equipment:text+="\n== Начальное снаряжение ==\n"+"\n".join("* "+v for v in equipment)+"\n"
            if data.get("weapon_choice"):text+="\nОсновное оружие выбирается при создании персонажа.\n"
            skills=[]
            for name,value in data.get("skills",{}).items():
                label="Выбранное оружие" if name=="weapon" else self.object_link(name.replace("_"," "))
                if label:skills.append((label,value))
            if skills:text+="\n== Начальные навыки ==\n"+self.table(skills).replace('! Параметр !! Значение','! Навык !! Начальный уровень')
            text+="\nСнаряжение и навыки могут корректироваться в зависимости от выбранного вида. Предыстория задаёт старт, а не ограничивает дальнейшее развитие.\n"
        elif group == "spells":
            plain=key.removesuffix(" spell");data=self.spells.get(plain.casefold(),{})
            rows=[]
            if data.get("level","").isdigit():rows.append(("Уровень заклинания",data["level"]))
            labels=[self.terms["skill"][self.skill_key(s)] for s in data.get("schools",[]) if self.skill_key(s) in self.terms["skill"]]
            if labels:rows.append(("Школы",", ".join(self.illustrated_link(v) for v in labels)))
            if data:rows.append(('Доступность','Сила существа или особого источника; не обычное изучаемое заклинание' if data['monster_only'] else 'Заклинание персонажа'))
            if rows:text+="\n== Параметры ==\n"+self.table(rows)
            books=[self.keys[('items',name)] for name,enums in self.books.items() if data.get('enum') in enums and ('items',name) in self.keys]
            if books:text+='\n== Где найти ==\nЭта магия встречается в следующих шаблонах книг нашей версии:\n\n<div class="dc-related-links">'+' '.join(self.illustrated_link(v) for v in sorted(set(books)))+'</div>\n'
            users=self.spell_users.get(data.get('enum'),[])
            if users:text+='\n== Кто использует ==\nВ базовых наборах следующих существ нашей версии есть это заклинание. Разновидности и особые состояния могут менять набор сил.\n\n<div class="dc-related-links">'+' '.join(self.illustrated_link(t) for t in users)+'</div>\n'
        elif group == 'items':
            rows=[]
            if key in self.weapons:
                data=self.weapons[key]
                skill_names={'SK_MACES_FLAILS':'Maces & Flails','SK_SHORT_BLADES':'Short Blades','SK_LONG_BLADES':'Long Blades','SK_AXES':'Axes','SK_POLEARMS':'Polearms','SK_STAVES':'Staves','SK_RANGED_WEAPONS':'Ranged Weapons'}
                rows=[('Базовый урон',str(data['damage'])),('Базовый бонус точности',f"{data['accuracy']:+}"),('Базовая задержка',f"{data['delay']/10:g}")]
                skill=skill_names.get(data['skill'])
                if skill:rows.append(('Навык',self.object_link(skill)))
                rows.append(('Сравнение','[[Скорость атаки]] · [[Оружие и выбор навыка]]'))
            elif key in self.armour:
                data=self.armour[key]
                shield=data['slot']=='SLOT_OFFHAND'
                rows=[('Базовый показатель щита' if shield else 'Базовая броня AC',str(data['ac']))]
                if data['slot'] in ('SLOT_BODY_ARMOUR','SLOT_OFFHAND'):rows.append(('Тяжесть',f"{data['encumbrance']:g}"))
                rows.append(('Сравнение','[[Тяжесть доспехов и щитов]]'))
            elif key in self.missiles:rows=[('Базовый урон',str(self.missiles[key]['damage'])),('Применение','[[Дальний бой и метание]]')]
            if rows:
                text+='\n== Базовые параметры ==\n'+self.table(rows)
                text+='\nЭто параметры типа предмета из [https://github.com/Mr-Vivor/DCSS-RU/blob/ru-bootstrap/crawl-ref/source/item-prop.cc текущего исходного кода]. Итоговые показатели зависят от навыков, характеристик, зачарования, свойств, формы и другого снаряжения. Задержка указана в обычных единицах времени (1,0 = стандартное действие), до обучения и прочих изменений. Базовый урон не равен гарантированному урону за попадание.\n'
            if key in self.books:
                links=[]
                for enum in self.books[key]:
                    name=self.spells_by_enum.get(enum)
                    if not name:raise ValueError(('Unknown spell in current book',key,enum))
                    title=self.titles.get(name)
                    if not title:raise ValueError(('Missing translated spell page',key,name))
                    links.append('* '+self.illustrated_link(title)+' — уровень '+self.spells[name]['level'])
                text+='\n== Заклинания в книге ==\n'+'\n'.join(links)
                text+='\n\nСостав взят из [https://github.com/Mr-Vivor/DCSS-RU/blob/ru-bootstrap/crawl-ref/source/book-data.h шаблонов книг активной версии]. Нахождение книги добавляет знания в библиотеку; само по себе не даёт навыков, надёжности или свободных уровней для заучивания.\n'
        elif group == 'skills':
            learned={enum for values in self.books.values() for enum in values}
            related=[]
            for name,data in self.spells.items():
                if data['enum'] not in learned:continue
                if key not in [self.skill_key(s) for s in data['schools']]:continue
                title=self.titles.get(name)
                if title and data['level'].isdigit():related.append((int(data['level']),title))
            if related:
                text+='\n== Заклинания школы в книгах ==\n'+'\n'.join('* '+self.illustrated_link(title)+' — уровень '+str(level) for level,title in sorted(set(related)))
                text+='\n\nСписок относится к книгам нашей версии. Наличие заклинания не означает, что его можно надёжно применять без подходящего обучения и снаряжения.\n'
            weapon_skills={'Maces & Flails':'SK_MACES_FLAILS','Short Blades':'SK_SHORT_BLADES','Long Blades':'SK_LONG_BLADES','Axes':'SK_AXES','Polearms':'SK_POLEARMS','Staves':'SK_STAVES','Ranged Weapons':'SK_RANGED_WEAPONS'}
            related_items=[]
            for name,data in self.weapons.items():
                if data['skill']==weapon_skills.get(key) and ('items',name) in self.keys:related_items.append(self.keys[('items',name)])
            if key=='Throwing':related_items=[self.keys[('items',name)] for name in self.missiles if ('items',name) in self.keys]
            if key in ('Armour','Shields'):
                slot='SLOT_BODY_ARMOUR' if key=='Armour' else 'SLOT_OFFHAND'
                related_items=[self.keys[('items',name)] for name,data in self.armour.items() if data['slot']==slot and ('items',name) in self.keys]
            if related_items:text+='\n== Связанные предметы ==\n<div class="dc-related-links">'+' '.join(self.illustrated_link(t) for t in sorted(set(related_items)))+'</div>\n'
        elif group == "gods":
            linked=self.linked_powers(key)
            if linked:text+='\n== Связанные способности ==\n<div class="dc-related-links">'+' '.join(self.illustrated_link(r['title']) for r in linked)+'</div>\nУсловия получения и применения указаны в описании конкретной силы.\n'
            gods=read_db(ROOT / "crawl-ref/source/dat/descript/ru/gods.txt")
            for suffix,heading in [(" powers","Божественные силы"),(" likes","Что одобряет бог"),(" dislikes","Что вызывает недовольство"),(" wrath","Божественный гнев")]:
                value=gods.get(key+suffix)
                if value:text+="\n== "+heading+" ==\n"+self.prose(value)+"\n"
        elif group=='unrand':
            artifact=self.artifact_for(row)
            base=artifact.get('OBJ','').split('/')[-1]
            base_name=next((name for name,data in self.weapons.items() if data.get('enum')==base),None)
            if not base_name:base_name=next((name for name,data in self.armour.items() if data.get('enum')==base),None)
            values=[('Тип предмета',self.illustrated_link(self.keys[('items',base_name)]))] if base_name and ('items',base_name) in self.keys else []
            if artifact.get('PLUS') and re.fullmatch(r'[+-]?\d+',artifact['PLUS']):values.append(('Зачарование',artifact['PLUS']))
            if values:text+='\n== Базовые параметры ==\n'+self.table(values)
        elif group == "egos":
            short=re.search(r'\(([^)]+)\)',key)
            label=self.annotations.get(short[1].casefold()) if short else None
            if label:text+='\n== Обозначение в игре ==\n'+self.prose(label)+'\n'
        if row.get("powers"):
            text+="\n== Особые свойства ==\n"+"\n".join("* '''"+v["label"]+".''' "+self.prose(v["text"]) for v in row["powers"])+"\n"
        return text

    def render(self):
        pages={}
        counts={g:0 for g in GROUPS}
        for group,entries in self.notes.items():
            for key in entries:
                if (group,key) not in self.keys:
                    raise ValueError(('Advice has no matching game entry',group,key))
        for title,row in self.rows.items():
            group=row["group"];key=row["entries"][0]["key"];counts[group]+=1
            sprite=row.get("sprite")
            if sprite:self.sprite_map[title]=sprite
            image='<div class="dc-article-sprite">[[Файл:'+sprite+'|32px|link=|'+row["name"]+']]</div>' if sprite else ""
            prefix=self.breadcrumbs(GROUPS[group][0],row['name'])+'<div class="dc-article-top">'+image+'<div><div class="dc-kicker">'+GROUPS[group][0]+' · 0.35-a0</div><div class="dc-native">'+row["name"]+'</div><div class="dc-meta">Английское название: '+html.escape(re.sub(r" (spell|ability|card|mutation|status)$","",key))+'</div></div></div>\n'
            body=''
            seen=set()
            for entry in row["entries"]:
                value=self.prose(entry["text"])
                if not value.strip():raise ValueError(('Empty wiki description',group,entry['key']))
                if value not in seen:
                    heading=VARIANT_HEADINGS.get(entry['key']) if len(row['entries'])>1 else None
                    if heading:body+='\n== '+heading+' ==\n'
                    body+="\n"+value+"\n";seen.add(value)
            body+=self.metadata(row)
            advice=self.notes.get(group,{}).get(key)
            if advice:
                if isinstance(advice,str):advice={"text":advice}
                body+="\n== Советы по игре ==\n"+advice['text']+"\n"
                body+=self.community_sources(advice.get('sources',[]))
            body=prefix+self.article_layout(body)+self.article_navigation(row,GROUPS[group][0])+self.source(row)
            body+="\n[[Категория:"+GROUPS[group][0]+"]]"
            pages[title]=dict(text=body,key=group+":"+key,kind="article")
        for group,(category,_) in GROUPS.items():
            content=self.directory(group,category)
            pages[category]=dict(text=content,key="index:"+group,kind="index")
            pages["Категория:"+category]=dict(text="См. полный справочник: [["+category+"]].",key="category:"+group,kind="category")
        self.add_site(pages,counts)
        for title,targets in DISAMBIGUATIONS.items():
            pages[title]=dict(text="Так может называться несколько разных эффектов. Выберите нужный контекст:\n\n"+"\n".join('* [['+v+']]' for v in targets),key='disambiguation:'+title,kind='guide')
        for row in self.rows.values():
            if row['group']=='egos':
                base=row['entries'][0]['key'].split(' (',1)[0]
                if base in EGO_OLD_NAMES:
                    old=EGO_OLD_NAMES[base]+row['name'][len(EGO_NAMES[base]):]
                    if old not in pages:pages[old]=dict(text='#REDIRECT [['+row['title']+']]',key='redirect:'+old,kind='redirect')
        # English lookup redirects make familiar upstream names searchable.
        for title,row in self.rows.items():
            for entry in row["entries"]:
                en=re.sub(r" (spell|ability|card|mutation|status)$","",entry["key"])
                en=cap(en)
                if en not in pages and not any(c in en for c in "[]{}|<>#"):
                    pages[en]=dict(text="#REDIRECT [["+title+"]]",key="redirect:"+en,kind="redirect")
        for name,source in self.assets.items():
            body="Игровой спрайт Dungeon Crawl Stone Soup.\n\nИсточник: [https://github.com/Mr-Vivor/DCSS-RU/blob/ru-bootstrap/"+source["path"]+" исходный файл].\n\nАвторы — участники проекта DCSS. Условия использования: [https://github.com/crawl/crawl/blob/master/LICENSE лицензия проекта]; большинство тайлов опубликованы как CC0, отдельные старые ресурсы могут иметь другие совместимые условия.\n[[Категория:Спрайты игры]]"
            pages["Файл:"+name]=dict(text=body,key="file:"+name,kind="file")
        revision=self.revision or subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
        payload=dict(schema=1,version="0.35-a0",source_revision=revision,pages=pages,assets=self.assets,counts=counts)
        extracts={}
        for title,row in self.rows.items():
            plain=self.prose(row['entries'][0]['text']).split('\n\n',1)[0]
            plain=re.sub(r'<[^>]*>','',plain)
            plain=re.sub(r'\[\[([^\]|]+\|)?([^\]]+)\]\]',lambda m:m[2],plain)
            plain=re.sub(r'\s+',' ',plain).strip()
            extracts[title]=plain[:300]+('…' if len(plain)>300 else '')
        for title,row in pages.items():
            if row['kind']=='guide' and title not in extracts:
                plain=re.sub(r'<[^>]*>|__\w+__|^=+.*?=+\s*$', '', row['text'], flags=re.M)
                plain=re.sub(r'\[\[([^\]|]+\|)?([^\]]+)\]\]',lambda m:m[2],plain)
                plain=re.sub(r'\[https?://[^\s\]]+\s+([^\]]+)\]',lambda m:m[1],plain)
                plain=re.sub(r"'{2,}", '', plain)
                plain=re.sub(r'\s+',' ',plain).strip()
                extracts[title]=plain[:300]+('…' if len(plain)>300 else '')
        for title,row in pages.items():
            if row['kind']=='redirect':
                match=re.search(r'\[\[([^\]]+)\]\]',row['text'])
                if match and match[1] in extracts:extracts[title]=extracts[match[1]]
        (self.output/'search-extracts.json').write_text(json.dumps(extracts,ensure_ascii=False)+'\n',encoding='utf8')
        (self.output/"pages.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        report=dict(article_counts=counts,pages=len(pages),sprites=len(self.assets),unresolved_references=sorted(self.unresolved),sprite_coverage={g:sum(bool(r.get("sprite")) for r in self.rows.values() if r["group"]==g) for g in GROUPS},
            editorial=dict(advice_counts={g:len(entries) for g,entries in self.notes.items()},
                branches=len(load(ROOT/'wiki/site/branches.json')),mechanics=len(load(ROOT/'wiki/site/mechanics.json')),
                attributed_community_revisions=len(self.community)))
        (self.output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        shutil.copyfile(ROOT/"wiki/site/wiki-logo.svg",self.output/"wiki-logo.svg")
        shutil.copyfile(ROOT/"wiki/site/theme.css",self.output/"theme.css")
        shutil.copyfile(ROOT/'wiki/site/navigation.js',self.output/'navigation.js')
        fallback=ROOT/"crawl-ref/source/rltiles/gui/startup/stonesoup.png"
        shutil.copyfile(fallback,self.output/"favicon.png")
        print(json.dumps(report,ensure_ascii=False,indent=2))

    def community_sources(self, keys):
        sources=[]
        for key in keys:
            source=self.community_by_key.get(key.casefold())
            if not source:raise ValueError(('Missing community attribution',key))
            sources.append("["+source["url"]+" "+source["title"]+"]")
        if not sources:return ''
        return '\n<div class="dc-source">Перевод и адаптация материалов CrawlWiki: '+" · ".join(sources)+". Авторы исходных страниц перечислены в их истории. Материал адаптирован для 0.35-a0; выбор тактики зависит от персонажа.</div>"

    def add_branches(self,pages):
        records=load(ROOT/'wiki/site/branches.json')
        stats=branch_data()
        names={key:row.get('title',self.terms['branches'].get(row['label'],self.static['dungeon'].get(row['label']))) for key,row in records.items()}
        if not all(names.values()):raise ValueError('Missing shared branch name')
        for key,row in records.items():
            title=names[key];data=stats[key]
            text=row['text']
            values=[('Название в игре',self.static['dungeon'].get(row['label'],title)),('Обозначение этажа',row['abbrev']),('Глубина',self.branch_depth(key))]
            parent_key=self.branch_parent(key)
            entrance=self.branch_entrance(key)
            if parent_key in names:entrance=self.branch_link(parent_key)+' · '+entrance
            values.append(('Вход',entrance))
            if row.get('reward'):values.append(('Главная цель',row['reward']))
            body=self.branch_header(key)+'\n'+text+'\n\n== Расположение и устройство ==\n'+self.table(values)
            body+='\nПараметры входа и длина ветви взяты из [https://github.com/Mr-Vivor/DCSS-RU/blob/ru-bootstrap/crawl-ref/source/branch-data.h текущего исходного кода]. Для порталов действуют особые правила входа; наличие записи в таблице не означает обычную лестницу в Подземелье.\n'
            body+=self.branch_navigation(key)+self.community_sources(row.get('sources',[]))
            body+='\nСм. также: [[Ветви подземелья]], [[Порталы]], [[Путь к Сфере]].\n[[Категория:Ветви подземелья]]'
            if title in pages:raise ValueError(('Branch page collision',title))
            pages[title]=dict(text=body,key='branch:'+key,kind='guide')
            for alias in row.get('aliases',[]):
                if alias!=title and alias not in pages:pages[alias]=dict(text='#REDIRECT [['+title+']]',key='redirect:'+alias,kind='redirect')
        world=load(ROOT/'wiki/site/world-guide.json')
        overview='__NOTOC__\n'+self.breadcrumbs('Ветви подземелья')+'<div class="dc-guide-lead">Куда ведёт каждая лестница: входы, глубина ветвей и руны нашей версии 0.35-a0.</div>\n== Схема подземелья ==\nВложенная ветвь открывается из родительской. Это схема связей, а не обязательный порядок прохождения. В каждой партии встречаются только две из четырёх рунических ветвей Логова.\n'+self.branch_tree()
        overview+='\n== Необязательные порталы ==\n'+self.portal_cards(PORTALS)
        overview+='\n== Испытания богов ==\n'+self.portal_cards(SPECIAL_WORLDS)
        overview+='\n'+world['text']+self.branch_navigation()+self.community_sources(world.get('sources',[]))+'\n[[Категория:Руководства]]'
        pages['Ветви подземелья']=dict(text=overview,key='guide:branches',kind='guide')
        pages['Категория:Ветви подземелья']=dict(text='Карта связей и полный список: [[Ветви подземелья]].',key='category:branches',kind='category')

    def add_site(self,pages,counts):
        self.add_branches(pages)
        weapon_guide="Базовый урон, точность и скорость — разные стороны оружия. Большое число урона само по себе не показывает, сколько ответных действий получит противник и насколько полезно свойство оружия.\n\n== Как выбирать ==\nСначала обеспечьте надёжный бой текущим оружием. Для замены сравнивайте реальную задержку с вашим навыком, свойства, зачарование, возможность носить щит и урон по ближайшим врагам. Не начинайте дорогое обучение ради редкого типа, если доступное оружие уже решает задачу.\n\nКороткие клинки особенно подходят для [[Удары исподтишка|ударов исподтишка]]. Топоры помогают против нескольких соседних целей, но не делают окружение безопасным. Древковое оружие позволяет атаковать через клетку. Дробящее оружие удобно против гидр, у которых режущие атаки могут вызывать рост голов. Посох и дальнее оружие требуют своих навыков; одно название «магический» не отменяет цену ближнего применения.\n\n== Базовые параметры типов ==\nЗначения ниже взяты из активной игры. Задержка указана до обучения и модификаторов: 1,0 — стандартное действие. При смене оружия проверяйте показанное игрой время атаки. Минимальная задержка, свойства и особые многократные удары требуют отдельной оценки: одна строка таблицы не является расчётом урона за ход.\n"
        weapon_guide+='\n{| class="wikitable"\n! Оружие !! Урон !! Бонус точности !! Базовая задержка\n'
        for key,data in self.weapons.items():
            title=self.keys.get(('items',key))
            if title:weapon_guide+='|-\n| [['+title+']] || '+str(data['damage'])+' || '+f"{data['accuracy']:+}"+' || '+f"{data['delay']/10:g}"+'\n'
        weapon_guide+='|}\n\n== После минимальной задержки ==\nДальнейший навык может улучшать атаку, но опыт нужно сравнивать с пользой здоровья, уклонения, щитов и вспомогательных средств. Целевое значение в меню навыков помогает вовремя пересмотреть распределение.\n\nСм. [[Скорость атаки]], [[Тяжесть доспехов и щитов]], [[Предметы]].\n[[Категория:Руководства]]'
        weapon_guide+=self.community_sources(['Weapon','Attack speed','Weapon speed'])
        pages['Оружие и выбор навыка']=dict(text=weapon_guide,key='guide:weapon-comparison',kind='guide')
        guides=load(ROOT/"wiki/site/guides.json")
        for title,row in load(ROOT/'wiki/site/mechanics.json').items():
            if title in guides:raise ValueError(('Duplicate guide',title))
            guides[title]=row
        for title,row in guides.items():
            text=row["text"]
            if title=='Порталы':text=self.portal_cards(PORTALS)+text+self.branch_navigation()
            text+=self.community_sources(row.get('sources',[]))
            if title in pages:raise ValueError(('Guide would replace a catalogue page',title))
            pages[title]=dict(text=text,key="guide:"+title,kind="guide")
            for alias in row.get('aliases',[]):
                if alias not in pages:pages[alias]=dict(text='#REDIRECT [['+title+']]',key='redirect:'+alias,kind='redirect')
        for title,row in pages.items():
            if row['kind']=='guide' and 'dc-breadcrumbs' not in row['text']:
                row['text']=self.breadcrumbs('Механики игры',title)+row['text']+self.guide_navigation(title,pages)
        self.topic_portals(pages)
        provenance="Конкретные редакции CrawlWiki, использованные при подготовке русского справочника. Численные игровые данные сверяются отдельно с русским форком.\n\n"+"\n".join("* ["+v["url"]+" "+k+"] — "+v["timestamp"][:10] for k,v in sorted(self.community.items()))+"\n[[Категория:Проект]]"
        pages["Dungeon Crawl:Источники"]=dict(text=provenance,key="community-provenance",kind="project")
        pages["MediaWiki:Common.css"]=dict(text=(ROOT/"wiki/site/theme.css").read_text(encoding="utf8"),key="theme",kind="css")
        pages['MediaWiki:Common.js']=dict(text='/* Directory filtering is served from /resources/dcss/navigation.js. */',key='wiki-navigation-js',kind='javascript')
        for title,text in {
            'Руководства':'Практические материалы: [[Первые шаги]], [[Механики игры]], [[Ветви подземелья]], [[Магия]], [[Снаряжение и расходники]].',
            'Проект':'О русском справочнике: [[Dungeon Crawl:О вики]], [[Dungeon Crawl:Источники]], [[Версия игры]], [[Справка:Редактирование]].',
            'Спрайты игры':'Оригинальные игровые изображения русского форка. Источник и условия использования указаны на странице каждого файла.'
        }.items():pages['Категория:'+title]=dict(text=text,key='category:'+title,kind='category')
        sidebar="* Навигация\n** mainpage|Заглавная страница\n** https://dungeoncrawl.ru/|Играть в браузере\n** Первые шаги|Первый заход\n** Управление|Клавиши и команды\n** Механики игры|Механики игры\n* Персонаж\n** Виды|Виды\n** Предыстории|Предыстории\n** Навыки|Навыки\n** Боги|Боги\n** Заклинания|Заклинания\n** Способности|Способности\n* Подземелье\n** Ветви подземелья|Ветви и маршрут\n** Порталы|Порталы\n** Существа|Существа\n** Предметы|Предметы\n** Артефакты|Артефакты\n** Местность|Местность\n** Состояния|Состояния\n** Мутации|Мутации\n** Карты|Карты\n* Сообщество\n** Версия игры|Версия игры\n** Dungeon Crawl:О вики|О вики и источники\n** Справка:Редактирование|Помочь с вики\n** recentchanges-url|Свежие правки\n** randompage-url|Случайная статья\n** https://github.com/Mr-Vivor/DCSS-RU|GitHub проекта\n* SEARCH\n* TOOLBOX\n* LANGUAGES"
        pages["MediaWiki:Sidebar"]=dict(text=sidebar,key="sidebar",kind="system")
        pages['MediaWiki:Sidebar']['text']=sidebar.replace('* Персонаж','** Справочник|Все разделы\n* Персонаж')
        pages["MediaWiki:Mainpage"]=dict(text="Заглавная страница",key="mainpage-name",kind="message")
        for key,value in {"Aboutpage":"Dungeon Crawl:О вики","Privacypage":"Dungeon Crawl:Конфиденциальность","Disclaimerpage":"Версия игры"}.items():
            pages["MediaWiki:"+key]=dict(text=value,key="interface:"+key,kind="message")
        main=self.main_page(counts)
        pages["Заглавная страница"]=dict(text=main,key="mainpage",kind="main")

    def grid(self,group):
        items=[]
        for row in self.rows.values():
            if row["group"]!=group:continue
            image="[[Файл:"+row["sprite"]+"|32px|link="+row["title"]+"|"+row["name"]+"]]" if row.get("sprite") else ""
            items.append('<div class="dc-sprite-card">'+image+'[['+row["title"]+'|'+row["name"]+']]</div>')
        return '<div class="dc-sprite-grid">'+"\n".join(items)+"</div>"

    def main_page(self,counts):
        art_source=ROOT/'crawl-ref/source/dat/tiles/title_white_noise_entering_the_dungeon.png'
        art_name='Dcss-art-entering-the-dungeon.png'
        shutil.copyfile(art_source,self.output/'sprites'/art_name)
        self.assets[art_name]=dict(path=art_source.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(art_source.read_bytes()).hexdigest())
        def panel(title,body,kind=""):
            return '<div class="dc-panel '+kind+'"><h2>'+title+'</h2><div class="dc-panel-body">'+body+'</div></div>'
        links=lambda entries:'<div class="dc-links dc-home-links">'+"\n".join('<div class="dc-home-link">'+self.illustrated_link(a,b)+'</div>' for a,b in entries)+"</div>"
        start=panel("Первый спуск",links([("Первые шаги","С чего начать"),("Управление","Клавиши и команды"),("Первый персонаж","Кого выбрать"),("Как выжить","Как выбраться из опасности"),("Развитие персонажа","Опыт и обучение"),("Выбор бога","Религия и божественные силы")]))
        reference=panel("Под рукой",links([("Существа","Существа"),("Заклинания","Заклинания"),("Предметы","Предметы и оружие"),("Артефакты","Уникальные артефакты"),("Навыки","Навыки"),("Свойства снаряжения","Свойства снаряжения"),("Состояния","Состояния и эффекты"),("Мутации","Мутации")]),"dc-violet")
        branch_preview='<div class="dc-main-branches">'+''.join('<div class="dc-home-branch'+(' dc-home-branch-goal' if k=='ZOT' else '')+'">'+self.branch_link(k)+'</div>' for k in ('DUNGEON','TEMPLE','LAIR','ORC','VAULTS','DEPTHS','ZOT'))+'</div>'
        world_map='<div class="dc-home-map">[[Ветви подземелья|Карта ветвей подземелья →]]<span>Все входы, глубины и руны на одной схеме</span></div>'
        world=panel("От лестницы до Сферы",world_map+branch_preview+'<div class="dc-home-guides">'+links([("Порталы","Временные порталы"),("Путь к Сфере","Руны и победа"),("Механики игры","Бой и механики"),("Снаряжение и расходники","Что брать в бой"),("Местность","Объекты подземелья"),("Магия","Как пользоваться магией"),("Защита и сопротивления","Броня, уклонение и Воля"),("Шум и разведка","Что слышат противники")])+'</div>',"dc-gold")
        god_links=[]
        for row in self.rows.values():
            if row['group']!='gods':continue
            if not row.get('sprite'):raise ValueError(('Missing altar sprite',row['name']))
            god_links.append('<div class="dc-god-card">[[Файл:'+row['sprite']+'|20px|link='+row['title']+'|Алтарь: '+row['name']+']] [['+row['title']+'|'+row['name']+']]</div>')
        gods=panel("Боги",'<div class="dc-links dc-gods">'+"\n".join(god_links)+'</div>',"dc-gold")
        intro='<div class="dc-intro dc-wiki-hero"><div class="dc-wiki-hero-copy"><div class="dc-kicker">Dungeon Crawl Stone Soup</div><div class="dc-title" role="heading" aria-level="1">Знания для<br>следующего спуска.</div><p>Русская вики <span class="dc-version">0.35-a0</span></p><div class="dc-muted">От первого героя до Сферы Зота. Механики, тактика и названия — как в русской игре.</div></div><div class="dc-wiki-hero-art">[[Файл:'+art_name+'|320px|link=|Воин у входа в Подземелье. Иллюстрация White Noise.]]</div></div>'
        notice='<div class="dc-main-note">Наш сервер использует ветку разработки <b>0.35-a0</b>. Статьи сообщества адаптируются под неё; подробности — [[Версия игры|на странице версии]]. [https://dungeoncrawl.ru/ Играть в браузере]</div>'
        footer=panel("Сообщество и редактура","Материалы основаны на [[Dungeon Crawl:О вики|CrawlWiki и исходниках игры]]. Правки доступны приглашённым редакторам. Нашли неточность? Проверьте название и версию, затем оставьте замечание на странице обсуждения или в [https://github.com/Mr-Vivor/DCSS-RU/issues задачах проекта].\n\n[[Справка:Редактирование|Как устроены страницы и как помочь]] · [[Служебная:Статистика|Статистика вики]]")
        summary='<div class="dc-quickstats"><span>27 видов</span><span>28 предысторий</span><span>26 богов</span><span>'+str(counts["spells"])+" описаний заклинаний</span></div>"
        toolbar='<div class="dc-main-toolbar">'+summary+'<div class="dc-directory-shortcut">[[Справочник|Все разделы вики →]]</div></div>'
        return "__NOTOC__\n"+intro+toolbar+'<div class="dc-home-priority">'+start+reference+'</div>'+notice+'<div class="dc-layout"><div>'+world+gods+'</div><div>'+panel("Виды",self.grid("species"),"dc-green")+panel("Предыстории",self.grid("background"),"dc-violet")+'</div></div>'+footer+'<div class="dc-art-credit">Иллюстрация на главной: White Noise, DCSS.</div>'


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--community",type=Path)
    parser.add_argument("--revision",help="Source commit when building from a git archive")
    args=parser.parse_args()
    Builder(args.output,args.community,args.revision).collect().render()
