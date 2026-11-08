"""Small, read-only extractors for published item and spellbook parameters."""
import re


def equipment_data(root):
    text=(root/'crawl-ref/source/item-prop.cc').read_text(encoding='utf8')
    weapons={}
    pattern=r'\{\s*(WPN_\w+),\s*"([^"\n]+)",\s*(\d+),\s*(-?\d+),\s*(\d+),\s*(SK_\w+)'
    for match in re.finditer(pattern,text):
        weapons[match[2]]=dict(enum=match[1],damage=int(match[3]),accuracy=int(match[4]),delay=int(match[5]),skill=match[6])
    armour={}
    for match in re.finditer(r'\{\s*(ARM_\w+),\s*"([^"\n]+)",\s*(\d+),\s*(-?\d+),\s*\d+,\s*(SLOT_\w+)',text):
        armour[match[2]]=dict(enum=match[1],ac=int(match[3]),encumbrance=abs(int(match[4]))/10,slot=match[5])
    for match in re.finditer(r'DRAGON_ARMOUR\(\w+,\s*"([^"\n]+)",\s*(\d+),\s*(-?\d+),',text):
        armour[match[1]+' dragon scales']=dict(ac=int(match[2]),encumbrance=abs(int(match[3]))/10,slot='SLOT_BODY_ARMOUR')
    missiles={}
    for match in re.finditer(r'\{\s*MI_\w+,\s*"([^"\n]+)",\s*(\d+),',text):
        missiles[match[1]]=dict(damage=int(match[2]))
    if not all(k in weapons for k in ['dagger','quick blade','hand cannon','partisan']):
        raise ValueError('Weapon table changed; review the wiki extractor')
    if not all(k in armour for k in ['plate armour','buckler','fire dragon scales']):
        raise ValueError('Armour table changed; review the wiki extractor')
    return weapons,armour,missiles


def spellbook_data(root):
    text=(root/'crawl-ref/source/book-data.h').read_text(encoding='utf8')
    result={}
    for match in re.finditer(r'\{\s*//\s*([^\n]+)\n(.*?)\n\}',text,re.S):
        title=match[1].strip().casefold()
        spells=re.findall(r'\bSPELL_[A-Z0-9_]+\b',re.sub(r'//[^\n]*','',match[2]))
        if title in result and result[title]!=spells:
            raise ValueError(('Conflicting spellbook templates',title))
        result[title]=spells
    if 'book of minor magic' not in result:raise ValueError('Spellbook table changed')
    return result


def monster_spellbook_data(root):
    text=(root/'crawl-ref/source/mon-spell.h').read_text(encoding='utf8')
    result={}
    for match in re.finditer(r'\{\s*MST_([A-Z0-9_]+),\s*\{(.*?)\n\s*\}\s*\n\s*\}',text,re.S):
        result[match[1].casefold()]=list(dict.fromkeys(re.findall(r'\bSPELL_[A-Z0-9_]+\b',match[2])))
    if 'ancient_lich' not in result or 'SPELL_PETRIFY' not in result['ancient_lich']:
        raise ValueError('Monster spellbook table changed; review the wiki extractor')
    return result
