#include "catch_amalgamated.hpp"

#include "AppHdr.h"
#include "database.h"
#include "artefact.h"
#include "ability.h"
#include "clua.h"
#include "command.h"
#include "describe.h"
#include "env.h"
#include "l-libs.h"
#include "initfile.h"
#include "invent.h"
#include "hiscores.h"
#include "localise.h"
#include "macro.h"
#include "map-cell.h"
#include "map-knowledge.h"
#include "newgame.h"
#include "options.h"
#include "player-save-info.h"
#include "ui.h"
#include "item-prop.h"
#include "item-use.h"
#include "player.h"
#include "pattern.h"
#include "stash.h"
#include "quiver.h"
#include "religion.h"
#include "skill-menu.h"
#include "stringutil.h"
#include "travel.h"
#include "spl-cast.h"
#include "spl-util.h"
#include "unicode.h"

namespace
{
class russian_localisation
{
public:
    russian_localisation()
        : old_language(Options.language), old_name(Options.lang_name),
          old_directory(SysEnv.crawl_dir.empty() ? "." : SysEnv.crawl_dir)
    {
        shutdown_localisation();
        databaseSystemShutdown();
        setlocale(LC_ALL, "");
        Options.language = lang_t::RU;
        Options.lang_name = "ru";
        SysEnv.crawl_dir = ".";
        databaseSystemInit();
        init_localisation();
    }

    ~russian_localisation()
    {
        shutdown_localisation();
        databaseSystemShutdown();
        Options.language = old_language;
        Options.lang_name = old_name;
        SysEnv.crawl_dir = old_directory;
        databaseSystemInit();
    }

private:
    lang_t old_language;
    const char* old_name;
    string old_directory;
};
}

TEST_CASE("Russian command help translates before binding and column layout", "[localise][single-file]")
{
    russian_localisation language;
    if (command_to_name(CMD_WIELD_WEAPON) == "CMD_NO_CMD")
        init_keybindings();
    for (bool hints : { false, true })
    {
        const string text = command_keyhelp_text(hints).tostring();
        CHECK(text.find("Передвижение:") != string::npos);
        CHECK(text.find("зелья (выпить — q)") != string::npos);
        CHECK(text.find("посохи (взять — w)") != string::npos);
        CHECK(text.find("талисманы (применить — V)") != string::npos);
        CHECK(text.find("колдовать") != string::npos);
        CHECK(text.find("hand weapons") == string::npos);
        CHECK(text.find("memorise") == string::npos);
        CHECK(text.find("uaff") == string::npos);
        CHECK(text.find("percent") == string::npos);
        CHECK(text.find("%</w>") == string::npos);
        for (const string &line : split_string("\n", text, false, true))
            CHECK(strwidth(line) <= 82);
    }
    const int previous_key = command_to_key(CMD_WIELD_WEAPON);
    const command_type displaced_command = key_to_command('W',
                                           context_for_command(CMD_WIELD_WEAPON));
    bind_command_to_key(CMD_WIELD_WEAPON, 'W');
    CHECK(command_keyhelp_text().tostring().find("оружие (взять — W)") != string::npos);
    bind_command_to_key(CMD_WIELD_WEAPON, previous_key);
    if (displaced_command != CMD_NO_CMD)
        bind_command_to_key(displaced_command, 'W');

    Options.language = lang_t::EN;
    CHECK(command_keyhelp_text().tostring().find("hand weapons (wield)") != string::npos);
    Options.language = lang_t::RU;

    CHECK(localise(", v - describe") == ", v — описание");
    CHECK(localise("Shift-Dir - straight line") == "Shift + направление — по прямой");
    CHECK(localise(" <w>buy</w>|examine items") == " <w>купить</w>|осмотреть");
    CHECK(localise("sort (price)") == "сортировка (цена)");
}

TEST_CASE("Russian item and spell prompts preserve keys and current mechanics", "[localise][single-file]")
{
    russian_localisation language;
    if (command_to_name(CMD_WIELD_WEAPON) == "CMD_NO_CMD")
        init_keybindings();

    CHECK(localise("<lightgray> ([<w>Tab</w>] to select)</lightgray>")
          == "<lightgray> ([<w>Tab</w>] — выбрать)</lightgray>");
    // A binding must stay literal even when its spelling has a translation.
    CHECK(localise("<lightgray> (Human to select)</lightgray>")
          == "<lightgray> (Human — выбрать)</lightgray>");
    CHECK(localise("<lightgray> ([<w>,</w>] to take off)</lightgray>")
          == "<lightgray> ([<w>,</w>] — снять доспех)</lightgray>");
    CHECK(localise("[<w>!</w>] focus mode: <w>off</w>|on")
          == "[<w>!</w>] один раздел: <w>выкл.</w>|вкл.");
    CHECK(localise("Your spells (quiver)") == "Ваши заклинания (подготовить)");
    CHECK(localise("<lightgrey>Select a spell to forget</lightgrey>")
          == "<lightgrey>Выберите заклинание, которое хотите забыть</lightgrey>");
    CHECK(localise("Memorise|<w>Describe</w>|Hide|Show")
          == "Выучить|<w>Описание</w>|Скрыть|Показать");
    CHECK(localise("<lightgreen>3 spell levels left</lightgreen>")
          == "<lightgreen>Свободных уровней заклинаний: 3</lightgreen>");
    CHECK(localise("Memorise Passwall, consuming 3 spell levels and leaving 1?")
          == "Выучить «Проход сквозь стену»? Затраты уровней заклинаний: 3, останется: 1.");

    for (const string &key : { string("Y"), string("y") })
    {
        const string prompt = localise("Purchase items in shopping list for 123 gold? "
            "This will use your shop voucher. (" + key + "/N)");
        INFO(prompt);
        CHECK(prompt.find("Купить предметы из списка покупок за 123 зол.?") != string::npos);
        CHECK(prompt.find("Будет использован купон магазина.") != string::npos);
        CHECK(prompt.find("(" + key + "/N)") != string::npos);
        CHECK(prompt.find("Purchase") == string::npos);
    }
    CHECK(localise("Shopping list: 21 items, total cost 132 gold pieces")
          == "Список покупок: позиций — 21, общая стоимость — 132 золота");
    CHECK(localise("As you read the scroll of fear, it crumbles to dust.")
          == "Вы читаете свиток страха, и он рассыпается в пыль.");
    CHECK(localise("This square is shrouded in silence and is covered in acidic slime.")
          == "Эта клетка окутана тишиной и покрыта кислотной слизью.");
    string reminder = localise("(Press <w>%</w> to maintain the ray.)");
    insert_commands(reminder, { CMD_WAIT });
    CHECK(reminder == "(Нажимайте <w>.</w>, чтобы поддерживать луч.)");

    CHECK(localise("Passwall") == "Проход сквозь стену");
    CHECK(localise("Call Canine Familiar") == "Призыв пса-фамильяра");
    CHECK(localise("Fulminant Prism") == "Взрывная призма");
    CHECK(getLongDescription("Passwall spell").find("не может действовать") != string::npos);
    CHECK(getLongDescription("Sandblast spell").find("в полтора раза") != string::npos);
    CHECK(getLongDescription("Petrify spell").find("ещё до двух врагов") != string::npos);
    CHECK(getLongDescription("Sticky Flame spell").find("двигаться") != string::npos);
    CHECK(getLongDescription("Call Canine Familiar spell").find("яд будет снят") != string::npos);
    CHECK(getLongDescription("Forge Lightning Spire spell").find("самого далёкого") != string::npos);
}

