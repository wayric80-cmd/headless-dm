# Way of Vanilla – instruktioner för installationsagenten

Den här filen ligger i roten av operatörens fork av HeadlessDM. Den gäller för **en ny installation från grunden**
av HeadlessDM som grund för projektet Way of Vanilla. Prata svenska med operatören.

## Läsordning och prioritet

1. Läs `CLAUDE.md` och därefter `docs/GUIDE.md`: Part 0 och Appendix A före Phase 1.
2. Följ guiden fas för fas, med alla gates, checks och records, **utom där den här filen säger något annat**.
3. Om den här filen och guiden säger olika saker gäller den här filen. Om den här filen inte nämner något gäller guiden.
4. Om något är oklart: stanna och fråga operatören. Gissa inte.

Alla guidens regler i 0.2 gäller oförändrade. Det betyder bland annat: aldrig `sudo` själv, hemligheter bara i
`site/secrets.env`, backup före envägssteg, stopp vid fel, och **ingen kodändring under installationen** (regel 6).

## Bakgrund: varför vissa steg hoppas över

Way of Vanilla ska bli ett samhälle av AI-botar som beter sig som **människor som spelar WoW**. HeadlessDM gör
botarna till **invånare i Azeroth** (guidens regel 8). Den omställningen görs **efter** installationen, i separata
och versionsstyrda ändringar. Den görs inte i den här installationen.

Därför gäller följande:

- Faserna för infrastruktur (0–9) körs exakt enligt guiden.
- Steg som genererar rollspelsinnehåll (kunskapsbas, temperament, bakgrundshistorier) körs **inte**. Det innehållet
  ska ersättas, och genereringen skulle ta många timmar på operatörens GPU.
- Under installationen skriver du **ingen ny text som botarna läser**: inga prompter, mallar eller personligheter.
  Regel 8 lämnas orörd tills vidare.

## Kända avvikelser från guiden

### Operativsystem: Ubuntu 26.04

Guiden kräver Ubuntu 24.04. Servern kör **Ubuntu 26.04**, och HeadlessDM har tidigare installerats och fungerat utan
problem på just den här servern. Så här hanterar du det:

- I Phase 1:s Check godkänner du 26.04 i stället för 24.04. Notera det under Gate answers i `site/SETUP-STATE.md`.
- I Phase 3 noterar du alla versioner (cmake, g++, MySQL, Boost, Python). De blir nyare än guidens
  "Known to work".
- Om ett apt-paket har ett annat namn på 26.04: ge operatören det korrigerade kommandot, notera det under
  Open problems och fortsätt först när Check passerar.
- Om bygget eller en Check fallerar på grund av nyare versioner gäller regel 5: rapportera det exakta felet och
  stanna. Ändra inte kod.

### Hårdvara

| Maskin | Känt |
|---|---|
| Spelserver | Cirka 16 GB RAM. Antalet kärnor mäts i Phase 1 |
| AI-server (separat) | GTX 1070 8 GB VRAM, 8 GB systemminne |

Mät alltid själv i Phase 1 och redovisa resultatet vid G1. Siffrorna ovan är operatörens uppgifter.

## Bestämda värden

Föreslå de här värdena vid respektive gate. Operatören bekräftar.

| Nyckel / gate | Värde | Kommentar |
|---|---|---|
| Phase 2, klon | operatörens fork | Inte `bazola/headless-dm` direkt |
| `REALM_NAME` | `Way of Vanilla` | |
| `ERA` | `classic` | |
| `BOT_MIN`, `BOT_MAX` | `50`, `60` | Pilotstorlek. Ingen uppskalning i den här installationen |
| `BOT_GUILDS` | `5` | Litet antal för en liten pilot |
| `MAP_THREADS` | enligt Phase 1 | Guidens tabell |
| `DASHBOARD_BIND` | `127.0.0.1` | Plus LAN- eller VPN-adress om operatören vill |
| `CHAT_CONCURRENCY` | `2` | Lika med `router_slots` för ambient-backenden |

### Phase 8, modell på AI-servern (G5)

8 GB VRAM räcker inte för guidens exempel med `-np 4 -c 32768`. KV-cachen för 32k kontext är ensam cirka 4,5 GB
med en 8B-modell. Föreslå i stället:

