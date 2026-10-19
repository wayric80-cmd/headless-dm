# Way of Vanilla – överlämning mellan Claude och Codex

**Läs hela filen innan du gör något.** Den hålls aktuell av den agent som arbetar (Claude eller Codex).
När du tar över: läs "Pågående arbete", fortsätt därifrån och uppdatera filen när du avslutar ett steg.
Prata svenska med operatören (Richard). Installationen är klar; `docs/AGENTS-installation.md` är historik.

## Målet
En WoW-värld i Vanilla-stil (Classic, level 60) där hundratals AI-botar beter sig som **riktiga engelsktalande
människor som spelar WoW**: levlar, hittar vänner, handlar, tävlar, har egna mål och en historia som fortsätter
mellan mötena. Varken chatt eller beteende får avslöja att det är botar. Botarna är **spelare**, inte invånare i
Azeroth (HeadlessDM:s regel 8 är medvetet omvänd här).

## Hur du når servern (via SentinelX)
SentinelX kör som användaren `sentinelx`. Dess fil-verktyg (`sentinel_edit`, upload m.fl.) är **läsbara** för
`/opt/wow/headless-dm` och ska inte användas för att skriva där. Allt skrivande görs i stället med
`sentinel_script_run` (bash), där kommandona körs **som idiadmin** via `sudo -u idiadmin ...`, t.ex.
`sudo -u idiadmin python3 wov/apply-overlay.py` eller en heredoc `sudo -u idiadmin tee fil <<'EOF'`.
Det är den godkända arbetsvägen (sentinelx har en sudoers-regel för just detta). Ändra inte SentinelX-policyn.
- Godkända sudo-anrop: `sudo -u idiadmin <kommando>` och `sudo systemctl restart|status wow-world|wow-auth|wow-router`.
- Inga andra sudo-anrop (inga paket, inga systemfiler, ingen root-shell).
- Långa jobb (bygge, omstart + väntan) med `background=true` och läs resultatet med notifications.
- Ingen pipe i `sentinel_exec` – använd `sentinel_script_run`.

## Regler (gäller alltid)
1. Inga sudo-anrop utöver de godkända ovan. Omstart av wow-world tar ca 50 s och kickar inloggade spelare –
   säg till operatören innan.
2. Hemligheter bara i `site/secrets.env` (mode 600). Skriv aldrig ut, kopiera eller logga nycklar
   (`ANTHROPIC_API_KEY` m.fl.).
3. Ta backup till `/opt/wow/backups/` före varje envägsändring (filer, SQL-dump av berörda tabeller).
4. Klientfiler, extraherad Blizzard-data och world-dumpar committas eller laddas aldrig upp.
5. Kör **aldrig** `ops/scripts/add-bots.sh`, `lore-fill.sh` eller HeadlessDM:s lore/temperament/backstory-jobb
   (steg 10.1–10.4, 12). De skriver rollspelsinnehåll. Botantal ändras via `site/site.env` (se nedan).
6. Efter `ops/scripts/conf-apply.py` måste **alltid** `python3 wov/apply-overlay.py` köras (annars försvinner
   vår spelarröst).
7. Stanna och fråga operatören vid oklarheter eller fel. Gissa inte.
8. Commita varje fungerande steg. Servern saknar global git-identitet:
   `git -c user.name=WayOfVanilla -c user.email=way.ric80@gmail.com commit ...`
9. Kör aldrig två `ra`-sessioner samtidigt. SQL via `db` i `ops/env.sh`.

## Miljö
- Spelserver: Ubuntu 26.04, `/opt/wow`, användare `idiadmin`. Tjänster (system-systemd): `wow-auth`, `wow-world`,
  `wow-router`. Repo: `/opt/wow/headless-dm` (fork `wayric80-cmd/headless-dm`, gren `main`).
- `. ops/env.sh` ger `ra "<GM-kommando>"` och `db <databas> -e "<SQL>"`. Databaser: `acore_auth`,
  `acore_characters` (även lore-tabeller, `wov_player`, ledger), `acore_world`.
