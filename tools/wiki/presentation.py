"""Editorial layouts built around the existing, reviewed game reference."""
import html
import re


DIRECTORY_TEXT = {
    'species':('Народы Подземелья','Врождённые особенности, склонности к обучению и ограничения снаряжения. Вид определяет основу персонажа; предыстория дополняет её стартовыми навыками и вещами.'),
    'background':('С чего начинается приключение','Предыстория задаёт начальные навыки и снаряжение. Дальнейшее развитие свободно: выбирайте старт, который помогает пережить первые этажи.'),
    'gods':('Пантеон Подземелья','У каждого бога свои награды, требования и запреты. В статье собраны божественные силы, правила поклонения и советы для нашей версии игры.'),
    'skills':('Навыки и обучение','Оружие, защита, магия и вспомогательные умения. Откройте навык, чтобы увидеть его описание, советы по развитию и связанные предметы или заклинания.'),
    'items':('Снаряжение, находки и расходники','Оружие и доспехи, книги и талисманы, средства усиления и спасения. Сравнивайте свойства находки с текущими задачами персонажа.'),
    'unrand':('Именные артефакты','Уникальные предметы с особыми свойствами и историей. Названия и изображения совпадают с русской игрой; английское имя поможет найти знакомую находку.'),
    'spells':('Библиотека магии','Изучаемые заклинания расположены по уровням. В отдельном разделе — силы существ и других источников: наличие статьи не означает возможность обычного заучивания.'),
    'monsters':('Обитатели Подземелья','Смотрите характеристики и набор сил до начала боя. Уникальные противники выделены отдельно, остальные существа сгруппированы по своей природе.'),
    'ability':('Способности и божественные силы','Описание действия и ограничений каждой способности. Её доступность зависит от вида, религии, формы и других особенностей персонажа.'),
    'status':('Состояния и эффекты','Усиления, ограничения и последствия вражеских атак. Здесь можно разобраться, что означает появившийся в игре значок или подпись.'),
    'mutations':('Мутации и особенности тела','Полезные и опасные изменения персонажа. Постоянные особенности вида, временные изменения и приобретённые мутации требуют разного подхода.'),
    'features':('Местность и объекты','Стены, двери, лестницы, алтари и особые объекты. Читайте описание перед взаимодействием с незнакомой частью подземелья.'),
    'cards':('Карты Немелекса','Эффекты карт, которые встречаются среди сил Немелекса. Их действие и доступность определяются описанием конкретной карты и текущими правилами бога.'),
    'egos':('Свойства снаряжения','Дополнительные свойства оружия, брони и снарядов. Одинаковое короткое обозначение может иметь разный смысл у разных типов предметов.')}
SKILL_SECTIONS = {
    'combat':('Бой и защита',('Fighting','Armour','Dodging','Shields','Unarmed Combat','Stealth')),
    'weapons':('Оружие и метание',('Short Blades','Long Blades','Axes','Maces & Flails','Polearms','Staves','Ranged Weapons','Throwing')),
    'magic':('Магические школы',('Spellcasting','Conjurations','Hexes','Summonings','Necromancy','Translocations','Forgecraft','Fire Magic','Ice Magic','Air Magic','Earth Magic','Alchemy')),
    'other':('Силы и устройства',('Invocations','Evocations','Shapeshifting'))}
HOLINESS_LABELS = {'undead':'Нежить','demonic':'Демоны','nonliving':'Неживые существа и конструкции',
    'holy':'Святые существа','plant':'Растения и грибы','natural':'Живые существа'}
GOD_PREFIXES = {'the Shining One':'TSO','Kikubaaqudgha':'KIKU','Yredelemnul':'YRED',
    'Nemelex Xobeh':'NEMELEX','Sif Muna':'SIF_MUNA','Hepliaklqana':'HEPLIAKLQANA','Wu Jian':'WU_JIAN'}