TEST_CASE("Russian spell and ability rows are translated before column padding", "[localise][single-file]")
{
    russian_localisation language;
    init_spell_descs();
    CHECK(spell_schools_for_display(SPELL_SEARING_RAY) == "Разрушение");
    CHECK(spell_schools_for_display(SPELL_FULMINANT_PRISM) == "Разрушение/Алхимия");
    // Raw English school strings remain usable by identifiers and old searches.
    CHECK(spell_schools_string(SPELL_FULMINANT_PRISM) == "Conjuration/Alchemy");
    const talent renounce = { ABIL_RENOUNCE_RELIGION, 'a', 0, false };
    const string row = describe_talent(renounce);
    INFO(row);
    CHECK(row.find("Отречься от веры") == 0);
    CHECK(row.find("Renounce") == string::npos);
    CHECK(row.find("None") == string::npos);
    CHECK(strwidth(row) <= 76);
    const string prepared_spell = quiver::spell_to_action(SPELL_MAGIC_DART)
                                ->valid_quiver_description().tostring();
    INFO(prepared_spell);
    CHECK(prepared_spell.find("Сотворить: Магический дротик") != string::npos);
    CHECK(prepared_spell.find("Cast:") == string::npos);
    CHECK(localise("Purchase items for 20 gold?")
          == "Купить предметы за 20 зол.?");
    CHECK(localise("Purchase items in shopping list for 240 gold? This will use your shop voucher. (Y/N)")
          == "Купить предметы из списка покупок за 240 зол.? Будет использован купон магазина. (Y/N)");
    CHECK(localise(" gold   ") == " зол.   ");
    CHECK(localise_in_context("quiver-action", "Fire") == "Выстрелить");
    CHECK(localise("Fire Magic") == "Магия огня");
    CHECK(localise_in_context("card", "the Storm") == "Буря");
    CHECK(getLongDescription("the Tomb card").find("если уйти из центра") != string::npos);
    CHECK(localise("a book of Air") == "книга воздуха");
    CHECK(localise("Codex of Conductivity") == "кодекс проводимости");
    CHECK(localise("Singing Sword") == "Поющий меч");
    CHECK(localise("the +8 lance \"Wyrmbane\" (slay drac)").find("Вирмбейн") != string::npos);
    CHECK(localise("+6 arbalest \"Damnation\" (damnation)").find("Адская кара") != string::npos);
    CHECK(getLongDescription("Sulking Sword") == getLongDescription("Singing Sword"));
    CHECK(localise("Piety***") == "Благочестие***");
    CHECK(localise("Zin always shields you from chaos.") == "Зин всегда защищает вас от хаоса.");
    CHECK(localise("Really take off and destroy +0 leather armour?")
          == "Действительно снять и уничтожить +0 кожаный доспех?");
    Options.language = lang_t::EN;
    CHECK(spell_schools_for_display(SPELL_FULMINANT_PRISM) == "Conjuration/Alchemy");
    CHECK(describe_talent(renounce).find("Renounce Religion") == 0);
    Options.language = lang_t::RU;
}