- Modell: **Qwen3 8B, Q4_K_M** (instruct, thinking av).
- llama-server:
  ```bash
  llama-server -m <model>.gguf --host 0.0.0.0 --port 8080 --jinja -np 2 -c 16384 \
    --chat-template-kwargs '{"enable_thinking":false}'
  ```
  Det ger 8k per slot, vilket guiden anger som behovet för skrivjobb.
- Om operatören hellre kör Ollama: flytta porten med `OLLAMA_HOST=0.0.0.0:11435`, enligt guiden.

`site/fleet.toml`: en enda backend (`main`) med AI-serverns adress, `router_slots = 2`, `batch_slots = 1` och
`[judge] slots = 1`. Alla routes och `[batch] lanes` pekar på `main`. Summan överstiger två slots, men det är
acceptabelt eftersom inga batchjobb för lore körs i den här installationen. Notera det i SETUP-STATE.md.

Kör guidens probe i 8.1 och notera svarstiderna.

## Fasplan

| Fas | Gör | Kommentar |
|---|---|---|
| 0–8 | **Exakt enligt guiden** | Med avvikelserna ovan |
| 9 (G8) | Exakt enligt guiden | Det är förväntat att botarna låter generiska eller som rollspelsfigurer. Det räknas som godkänt så länge de svarar och ledger-räknarna stiger |
| 10.1 | **Hoppa över** | Guilds fryses inte. De ska kunna förändras |
| 10.2 | **Hoppa över** | mod-ollama-chats kunskapsbas för spelare behålls som den är |
| 10.3 | **Hoppa över** | `temperaments-inworld.sql` laddas inte |
| 10.4 | **Hoppa över** | Inga bakgrundshistorier, traits, crafts eller `project` |
| 10.5 (G10) | **Gör** | Fråga operatören vilken karaktär som är hens main. Kör `alts` bara om guiden kräver det och det fungerar utan 10.4. Annars notera det och gå vidare |
| 10.6 | **Hoppa över** | Valfritt i guiden |
| 11.1–11.3 | **Kör inte, undersök bara** | Ta reda på, utan att köra något skrivande, om regard och chronicler kräver tabellerna från 10.4 (`lore_character`, `lore_guild`). Rapportera vad du hittar till operatören. Starta inga tjänster utan operatörens ja |
| 11.4 (G9) | **Gör** | Classic court-overlay, med backup enligt guiden |
| 11.5 | **Gör** | Merchants och allow-list för auktionshuset. Fråga operatören om namn |
| 12 | **Hoppa över** | Ingen uppskalning. Piloten stannar på 50–60 botar |
| 13 | **Gör** | Backup, nattlig timer och sammanfattning |

## Får inte göras i den här installationen

- Inga extra AzerothCore-moduler (inte heller från operatörens lista med 116 moduler).
- Inga Humanlike-patchar, inga ändringar av `mod-ollama-chat` eller `mod-playerbots`.
- Ingen import av personlighetsprofiler och ingen omskrivning av prompter eller `conf/*.overrides`-mallar.
- Ingen ändring av `docs/GUIDE.md`. Avvikelser beskrivs här och i SETUP-STATE.md.

## SETUP-STATE.md

Lägg till ett avsnitt `## Way of Vanilla` i `site/SETUP-STATE.md` med:

- Att den här filen styr installationen.
- Varje överhoppat steg markerat som `skipped by design (Way of Vanilla)`, så att en senare session inte kör det.
- Avvikelser: Ubuntu 26.04, modell- och slotval, pakets namnbyten.
- Resultatet av undersökningen i 11.1–11.3.

## När installationen är klar

Avsluta med en sammanfattning till operatören:

- Vad som fungerar: inloggning, botar online, chatt, ledger, dashboard, auktionshus och backup.
- Uppmätta värden: byggtid, första start, världsuppdateringstid med 50–60 botar, modellens svarstider.
- Överhoppade steg och öppna problem.
- Att nästa steg (omställning till spelarperspektiv, de 75 profilerna och utvalda moduler) görs separat och inte av
  den här installationen.
