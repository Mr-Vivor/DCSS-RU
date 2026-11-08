"""Shared, sprite-based navigation for the generated MediaWiki reference."""
import html
import json
import re


PORTALS = ('SEWER','OSSUARY','BAILEY','GULCH','GAUNTLET','ICE_CAVE','VOLCANO',
           'BAZAAR','TROVE','WIZLAB','DESOLATION')
SPECIAL_WORLDS = ('NECROPOLIS','CRUCIBLE','ARENA')
TREE_ORDER = ('DUNGEON','TEMPLE','LAIR','SWAMP','SHOALS','SNAKE','SPIDER','SLIME',
              'ORC','ELF','VAULTS','CRYPT','TOMB','ABYSS','DEPTHS','ZOT',
              'VESTIBULE','DIS','GEHENNA','COCYTUS','TARTARUS','PANDEMONIUM','ZIGGURAT')
ENTRY_TILES = {'DUNGEON':'EXIT_DUNGEON','ZOT':'ENTER_ZOT_OPEN',
               'VESTIBULE':'ENTER_HELL','WIZLAB':'PORTAL_WIZARD_LAB',
               'CRUCIBLE':'EXIT_CRUCIBLE','ARENA':'ALTAR_OKAWARU'}
RUNE_TYPES = {key:key.lower() for key in ('SWAMP','SHOALS','SNAKE','SPIDER','SLIME',
              'VAULTS','TOMB','DIS','GEHENNA','COCYTUS','TARTARUS')}
RUNE_TYPES['ABYSS'] = 'abyss'
RUNE_TYPES['PANDEMONIUM'] = ('demonic_1','mnoleg','lom_lobon','cerebov','gloorx_vloq')
ITEM_LABELS = {'weapons':'Оружие','armour':'Доспехи и щиты','missiles':'Метательные предметы',
    'potions':'Зелья','scrolls':'Свитки','wands':'Жезлы','rings':'Кольца','amulets':'Амулеты',
    'staves':'Магические посохи','books':'Книги','talismans':'Талисманы и безделушки',
    'evokers':'Устройства','other':'Прочие предметы'}
GROUP_GUIDES = {
    'species':('Первый персонаж','Развитие персонажа','Навыки'),
    'background':('Первый персонаж','Навыки','Снаряжение и расходники'),
    'gods':('Выбор бога','Благочестие и божественный гнев','Способности'),
    'skills':('Развитие персонажа','Магия','Оружие и выбор навыка'),
    'spells':('Магия','Навыки','Предметы'),
    'monsters':('Механики игры','Защита и сопротивления','Как выжить'),
    'items':('Снаряжение и расходники','Оружие и выбор навыка','Артефакты'),
    'unrand':('Предметы','Свойства снаряжения','Оружие и выбор навыка'),
    'ability':('Боги','Оборотничество','Магия'),
    'status':('Сопротивления урону','Как выжить','Состояния'),
    'mutations':('Виды','Оборотничество','Состояния'),
    'features':('Ветви подземелья','Лестницы и выманивание','Шум и разведка'),
    'cards':('Немелекс Зобех','Способности','Как выжить'),
    'egos':('Предметы','Защита и сопротивления','Оружие и выбор навыка')}