TEST_CASE("Russian names, grammar and game messages", "[localise][single-file]")
{
    russian_localisation language;

    CHECK(localise("Human") == "Человек");
    CHECK(localise("Fighter") == "Воин");
    CHECK(localise("Short Blades") == "Короткие клинки");
    CHECK(localise(" and ") == " и ");
    CHECK(localise(" or ") == " или ");
    CHECK(localise("flurble and blorb") == "flurble and blorb");
    CHECK(localise("flurble or blorb") == "flurble or blorb");
    CHECK(localise("flurble, blorb, and zorb") == "flurble, blorb, and zorb");
    CHECK(localise("flurble; blorb; and zorb") == "flurble; blorb; and zorb");
    CHECK(localise("a dagger and a club") == "кинжал и дубинка");
    CHECK(localise("a dagger and blorb") == "кинжал и blorb");
    CHECK(localise("a dagger, a club, and a rat") == "кинжал, дубинка и крыса");
    CHECK(localise("кинжал and дубинка") == "кинжал и дубинка");
    CHECK(localise("+0 buckler of the Valley {Will+++}")
          == "+0 buckler of the Valley {Воля+++}");
    CHECK(localise("Will/2") == "Воля/2");
    CHECK(localise("Covered") == "Латник");
    CHECK(localise("AC") == "Бр");
    CHECK(localise("Wiz") == "Чародейство");
    CHECK(localise(" (worn)") == " (надето)");
    CHECK(localise(" (quivered)") == " (подготовлено)");
    // Inventory names separate the suffix from its leading space before
    // translating it. Checking a bare suffix alone misses that path.
    CHECK(localise("+0 robe (worn)") == "+0 мантия (надето)");
    CHECK(localise("+0 dagger (weapon)") == "+0 кинжал (оружие)");
    CHECK(localise("+0 dagger (offhand)") == "+0 кинжал (вторая рука)");
    CHECK(localise("+0 robe (melded)") == "+0 мантия (слито с телом)");
    CHECK(localise("+0 robe (haunted)") == "+0 мантия (одержимо духом)");
    CHECK(localise("+0 dagger (bound)") == "+0 кинжал (связано)");
    CHECK(localise("+0 dagger (quivered)") == "+0 кинжал (подготовлено)");
    CHECK(localise("flurble (installed)") == "flurble (установлено)");
    CHECK(localise("flurble (my note)") == "flurble (my note)");
    CHECK(localise("(w)") == "(w)");
    CHECK(make_stringf(localise("(Confirm with \"%s\".)").c_str(), "yes")
          == "(Для подтверждения введите \"yes\".)");
    CHECK(make_stringf(localise("(Confirm with \"%s\".)").c_str(), "wiz")
          == "(Для подтверждения введите \"wiz\".)");
    CHECK(localise("Next:") == "Опыт:");
    CHECK(localise("Wear") == "Надеть доспех");
    CHECK(localise("Take off") == "Снять доспех");
    CHECK(localise("Missiles") == "Метательные снаряды");
    CHECK(localise("Train") == "Трен");
    CHECK(localise("Do you want to play this combination? [Y/n/q]")
          == "Играть этой комбинацией? [Y/n/q]");
    CHECK(localise("Cast: ") == "Сотворить: ");
    CHECK(localise("It affects your AC (+4).") == "Изменяет вашу броню (+4).");
    CHECK(localise("It greatly increases your willpower.") == "Значительно повышает вашу Волю.");
    CHECK(localise("Flame") == "Пламя");
    CHECK(localise_in_context("status", "Fire") == "Горение");
    CHECK(localise_in_context("status", "Slow") == "Замедл");
    CHECK(localise("You are petrified.") == "Вы окаменели.");
    CHECK(localise("Your spells return to their normal power.")
          == "Сила ваших заклинаний возвращается к обычной.");
    CHECK(localise("Lash (2)") == "Плеть (2)");
    CHECK(localise("Base accuracy: +2  Base damage: 7  Base attack delay: 1.2")
          == "Базовая точность: +2  Базовый урон: 7  Задержка атаки: 1.2");
    CHECK(localise("Base shield rating: 5     Encumbrance rating: 10     Max blocks/turn: 4")
          == "Базовый щит: 5     Тяжесть: 10     Блоков за ход: 4");
    CHECK(localise("This weapon's minimum attack delay (0.7) is reached at skill level 14.")
          == "Минимальная задержка атаки этим оружием (0.7) достигается на уровне навыка 14.");
    CHECK(localise("the Covered") == "Латник");
    CHECK(localise("the ice dragon") == "ледяной дракон");
    CHECK(localise_in_context("acc", "the ice dragon") == "ледяного дракона");
    CHECK(localise_in_context("ins", "a long sword") == "длинным мечом");
    CHECK(localise_in_context("ins", "a potion of curing") == "зельем исцеления");
    CHECK(localise("2 scrolls of teleportation") == "2 свитка телепортации");
    CHECK(localise("5 scrolls of teleportation") == "5 свитков телепортации");
    CHECK(localise("11 scrolls of teleportation") == "11 свитков телепортации");
    CHECK(localise("21 scrolls of teleportation") == "21 свиток телепортации");
    CHECK(localise("101 scrolls of teleportation") == "101 свиток телепортации");
    CHECK(localise_in_context("ins", "2 scrolls of teleportation")
          == "2 свитками телепортации");
    CHECK(localise("You hit the ice dragon!") == "Вы ударяете ледяного дракона!");
    CHECK(localise("You kill the hydra!") == "Вы убиваете гидру!");
    CHECK(localise("The rat bites you!") == "Крыса кусает вас!");
    CHECK(localise("You miss the orc.") == "Вы промахиваетесь по орку.");
    CHECK(localise("You hit the ice dragon with your long sword!")
          == "Вы ударяете ледяного дракона длинным мечом!");
    CHECK(localise("You see here a potion of curing.")
          == "Здесь лежит зелье исцеления.");
    CHECK(localise("You see 2 rats and 21 scrolls of teleportation.")
          == "Вы видите 2 крыс и 21 свиток телепортации.");
    CHECK(localise("You see a +2 dagger and 21 scrolls of teleportation.")
          == "Вы видите +2 кинжал и 21 свиток телепортации.");
    CHECK(localise("You hit the bat!") == "Вы ударяете летучую мышь!");
    CHECK(localise("An untranslated message about MrVivor.")
          == "An untranslated message about MrVivor.");
    CHECK(localise("<red>You die...</red>") == "<red>Вы погибаете...</red>");
    CHECK(localise("You headbutt the hydra!") == "Вы бодаете гидру!");
    CHECK(localise("The orc misses the bat.") == "Орк промахивается по летучей мыши.");
    CHECK(localise("Roots grab the bat.") == "Корни хватают летучую мышь.");
    CHECK(localise("You can now recite Zin's Axioms of Law.")
          == "Теперь вы можете читать Аксиомы Закона Зина.");
    CHECK(localise("Your hands briefly pass through it before you manage to get a firm grip on it.")
          == "У вас руки на миг проходят сквозь предмет, прежде чем вы крепко его схватываете.");
    CHECK(localise("His hands briefly pass through it before he manages to get a firm grip on it.")
          == "Его руки на миг проходят сквозь предмет, прежде чем он умудряется крепко его схватить.");
    CHECK(localise("Sparks fly from your hands") == "У вас из рук сыплются искры");
    CHECK(localise("You collide with the bat!") == "Вы сталкиваетесь с летучей мышью!");
    CHECK(localise("Your soul already belongs to Yredelemnul.")
          == "Ваша душа уже принадлежит Йредэлемнулу.");
    CHECK(localise("Stack Five") == "Сложить пять");
    CHECK(localise("Drain Life") == "Вытянуть жизненную силу");

    CHECK(localise("Spriggan") == "Спригган");
    CHECK(localise("Gnoll") == "Гнолл");
    CHECK(localise("Barachi") == "Барачи");
    CHECK(localise("the Trog") == "Трог");
    CHECK(localise("Shock") == "Электрический разряд");
    CHECK(localise("You hear a click...") == "Вы слышите щелчок...");
    CHECK(localise("Welcome, Vivor.") == "Добро пожаловать, Vivor.");
    CHECK(localise("Welcome, Спригган.") == "Добро пожаловать, Спригган.");
    CHECK(localise("Found a staircase leading out of the dungeon.")
          == "Найдено: лестница из подземелья.");
    CHECK(localise("Hello, welcome to Dungeon Crawl Stone Soup 0.35-a0-1349-g89dca86ecd!")
          == "Добро пожаловать в Dungeon Crawl Stone Soup 0.35-a0-1349-g89dca86ecd!");
    CHECK(localise("Lesson 5: Gods and Divine Abilities")
          == "Урок 5: Боги и божественные способности");
    ui::Text lesson("Lesson 1: Movement and Exploration");
    CHECK(lesson.get_text().tostring() == "Урок 1: Передвижение и исследование");
    formatted_string multiline("Human\nSpriggan");
    CHECK(localise(multiline).tostring() == "Человек\nСпригган");

    player_save_info saved;
    saved.name = "Vivor";
    saved.species_name = "Human";
    saved.class_name = "Fighter";
    saved.experience_level = 2;
    saved.saved_game_type = GAME_TYPE_TUTORIAL;
    CHECK(saved.short_desc() == "[Обучение] Vivor, ур. 2 · Человек · Воин");
    CHECK(saved.really_short_desc() == "Vivor · Человек · Воин");
}

