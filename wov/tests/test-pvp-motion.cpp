#include "../../src/modules/mod-playerbots/src/Ai/Base/Actions/WovPvpMotion.h"
#include <cassert>
#include <iostream>
int main()
{
    using namespace WovPvp;
    assert(Choose(100, false, 3, false, false) == Intent::Flank);
    assert(Choose(100, false, 15, false, false) == Intent::None);
    assert(Choose(100, true, 8, false, false) == Intent::Kite);
    assert(Choose(20, false, 8, false, false) == Intent::Retreat);
    assert(Choose(20, true, 8, true, true) == Intent::Retreat);
    assert(Choose(100, true, 20, false, true) == Intent::Cover);
    assert(Choose(100, true, 20, true, false) == Intent::Spread);
    assert(Choose(100, false, 3, true, false) == Intent::Spread);
    assert(Choose(100, true, 40, true, true) == Intent::None);
    assert(Choose(20, true, 40, false, false) == Intent::None);
    assert(Choose(100, true, 30, false, false) == Intent::None);
    std::cout << "11 PvP intent checks passed\n";
}
