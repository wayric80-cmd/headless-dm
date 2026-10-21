#include "../../src/modules/mod-ollama-chat/src/wov_player_voice.h"
#include <cassert>
#include <iostream>
int main()
{
    assert(Wov::IsSelfNarration("Osloisi is in Nightsong Woods at level 21.", "Osloisi"));
    assert(Wov::IsSelfNarration("lardbutt just danced on a mailbox", "Lardbutt"));
    assert(Wov::IsSelfNarration("Kirdo's in Dalaran Crater.", "Kirdo"));
    assert(Wov::IsSelfNarration("yeah. Blitsi is level 37.", "Blitsi"));
    assert(!Wov::IsSelfNarration("I'm Osloisi, lvl 21 rogue", "Osloisi"));
    assert(!Wov::IsSelfNarration("Osloisi here, anyone questing?", "Osloisi"));
    assert(!Wov::IsSelfNarration("Bob is fighting, I'm healing him", "Alice"));
    assert(!Wov::IsSelfNarration("Bigbob is fighting", "Bob"));
    assert(!Wov::IsSelfNarration("just hit 30, finally", "Bob"));
    assert(!Wov::IsSelfNarration("I play Bob and need a group", "Bob"));
    assert(Wov::IsSelfNarration("Kirdo’s in Dalaran Crater.", "Kirdo"));
    std::cout << "11 player voice checks passed\n";
}