class WikiPresentation:
    def prepare_presentation(self):
        self.spell_users={}
        for row in self.sorted_groups['monsters']:
            data=self.monsters.get(row['entries'][0]['key'].casefold(),{})
            for enum in self.monster_books.get(data.get('spells',''),[]):
                self.spell_users.setdefault(enum,[]).append(row['title'])
        self.guide_sprites={}
        for group,category in self.group_names.items():
            sample=next((r for r in self.sorted_groups[group] if r.get('sprite')),None)
            if sample:self.guide_sprites[category]=sample['sprite']
        symbols={
            'Время и действия':('skills','Dodging'),'Движение и отступление':('skills','Dodging'),
            'Скорость атаки':('skills','Long Blades'),'Сила и надёжность заклинаний':('skills','Spellcasting'),
            'Сопротивления урону':('skills','Shields'),'Видимость и линии огня':('skills','Stealth'),
            'Ловушки и облака':('skills','Evocations'),'Благочестие и божественный гнев':('skills','Invocations'),
            'Тяжесть доспехов и щитов':('skills','Armour'),'Оружие и выбор навыка':('skills','Long Blades'),
            'Опознание и оценка предметов':('items','scroll of identify'),
            'Развитие персонажа':('skills','Fighting'),'Первые шаги':('species','Human'),
            'Механики игры':('skills','Fighting'),'Магия':('skills','Spellcasting'),
            'Справочник':('items','book of minor magic'),
            'Снаряжение и расходники':('items','potion of curing'),'Выбор бога':('skills','Invocations')}
        for title,key in symbols.items():
            target=self.keys.get(key)
            if target and self.rows[target].get('sprite'):self.guide_sprites[title]=self.rows[target]['sprite']

    def excerpt(self, row, length=145):
        text=self.prose(row['entries'][0]['text'])
        text=re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]',r'\2',text)
        text=re.sub(r'\[\[([^\]]+)\]\]',r'\1',text)
        text=re.sub(r'<[^>]+>|\'{2,}|={2,}.*?={2,}', '', text)
        text=re.sub(r'\s+',' ',text).strip()
        if len(text)>length:text=text[:length].rsplit(' ',1)[0].rstrip(' ,;:')+'…'
        return html.escape(text)

    def directory_cover(self, group, category, count):
        title,lead=DIRECTORY_TEXT[group]
        rows=self.sorted_groups[group]
        samples=[r for r in rows if r.get('sprite')]
        # Real game illustrations, never decorative substitutes for absent art.
        art=''.join(self.picture(r['sprite'],r['title'],40,r['name']) for r in samples[:3])
        return '<div class="dc-directory-cover"><div class="dc-cover-art">'+art+'</div><div><div class="dc-kicker">'+category+' · 0.35-a0</div><div class="dc-cover-title">'+title+'</div><p>'+lead+'</p><span class="dc-cover-count">Записей в справочнике: '+str(count)+'</span></div></div>\n'

    def profile_entry(self, row):
        group=row['group'];key=row['entries'][0]['key'];title=row['title']
        search=html.escape(title+' '+key,quote=True)
        image=self.picture(row.get('sprite'),title,48,row['name'])
        detail=''
        if group=='species':
            data=self.species.get(key.casefold(),{})
            detail=' · '.join(label+' '+str(data[field]) for field,label in [('str','Сила'),('int','Инт.'),('dex','Ловк.')] if field in data)
        elif group=='background':
            data=self.backgrounds.get(key.casefold(),{})
            labels=[self.terms['skill'].get(self.skill_key(k)) for k in data.get('skills',{}) if k!='weapon']
            detail=' · '.join(v for v in labels[:3] if v)
        return '<div class="dc-icon-entry dc-profile-entry" data-dc-search="'+search+'"><div class="dc-profile-art">'+image+'</div><div class="dc-entry-text">[['+title+']]<p>'+self.excerpt(row)+'</p>'+('<small>'+detail+'</small>' if detail else '')+'</div></div>'

    def artifact_for(self, row):
        key=row['entries'][0]['key'].casefold()
        if key in ('sulking sword','screaming sword'):key='singing sword'
        return self.artifacts.get(key) or next((a for name,a in self.artifacts.items() if '"'+name+'"' in key),{})

    def monster_kind(self, row):
        data=self.monsters.get(row['entries'][0]['key'].casefold(),{})
        nature=data.get('holiness',[])
        if isinstance(nature,str):nature=[nature]
        return next((key for key in HOLINESS_LABELS if key in nature),'other')

    def directory_sections(self, group, rows):
        if group=='skills':
            return [(key,label,[r for r in rows if r['entries'][0]['key'] in keys]) for key,(label,keys) in SKILL_SECTIONS.items()]
        if group=='unrand':
            labels={'OBJ_WEAPONS':'Оружие','OBJ_ARMOUR':'Доспехи и щиты','OBJ_JEWELLERY':'Украшения'}
            sections=[];used=set()
            for key,label in labels.items():
                chosen=[r for r in rows if self.artifact_for(r).get('OBJ','').startswith(key+'/')]
                sections.append((key.lower(),label,chosen));used.update(r['title'] for r in chosen)
            other=[r for r in rows if r['title'] not in used]
            if other:sections.append(('other','Прочие уникальные предметы',other))
            return sections
        if group=='monsters':
            unique=[r for r in rows if 'unique' in self.monsters.get(r['entries'][0]['key'].casefold(),{}).get('flags',[])]
            others=[r for r in rows if r not in unique]
            result=[('unique','Уникальные противники',unique)]
            for kind,label in HOLINESS_LABELS.items():
                chosen=[r for r in others if self.monster_kind(r)==kind]
                if chosen:result.append((kind,label,chosen))
            remaining=[r for r in others if self.monster_kind(r)=='other']
            if remaining:result.append(('other','Особые разновидности и дополнительные описания',remaining))
            return result
        return None

    def article_layout(self, body):
        # Move the existing first statistics table intact: no values or caveats
        # are reinterpreted by the presentation layer.
        facts=''
        match=re.search(r'\n== (?:Характеристики|Параметры|Базовые параметры|Начальные характеристики|Бонусы характеристик) ==\n(\{\|.*?\n\|\}\n)',body,re.S)
        if match:
            table=match[1].replace('class="wikitable"','class="wikitable dc-fact-table"').replace('! Параметр !! Значение\n','')
            facts='<div class="dc-factbox"><div class="dc-side-title">Краткая справка</div>\n'+table+'</div>'
            body=body[:match.start()]+body[match.end():]
        headings=[]
        def heading(match):
            index=len(headings)+1;title=match[1]
            headings.append((index,title))
            return '<div class="dc-section-anchor" id="dc-section-'+str(index)+'"></div>\n== '+title+' =='
        body=re.sub(r'^== ([^\n]+) ==$',heading,body,flags=re.M)
        toc=''
        if len(headings)>1:
            toc='<div class="dc-page-contents" role="navigation" aria-label="На этой странице"><div class="dc-side-title">На этой странице</div><ol>'+''.join('<li>[[#dc-section-'+str(i)+'|'+title+']]</li>' for i,title in headings)+'</ol></div>'
        if facts or toc:
            body='<div class="dc-reading-layout"><div class="dc-reading-main">\n'+body+'\n</div><div class="dc-reading-aside">'+facts+toc+'</div></div>\n'
        return '__NOTOC__\n'+body

    def linked_powers(self, god_key):
        prefix=GOD_PREFIXES.get(god_key,god_key.upper().replace(' ','_'))
        return [r for r in self.sorted_groups['ability'] if self.ability_enums.get(r['entries'][0]['key'].removesuffix(' ability').casefold(),'').startswith('ABIL_'+prefix+'_')]

    def illustrated_cards(self, entries):
        return '<div class="dc-topic-grid">'+''.join('<div class="dc-topic-card">'+self.illustrated_link(title,size=24)+'<small>'+html.escape(detail)+'</small></div>' for title,detail in entries)+'</div>'

    def topic_portals(self, pages):
        topics={
            'Механики игры':('Как устроено Подземелье',[
                ('Время и действия','Ходы, скорость и ответ противника'),('Движение и отступление','Выбор позиции и безопасного пути'),
                ('Скорость атаки','Оружие, обучение и время удара'),('Сила и надёжность заклинаний','Мощность магии и вероятность неудачи'),
                ('Сопротивления урону','Как читать защитные свойства'),('Видимость и линии огня','Что видно и куда можно попасть'),
                ('Ловушки и облака','Опасная местность'),('Благочестие и божественный гнев','Награды и требования религии')]),
            'Магия':('От книги до заклинания',[
                ('Заклинания','Уровни, школы и описания эффектов'),('Навыки','Обучение магическим школам'),
                ('Сила и надёжность заклинаний','Сила эффекта и успешное сотворение'),('Тяжесть доспехов и щитов','Как снаряжение влияет на магию')]),
            'Снаряжение и расходники':('Что взять в следующий бой',[
                ('Предметы','Оружие, броня и расходные средства'),('Артефакты','Именные находки с особыми свойствами'),
                ('Оружие и выбор навыка','Сравнение типов оружия'),('Опознание и оценка предметов','Как читать свойства находки')]),
            'Первый персонаж':('Выбор первого героя',[
                ('Виды','Врождённые особенности и ограничения'),('Предыстории','Навыки и снаряжение на старте'),
                ('Боги','Выбор религии'),('Развитие персонажа','Как распределять опыт')]),
            'Выбор бога':('Религия и божественные силы',[
                ('Боги','Покровители, требования и запреты'),('Способности','Описание активных сил'),
                ('Благочестие и божественный гнев','Благочестие, отказ и наказания')])}
        for title,(heading,entries) in topics.items():
            if title not in pages:continue
            text=pages[title]['text']
            marker=text.find('</div>\n')
            insert='<div class="dc-topic-heading">'+heading+'</div>'+self.illustrated_cards(entries)
            if marker>=0:pages[title]['text']=text[:marker+7]+insert+text[marker+7:]
        pages['Справочник']=dict(text='__NOTOC__\n'+self.breadcrumbs('Справочник')+'<div class="dc-guide-lead">Персонаж, снаряжение, магия и мир игры — все разделы русского справочника.</div>'+self.illustrated_cards([(self.group_names[g],DIRECTORY_TEXT[g][1]) for g in self.group_names])+self.guide_navigation('Справочник',pages),key='guide:reference-hub',kind='guide')
