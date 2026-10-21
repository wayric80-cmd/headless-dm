#include "../../src/modules/mod-ollama-chat/src/wov_model_tiers.h"
#include <cassert>
#include <iostream>
int main()
{
    using namespace WovTier;
    // Guild rank never buys premium without the permitted human context.
    assert(UsePremium(false,false,false,true,true,2,2,true,false,true));
    assert(!UsePremium(false,false,false,true,true,3,2,true,false,true));
    assert(!UsePremium(false,false,false,true,true,2,2,false,true,true));
    assert(!UsePremium(false,false,false,true,false,0,2,true,true,true));
    assert(UsePremium(false,false,false,true,true,1,2,true,true,false));
    assert(!UsePremium(false,false,false,true,true,1,2,true,false,false));
    assert(!UsePremium(false,false,false,true,true,2,1,true,true,false));
    assert(UsePremium(true,true,false,false,false,9,2,false,false,false));
    assert(UsePremium(true,false,true,false,false,9,2,false,false,false));
    assert(!UsePremium(false,true,true,false,true,0,2,true,true,true));
    Audience a; a.realOnline=true; a.factionAllowed=true;
    a.sameGuild=true; a.sameGroup=true; a.inChannel=true; a.sameMapPhase=true; a.distance=30;
    assert(CanHear(Scope::Say,a,30,300));
    a.distance=31; assert(!CanHear(Scope::Say,a,30,300));
    assert(CanHear(Scope::Yell,a,30,300));
    a.distance=301; assert(!CanHear(Scope::Yell,a,30,300));
    a.sameMapPhase=false; a.distance=5; assert(!CanHear(Scope::Say,a,30,300));
    assert(CanHear(Scope::Guild,a,30,300));
    assert(CanHear(Scope::Group,a,30,300));
    assert(CanHear(Scope::Channel,a,30,300));
    a.inChannel=false; assert(!CanHear(Scope::Channel,a,30,300));
    assert(!CanHear(Scope::Whisper,a,30,300));
    a.realOnline=false; assert(!CanHear(Scope::Guild,a,30,300));
    a.realOnline=true; a.factionAllowed=false; assert(!CanHear(Scope::Group,a,30,300));
    std::cout << "22 model tier checks passed\n";
}