TEST_CASE("Russian character greetings preserve user names and multiword choices", "[localise][single-file]")
{
    russian_localisation language;
    newgame_def character;
    character.name = "Human"; // A user name that is also a dictionary key.
    character.species = SP_HUMAN;
    character.job = JOB_CHAOS_KNIGHT;
    CHECK(newgame_welcome(character) == "Добро пожаловать, Human. Человек · Рыцарь хаоса.");
    // The message stream and Text widgets also run the localisation hook.
    // A second pass must not translate the user's name as a species name.
    CHECK(localise(newgame_welcome(character)) == newgame_welcome(character));
    CHECK(localise(formatted_string(newgame_welcome(character))).tostring()
          == newgame_welcome(character));
    character.name = "Вивор";
    character.species = SP_DEEP_ELF;
    character.job = JOB_AIR_ELEMENTALIST;
    CHECK(newgame_welcome(character) == "Добро пожаловать, Вивор. Глубинный эльф · Маг воздуха.");
    CHECK(newgame_welcome(character, true) == "С возвращением, Вивор. Глубинный эльф · Маг воздуха.");
    CHECK(localise(newgame_welcome(character, true)) == newgame_welcome(character, true));
    character.species = SP_UNKNOWN;
    character.job = JOB_UNKNOWN;
    character.name.clear();
    CHECK(newgame_welcome(character) == "Добро пожаловать.");

    Options.language = lang_t::EN;
    character.name = "Human";
    character.species = SP_HUMAN;
    character.job = JOB_FIGHTER;
    CHECK(newgame_welcome(character) == "Welcome, Human the Human Fighter.");
    CHECK(newgame_welcome(character, true) == "Welcome back, Human the Human Fighter.");
    Options.language = lang_t::RU;
}

TEST_CASE("Russian endgame summary uses structured character data and preserves xlog", "[localise][single-file]")
{
    russian_localisation language;
    const string record = "v=0.35:name=Human:sc=1061:race=Troll:cls=Berserker:char=TrBe:xl=8:"
        "title=Ruffian:ktyp=pois:killer=a water moccasin:br=D:lvl=5:hp=0:mhp=112:mmhp=112:"
        "god=Trog:piety=85:start=20260928120000S:end=20260928121158S:dur=718:turn=3249";
    scorefile_entry score;
    REQUIRE(score.parse(record));
    const string summary = score.localised_summary();
    INFO(summary);
    CHECK(summary.find("Human — Разбойник") != string::npos);
    CHECK(summary.find("Тролль · Берсерк") != string::npos);
    CHECK(summary.find("Очки: 1061") != string::npos);
    CHECK(summary.find("Уровень: 8") != string::npos);
    CHECK(summary.find("Бог: Трог") != string::npos);
    CHECK(summary.find("Духовный сан: Жрец") != string::npos);
    CHECK(summary.find("Погиб от яда водяного щитомордника") != string::npos);
    CHECK(summary.find("Ходов: 3249") != string::npos);
    CHECK(summary.find("Began as") == string::npos);
    CHECK(summary.find("turns") == string::npos);
    CHECK(score.raw_string() == record);

    Options.language = lang_t::EN;
    CHECK(score.localised_summary() == score.hiscore_line(scorefile_entry::DDV_VERBOSE));
    CHECK(score.raw_string() == record);
    Options.language = lang_t::RU;
}

TEST_CASE("Russian runtime comparisons describe the direction of stat changes", "[localise][single-file]")
{
    russian_localisation language;
    CHECK(localise("Your EV would decrease by 2.0 (10.0 -> 8.0).")
          == "Уклонение уменьшилось бы на 2.0 (10.0 → 8.0).");
    CHECK(localise("Your attack delay would increase by 0.2 (1.0 -> 1.2).")
          == "Задержка атаки увеличилась бы на 0.2 (1.0 → 1.2).");
    CHECK(localise("With your current stats and equipment, training 1 level of this skill would increase your AC by 0.4 and your EV by 0.1.")
          == "С вашими текущими характеристиками и снаряжением повышение на один уровень этого навыка повысило бы броню на 0.4 и уклонение на 0.1.");
    CHECK(localise("Your spell failure would improve by up to 3% (press '!' for details).")
          == "Вероятность неудачи при колдовстве уменьшилась бы на величину до 3 процентных пунктов ('!' — подробнее).");
    CHECK(localise("Enter a base skill target for Short Blades: ")
          == "Укажите целевой базовый уровень навыка «Короткие клинки»: ");
    CHECK(localise("Enter a skill target for Armour: ")
          == "Укажите целевой уровень навыка «Доспехи»: ");
    CHECK(localise("  Human  ") == "  Человек  ");
    CHECK(localise("  flurble blorb  ") == "  flurble blorb  ");
    CHECK(localise("Spell refund chance: 25% (max 50%)")
          == "Шанс вернуть затраченную магию: 25% (максимум 50%)");
    CHECK(localise("+0 rapier") == "+0 рапира");
    CHECK(localise("-2 leather armour") == "-2 кожаный доспех");
    CHECK(localise("+0 flurble") == "+0 flurble");
    CHECK(localise("2 rock fish") == "2 каменные рыбы");
    CHECK(localise("11 rock fish") == "11 каменных рыб");
    CHECK(localise("21 rock fish") == "21 каменная рыба");
    CHECK(localise("The iguana bites you!") == "Игуана кусает вас!");
    CHECK(localise("The air fills with toxic fumes!") == "Воздух наполняется ядовитыми испарениями!");
    CHECK(localise("Fire: e) +0 shortbow") == "Выстрел: e) +0 короткий лук");
    CHECK(localise("97% to hit") == "шанс попадания: 97%");
    CHECK(localise("You shoot an arrow.") == "Вы выпускаете стрелу.");
    CHECK(localise_in_context("acc", "a training dummy") == "учебный манекен");

    for (const string key : {"welcome_spam", "welcome_spam dungeon descent", "welcome_spam Halloween"})
    {
        for (int i = 0; i < 30; ++i)
        {
            const string message = getMiscString(key);
            INFO(message);
            CHECK(message.find("Сфер") != string::npos);
            CHECK(message.find('@') == string::npos);
            CHECK(message.find("Orb of Zot") == string::npos);
        }
    }
}

