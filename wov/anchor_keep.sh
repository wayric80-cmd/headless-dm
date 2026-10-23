#!/bin/bash
# wov: keep the progression of bots people know. Bots a real player has met (sentiment/relationship rows),
# bots in a guild with a real player and every bot at level 60 get a row in playerbots_bot_anchor
# (PersistentProgression = 2), so level brackets never reroll them (a 60 suddenly level 8 is what it prevents).
# Idempotent, only adds rows with source wov-*. Run from guild_fill (every 20 min).
cd "$(dirname "$0")/.." || exit 1
. ops/env.sh >/dev/null 2>&1
R='SELECT c.guid FROM acore_characters.characters c JOIN acore_auth.account a ON a.id=c.account WHERE a.username NOT LIKE "RNDBOT%"'
B='SELECT c.guid FROM acore_characters.characters c JOIN acore_auth.account a ON a.id=c.account WHERE a.username LIKE "RNDBOT%"'
db acore_playerbots -N -e "
INSERT IGNORE INTO playerbots_bot_anchor (bot, anchor, source)
  SELECT s.bot_guid, MIN(s.player_guid), 'wov-met' FROM acore_characters.mod_ollama_chat_bot_player_sentiments s
  WHERE s.player_guid IN ($R) AND s.bot_guid IN ($B) GROUP BY s.bot_guid;
INSERT IGNORE INTO playerbots_bot_anchor (bot, anchor, source)
  SELECT r.bot_guid, MIN(r.other_guid), 'wov-met' FROM acore_characters.mod_ollama_chat_relationships r
  WHERE r.other_guid IN ($R) AND r.bot_guid IN ($B) GROUP BY r.bot_guid;
INSERT IGNORE INTO playerbots_bot_anchor (bot, anchor, source)
  SELECT m.guid, MIN(rm.guid), 'wov-guild' FROM acore_characters.guild_member m
  JOIN acore_characters.guild_member rm ON rm.guildid=m.guildid AND rm.guid IN ($R) WHERE m.guid IN ($B) GROUP BY m.guid;
INSERT IGNORE INTO playerbots_bot_anchor (bot, anchor, source)
  SELECT c.guid, c.guid, 'wov-max' FROM acore_characters.characters c WHERE c.level >= 60 AND c.guid IN ($B);
SELECT COUNT(*) FROM playerbots_bot_anchor;"
