#!/usr/bin/env python3
"""Compile the actual goal selectors with small world fixtures; no live server writes."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'src/modules/mod-playerbots/src/Ai/World/Rpg/Action/NewRpgBaseAction.cpp').read_text()
s=s[s.index('WorldPosition NewRpgBaseAction::SelectRandomGrindPos'):s.index('bool NewRpgBaseAction::SelectRandomFlightTaxiNode')]
preamble=r'''
#include <vector>
#include <cmath>
#include <cassert>
using uint32=unsigned;
#define LOG_DEBUG(...)
constexpr unsigned AREA_FLAG_CAPITAL=1;
struct WorldLocation { int map=-1; float x=0; int GetMapId()const{return map;} float GetPositionX()const{return x;} float GetPositionY()const{return 0;} float GetPositionZ()const{return 0;} };
struct WorldPosition:WorldLocation {WorldPosition()=default;WorldPosition(WorldLocation const& p):WorldLocation(p){};bool operator==(WorldPosition const& p)const{return map==p.map&&x==p.x;}};
struct AreaTableEntry {unsigned flags=0;};
struct Store {AreaTableEntry area;AreaTableEntry const* LookupEntry(unsigned){return &area;}} sAreaTableStore;
struct Map {unsigned GetZoneId(unsigned,float x,float,float){return x>=0?1:2;}};
struct Player {Map map; unsigned GetLevel(){return 30;} unsigned GetZoneId(){return 1;} unsigned GetMapId(){return 1;} unsigned GetPhaseMask(){return 1;} Map* GetMap(){return &map;} float GetExactDist(WorldLocation const& p){return std::abs(p.x);}};
struct Travel {std::vector<WorldLocation> locs;auto const& GetLocsPerLevelCache(unsigned){return locs;} auto GetTravelHubs(Player*){return locs;}} travel;
auto* travelPtr=&travel;
#define sTravelMgr (*travelPtr)
unsigned urand(unsigned lo,unsigned){return lo;}
struct NewRpgBaseAction {static WorldPosition SelectRandomGrindPos(Player*);static WorldPosition SelectRandomCampPos(Player*);};
'''
checks=r'''
int main(){Player p;
 travel.locs={{1,-100}};assert(NewRpgBaseAction::SelectRandomGrindPos(&p).x==-100);assert(NewRpgBaseAction::SelectRandomCampPos(&p).x==-100);
 travel.locs={{1,-100},{1,200}};assert(NewRpgBaseAction::SelectRandomGrindPos(&p).x==200);assert(NewRpgBaseAction::SelectRandomCampPos(&p).x==200);
 travel.locs={{1,-3000},{2,-100}};assert(NewRpgBaseAction::SelectRandomGrindPos(&p)==WorldPosition());assert(NewRpgBaseAction::SelectRandomCampPos(&p)==WorldPosition());
 travel.locs={{1,-20}};assert(NewRpgBaseAction::SelectRandomCampPos(&p)==WorldPosition());
 travel.locs={{1,-2500}};assert(NewRpgBaseAction::SelectRandomCampPos(&p).x==-2500);
}
'''
with tempfile.TemporaryDirectory() as d:
 path=Path(d)/'test.cpp';path.write_text(preamble+s+checks)
 subprocess.run(['g++','-std=c++17',str(path),'-o',str(Path(d)/'test')],check=True)
 subprocess.run([str(Path(d)/'test')],check=True)
print('8 goal-selection assertions passed: neighboring fallback, local preference, map/range rejection and camp distance boundaries')
