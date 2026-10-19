# Way of Vanilla – överlämning mellan Claude och Codex

**Läs hela filen innan du gör något.** Den hålls aktuell av den agent som arbetar (Claude eller Codex).
När du tar över: läs "Pågående arbete", fortsätt därifrån och uppdatera filen när du avslutar ett steg.
Prata svenska med operatören (Richard). Installationen är klar; `docs/AGENTS-installation.md` är historik.

## Målet
En WoW-värld i Vanilla-stil (Classic, level 60) där hundratals AI-botar beter sig som **riktiga engelsktalande
människor som spelar WoW**: levlar, hittar vänner, handlar, tävlar, har egna mål och en historia som fortsätter
mellan mötena. Varken chatt eller beteende får avslöja att det är botar. Botarna är **spelare**, inte invånare i
Azeroth (HeadlessDM:s regel 8 är medvetet omvänd här).

## Regler (gäller alltid)
1. Kör aldrig `sudo` själv. Behövs omstart: be operatören köra `sudo systemctl restart wow-world` (ca 50 s).
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
(uppdaterad 2026-10-19 12:44)
Inget halvfärdigt steg. Speltider (punkt 4) är klara och i drift: 60 online mitt på dagen (golvet), förväntat
150–200 på kvällen när alla scheman finns.
- Bakgrundsjobb: `logs/gen-players-2.log` genererar biografier/scheman för resterande botar (slutar med ALL-DONE,
  kör då `project` + `ollama reload` själv). Kontroll: `db acore_characters -e "SELECT COUNT(*) FROM wov_player"`
  (mål ca 854).
- Nästa: punkt 3 (verifiera General-prat ikväll när fler är online), sedan punkt 5 (del 3, minne/relationer).
- Justera speltider: `AiPlayerbot.WoV.Schedule.SessionPercent` (längre sessioner = fler online) och `MinOnline`
  i `wov/conf/playerbots.wov.overrides`, simulera först med `WOV_SESSION_PCT=250 python3 wov/wov_schedule.py sim 2`.

## Logg
- 2026-10-19 12:30 Claude: överlämningsfilen skapad. 300 botar online, zonprat 8 %.
- 2026-10-19 12:36 Claude: speltider implementerade (bygge pågår). Hittade att 235 av 300 online-botar saknade biografi; generering startad.
- 2026-10-19 12:44 Claude: speltider i drift (commits 84ce14ca i mod-playerbots, 20cca3c). 631 scheman laddade, 60 online vid 12:45.
- 2026-10-19 13:17 Claude: GitHub-push fungerar (forkar + token). .gitmodules pekar på forkarna, gren wov.