class WikiNavigation:
    def item_sprite(self, key):
        enum=None
        if key in self.weapons:enum=self.weapons[key].get('enum')
        elif key in self.armour:enum=self.armour[key].get('enum')
        elif key in self.missiles:enum='MI_'+key.upper().replace(' ','_')
        prefixes={'potion of ':'POT_','scroll of ':'SCR_','wand of ':'WAND_',
                  'ring of ':'RING_','amulet of ':'AMU_','staff of ':'STAFF_'}
        for prefix,value in prefixes.items():
            if key.startswith(prefix):enum=value+key[len(prefix):].upper().replace(' ','_')
        aliases={'staff of alchemy':'STAFF_POISON','pair of boots':'ARM_BOOTS',
            'pair of gloves':'ARM_GLOVES','orb of zot':'ORB','rune of zot':'MISC_RUNE_OF_ZOT',
            'figurine of a ziggurat':'MISC_ZIGGURAT',"gell's gravitambourine":'MISC_TAMBOURINE',
            'quad damage':'MISC_QUAD_DAMAGE','shop voucher':'MISC_SHOP_VOUCHER',
            'serpent talisman':'TALISMAN_SNAKE','granite talisman':'TALISMAN_STATUE',
            'dragon-coil talisman':'TALISMAN_DRAGON','lupine talisman':'TALISMAN_WEREWOLF',
            'riddle talisman':'TALISMAN_SPHINX','sanguine talisman':'TALISMAN_VAMPIRE',
            'wellspring talisman':'TALISMAN_AQUA','talisman of death':'TALISMAN_DEATH'}
        aliases.update({'amulet of chemistry':'AMU_ALCHEMY','amulet of magic regeneration':'AMU_MANA_REGENERATION',
            'amulet of the acrobat':'AMU_ACROBAT','potion of lignification':'POT_LIGNIFY',
            'scroll of summoning':'SCR_UNHOLY_CREATION',
            'eudemon blade':'WPN_BLESSED_BLADE','the unrestrained analects':'BOOK',
            'gold piece':'GOLD01','gem':'GEM_GENERIC','detected item':'UNSEEN_ITEM'})
        if key in aliases:enum=aliases[key]
        if key.endswith(' dragon scales'):enum='ARM_'+key.removesuffix(' scales').upper().replace(' ','_')+'_ARMOUR'
        if key.endswith(' talisman') and key not in aliases:enum='TALISMAN_'+key.removesuffix(' talisman').upper().replace(' ','_')
        if key.endswith(' bauble'):enum='BAUBLE_'+key.removesuffix(' bauble').upper()
        if self.item_group(key)=='evokers' and not enum:enum='MISC_'+key.upper().replace(' ','_')
        if self.item_group(key)=='books':enum='BOOK_MANUAL' if key=='manual' else 'BOOK'
        if key.endswith(' gem'):enum=self.gem_enums.get(key)
        path=self.item_tiles.get(enum)
        if key.startswith('deck of '):path=path or self.find_sprite('deck_'+key.removeprefix('deck of '),('item',))
        return path

    def prepare_navigation(self, root, branch_stats):
        self.branch_records=json.loads((root/'wiki/site/branches.json').read_text(encoding='utf8'))
        self.branch_stats=branch_stats
        self.branch_names={k:r.get('title',self.terms['branches'].get(r['label'],self.static['dungeon'].get(r['label']))) for k,r in self.branch_records.items()}
        self.branch_sprites={}
        for key,row in self.branch_records.items():
            suffix=ENTRY_TILES.get(key,row.get('tile','ENTER_'+key))
            path=self.feature_tiles.get('DNGN_'+suffix) or self.feature_tiles.get('DNGN_PORTAL_'+key)
            sprite=self.sprite(path)
            if not sprite:raise ValueError(('Missing branch/portal illustration',key,suffix))
            self.branch_sprites[key]=sprite
        self.rune_sprites={}
        for key,types in RUNE_TYPES.items():
            if isinstance(types,str):types=(types,)
            self.rune_sprites[key]=[self.sprite(self.find_sprite('rune_'+v,('runes',))) for v in types]
            if not all(self.rune_sprites[key]):raise ValueError(('Missing rune illustration',key))
        self.orb_sprite=self.sprite(self.find_sprite('orb_of_zot1',('item',)))
        self.sorted_groups={group:sorted((r for r in self.rows.values() if r['group']==group),key=lambda r:r['title'].casefold()) for group in self.reference}
        for group in ('species','background','gods'):
            self.sorted_groups[group]=sorted((r for r in self.rows.values() if r['group']==group),key=lambda r:r['title'].casefold())

    @staticmethod
    def picture(sprite, title, size=24, alt=None):
        return '[[Файл:'+sprite+'|'+str(size)+'px|link='+title+'|'+(alt or title)+']]' if sprite else ''

    def illustrated_link(self, title, label=None, size=20):
        row=self.rows.get(title)
        sprite=row.get('sprite') if row else None
        if title in self.branch_names.values():
            key=next(k for k,v in self.branch_names.items() if v==title)
            sprite=self.branch_sprites[key]
        link='[['+title+('|' + label if label else '')+']]'
        return '<span class="dc-inline-link">'+self.picture(sprite,title,size)+' '+link+'</span>' if sprite else link

    @staticmethod
    def breadcrumbs(section, title=None):
        tail=' <span aria-hidden="true">›</span> [['+section+']]' if section!='Заглавная страница' else ''
        if title:tail+=' <span aria-hidden="true">›</span> <span>'+html.escape(title)+'</span>'
        return '<div class="dc-breadcrumbs" role="navigation" aria-label="Путь по вики">[[Заглавная страница|Вики]]'+tail+'</div>\n'

    def item_group(self, key):
        prefixes={'potion of ':'potions','scroll of ':'scrolls','wand of ':'wands',
                  'ring of ':'rings','amulet of ':'amulets','staff of ':'staves'}
        for prefix,group in prefixes.items():
            if key.startswith(prefix):return group
        if key in self.weapons:return 'weapons'
        if key in self.armour:return 'armour'
        if key in self.missiles:return 'missiles'
        if key in self.books or key.startswith('book of ') or key in ('manual','grand grimoire','necronomicon'):return 'books'
        if 'talisman' in key or key.endswith(' bauble'):return 'talismans'
        if key in ('box of beasts','condenser vane','figurine of a ziggurat',"gell's gravitambourine",'horn of Geryon','lightning rod','phantom mirror','phial of floods','sack of spiders','tin of tremorstones'):return 'evokers'
        return 'other'

    def icon_entry(self, row, detail=''):
        title=row['title'];key=row['entries'][0]['key']
        icon=self.picture(row.get('sprite'),title,24,row['name']) or '<span class="dc-icon-empty" aria-hidden="true"></span>'
        search=html.escape(title+' '+key,quote=True)
        return '<div class="dc-icon-entry" data-dc-search="'+search+'">'+icon+' <span class="dc-entry-text">[['+title+']]'+('<small>'+detail+'</small>' if detail else '')+'</span></div>'

    def directory(self, group, category):
        rows=self.sorted_groups[group]
        sections=[]
        intro='Названия совпадают с русской игрой. Можно искать по русскому или английскому названию.'
        if group=='items':
            for kind,label in ITEM_LABELS.items():
                chosen=[r for r in rows if self.item_group(r['entries'][0]['key'])==kind]
                if chosen:sections.append((kind,label,chosen))
        elif group=='spells':
            learned={enum for values in self.books.values() for enum in values}
            for level in range(1,10):
                chosen=[r for r in rows if self.spells.get(r['entries'][0]['key'].removesuffix(' spell').casefold(),{}).get('enum') in learned and self.spells[r['entries'][0]['key'].removesuffix(' spell').casefold()]['level']==str(level)]
                if chosen:sections.append(('level-'+str(level),'Уровень '+str(level),chosen))
            chosen=[r for r in rows if self.spells.get(r['entries'][0]['key'].removesuffix(' spell').casefold(),{}).get('enum') not in learned]
            sections.append(('other','Силы существ и другие источники',chosen))
            intro+=' Сначала перечислены заклинания из книг нашей версии по уровню, затем — остальные силы. Наличие статьи не означает возможность обычного заучивания.'
        elif group=='monsters':
            uniques=[r for r in rows if 'unique' in self.monsters.get(r['entries'][0]['key'].casefold(),{}).get('flags',[])]
            if uniques:sections.append(('unique','Уникальные противники',uniques))
            ordinary=[r for r in rows if r not in uniques]
            sections.append(('others','Все остальные существа',ordinary))
        else:sections=[('all',category,rows)]
        jump='<div class="dc-section-jumps">'+' '.join('[[#dc-'+group+'-'+key+'|'+label+']]' for key,label,chosen in sections if chosen)+'</div>' if len(sections)>1 else ''
        text='__NOTOC__\n'+self.breadcrumbs(category)+'<div class="dc-directory-lead">'+intro+'</div>\n'+jump+'\n<div class="dc-directory" data-dc-directory="'+group+'"><div class="dc-directory-tools"></div>\n'
        for key,label,chosen in sections:
            if not chosen:continue
            text+='<div class="dc-directory-section"><h2 id="dc-'+group+'-'+key+'">'+label+' <span class="dc-section-count">'+str(len(chosen))+'</span></h2><div class="dc-icon-index">\n'
            for row in chosen:
                detail=''
                if group=='spells':
                    data=self.spells.get(row['entries'][0]['key'].removesuffix(' spell').casefold(),{})
                    detail=' · '.join(self.terms['skill'][self.skill_key(s)] for s in data.get('schools',[]) if self.skill_key(s) in self.terms['skill'])
                text+=self.icon_entry(row,detail)+'\n'
            text+='</div></div>\n'
        return text+'</div>\n'

    def article_navigation(self, row, category):
        group=row['group'];rows=self.sorted_groups[group]
        if group=='items':
            kind=self.item_group(row['entries'][0]['key'])
            rows=[r for r in rows if self.item_group(r['entries'][0]['key'])==kind]
        index=rows.index(row)
        prev=rows[index-1] if index else None;next_row=rows[index+1] if index+1<len(rows) else None
        neighbors='<div class="dc-neighbors">'
        neighbors+='<span>'+('← '+self.illustrated_link(prev['title']) if prev else '')+'</span>'
        neighbors+='<span>[['+category+'|Весь раздел]]</span>'
        neighbors+='<span>'+((self.illustrated_link(next_row['title'])+' →') if next_row else '')+'</span></div>'
        guides=GROUP_GUIDES.get(group,())
        related='<div class="dc-nav-related"><b>По теме</b> '+' · '.join('[['+t+']]' for t in guides)+'</div>'
        family=''
        if group in ('species','background','gods','skills') or group=='items' and len(rows)<=35:
            family='<div class="dc-nav-family">'+' '.join('<span class="dc-nav-current">'+self.picture(r.get('sprite'),r['title'],20)+' '+r['name']+'</span>' if r is row else self.illustrated_link(r['title']) for r in rows)+'</div>'
        return '\n<div class="dc-navbox" role="navigation" aria-label="'+category+'"><div class="dc-navbox-title">[['+category+']]</div>'+family+related+neighbors+'</div>\n'

    def branch_parent(self, key):
        # Hell and Pan are portals placed in Depths vaults; the C++ table has
        # no ordinary parent. The guaranteed Abyss entry moved to D:13–15.
        return {'ABYSS':'DUNGEON','VESTIBULE':'DEPTHS','PANDEMONIUM':'DEPTHS'}.get(key,self.branch_stats[key]['parent'])

    def branch_depth(self, key):
        if key=='PANDEMONIUM':return 'множество отдельных этажей'
        if key=='ABYSS':return '7 глубин с меняющейся местностью'
        value=self.branch_stats[key]['levels']
        suffix='этаж' if value%10==1 and value%100!=11 else 'этажа' if value%10 in (2,3,4) and value%100 not in (12,13,14) else 'этажей'
        return str(value)+' '+suffix

    def branch_entrance(self, key):
        if key=='DUNGEON':return 'начало партии; Проходчик — D:5'
        if key=='ABYSS':return 'D:13–15; также изгнание и другие входы'
        if key in ('VESTIBULE','PANDEMONIUM'):return 'порталы в Глубинах'
        if key=='NECROPOLIS':return 'испытание Кикубаакудги'
        if key=='CRUCIBLE':return 'испытание Махлеба'
        if key=='ARENA':return 'испытание Окавару'
        parent=self.branch_parent(key);data=self.branch_stats[key]
        if parent in self.branch_records and data['first']>=0:
            code=self.branch_records[parent]['abbrev']+':'+str(data['first'])
            if data['first']!=data['last']:code+='–'+str(data['last'])
            return code
        return 'необязательный портал; условия см. в статье'

    def branch_link(self, key, size=24, current=None):
        title=self.branch_names[key]
        label='<strong>'+title+'</strong>' if current==key else '[['+title+']]'
        return '<span class="dc-branch-link">'+self.picture(self.branch_sprites[key],title,size)+' '+label+'</span>'

    def branch_reward(self, key):
        if key=='ZOT':return self.picture(self.orb_sprite,'Путь к Сфере',24,'Сфера Зота')+' <span>Сфера Зота · нужны 3 руны</span>'
        sprites=self.rune_sprites.get(key,[])
        if not sprites:return ''
        return ''.join(self.picture(s,'Путь к Сфере',24,'Руна: '+self.branch_names[key]) for s in sprites)+' <span>'+('5 рун' if key=='PANDEMONIUM' else '1 руна')+'</span>'

    def branch_tree(self):
        def node(key):
            alternatives={'SWAMP':'или Мелководья','SHOALS':'или Болото','SNAKE':'или Паучье гнездо','SPIDER':'или Змеиная яма'}
            detail=self.branch_entrance(key)+' · '+self.branch_depth(key)
            if key in alternatives:detail+=' · '+alternatives[key]
            reward=self.branch_reward(key)
            line='<li><div class="dc-branch-node">'+self.branch_link(key,32)+'<span class="dc-branch-facts">'+detail+'</span>'
            if reward:line+='<span class="dc-branch-reward">'+reward+'</span>'
            line+='</div>'
            children=[k for k in TREE_ORDER if k!=key and self.branch_parent(k)==key]
            if children:line+='<ul>'+''.join(node(k) for k in children)+'</ul>'
            return line+'</li>'
        return '<div class="dc-branch-map"><ul class="dc-branch-tree">'+node('DUNGEON')+'</ul></div>'

    def portal_cards(self, keys):
        return '<div class="dc-portal-grid">'+''.join('<div class="dc-portal-card">'+self.branch_link(key,32)+'<small>'+self.branch_depth(key)+' · '+self.branch_records[key]['summary']+'</small></div>' for key in keys)+'</div>'

    def branch_header(self, key):
        title=self.branch_names[key];row=self.branch_records[key]
        title_block='<div class="dc-article-top">'+ '<div class="dc-article-sprite">'+self.picture(self.branch_sprites[key],title,32)+'</div><div><div class="dc-kicker">Ветви и порталы · 0.35-a0</div><div class="dc-native">'+title+'</div><div class="dc-meta">'+row['summary']+'</div></div></div>'
        facts='<div class="dc-branch-summary"><div><b>Вход</b><span>'+self.branch_entrance(key)+'</span></div><div><b>Глубина</b><span>'+self.branch_depth(key)+'</span></div><div><b>Обозначение</b><span>'+row['abbrev']+'</span></div>'
        reward=self.branch_reward(key)
        if reward:facts+='<div><b>Цель</b><span class="dc-branch-reward">'+reward+'</span></div>'
        facts+='</div>'
        children=[k for k in TREE_ORDER if k!=key and self.branch_parent(k)==key]
        connection=''
        parent=self.branch_parent(key)
        if parent in self.branch_records:connection+='<div><b>Откуда прийти</b> '+self.branch_link(parent)+'</div>'
        if children:connection+='<div><b>Куда ведёт</b> '+' '.join(self.branch_link(k) for k in children)+'</div>'
        return self.breadcrumbs('Ветви подземелья',title)+title_block+facts+('<div class="dc-connections">'+connection+'</div>' if connection else '')

    def branch_navigation(self, current=None):
        sections=(('Подземелье и рунические ветви',TREE_ORDER[:15]),('Поздние миры',TREE_ORDER[15:]),('Порталы',PORTALS),('Испытания богов',SPECIAL_WORLDS))
        return '\n<div class="dc-navbox dc-world-nav" role="navigation" aria-label="Ветви подземелья"><div class="dc-navbox-title">[[Ветви подземелья|Карта подземелья]] · [[Порталы]] · [[Путь к Сфере]]</div>'+''.join('<div class="dc-nav-row"><b>'+label+'</b><div>'+' '.join(self.branch_link(k,20,current) for k in keys)+'</div></div>' for label,keys in sections)+'</div>\n'

    def guide_navigation(self, title, pages):
        links=[t for t in ('Первые шаги','Первый персонаж','Как выжить','Развитие персонажа','Управление','Магия','Снаряжение и расходники','Механики игры','Ветви подземелья') if t in pages and t!=title]
        return '\n<div class="dc-navbox"><div class="dc-navbox-title">Руководства</div><div class="dc-nav-family">'+' '.join('[['+t+']]' for t in links)+'</div></div>\n'
