#!/usr/bin/env python3
"""Way of Vanilla - fresh start (launch day): everyone starts at level 1.

  python3 wov/fresh_start.py plan
      Read-only. What a fresh start would reset and delete, counted on the live databases.
  python3 wov/fresh_start.py dryrun
      Copies the databases into a throwaway MySQL in /tmp (port 3399), runs the full reset on the copy,
      checks the result and removes the copy again. The live server is not touched.
  python3 wov/fresh_start.py apply --launch N --yes
      Launch day. wow-world must be stopped first (sudo systemctl stop wow-world). Takes a full SQL backup
      to /opt/wow/backups/fresh-start-<time>/, resets the databases, sets AiPlayerbot.WoV.FreshStart = N and
      clears AiPlayerbot.WoV.Bands in the overlay and runs apply-overlay.py. Then: sudo systemctl start wow-world.

  --real-chars delete|keep   characters on real (non-bot) accounts: deleted (default; the accounts stay) or untouched
  --keep-account NAME        an account that is left alone entirely (default: MERCHANTS, the auction house bot)
  --keep-dk                  keep death knight bots (default: each becomes another class its race can be, picked so
                             the classes of that race even out; Way of Vanilla has no death knights, blood elves or
                             draenei, see CharacterCreating.Disabled.* in worldserver.wov.overrides)

What happens
  Bots (accounts RNDBOT*): level 1 (death knights 55), no xp/money/items/spells/skills/talents/quests/reputation/
  achievements/pets/honour/titles/taxi nodes/exploration, standing in their race's starting area with the hearth
  there. Name, look, the player behind them (wov_player, lore_character, BIO personality) and the name pools stay.
  On their first login the worldserver gives them their level-1 spells, skills and gear (AiPlayerbot.WoV.FreshStart).
  Everyone: guilds, groups, instance saves, mail, auction house, arena teams, petitions, calendar, ledger history
  (portal chronicle starts at Day 1), battles, craft orders, bot memories/relationships/chat history are emptied.
  Level-anchor and bot schedule state in acore_playerbots is cleared so the bots are picked and placed afresh.
No secrets are printed.
"""
import argparse, os, subprocess, sys, tempfile, time, shutil

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
C, P, A, W = 'acore_characters', 'acore_playerbots', 'acore_auth', 'acore_world'
BOT_LIKE = 'RNDBOT%'
DK_LEVEL = 55
EXPLORED = '0 ' * 128

# per character: (table, column) rows removed for every reset bot and every deleted character
PER_CHAR = [
    ('character_achievement', 'guid'), ('character_achievement_progress', 'guid'),
    ('character_achievement_offline_updates', 'guid'), ('character_action', 'guid'), ('character_aura', 'guid'),
    ('character_arena_stats', 'guid'), ('character_battleground_random', 'guid'),
    ('character_brew_of_the_month', 'guid'), ('character_entry_point', 'guid'), ('character_equipmentsets', 'guid'),
    ('character_gifts', 'guid'), ('character_glyphs', 'guid'), ('character_instance', 'guid'),
    ('character_inventory', 'guid'), ('character_queststatus', 'guid'), ('character_queststatus_daily', 'guid'),
    ('character_queststatus_monthly', 'guid'), ('character_queststatus_rewarded', 'guid'),
    ('character_queststatus_seasonal', 'guid'), ('character_queststatus_weekly', 'guid'),
    ('character_reputation', 'guid'), ('character_skills', 'guid'), ('character_social', 'guid'),
    ('character_social', 'friend'), ('character_spell', 'guid'), ('character_spell_cooldown', 'guid'),
    ('character_talent', 'guid'), ('character_stats', 'guid'), ('character_account_data', 'guid'),
    ('character_settings', 'guid'), ('character_homebind', 'guid'), ('corpse', 'guid'),
    ('item_instance', 'owner_guid'), ('item_refund_instance', 'player_guid'), ('battleground_deserters', 'guid'),
    ('lfg_data', 'guid'), ('quest_tracker', 'character_guid'), ('recovery_item', 'Guid'),
    ('pvpstats_players', 'character_guid'), ('gm_ticket', 'playerGuid'),
]
# only for deleted (real-account) characters
PER_DELETED = [('character_declinedname', 'guid'), ('character_banned', 'guid'), ('player_main', 'main_guid'),
               ('person_kind', 'guid'), ('lore_main', 'guid'), ('lore_alt', 'guid'), ('lore_character', 'guid'),
               ('wov_player', 'guid'), ('mod_ollama_chat_personality', 'guid'), ('characters', 'guid')]