TEST_CASE("Russian item and conditional skill descriptions", "[localise][single-file]")
{
    russian_localisation language;
    cluaopen_you(clua.state());
    CHECK(getLongDescription("ring of willpower").find("Волю") != string::npos);
    CHECK(getLongDescription("potion of invisibility").find("[[player invis desc]]") == string::npos);
    CHECK(getLongDescription("potion of invisibility").find("Стоя в воде") != string::npos);
    CHECK(getEgoString("harm (Harm) armour ego").find("получаемый") != string::npos);
    CHECK(getEgoString("sniping (Snipe) armour ego").find("50%") != string::npos);
    CHECK(getLongDescription("Shock spell").find("половину брони") != string::npos);
    CHECK(getLongDescription("Bind Soul ability").find("сравнительно невредимой") != string::npos);
    CHECK(getLongDescription("Bind Soul ability").find("треть текущего здоровья") != string::npos);
    CHECK(getLongDescription("Finesse ability").find("загрязнение") == string::npos);
    CHECK(getLongDescription("Finesse ability").find("Молитв") != string::npos);
    CHECK(localise("Hurl Torchlight") == "Метнуть свет Чёрного факела");
    CHECK(localise("Bolster") == "Укрепление");
    CHECK(localise("Deflect Missiles") == "Отклонение снарядов");

    const species_type old_species = you.species;
    you.species = SP_DJINNI;
    CHECK(getLongDescription("crystal ball of Wucad Mu").find("Для джиннов") != string::npos);
    const string djinni = trimmed_string(getLongDescription("Spellcasting"));
    CHECK(djinni == "Навык Колдовства повышает вероятность успешного сотворения и силу всех заклинаний.");
    CHECK(getLongDescription("Invocations").find("запас магии") == string::npos);
    you.species = SP_HUMAN;
    CHECK(getLongDescription("crystal ball of Wucad Mu").find("Для джиннов") == string::npos);
    const string human_hand = getLongDescription("Sacrifice a Hand ability");
    CHECK(human_hand.find("щитами и двуручным оружием") != string::npos);
    CHECK(human_hand.find("one fewer ring") == string::npos);
    you.species = SP_FORMICID;
    const string formicid_hand = getLongDescription("Sacrifice a Hand ability");
    CHECK(formicid_hand.find("двуручным") == string::npos);
    CHECK(formicid_hand.find("одно кольцо меньше") != string::npos);
    you.species = SP_FELID;
    const string feline_eels = getLongDescription("eel talisman");
    CHECK(feline_eels.find("Лапы владельца") != string::npos);
    CHECK(feline_eels.find("Causes") == string::npos);
    CHECK(feline_eels.find("электрических угрей") != string::npos);
    you.species = SP_HUMAN;
    CHECK(getLongDescription("eel talisman").find("Руки владельца") != string::npos);
    CHECK(localise("Your earthen and fiery crystals are infused with energy.")
          == "Заряжены кристаллы: земли, огня.");
    CHECK(localise("Your earthen, fiery, airy and icy crystals are infused with energy.")
          == "Заряжены кристаллы: земли, огня, воздуха, льда.");
    const string human = getLongDescription("Spellcasting");
    CHECK(human.find("уровней для изучения") != string::npos);
    CHECK(getLongDescription("Invocations").find("запас магии") != string::npos);
    CHECK(getLongDescription("quick blade").find("два удара") != string::npos);
    CHECK(getLongDescription("quicksilver dragon scales").find("нельзя зачаровать") != string::npos);
    CHECK(getLongDescription("javelin").find("слишком длинное") == string::npos);
    you.species = SP_KOBOLD;
    CHECK(getLongDescription("javelin").find("слишком длинное") != string::npos);
    CHECK(getLongDescription("large rock").find("только крупные") != string::npos);
    you.species = SP_TROLL;
    CHECK(getLongDescription("large rock").find("только крупные") == string::npos);
    you.species = old_species;

    // Exercise the real artifact formatter, including long wrapped text and
    // labels. The generated description must already be Russian at this stage.
    item_def item;
    item.base_type = OBJ_WEAPONS;
    item.sub_type = WPN_DAGGER;
    item.quantity = 1;
    item.flags |= ISFLAG_RANDART | ISFLAG_IDENTIFIED;
    CrawlVector &props = item.props[ARTEFACT_PROPS_KEY].new_vector(SV_SHORT);
    props.resize(ART_PROPERTIES);
    props.set_max_size(ART_PROPERTIES);
    for (int p = 0; p < ART_PROPERTIES; ++p)
        artefact_set_property(item, static_cast<artefact_prop_type>(p), 0);
    artefact_set_property(item, ARTP_AC, 4);
    artefact_set_property(item, ARTP_WILLPOWER, 3);
    artefact_set_property(item, ARTP_SLAYING, 4);
    vector<string> lines;
    desc_randart_props(item, lines);
    REQUIRE(lines.size() >= 3);
    const string properties = join_strings(lines.begin(), lines.end(), "\n");
    INFO(properties);
    CHECK(properties.find("Бр+4:") != string::npos);
    CHECK(properties.find("Изменяет вашу броню (+4).") != string::npos);
    CHECK(properties.find("Значительно повышает вашу Волю.") != string::npos);
    CHECK(properties.find("It affects") == string::npos);
    CHECK(properties.find("willpower") == string::npos);
}

TEST_CASE("Russian unique artefact powers and inscriptions preserve their context", "[localise][single-file]")
{
    russian_localisation language;
    const species_type old_species = you.species;
    you.species = SP_HUMAN;

    for (const int type : { UNRAND_TROG, UNRAND_CHARLATANS_ORB })
    {
        const auto old_status = get_unique_item_status(type);
        item_def item;
        item.quantity = 1;
        REQUIRE(make_item_unrandart(item, type));
        set_unique_item_status(item, old_status);
        const string description = get_item_description(item, IDM_PLAIN);
        INFO(description);
        if (type == UNRAND_TROG)
        {
            int raw_rating = 0;
            const string raw_formula = damage_rating(&item, &raw_rating);
            const string displayed_formula = damage_rating_for_display(&item);
            INFO(displayed_formula);
            CHECK(raw_formula.find("(Base ") != string::npos);
            CHECK(raw_formula.find("(Str)") != string::npos);
            CHECK(displayed_formula.find(to_string(raw_rating) + " (Основа ") == 0);
            CHECK(displayed_formula.find("(Сил)") != string::npos);
            CHECK(displayed_formula.find("(Навыки)") != string::npos);
            CHECK(displayed_formula.find("(Чары)") != string::npos);
            CHECK(localise("It is a two-handed weapon.") == "Двуручное оружие.");
            const string category = localise("This battleaxe falls into the 'Axes' category.");
            CHECK(category.find("Тип оружия:") == 0);
            CHECK(category.find("battleaxe") == string::npos);
            CHECK(category.find("Axes") == string::npos);
            CHECK(localise_in_context("item-actions", ", or ") == ", ");
            CHECK(description.find("Яростный раскол:") != string::npos);
            CHECK(description.find("При экипировке вызывает замедление и истощение сил.") != string::npos);
            CHECK(description.find("RageSunder") == string::npos);
            CHECK(description.find("consecutive") == string::npos);
            CHECK(description.find("when equipped") == string::npos);
            Options.language = lang_t::EN;
            CHECK(damage_rating_for_display(&item) == raw_formula);
            CHECK(get_item_description(item, IDM_PLAIN).find("RageSunder:") != string::npos);
            Options.language = lang_t::RU;
        }
        else
        {
            CHECK(description.find("Резко снижает вашу скрытность.") != string::npos);
            CHECK(description.find("Мешает магии Перемещений, задерживая телепортацию.") != string::npos);
            CHECK(description.find("Шарлатан:") != string::npos);
            CHECK(description.find("massively reduces") == string::npos);
        }
    }
    CHECK(localise("{sonic wave, Invo=14 Evo=0}")
          == "{Звуковая волна, Молитвы=14 Устройства=0}");
    CHECK(localise("{coup de grace rPois∞}")
          == "{Удар милосердия Яд∞}");
    CHECK(localise("{orb Charlatan}") == "{сфера Шарлатан}");
    CHECK(localise("{Will+++ HP--}") == "{Воля+++ ОЗ--}");
    you.species = old_species;
}

