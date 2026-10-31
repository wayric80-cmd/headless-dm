# AI-servern: två GTX 1070 (förberett 2026-10-31, inte aktivt)

## Hårdvara
- AI-server 192.168.0.115: Ryzen 5 2600 (6 kärnor/12 trådar, ingen iGPU, så x8/x8 fungerar), ASUS Prime X370.
- Uppgradering (operatören): RAM 8 → 16 GB, ett andra GTX 1070 8 GB. Totalt 16 GB VRAM.
- Nätaggregat Tecnoware Free Silent PRO 550 W (budgetmodell, en PCIe-kontakt). Båda korten matas via en
  splitter 8-pin → 2×8-pin, 18 AWG, på en egen PCIe-kabel från aggregatet.
- **Korten får gå på 75–95 W, aldrig standardgränsen 151 W.** Med gräns: ca 260–330 W för hela maskinen.
  Utan gräns: nära 400–450 W och över 200 W genom splittern – för mycket.
- Korten i de två PCIe 3.0 x16-platserna från CPU:n (x8/x8), inte den nedersta (chipset, x4). Se manualen
  för exakt platsfördelning. Kontrollera +12V-amperen på aggregatets etikett (minst ca 30 A, annars 75–85 W).
- Nuläge 2026-10-31: ett kort, power.limit 151 W (ingen gräns satt), persistence mode av, 74 °C i vila
  under last från spelservern. `gpu-fancurve.service` finns sedan tidigare.

## Filer
- `wov-gpu-power.service` – systemenhet (root): persistence mode + `nvidia-smi -pl 95` på alla kort vid boot.
- `gpu-power-check.sh` – vägrar starta llama-server om något kort har gräns > 100 W eller om kort saknas.
- `llama-server@.service` – användarenhet, en instans per kort: `@0` → GPU 0 port 8080, `@1` → GPU 1 port 8081.
- `fleet.two-gpu.toml` – `site/fleet.toml` med backend `gpu1` (8081): alla routes `["main", "gpu1"]`,
  person `["haiku", "main", "gpu1"]`, batch-lanes båda, judge på `gpu1`.

## Aktivera (Väg A: en Qwen3 8B per kort)
Efter monteringen, i ordning:
1. **Operatören (sudo, på AI-servern):**
   `sudo cp wov-gpu-power.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now wov-gpu-power`
   Kontroll: `nvidia-smi --query-gpu=index,power.limit,persistence_mode --format=csv` → 2 kort, 95 W, Enabled.
2. **Agenten (idiadmin, ingen sudo):** kopiera `gpu-power-check.sh` till `~/headlessdm-ai/bin/` (redan
   förberett där) och `llama-server@.service` till `~/.config/systemd/user/`, sedan
   `systemctl --user daemon-reload && systemctl --user disable --now llama-server && systemctl --user enable --now llama-server@0 llama-server@1`.
   Kontroll: båda svarar på `/health`, `nvidia-smi` visar en modell per kort.
3. **Spelservern:** backup av `site/fleet.toml`, `cp wov/ai-server/fleet.two-gpu.toml site/fleet.toml`,
   `sudo systemctl restart wow-router`. Därefter `CHAT_CONCURRENCY=4` i `site/site.env` →
   `conf-apply.py` → `apply-overlay.py` → omstart av wow-world (godkänd av operatören).
4. Mät: svarstid och tokens/s per kort under last, temperatur, effekt (ska ligga ≤ 95 W). Kör kontrollfrågorna.

Återställning: `systemctl --user disable --now llama-server@0 llama-server@1 && systemctl --user enable --now llama-server`,
gamla `site/fleet.toml` tillbaka, `CHAT_CONCURRENCY=2`, restart router/world. Lägg gärna till samma
`ExecStartPre=%h/headlessdm-ai/bin/gpu-power-check.sh 1 100` i gamla `llama-server.service`.

## Väg B (prov efter A): större modell över båda korten
Qwen3 14B Q4_K_M (ca 9 GB) delad med `--split-mode layer` över båda korten, en instans, färre slots.
Väntat 10–15 tokens/s mot 21–27 i dag. Avgörs med kontrollfrågorna sida vid sida mot 8B.
Qwen3 30B-A3B (MoE) får inte plats helt i 16 GB VRAM; prövas bara med delar på CPU (`--n-cpu-moe`).
Inför B (och gärna A): bygg aktuell llama.cpp med CUDA i stället för Ollamas 0.4.1-dev
(tar bort varningen för thinking-flaggan).

## Före flytten till garaget
Ping från spelservern ger dubblettsvar och en MAC-dubblett (22:e1:5d:0e:47:83) syns på nätet;
LAN-hastighet mot AI-servern bara 27–31 Mbit/s. Utred innan servern flyttas (CPE210-länken).