# emptied completely
WIPE = ['auctionhouse', 'mail', 'mail_items', 'mail_server_character', 'guild', 'guild_rank', 'guild_member',
        'guild_member_withdraw', 'guild_bank_tab', 'guild_bank_right', 'guild_bank_item', 'guild_bank_eventlog',
        'guild_eventlog', 'lore_guild', 'wov_guild_type', 'arena_team', 'arena_team_member', 'petition',
        'petition_sign', 'groups', 'group_member', 'instance', 'character_instance', 'account_instance_times',
        'instance_saved_go_state_data', 'creature_respawn', 'gameobject_respawn', 'corpse', 'calendar_events',
        'calendar_invites', 'lfg_data', 'ledger_event', 'ledger_chat', 'ledger_auction', 'wov_battle',
        'wov_craft_order', 'wov_regear', 'wov_regear_bracket', 'wov_wealth', 'wov_raid_loot_rule', 'wov_raid_dkp',
        'wov_raid_loot', 'pvpstats_battlegrounds',
        'pvpstats_players', 'log_arena_fights', 'log_arena_memberstats', 'log_encounter', 'log_money',
        'quest_tracker', 'item_loot_storage', 'item_soulbound_trade_data', 'item_refund_instance',
        'mod_ollama_chat_bot_player_sentiments', 'mod_ollama_chat_event_buffer', 'mod_ollama_chat_history',
        'mod_ollama_chat_memories', 'mod_ollama_chat_relationships', 'market_word']
# acore_playerbots
PB_PER_BOT = [('playerbots_random_bots', 'bot'), ('playerbots_db_store', 'guid')]
PB_WIPE = ['playerbots_bot_anchor']

# set on every bot (only columns that exist are used)
BOT_SET = {
    'level': f'IF(c.class=6,{DK_LEVEL},1)', 'xp': '0', 'money': '0', 'map': 'p.map', 'zone': 'p.zone',
    'position_x': 'p.position_x', 'position_y': 'p.position_y', 'position_z': 'p.position_z',
    'orientation': 'p.orientation', 'instance_id': '0', 'instance_mode_mask': '0', 'taximask': "''",
    'taxi_path': "''", 'online': '0', 'totaltime': '0', 'leveltime': '0', 'is_logout_resting': '0',
    'rest_bonus': '0', 'resettalents_cost': '0', 'resettalents_time': '0', 'trans_x': '0', 'trans_y': '0',
    'trans_z': '0', 'trans_o': '0', 'transguid': '0', 'stable_slots': '0', 'death_expire_time': '0',
    'arenaPoints': '0', 'totalHonorPoints': '0', 'todayHonorPoints': '0', 'yesterdayHonorPoints': '0',
    'totalKills': '0', 'todayKills': '0', 'yesterdayKills': '0', 'chosenTitle': '0', 'knownCurrencies': '0',
    'watchedFaction': '4294967295', 'drunk': '0', 'health': '50', 'power1': '0', 'power2': '0', 'power3': '0',
    'power4': '0', 'power5': '0', 'power6': '0', 'power7': '0', 'talentGroupsCount': '1',
    'activeTalentGroup': '0', 'exploredZones': f"'{EXPLORED}'", 'equipmentCache': "''", 'ammoId': '0',
    'knownTitles': "'0 0 0 0 0 0'", 'actionBars': '0', 'grantableLevels': '0', 'innTriggerId': '0',
    'extraBonusTalentCount': '0', 'bankSlots': '0',
}


def env():
    e = dict(os.environ)
    out = subprocess.run(['bash', '-c', '. ops/env.sh >/dev/null 2>&1; env -0'], cwd=REPO, capture_output=True)
    for kv in out.stdout.split(b'\0'):
        if b'=' in kv:
            k, v = kv.split(b'=', 1)
            e[k.decode()] = v.decode(errors='replace')
    return e


