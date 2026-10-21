> PAUSAT av operatören: routing får inte ändras, även efter omstart. Följande är en vilande plan; aktivera inte utan nytt uttryckligt beslut.

# Modellnivåer för WoV-snack

## Routing
- Normalt snack/svar: `ambient` och `person` -> Haiku 5.5 -> lokal Qwen.
- Premium: `premium` -> Sonnet 5.5 -> Haiku 5.5 -> lokal Qwen.
- Utility/klassificering behåller sin befintliga lokala route.
- Backend-kön delas per fysisk backend. Haiku har 4 slots, Sonnet 2.
- Router och world behöver godkänd omstart efter denna första installation.

Officiella modell-ID:n: https://platform.claude.com/docs/en/models/overview
Inga fasta månadskostnader garanteras; utfallet beror på faktisk tokenvolym och reservväg.

## Installation
`site/fleet.toml` är lokalt och ignorerat av Git. De hanterade route-/backendvärdena
finns i `wov/conf/model-tiers.fleet.toml`. `wov/apply-overlay.py` kör även det
idempotenta `wov/apply-model-tiers.py`, som behåller övriga fleetinställningar och
säkerhetskopierar ändrad fleet till `/opt/wow/backups/`. Inga API-nycklar läses av installationssteget.
Den befintliga Haiku-backenden måste vara konfigurerad. Kör först `wov/sql/model-tiers.sql`
via `db acore_characters` vid en ny installation.

## Vem får premium?
1. Guildvariant: bot med rang <= `OllamaChat.WoV.PremiumMaxRank` (2 = rang 0–2) i guild
   med en riktig spelare online, vid person-svar eller guildchatt. Officerchatt kräver
   en riktig guildpublik med rätt att läsa officerchatten.
2. Kontovariant: svar till ett explicit premiumkonto, eller snack där en sådan riktig
   spelare faktiskt kan höra kanalen/gruppen/närheten. Whisper använder bara sin mottagare.
   Samma fas/avstånd gäller för say/yell; faktisk kanalmedlemskap för kanalchatt.
   WoV:s fraktionsregel respekteras.

Ingen får premium genom GM-nivå eller automatiskt. `wov_premium_player` skapades tom.
Premiumkonton läses om högst en gång per minut; återkallelse kan därför dröja upp till 60 s.

## Operatörens kontolista
Allt via SentinelX som idiadmin, SQL via `db` i `ops/env.sh`.
Säkerhetskopiera berörda rader innan en uttryckligen begärd ändring.

```sql
-- Ersätt <account_id> med ett konto operatören valt; kör inte platshållaren.
INSERT IGNORE INTO wov_premium_player (account_id) VALUES (<account_id>);
DELETE FROM wov_premium_player WHERE account_id = <account_id>;
SELECT account_id, added_at FROM wov_premium_player;
```

## Kontroller
- `wov/tests/test-model-tiers.cpp`: ranggränser, mänsklig publik, kontoopt-in,
  avstånd/fas, guild/grupp/kanal och viskningar.
- `wov/tests/test-model-tiers.py`: modell-ID:n, fallbackkedjor och backendreferenser,
  utan att läsa några nycklar.
- Efter godkänd omstart: korta prov mot routerns `person`, `ambient`, `premium`,
  verifiera backend i wow-router-journalen och att fallback fungerar.
- I spelet: vanlig bot/normal mottagare ska använda Haiku; kvalificerad guildrang
  med riktig publik eller uttryckligt premiumkonto ska logga `WoV model tier` och använda Sonnet.
- Kontrollera att en premiumspelare utanför hörhåll/kanalen inte uppgraderar publiken.
- Avstängning av premium kräver bara båda `PremiumByGuildRank` och `PremiumByAccount`
  satta till 0, overlay och `ollama reload`. Routerfallback återställs separat vid behov.

## Återställning
Originalfiler och tidigare binär finns under `/opt/wow/backups/model-tiers-20261021-212407`.
Återställ bara de filer som hör till detta steg. Omstart av tjänster kräver operatörens
uttryckliga godkännande. Kontotabellen innehåller inga konton från installationen.
