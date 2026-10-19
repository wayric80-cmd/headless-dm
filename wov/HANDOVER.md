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
- Submodulernas origin är bazola:s repon – **pusha inte dit**. Kodbackup som git-bundles i
  `/opt/wow/backups/code-*`.

## Dokumentation hos operatören (Claude-projektet "Server")
`Driftlogg.md`, `Testprotokoll.md` (fynd från speltest), `Kontrollfragor.md` (standardtest A–E efter varje
större chattändring). Codex: skriv motsvarande anteckningar i slutet av denna fil under "Logg", så för Claude
över dem till projektet senare.

## Att göra (prioritetsordning)
1. [ ] Pusha koden: operatören behöver forka mod-ollama-chat och mod-playerbots på GitHub och ge servern
       en token/deploy key. Tills dess: git-bundles (gjort 2026-10-19 12:28).
2. [ ] AI-servern (operatören, sudo): `sudo loginctl enable-linger idiadmin` och
       `sudo systemctl disable --now ollama`.
3. [ ] Verifiera General-prat med 300 botar (operatören loggar in i Durotar; räkna per kanal i ledger_chat;
       kolla att Qwen-kön inte växer i router-loggen).
4. [ ] **Speltider**: botar loggar in/ut enligt `wov_player` (se Pågående arbete).
5. [ ] Del 3: regard/chronicler i spelarperspektiv (minne, relationer mellan mötena).
6. [ ] Socialt initiativ: gruppinbjudningar, LFG, guildrekrytering, viskningar till kända spelare.
7. Beslut hos operatören: mount-regler (WotLK 20/40 eller Vanilla 40), välkomsttext (MOTD), fler moduler.
8. Efter testperioden: `OllamaChat.DebugEnabled = 0`, `OllamaChat.DebugShowFullPrompt = 0`.

## Pågående arbete
(uppdateras löpande)

## Logg
- 2026-10-19 12:30 Claude: överlämningsfilen skapad. 300 botar online, zonprat 8 %.