class DB:
    """mysql client against the live server (TCP, password from site/secrets.env) or a throwaway one (socket)."""

    def __init__(self, sock=None):
        self.sock, self.e = sock, env()

    def args(self, tool='mysql'):
        if self.sock:
            return [tool, '--default-character-set=utf8mb4', '-S', self.sock, '-uroot']
        return [tool, '--default-character-set=utf8mb4', '-h' + self.e.get('DB_HOST', '127.0.0.1'),
                '-P' + self.e.get('DB_PORT', '3306'), '-u' + self.e.get('DB_USER', 'acore')]

    def penv(self):
        e = dict(os.environ)
        if not self.sock:
            e['MYSQL_PWD'] = self.e.get('DB_PASS', '')
        return e

    def q(self, sql, db=C):
        r = subprocess.run(self.args() + ['-N', '--batch', db, '-e', sql], capture_output=True, text=True,
                           env=self.penv())
        if r.returncode:
            sys.exit('SQL failed: ' + r.stderr.strip()[:500])
        return [l.split('\t') for l in r.stdout.splitlines() if l]

    def run_file(self, path, db=C):
        with open(path) as f:
            r = subprocess.run(self.args() + [db], stdin=f, capture_output=True, text=True, env=self.penv())
        if r.returncode:
            sys.exit('SQL failed: ' + r.stderr.strip()[:800])
        return r.stdout

    def tables(self, db):
        return {r[0] for r in self.q(f"SELECT table_name FROM information_schema.tables WHERE table_schema='{db}' "
                                     f"AND table_type='BASE TABLE'")}  # views are left alone

    def columns(self, db, table):
        return {r[0] for r in self.q(f"SELECT column_name FROM information_schema.columns WHERE table_schema='{db}' "
                                     f"AND table_name='{table}'")}


def dk_moves(db, keep_accounts):
    """death knight bots -> (guid, new class): a class the race can be, the least common one among that race's bots"""
    keep = ','.join("'" + a.replace("'", "") + "'" for a in keep_accounts) or "''"
    bots = f"FROM {C}.characters c JOIN {A}.account a ON a.id=c.account WHERE a.username LIKE '{BOT_LIKE}' AND a.username NOT IN ({keep})"
    combos = {}
    for race, cls in db.q(f'SELECT race, class FROM {W}.playercreateinfo WHERE class<>6'):
        combos.setdefault(int(race), []).append(int(cls))
    count = {(int(r), int(c)): int(n) for r, c, n in db.q(f'SELECT c.race, c.class, COUNT(*) {bots} AND c.class<>6 GROUP BY c.race, c.class')}
    moves = []
    for guid, race in db.q(f'SELECT c.guid, c.race {bots} AND c.class=6 ORDER BY c.guid'):
        opts = combos.get(int(race))
        if not opts:
            continue
        cls = min(opts, key=lambda k: (count.get((int(race), k), 0), k))
        count[(int(race), cls)] = count.get((int(race), cls), 0) + 1
        moves.append((int(guid), cls))
    return moves


