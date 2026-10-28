#include "catch_amalgamated.hpp"

#include "AppHdr.h"
#include "database.h"
#include "artefact.h"
#include "describe.h"
#include "initfile.h"
#include "localise.h"
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

TEST_CASE("Russian item and conditional skill descriptions", "[localise][single-file]")
{
    russian_localisation language;
    CHECK(getLongDescription("ring of willpower").find("Волю") != string::npos);
    CHECK(getLongDescription("potion of invisibility").find("[[player invis desc]]") == string::npos);
    CHECK(getLongDescription("potion of invisibility").find("Стоя в воде") != string::npos);
    CHECK(getEgoString("harm (Harm) armour ego").find("получаемый") != string::npos);
    CHECK(getEgoString("sniping (Snipe) armour ego").find("50%") != string::npos);

    const species_type old_species = you.species;
    you.species = SP_DJINNI;
    const string djinni = getLongDescription("Spellcasting");
    CHECK(djinni == "Навык Колдовства повышает вероятность успешного сотворения и силу всех заклинаний.");
    CHECK(getLongDescription("Invocations").find("запас магии") == string::npos);
    you.species = SP_HUMAN;
    const string human = getLongDescription("Spellcasting");
    CHECK(human.find("уровней для изучения") != string::npos);
    CHECK(getLongDescription("Invocations").find("запас магии") != string::npos);
    you.species = old_species;

    // Exercise the real artifact formatter, including long wrapped text and
    // labels. The generated description must already be Russian at this stage.
    item_def item;
    item.base_type = OBJ_JEWELLERY;
    item.sub_type = RING_PROTECTION;
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
    CHECK(properties.find("Бр+4:") != string::npos);
    CHECK(properties.find("Изменяет вашу броню (+4).") != string::npos);
    CHECK(properties.find("Значительно повышает вашу Волю.") != string::npos);
    CHECK(properties.find("It affects") == string::npos);
    CHECK(properties.find("willpower") == string::npos);
}
