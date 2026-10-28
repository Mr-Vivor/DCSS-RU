#include "catch_amalgamated.hpp"

#include "AppHdr.h"
#include "database.h"
#include "artefact.h"
#include "clua.h"
#include "describe.h"
#include "l-libs.h"
#include "initfile.h"
#include "localise.h"
#include "newgame.h"
#include "options.h"
#include "player-save-info.h"
#include "ui.h"
#include "item-prop.h"
#include "player.h"
#include "stringutil.h"

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
    CHECK(localise("Next:") == "Опыт:");
    CHECK(localise("Wear") == "Надеть доспех");
    CHECK(localise("Take off") == "Снять доспех");
    CHECK(localise("Missiles") == "Метательные снаряды");
    CHECK(localise("Train") == "Трен");
    CHECK(localise("Do you want to play this combination? [Y/n/q]")
          == "Играть этой комбинацией? [Y/n/q]");
    CHECK(localise("Cast: ") == "Заклинание: ");
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
    const string djinni = trimmed_string(getLongDescription("Spellcasting"));
    CHECK(djinni == "Навык Колдовства повышает вероятность успешного сотворения и силу всех заклинаний.");
    CHECK(getLongDescription("Invocations").find("запас магии") == string::npos);
    you.species = SP_HUMAN;
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
