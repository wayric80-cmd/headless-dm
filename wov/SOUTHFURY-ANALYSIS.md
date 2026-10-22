# Southfury-klungan, 2026-10-22

## Verifierat
- Klungan återkommer kring map1,x1927,y-3727,Southfury River (Azshara).
- Flera separata botgrupper drabbas. Ledarna står utan master; följare stannar hos dem.
- Lägre nivåer har lämnat platsen efter ändringen som tillät närliggande mål över zongränsen. Senare återstår framför allt nivå35–38.
- Playerbots.log visar upprepat för Tzuljaaro, Mondlicht och Blitsi: 0 giltiga grindmål ur totalt782/685/737 och 0 giltiga resehubbar ur9/7/8. Den vanliga AI:n kör alltså målval; detta är inte bevis för en frusen AI-kö.
- SelectRandomGrindPos och SelectRandomCampPos filtrerar på karta, avstånd och nivåanpassade cachelistor. Grannzonsfixen behöll gränsen2500yd. Ingen kandidat inom den radien ger fortsatt vila.
- GetOptimalFlightDestinations kräver en flygmästare inom500yd. Närmaste vänliga FM är Doras i Orgrimmar, cirka640yd från klungan. Botarna kan därför inte välja en vanlig flygresa där de står.

## Orsak och begränsningar
Det finns ett verifierat tomrum i aktiviteternas målval: lokala nivåanpassade mål saknas samtidigt som flygmästaren ligger utanför flygresefunktionens närhetsgräns. REST väljs igen, följare stannar och grupper kan ombildas på samma plats. Att återställa REST till IDLE löser inte den tomma mållistan.

Detta förklarar stillaståendet för de granskade botarna. Den ursprungliga ankomsten till platsen och alla enskilda återkomster är inte spårade. Påstå inte att samtliga åtta har samma verifierade orsak utan nya loggprov.

## Förberedd ändring
När ordinarie campmål och grannzonsmål båda saknas används närmaste vänliga flygmästare som reservmål. Befintliga fraktionsspecifika FM-cache och samma karta krävs. Minst nivå10, giltig taxinod och avstånd50–10000yd. Botarna går via ordinarie rörelselager; inga nya teleporteringar eller ändringar av hastigheter/grupper/LLM-routing.

Efter ankomsten kan vanliga NPC-aktiviteter och flygresor mot nivåanpassade områden bli tillgängliga. Ordinarie mål har alltid prioritet; detta är en utväg ur ett tomt målval.

## Kontroll
15 tester kör de riktiga målväljarnas kod mot små världsstubbar: lokal prioritet, grannzon, kart-/avståndsgränser och FM-reservens villkor. Bygge/install lyckat18,91s. Backup /opt/wow/backups/no-goal-fallback-20261022-211322. Ingen aktivering utan nytt omstartsgodkännande.

Efter godkänd omstart: följ de aktuella ledarnas positioner och mål tills de verkligen lämnar floden. Följ även återkomst/klumpning vid FM. Enbart minskad klunga direkt efter omstart räcker inte som bevis. Botinloggningen tar tid; kontrollera samma GUID när de är online.