def reset_sql(db, keep_accounts, real_mode, convert_dk=True):
    ct, pt = db.tables(C), db.tables(P)
    keep = ','.join("'" + a.replace("'", "") + "'" for a in keep_accounts) or "''"
    s = ['SET SESSION sql_mode=REPLACE(@@sql_mode,"ONLY_FULL_GROUP_BY","");', 'SET autocommit=1;',
         'SET FOREIGN_KEY_CHECKS=0;',
         f'DROP TEMPORARY TABLE IF EXISTS {C}.wov_fs_bot, {C}.wov_fs_del, {C}.wov_fs_all;',
         f"CREATE TEMPORARY TABLE {C}.wov_fs_bot (guid INT UNSIGNED PRIMARY KEY) SELECT c.guid FROM {C}.characters c "
         f"JOIN {A}.account a ON a.id=c.account WHERE a.username LIKE '{BOT_LIKE}' AND a.username NOT IN ({keep});",
         f'CREATE TEMPORARY TABLE {C}.wov_fs_del (guid INT UNSIGNED PRIMARY KEY);']
    if real_mode == 'delete':
        s.append(f"INSERT INTO {C}.wov_fs_del SELECT c.guid FROM {C}.characters c JOIN {A}.account a ON a.id=c.account "
                 f"WHERE a.username NOT LIKE '{BOT_LIKE}' AND a.username NOT IN ({keep});")
    s += [f'CREATE TEMPORARY TABLE {C}.wov_fs_all (guid INT UNSIGNED PRIMARY KEY) SELECT guid FROM {C}.wov_fs_bot;',
          f'INSERT INTO {C}.wov_fs_all SELECT guid FROM {C}.wov_fs_del;']
    # pets of everyone touched
    if 'character_pet' in ct:
        for t in ('pet_aura', 'pet_spell', 'pet_spell_cooldown'):
            if t in ct:
                s.append(f'DELETE x FROM {C}.{t} x JOIN {C}.character_pet cp ON cp.id=x.guid '
                         f'JOIN {C}.wov_fs_all f ON f.guid=cp.owner;')
        for t in ('character_pet_declinedname', 'character_pet'):
            if t in ct:
                s.append(f'DELETE x FROM {C}.{t} x JOIN {C}.wov_fs_all f ON f.guid=x.owner;')
    # mail sent by or to them (the items in it go with item_instance below)
    for tbl, col in PER_CHAR:
        if tbl in ct and col in db.columns(C, tbl):
            s.append(f'DELETE x FROM {C}.{tbl} x JOIN {C}.wov_fs_all f ON f.guid=x.{col};')
    for t in WIPE:
        if t in ct:
            s.append(f'DELETE FROM {C}.{t};')
    if 'lore_character' in ct and 'guildid' in db.columns(C, 'lore_character'):
        s.append(f'UPDATE {C}.lore_character SET guildid=NULL;')
    for tbl, col in PER_DELETED:
        if tbl in ct and col in db.columns(C, tbl):
            s.append(f'DELETE x FROM {C}.{tbl} x JOIN {C}.wov_fs_del f ON f.guid=x.{col};')
    # no death knights: each becomes another class of its race (before the start areas are looked up)
    if convert_dk:
        by_cls = {}
        for guid, cls in dk_moves(db, keep_accounts):
            by_cls.setdefault(cls, []).append(str(guid))
        for cls, guids in sorted(by_cls.items()):
            s.append(f'UPDATE {C}.characters SET class={cls} WHERE guid IN ({",".join(guids)});')
    # the bots themselves: level 1 in the starting area of their race and class, hearth there
    cols = db.columns(C, 'characters')
    sets = ', '.join(f'c.`{k}`={v}' for k, v in BOT_SET.items() if k in cols)
    s.append(f'UPDATE {C}.characters c JOIN {C}.wov_fs_bot b ON b.guid=c.guid '
             f'JOIN {W}.playercreateinfo p ON p.race=c.race AND p.class=c.class SET {sets};')
    s.append(f'INSERT INTO {C}.character_homebind (guid, mapId, zoneId, posX, posY, posZ) '
             f'SELECT c.guid, p.map, p.zone, p.position_x, p.position_y, p.position_z FROM {C}.characters c '
             f'JOIN {C}.wov_fs_bot b ON b.guid=c.guid JOIN {W}.playercreateinfo p ON p.race=c.race AND p.class=c.class;')
    # items nobody holds any more (auction house, mail, guild banks, the reset characters)
    held = [f'SELECT item FROM {C}.character_inventory']
    for t, col in (('mail_items', 'item_guid'), ('guild_bank_item', 'item_guid'), ('auctionhouse', 'itemguid')):
        if t in ct:
            held.append(f'SELECT {col} FROM {C}.{t}')
    s.append(f'CREATE TEMPORARY TABLE {C}.wov_fs_held (guid INT UNSIGNED PRIMARY KEY) '
             f'SELECT DISTINCT item AS guid FROM ({" UNION ".join(held)}) h;')
    s.append(f'DELETE ii FROM {C}.item_instance ii LEFT JOIN {C}.wov_fs_held h ON h.guid=ii.guid WHERE h.guid IS NULL;')
    # acore_playerbots: schedules, level/factory state and anchors of the bots
    for tbl, col in PB_PER_BOT:
        if tbl in pt and col in db.columns(P, tbl):
            s.append(f'DELETE x FROM {P}.{tbl} x JOIN {C}.wov_fs_bot b ON b.guid=x.{col};')
    for t in PB_WIPE:
        if t in pt:
            s.append(f'DELETE FROM {P}.{t};')
    s.append(f'UPDATE {A}.realmcharacters rc SET numchars=(SELECT COUNT(*) FROM {C}.characters c WHERE c.account=rc.acctid);')
    s.append('SET FOREIGN_KEY_CHECKS=1;')
    return '\n'.join(s) + '\n'