- AI-server 192.168.0.115 (GTX 1070): llama-server med Qwen3 8B, `-np 2 -c 16384`, användartjänst
  `llama-server.service`. SSH från spelservern: `ssh -i ~/.ssh/headlessdm_ai idiadmin@192.168.0.115`.
- Router `services/router/03-router.py` på :11434. Routes i `site/fleet.toml`. Route `person` =
  Claude Haiku 5.5 (spelarsvar, betalt, ca 0,0003 USD/svar) med Qwen som reserv. Allt annat går till Qwen.
- Bygge: `cd src/azerothcore-wotlk/build && nice -n 10 make -j4 install` (25–75 s), sedan omstart.
- Konfig: `OllamaChat.*` laddas om med `ra "ollama reload"`; övrigt kräver omstart.
- Botantal: `BOT_MIN`/`BOT_MAX`/`MAP_THREADS` i `site/site.env` → `conf-apply.py` → `apply-overlay.py` → omstart.
  Nu 290/300, `MAP_THREADS=4`. Medel 2 ms världsuppdatering.

## Våra ändringar (allt under `wov/` + patchar)
- `wov/conf/mod_ollama_chat.wov.overrides` – spelarröst, prompter, chatter-inställningar. Appliceras med
  `wov/apply-overlay.py` (backup `.bak-wov-*`).
- `wov/rag/`, `wov/rag_classic.py`, `wov/install-rag.sh` – Classic-kunskapsbas (188 poster), laddas vid start.
- `wov/sql/player-profiles.*`, `player-weights.json` – 53 spelarprofiler.
- `wov/gen_players.py` – "spelaren bakom boten": `lore_character` + `wov_player(guid, play_days,
  play_start_hour, session_minutes)`, `project` skriver `BIO_/BIOX_<guid>`.
- Submodul `src/modules/mod-ollama-chat`, gren `wov`: ekoskydd, läckfilter, frågan sist i prompten,
  zonpublik för random chatter (`OllamaChat.WoV.ZoneChatterChance`).
- Submodul `src/modules/mod-playerbots`, gren `wov`: inga säkerhetssvar på viskningar, ingen `<Away>`,
  inga inloggningsrader.
- GitHub: allt pushas till operatörens forkar. `headless-dm` gren `main`; `mod-ollama-chat` och `mod-playerbots`
  gren `wov` (remote `origin` = fork, `upstream` = bazola – pusha aldrig till upstream). Token i
  `site/secrets.env` (`GITHUB_TOKEN`), läses av `wov/git-cred.sh`. **Pusha efter varje commit**: först submodulen
  (`git push origin wov`), sedan superprojektet (`git push origin main`).

## Dokumentation hos operatören (Claude-projektet "Server")
`Driftlogg.md`, `Testprotokoll.md` (fynd från speltest), `Kontrollfragor.md` (standardtest A–E efter varje
större chattändring). Codex: skriv motsvarande anteckningar i slutet av denna fil under "Logg", så för Claude
över dem till projektet senare.

## Att göra (prioritetsordning)
1. [x] Pusha koden: operatören behöver forka mod-ollama-chat och mod-playerbots på GitHub och ge servern
       en token/deploy key. Tills dess: git-bundles (gjort 2026-10-19 12:28).
2. [ ] AI-servern (operatören, sudo): `sudo loginctl enable-linger idiadmin` och
       `sudo systemctl disable --now ollama`.
3. [ ] Verifiera General-prat med 300 botar (operatören loggar in i Durotar; räkna per kanal i ledger_chat;
       kolla att Qwen-kön inte växer i router-loggen).
4. [x] **Speltider**: botar loggar in/ut enligt `wov_player` (se Pågående arbete).
5. [ ] Del 3: regard/chronicler i spelarperspektiv (minne, relationer mellan mötena).
6. [ ] Socialt initiativ: gruppinbjudningar, LFG, guildrekrytering, viskningar till kända spelare.
7. Beslut hos operatören: mount-regler (WotLK 20/40 eller Vanilla 40), välkomsttext (MOTD), fler moduler.
8. Efter testperioden: `OllamaChat.DebugEnabled = 0`, `OllamaChat.DebugShowFullPrompt = 0`.