TEST_CASE("Russian navigation and multi-turn actions keep their meaning", "[localise][single-file]")
{
    russian_localisation language;
    runrest mode;
    for (const int value : { RMODE_EXPLORE, RMODE_EXPLORE_GREEDY,
                            RMODE_TRAVEL, RMODE_INTERLEVEL })
    {
        mode.runmode = value;
        const bool explore = value == RMODE_EXPLORE || value == RMODE_EXPLORE_GREEDY;
        CHECK(mode.runmode_name() == (explore ? "explore" : "travel"));
        CHECK(localise_in_context("travel-mode", mode.runmode_name())
              == (explore ? "автоисследование" : "автопереход"));
    }
    mode.runmode = RMODE_WAIT_DURATION;
    mode.pos.reset();
    CHECK(mode.runmode_name() == "rest");
    CHECK(localise_in_context("travel-mode", mode.runmode_name()) == "отдых");
    mode.pos = coord_def(1, 0);
    CHECK(mode.runmode_name() == "run");
    CHECK(localise_in_context("travel-mode", mode.runmode_name()) == "бег");

    CHECK(make_stringf(localise_in_context("travel-shortcut", "%s - %s").c_str(),
                       "Tab/Enter", "D:3") == "Tab/Enter — D:3");
    CHECK(make_stringf(localise("Where to? %s").c_str(), "(? — справка) ")
          == "Куда идти? (? — справка) ");
    CHECK(make_stringf(localise("What level of %s? (default %s, ? - help) ").c_str(),
                       localise("the Dungeon").c_str(), "1")
          == "На какой этаж ветви «Подземелье» идти? (по умолчанию 1, ? — справка) ");
    CHECK(make_stringf(localise("Assign waypoint to what number? (0-9%s) ").c_str(), "")
          == "Какой номер назначить путевой точке? (0–9) ");
    CHECK(make_stringf(localise("Assign waypoint to what number? (0-9%s) ").c_str(),
                       localise(", D - delete waypoint").c_str())
          == "Какой номер назначить путевой точке? (0–9, D — удалить путевую точку) ");
    CHECK(localise("Key pressed, stopping автоисследование.")
          == "Нажата клавиша. Остановлено: автоисследование.");
    CHECK(localise("You're confused, stopping отдых.")
          == "Вы в замешательстве. Остановлено: отдых.");
    CHECK(localise("Partly explored, can't reach some items and places.")
          == "Этаж исследован частично: некоторые предметы и места недоступны.");
    CHECK(localise("Could not pick up a dagger here; Ignore it?")
          == "Здесь не удалось подобрать: кинжал. Игнорировать этот предмет?");
    CHECK(localise("Calm down first, please.")
          == "Сначала дождитесь окончания ярости берсерка.");
    CHECK(localise("You start attuning to your weapon.")
          == "Вы начинаете настраиваться на оружие.");
    CHECK(localise("You stop parting from your weapon.")
          == "Вы прекращаете разрывать связь с оружием.");
    CHECK(localise("You start haunting your armour.")
          == "Вы начинаете вселяться в доспехи.");
    CHECK(localise("You start fusing with your armour.")
          == "Вы начинаете сращиваться с доспехами.");
    CHECK(localise("You continue putting on your +0 robe.")
          == "Вы продолжаете надевать: +0 мантия.");
    CHECK(localise("You finish removing your +0 robe.")
          == "Вы сняли: +0 мантия.");
    CHECK(localise("You finish attuning to your +0 dagger.")
          == "Настройка на оружие завершена: +0 кинжал.");
    CHECK(localise("You continue untransforming.")
          == "Вы продолжаете возвращаться в обычный облик.");
    CHECK(localise("There are probably monsters nearby")
          == "Вероятно, поблизости есть монстры");
    CHECK(localise("There are monsters nearby") == "Поблизости есть монстры");
    CHECK(localise("you are contaminated with a potentially lethal amount of magic")
          == "Уровень магического загрязнения может оказаться смертельным");
    CHECK(localise("you are being drained by your emergency flight")
          == "Аварийный полёт истощает вас и уменьшает максимальное здоровье");
    CHECK(localise(" (Press *t to temporarily disregard this.)")
          == " (Нажмите *t, чтобы временно игнорировать эту угрозу.)");
    CHECK(localise(" (Press Ctrl+T to temporarily disregard this.)")
          == " (Нажмите Ctrl+T, чтобы временно игнорировать эту угрозу.)");

    Options.language = lang_t::EN;
    CHECK(localise_in_context("travel-mode", mode.runmode_name()) == "run");
    CHECK(localise("You start haunting your armour.") == "You start haunting your armour.");
    CHECK(localise_in_context("travel-shortcut", "%s - %s") == "%s - %s");
    Options.language = lang_t::RU;
}

TEST_CASE("Russian stash queries match display names without changing English patterns", "[localise][single-file]")
{
    russian_localisation language;
    plaintext_pattern russian("рапира", true);
    plaintext_pattern english("rapier", true);
    plaintext_pattern other("мантия", true);
    text_pattern anchored_english("^rapier$", true);
    text_pattern anchored_russian("^рапира$", true);
    const string raw = "[carried] {inventory} +0 rapier";
    const string label = "+0 rapier {inventory}";
    CHECK(stash_search_matches(russian, raw, label));
    CHECK(stash_search_matches(english, raw, label));
    CHECK_FALSE(stash_search_matches(other, raw, label));
    CHECK(stash_search_matches(anchored_russian, "rapier", "rapier"));
    CHECK(stash_search_matches(anchored_english, "rapier", "rapier"));
    // English anchors are checked against precisely the original haystack,
    // even when a display label would match that expression.
    CHECK_FALSE(stash_search_matches(anchored_english, "+0 rapier", "rapier"));
    CHECK(localise("[carried] +0 rapier") == "[при себе] +0 рапира");
    for (const int count : { 0, 2, 5, 21 })
        CHECK(localise(make_stringf("%d matches", count)) == "Найдено: " + to_string(count));
    CHECK(localise("1 match") == "Найдено: 1");
    CHECK(localise_in_context("stash-action", "travel") == "автопереход");
    CHECK(localise_in_context("stash-action", "view") == "осмотр");
    CHECK(localise_in_context("stash-sort", "type") == "тип");
    CHECK(localise_in_context("stash-sort", "dist") == "расстояние");
    CHECK(localise_in_context("stash-filter", "hide") == "скрывать");
    CHECK(localise_in_context("stash-filter", "show") == "показывать");
    CHECK(make_stringf(localise("Search for what%s? ").c_str(), "") == "Что искать? ");
    CHECK(make_stringf(localise("Enter for \"%s\"").c_str(), "Will+++")
          == "Enter — повторить «Will+++»");
    Options.language = lang_t::EN;
    CHECK_FALSE(stash_search_matches(russian, raw, label));
    CHECK(stash_search_matches(english, raw, label));
    CHECK(localise_in_context("stash-action", "travel") == "travel");
    Options.language = lang_t::RU;
}