def counts(db, keep_accounts, real_mode, label):
    keep = ','.join("'" + a.replace("'", "") + "'" for a in keep_accounts) or "''"
    one = lambda sql, d=C: int((db.q(sql, d) or [['0']])[0][0] or 0)
    bots = f"SELECT c.guid FROM characters c JOIN {A}.account a ON a.id=c.account WHERE a.username LIKE '{BOT_LIKE}'"
    real = (f"SELECT c.guid FROM characters c JOIN {A}.account a ON a.id=c.account WHERE a.username NOT LIKE '{BOT_LIKE}' "
            f"AND a.username NOT IN ({keep})")
    ct = db.tables(C)
    r = {
        'bots': one(f'SELECT COUNT(*) FROM ({bots}) b'),
        'death knight bots': one(f'SELECT COUNT(*) FROM characters WHERE guid IN ({bots}) AND class=6'),
        'bots above start level': one(f'SELECT COUNT(*) FROM characters WHERE guid IN ({bots}) AND level > IF(class=6,{DK_LEVEL},1)'),
        'bots outside their starting area': one(
            f'SELECT COUNT(*) FROM characters c JOIN {W}.playercreateinfo p ON p.race=c.race AND p.class=c.class '
            f'WHERE c.guid IN ({bots}) AND (c.map<>p.map OR ABS(c.position_x-p.position_x)>1 OR ABS(c.position_y-p.position_y)>1)'),
        'bot items': one(f'SELECT COUNT(*) FROM item_instance WHERE owner_guid IN ({bots})'),
        'bot spells': one(f'SELECT COUNT(*) FROM character_spell WHERE guid IN ({bots})'),
        'bot gold (g)': one(f'SELECT COALESCE(SUM(money),0) DIV 10000 FROM characters WHERE guid IN ({bots})'),
        'characters on real accounts to ' + real_mode: one(f'SELECT COUNT(*) FROM ({real}) r'),
        'kept accounts characters': one(f"SELECT COUNT(*) FROM characters c JOIN {A}.account a ON a.id=c.account WHERE a.username IN ({keep})"),
        'guilds': one('SELECT COUNT(*) FROM guild'),
        'mail': one('SELECT COUNT(*) FROM mail'),
        'auctions': one('SELECT COUNT(*) FROM auctionhouse'),
        'ledger events': one('SELECT COUNT(*) FROM ledger_event') if 'ledger_event' in ct else 0,
        'bot memories': one('SELECT COUNT(*) FROM mod_ollama_chat_memories') if 'mod_ollama_chat_memories' in ct else 0,
        'items in total': one('SELECT COUNT(*) FROM item_instance'),
        'players behind bots (kept)': one('SELECT COUNT(*) FROM wov_player') if 'wov_player' in ct else 0,
        'lore characters (kept)': one('SELECT COUNT(*) FROM lore_character') if 'lore_character' in ct else 0,
        'personalities (kept)': one('SELECT COUNT(*) FROM mod_ollama_chat_personality') if 'mod_ollama_chat_personality' in ct else 0,
        'bot schedule rows': one(f'SELECT COUNT(*) FROM {P}.playerbots_random_bots WHERE bot IN (SELECT guid FROM {C}.characters c JOIN {A}.account a ON a.id=c.account WHERE a.username LIKE \'{BOT_LIKE}\')'),
        'level anchors': one(f'SELECT COUNT(*) FROM {P}.playerbots_bot_anchor') if 'playerbots_bot_anchor' in db.tables(P) else 0,
    }
    print(f'\n{label}')
    for k, v in r.items():
        print(f'  {k:40s} {v}')
    return r