## Pågående arbete
(uppdaterad 2026-10-19 15:26)
**Förberett, väntar på en omstart (operatören är inloggad – fråga innan).** Gör i denna ordning:
1. `sudo systemctl stop wow-world`
2. Backup: `db acore_characters` dump av `characters` (guid,name), `lore_character`, `playerbots_names` till /opt/wow/backups/before-wov-names-*.
3. `python3 wov/rename_bots.py apply` (60 % av botarna får spelarnamn från `wov/names/player-names.txt`; botar som pratat
   med riktiga spelare behåller namnet; mapping i tabellen `wov_rename`, ångra med `rename_bots.py revert`).
4. `python3 wov/gen_players.py project` (BIO_-mallar med nya namn).
5. PvP: `python3 wov/apply-overlay.py` (GameType = 1 i `wov/conf/worldserver.wov.overrides`) och
   `db acore_auth -e "UPDATE realmlist SET icon=1 WHERE id=1"`.
6. `sudo systemctl start wow-world`. Den laddar också nya RAG:en (Varian bort, Classic-ledare in).
7. Verifiera: namn i spel, realm visas som PvP, `ra "server info"`. Commit + push.
- Namnpoolen genereras med `wov/gen_names.py` (Haiku, ~1200+ namn, logg `logs/gen-names.log`).
- Bios-genereringen för de 273 är klar (ALL-DONE).

## Logg
- 2026-10-19 12:30 Claude: överlämningsfilen skapad. 300 botar online, zonprat 8 %.
- 2026-10-19 12:36 Claude: speltider implementerade (bygge pågår). Hittade att 235 av 300 online-botar saknade biografi; generering startad.
- 2026-10-19 12:44 Claude: speltider i drift (commits 84ce14ca i mod-playerbots, 20cca3c). 631 scheman laddade, 60 online vid 12:45.
- 2026-10-19 13:17 Claude: GitHub-push fungerar (forkar + token). .gitmodules pekar på forkarna, gren wov.
- 2026-10-19 13:54 Claude: lade till 'Hur du når servern' (SentinelX + sudo -u idiadmin) efter att Codex stoppats av read-only file_ops.
- 2026-10-19 14:00 Codex: statuskontroll via SentinelX som idiadmin. Generering ALL-DONE; 854 scheman; project och ollama reload bekräftade i loggen. Kodsubmoduler rena och matchar sparade origin-referenser. Ospårad mod-dashboard/tools/mpq_extract orörd. Ingen driftändring. Nästa: General-test i Durotar och kontroll av router-kön.
- 2026-10-19 14:03 Codex: General-funktionstest, 61 online. Zugzug skrev 14:02:42.859 'Anyone questing around Razor Hill?' i General - Durotar. Ugdesh svarade 14:02:45.282 (2,423 s): 'nah not me, I’m up in the Valley of Trials still, lvl 5 rogue.' DB bekräftar nivå 5, klass 4 (rogue), zon Durotar; exakt delområde ej verifierat. Ett loggat botsvar under observationen. Router: utility/main 1295 ms samt tre person/haiku 1059–1126 ms, alla queued 0 ms. Inga fel i dessa anrop. Funktionstest lyckat; 300-botars belastningstest återstår. Ingen driftändring.
- 2026-10-19 14:37 Claude: Varian i RAG (inte i världen – spawnen är dold). RAG-trim utökad + fakta om Classic-ledare. Kräver omstart av wow-world för att laddas. 28 konton (27 nya botkonton + MERCHANTS) satta till expansion 0.
- 2026-10-19 15:26 Claude: operatören vill ha PvP-server och spelarlika namn (Sirkillalot, Mookin...). Förberett enligt Pågående arbete.