TEST_CASE("Russian spell expansion preserves mechanics and configurable reminders", "[localise][single-file]")
{
    russian_localisation language;
    CHECK(localise("Manifold Assault") == "Множественная атака");
    CHECK(localise("Brom's Barrelling Boulder") == "Катящийся валун Брома");
    CHECK(localise("Yara's Violent Unravelling") == "Разрушительное рассеивание Яры");
    const string assault = getLongDescription("Manifold Assault spell");
    CHECK(assault.find("вдвое меньше целей") != string::npos);
    CHECK(assault.find("никогда не промахиваются") != string::npos);
    CHECK(assault.find("дополнительного урона") != string::npos);
    const string invisibility = getLongDescription("Invisibility spell");
    CHECK(invisibility.find("перемещает") != string::npos);
    CHECK(invisibility.find("случайное место") != string::npos);
    CHECK(getLongDescription("Sublimation of Blood spell").find("никогда не приводит к смерти") != string::npos);
    CHECK(getLongDescription("Fugue of the Fallen spell").find("сбрасывает накопленное усиление") != string::npos);
    CHECK(getLongDescription("Rimeblight spell").find("игнорирующий броню") != string::npos);
    CHECK(getLongDescription("Passage of Golubria spell").find("случайному другому открытому проходу") != string::npos);
    CHECK(localise("You feel a numb sensation.") == "Вы ощущаете ослабление магии.");
    CHECK(localise("You can't swap your ancestor with themself.")
          == "Нельзя поменять предка местами с самим собой.");
    CHECK(localise_in_context("target-menu", "target/travel") == "наведение/переход");
    CHECK(localise("target") == "цель");
    CHECK(make_stringf(localise("Spell assigned to '%c'.").c_str(), 'b')
          == "Заклинанию назначена клавиша 'b'.");
    CHECK(make_stringf(localise("With your current stats and equipment, training %s to %d.%d would reduce your failure rate to %d%%.").c_str(),
                       localise("Translocations").c_str(), 17, 9, 10)
          == "С текущими характеристиками и снаряжением развитие «Перемещения» до уровня 17.9 снизило бы вероятность неудачи до 10%.");
    CHECK(make_stringf(localise(" This would take %s.").c_str(), localise("about 10.7 XLs").c_str())
          == " Для этого потребуется примерно 10.7 уровня персонажа.");

    if (command_to_name(CMD_WAIT) == "CMD_NO_CMD")
        init_keybindings();
    const int previous = command_to_key(CMD_WAIT);
    const command_type displaced = key_to_command('W', context_for_command(CMD_WAIT));
    bind_command_to_key(CMD_WAIT, 'W');
    string reminder = localise("(Press <w>%</w> to continue winding your bee.)");
    insert_commands(reminder, { CMD_WAIT });
    CHECK(reminder.find("<w>W</w>") != string::npos);
    CHECK(reminder.find("заводить пчелу") != string::npos);
    CHECK(reminder.find('%') == string::npos);
    bind_command_to_key(CMD_WAIT, previous);
    if (displaced != CMD_NO_CMD)
        bind_command_to_key(displaced, 'W');

    Options.language = lang_t::EN;
    CHECK(localise("Manifold Assault") == "Manifold Assault");
    CHECK(localise("(Press <w>%</w> to maintain the ray.)")
          == "(Press <w>%</w> to maintain the ray.)");
    Options.language = lang_t::RU;
}


TEST_CASE("Russian terrain descriptions resolve aliases, conditions and actual door keys", "[localise][single-file]")
{
    russian_localisation language;
    cluaopen_you(clua.state());
    CHECK(localise("some deep water") == "глубокая вода");
    CHECK(localise("a passage of Golubria") == "проход Голубрии");
    CHECK(getLongDescription("A large closed door") == getLongDescription("A closed door"));
    CHECK(getLongDescription("A gateway leading out of Dis").find("Преддверие Ада") != string::npos);
    const string dispersal = getLongDescription("A dispersal trap (recharging)");
    CHECK(dispersal.find("в поле зрения") != string::npos);
    CHECK(dispersal.find("перезаряжается") != string::npos);
    CHECK(dispersal.find("[[") == string::npos);
    const string mud = getLongDescription("Some mud");
    CHECK(mud.find("разжижена") != string::npos);
    CHECK(mud.find("liquefied") == string::npos);

    const god_type old_god = you.religion;
    you.religion = GOD_NO_GOD;
    const string down = getLongDescription("A slimy stone staircase leading down");
    CHECK(down.find("ускорит восстановление здоровья и магии") != string::npos);
    CHECK(down.find("не позволит вернуться наверх") != string::npos);
    CHECK(getLongDescription("A slimy stone staircase leading up").find("восстановление") == string::npos);
    you.religion = GOD_JIYVA;
    const string friendly = getLongDescription("A slimy stone staircase leading down");
    CHECK(friendly.find("последователю Джийвы она не помешает") != string::npos);
    CHECK(friendly.find("не позволит") == string::npos);
    CHECK(friendly.find("It is slick") == string::npos);
    you.religion = old_god;

    if (command_to_name(CMD_OPEN_DOOR) == "CMD_NO_CMD")
        init_keybindings();
    const int previous_key = command_to_key(CMD_OPEN_DOOR);
    const command_type displaced = key_to_command('P', context_for_command(CMD_OPEN_DOOR));
    bind_command_to_key(CMD_OPEN_DOOR, 'P');
    const coord_def pos(40, 35);
    const auto old_feature = env.grid(pos);
    const map_cell old_cell = env.map_knowledge(pos);
    env.grid(pos) = DNGN_CLOSED_DOOR;
    env.map_knowledge(pos).set_feature(DNGN_CLOSED_DOOR);
    describe_info inf;
    get_feature_desc(pos, inf, false);
    INFO(inf.title);
    INFO(inf.body.str());
    CHECK(inf.title.find("Закрытая дверь") != string::npos);
    CHECK(inf.body.str().find("<w>P</w>, чтобы открыть") != string::npos);
    CHECK(inf.body.str().find("While adjacent") == string::npos);
    env.grid(pos) = old_feature;
    env.map_knowledge(pos) = old_cell;
    bind_command_to_key(CMD_OPEN_DOOR, previous_key);
    if (displaced != CMD_NO_CMD)
        bind_command_to_key(displaced, 'P');
}