def dryrun(args):
    live = DB()
    d = tempfile.mkdtemp(prefix='wov-fresh-', dir='/tmp')
    sock, data = os.path.join(d, 'sock'), os.path.join(d, 'data')
    print(f'throwaway MySQL in {d}')
    srv = None
    try:
        subprocess.run(['/usr/sbin/mysqld', '--no-defaults', '--initialize-insecure', f'--datadir={data}'],
                       check=True, capture_output=True)
        srv = subprocess.Popen(['/usr/sbin/mysqld', '--no-defaults', f'--datadir={data}', f'--socket={sock}',
                                '--port=3399', '--bind-address=127.0.0.1', '--mysqlx=OFF',
                                '--innodb-buffer-pool-size=256M', '--innodb-log-file-size=64M',
                                f'--log-error={d}/err.log', f'--pid-file={d}/pid', '--skip-log-bin'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            if os.path.exists(sock):
                break
            time.sleep(1)
        tmp = DB(sock)
        tmp.q(f'CREATE DATABASE {C}; CREATE DATABASE {P}; CREATE DATABASE {A}; CREATE DATABASE {W};', 'mysql')
        # views and routines in the copy carry the live definer
        tmp.q("CREATE USER 'acore'@'localhost'; GRANT ALL ON *.* TO 'acore'@'localhost';", 'mysql')
        big_wipe = ['ledger_event', 'ledger_chat', 'ledger_auction']
        plan = [(A, [], ['account', 'realmcharacters']),
                (W, [], ['playercreateinfo']),
                (C, [f'--ignore-table={C}.{t}' for t in big_wipe], []),
                (C, ['--no-data'], big_wipe),
                (P, [f'--ignore-table={P}.playerbots_travelnode_path', f'--ignore-table={P}.playerbots_travelnode_link',
                     f'--ignore-table={P}.playerbots_travelnode'], [])]
        for dbn, extra, tables in plan:
            t0 = time.time()
            dump = subprocess.Popen(live.args('mysqldump') + ['--single-transaction', '--no-tablespaces',
                                    '--skip-triggers', '--set-gtid-purged=OFF'] + extra + [dbn] + tables,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=live.penv())
            load = subprocess.run(tmp.args() + [dbn], stdin=dump.stdout, capture_output=True, text=True)
            dump.wait()
            if dump.returncode or load.returncode:
                sys.exit(f'copy of {dbn} failed: {dump.stderr.read().decode()[:300]} {load.stderr[:300]}')
            print(f'  copied {dbn} {" ".join(tables)} ({time.time() - t0:.0f} s)')
        # (the big ledger tables are copied empty: they are only emptied, never read, by the reset)
        before = counts(tmp, args.keep_account, args.real_chars, 'copy before the reset:')
        sql = reset_sql(tmp, args.keep_account, args.real_chars, not args.keep_dk)
        path = os.path.join(d, 'reset.sql')
        open(path, 'w').write(sql)
        t0 = time.time()
        tmp.run_file(path)
        print(f'\nreset ran on the copy in {time.time() - t0:.0f} s ({sql.count(chr(10))} statements)')
        after = counts(tmp, args.keep_account, args.real_chars, 'copy after the reset:')
        must_zero = ['bots above start level', 'bots outside their starting area', 'bot items', 'bot spells',
                     'bot gold (g)', 'guilds', 'mail', 'auctions', 'bot memories', 'bot schedule rows', 'level anchors']
        if args.real_chars == 'delete':
            must_zero.append('characters on real accounts to delete')
        if not args.keep_dk:
            must_zero.append('death knight bots')
        bad = [k for k in must_zero if after[k]]
        for k in ('bots', 'players behind bots (kept)', 'lore characters (kept)', 'kept accounts characters'):
            if after[k] != before[k]:
                bad.append(f'{k} changed {before[k]} -> {after[k]}')
        orphans = int(tmp.q(f'SELECT COUNT(*) FROM {C}.item_instance ii LEFT JOIN {C}.character_inventory ci ON ci.item=ii.guid WHERE ci.item IS NULL')[0][0])
        if orphans:
            bad.append(f'{orphans} items held by nobody')
        homeless = int(tmp.q(f"SELECT COUNT(*) FROM {C}.characters c JOIN {A}.account a ON a.id=c.account LEFT JOIN {C}.character_homebind h ON h.guid=c.guid WHERE a.username LIKE '{BOT_LIKE}' AND h.guid IS NULL")[0][0])
        if homeless:
            bad.append(f'{homeless} bots without a hearth')
        zones = tmp.q(f"SELECT c.map, c.zone, COUNT(*) FROM {C}.characters c JOIN {A}.account a ON a.id=c.account WHERE a.username LIKE '{BOT_LIKE}' GROUP BY c.map, c.zone ORDER BY 3 DESC")
        cls = tmp.q(f"SELECT c.class, COUNT(*) FROM {C}.characters c JOIN {A}.account a ON a.id=c.account WHERE a.username LIKE '{BOT_LIKE}' GROUP BY c.class ORDER BY c.class")
        print('\nbots per class (class: count): ' + ', '.join(f'{c}: {n}' for c, n in cls))
        print('\nbots per starting zone (map/zone: count): ' + ', '.join(f'{m}/{z}: {n}' for m, z, n in zones))
        print('\nRESULT: ' + ('OK, the reset does what it should' if not bad else 'PROBLEMS: ' + '; '.join(bad)))
        return 0 if not bad else 1
    finally:
        if srv:
            subprocess.run(['mysqladmin', '-S', sock, '-uroot', 'shutdown'], capture_output=True)
            try:
                srv.wait(60)
            except subprocess.TimeoutExpired:
                srv.kill()
        shutil.rmtree(d, ignore_errors=True)
        print(f'throwaway MySQL removed')


def set_overlay(launch):
    path = os.path.join(REPO, 'wov', 'conf', 'playerbots.wov.overrides')
    lines = open(path).read().splitlines()
    want = {'AiPlayerbot.WoV.FreshStart': str(launch), 'AiPlayerbot.WoV.FreshStart.Only': '', 'AiPlayerbot.WoV.Bands': ''}
    out, seen = [], set()
    for l in lines:
        k = l.split('=', 1)[0].strip()
        if k in want:
            out.append(f'{k} = {want[k]}'.rstrip())
            seen.add(k)
        else:
            out.append(l)
    for k, v in want.items():
        if k not in seen:
            out.append(f'{k} = {v}'.rstrip())
    open(path, 'w').write('\n'.join(out) + '\n')
    subprocess.run(['python3', 'wov/apply-overlay.py'], cwd=REPO, check=True)


def apply(args):
    if not args.yes or not args.launch:
        sys.exit('apply needs --launch N and --yes')
    st = subprocess.run(['systemctl', 'is-active', 'wow-world'], capture_output=True, text=True).stdout.strip()
    if st in ('active', 'activating', 'reloading'):
        sys.exit('wow-world is running: stop it first (sudo systemctl stop wow-world)')
    live = DB()
    stamp = time.strftime('%Y%m%d-%H%M%S')
    bdir = f'/opt/wow/backups/fresh-start-{stamp}'
    os.makedirs(bdir, exist_ok=True)
    for dbn in (A, C, P):
        out = os.path.join(bdir, f'{dbn}.sql.gz')
        with open(out, 'wb') as f:
            dump = subprocess.Popen(live.args('mysqldump') + ['--single-transaction', '--no-tablespaces',
                                    '--routines', '--set-gtid-purged=OFF', dbn], stdout=subprocess.PIPE, env=live.penv())
            gz = subprocess.run(['gzip', '-c'], stdin=dump.stdout, stdout=f)
            dump.wait()
            if dump.returncode or gz.returncode:
                sys.exit(f'backup of {dbn} failed, nothing was changed')
        print(f'backup {out} ({os.path.getsize(out) // 1048576} MB)')
    counts(live, args.keep_account, args.real_chars, 'before:')
    sql = reset_sql(live, args.keep_account, args.real_chars, not args.keep_dk)
    path = os.path.join(bdir, 'reset.sql')
    open(path, 'w').write(sql)
    live.run_file(path)
    counts(live, args.keep_account, args.real_chars, 'after:')
    set_overlay(args.launch)
    with open(os.path.join(REPO, 'logs', 'fresh-start-at'), 'w') as f:  # guild_fill.py ramps guilds up from here
        f.write(f'{time.time():.0f} launch {args.launch}\n')
    print(f'\nDone. AiPlayerbot.WoV.FreshStart = {args.launch}, level bands off. Now: sudo systemctl start wow-world\n'
          f'Restore if needed: zcat {bdir}/<db>.sql.gz | mysql <db>')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'dryrun', 'apply'])
    ap.add_argument('--real-chars', choices=['delete', 'keep'], default='delete')
    ap.add_argument('--keep-account', action='append', default=None)
    ap.add_argument('--launch', type=int, default=0)
    ap.add_argument('--yes', action='store_true')
    ap.add_argument('--keep-dk', action='store_true')
    args = ap.parse_args()
    if args.keep_account is None:
        args.keep_account = ['MERCHANTS']
    if args.mode == 'plan':
        counts(DB(), args.keep_account, args.real_chars, 'live databases now (nothing is changed):')
        return 0
    if args.mode == 'dryrun':
        return dryrun(args)
    return apply(args)


if __name__ == '__main__':
    sys.exit(main())