TEST_CASE("Russian ability costs preserve resources, failure costs and raw ability IDs", "[localise][single-file]")
{
    russian_localisation language;
    const string cost = make_cost_description(ABIL_OKAWARU_FINESSE);
    INFO(cost);
    CHECK(cost.find("5 ОМ") != string::npos);
    CHECK(cost.find("благочестие") != string::npos);
    CHECK(cost.find("MP") == string::npos);
    CHECK(cost.find("Piety") == string::npos);
    const string finesse = get_ability_desc(ABIL_OKAWARU_FINESSE);
    INFO(finesse);
    CHECK(finesse.find("Искусность") == 0);
    CHECK(finesse.find("Магия: 5") != string::npos);
    CHECK(finesse.find("Благочестие: ") != string::npos);
    CHECK(finesse.find("от максимально возможного благочестия") != string::npos);
    CHECK(finesse.find("This ability costs") == string::npos);
    CHECK(finesse.find("Range:") == string::npos);
    CHECK(get_ability_desc(ABIL_RENOUNCE_RELIGION).find("Затраты способности: нет.") != string::npos);
    CHECK(get_ability_desc(ABIL_EVOKE_TURN_INVISIBLE).find("даже если она неудачна") != string::npos);
    CHECK(get_ability_desc(ABIL_EVOKE_TURN_INVISIBLE).find("Затраты способности: нет.") == string::npos);
    CHECK(get_ability_desc(ABIL_IMBUE_SERVITOR).find("после некоторой подготовки") != string::npos);
    CHECK(get_ability_desc(ABIL_RU_SACRIFICE_HAND).find("Жертвы необратимы.") != string::npos);
    CHECK(get_ability_desc(ABIL_GOZAG_POTION_PETITION).find("Золото: ") != string::npos);
    CHECK(get_ability_desc(ABIL_USKAYAW_STOMP).find("текущего здоровья цели") != string::npos);
    const talent tal = { ABIL_OKAWARU_FINESSE, 'b', 0, true };
    CHECK(strwidth(describe_talent(tal)) <= 76);
    CHECK(ability_name(ABIL_OKAWARU_FINESSE) == "Finesse");
    CHECK(ability_by_name("Finesse") == ABIL_OKAWARU_FINESSE);
    CHECK(make_stringf(localise("Enter a skill target for %s: ").c_str(), localise("Invocations").c_str())
          == "Целевой уровень навыка «Молитвы»: ");
    CHECK(make_stringf(localise("Enter a base skill target for %s: ").c_str(), localise("Fighting").c_str())
          == "Целевой базовый уровень навыка «Бой»: ");
    CHECK(localise_in_context("curse-boost", "Fire") == "Огонь");
    CHECK(localise_in_context("ability-silence", "unable to breathe") == "вы не можете дышать");
    CHECK(localise_in_context("sacrifice-value", "an incredible") == "невероятно ценная");
    CHECK(skill_name_for_menu(SK_EVOCATIONS) == "Упр. устройст.");
    CHECK(localise("Evocations") == "Управление устройствами");
    for (const auto sk : { SK_FIGHTING, SK_POLEARMS, SK_RANGED_WEAPONS,
                          SK_EVOCATIONS, SK_SPELLCASTING, SK_INVOCATIONS })
        CHECK(strwidth(skill_name_for_menu(sk)) <= 15);
    for (const auto& god : get_all_god_powers())
        for (const auto& power : god)
            for (const char* field : { power.gain, power.loss, power.general })
                if (*field)
                {
                    INFO(field);
                    CHECK(localise(field) != field);
                }
    Options.language = lang_t::EN;
    CHECK(make_cost_description(ABIL_OKAWARU_FINESSE).find("5 MP") != string::npos);
    CHECK(make_cost_description(ABIL_OKAWARU_FINESSE).find("Piety") != string::npos);
    CHECK(get_ability_desc(ABIL_OKAWARU_FINESSE).find("This ability costs: ") != string::npos);
    Options.language = lang_t::RU;
}


TEST_CASE("Russian item warnings preserve inscriptions, destruction and teleport conditions", "[localise][single-file]")
{
    russian_localisation language;
    item_def scroll;
    scroll.base_type = OBJ_SCROLLS;
    scroll.sub_type = SCR_FEAR;
    scroll.quantity = 1;
    scroll.flags |= ISFLAG_IDENTIFIED;
    scroll.inscription = "!r";
    CHECK(needs_handle_warning(scroll, OPER_READ));
    CHECK_FALSE(needs_handle_warning(scroll, OPER_QUAFF));
    const string prompt = item_operation_warning(scroll, OPER_READ);
    INFO(prompt);
    CHECK(prompt.find("Прочитать:") == 0);
    CHECK(prompt.find("свиток страха") != string::npos);
    CHECK(prompt.find("!r") != string::npos);
    CHECK(prompt.find("Really") == string::npos);
    CHECK(scroll.inscription == "!r");
    CHECK(scroll.name(DESC_DBNAME) == "scroll of fear");
    CHECK(scroll.quantity == 1);

    item_def weapon;
    weapon.base_type = OBJ_WEAPONS;
    weapon.sub_type = WPN_DAGGER;
    weapon.quantity = 1;
    weapon.flags |= ISFLAG_IDENTIFIED;
    CHECK(item_removal_warning(weapon).find("Убрать из рук:") == 0);
    CHECK(item_removal_warning(weapon).find("уничтожить") == string::npos);
    weapon.flags |= ISFLAG_SUMMONED;
    CHECK(item_removal_warning(weapon).find("и уничтожить:") != string::npos);
    CHECK(item_unequip_verb(weapon) == "unwield");

    item_def armour;
    armour.base_type = OBJ_ARMOUR;
    armour.sub_type = ARM_ROBE;
    armour.quantity = 1;
    armour.flags |= ISFLAG_IDENTIFIED;
    CHECK(item_removal_warning(armour).find("Снять доспехи:") == 0);
    armour.flags |= ISFLAG_SUMMONED;
    CHECK(item_removal_warning(armour).find("Снять и уничтожить доспехи:") == 0);

    const auto old_unique = get_unique_item_status(UNRAND_TROG);
    item_def artifact;
    artifact.quantity = 1;
    REQUIRE(make_item_unrandart(artifact, UNRAND_TROG));
    set_unique_item_status(artifact, old_unique);
    artifact.flags |= ISFLAG_IDENTIFIED;
    artefact_set_property(artifact, ARTP_PREVENT_TELEPORTATION, 1);
    const int previous_teleport = you.duration[DUR_TELEPORT];
    you.duration[DUR_TELEPORT] = 20;
    CHECK(needs_notele_warning(artifact, OPER_EQUIP));
    CHECK(item_operation_warning(artifact, OPER_EQUIP).find("заблокирует ожидаемую телепортацию") != string::npos);
    you.duration[DUR_TELEPORT] = 0;
    CHECK_FALSE(needs_notele_warning(artifact, OPER_EQUIP));
    CHECK(item_operation_warning(artifact, OPER_EQUIP).find("телепортацию") == string::npos);
    you.duration[DUR_TELEPORT] = previous_teleport;

    for (int count : { 1, 2, 5, 21 })
    {
        const char* format = count == 1 ? " %d selected item" : " %d selected items";
        CHECK(make_stringf(localise(format).c_str(), count) == " Выбрано: " + to_string(count));
    }
    Options.language = lang_t::EN;
    CHECK(item_operation_warning(scroll, OPER_READ).find("Really read ") == 0);
    CHECK(item_removal_warning(armour).find("Really take off and destroy ") == 0);
    CHECK(scroll.inscription == "!r");
    Options.language = lang_t::RU;
}
