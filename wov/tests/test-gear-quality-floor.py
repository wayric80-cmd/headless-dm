#!/usr/bin/env python3
"""Compile actual equipment-quality selection statements and check boundaries."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "src/modules/mod-playerbots/src/Bot/Factory/PlayerbotFactory.cpp").read_text()
start = source.index("        int32 desiredQuality = itemQuality;", source.index("void PlayerbotFactory::InitEquipment("))
end = source.index("        do", start)
selection = source[start:end]
start = source.index("        } while (items[slot].size() < 25 &&", end)
end = source.index(";", start)
condition = source[start:end + 1].replace("        } while (", "        } while (")
program = r"""
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
#include <vector>
using int32 = int32_t;
constexpr int ITEM_QUALITY_POOR=0, ITEM_QUALITY_NORMAL=1, ITEM_QUALITY_UNCOMMON=2;
struct { float randomGearLoweringChance = 0.25f; } sPlayerbotAIConfig;
int draw;
int urand(int, int) { return draw; }
std::vector<int> choose(int level, int itemQuality, bool lower, bool full) {
    draw = lower ? 0 : 100;
    std::map<int, std::vector<int>> items;
    int slot = 0;
    if (full) items[slot].resize(25);
    std::vector<int> visited;
""" + selection + r"""
    do {
        visited.push_back(desiredQuality);
""" + condition + r"""
    return visited;
}
int main() {
    int tests = 0;
    for (int level : {1,19,20,30,40,50,60})
    for (int requested = 0; requested <= 4; ++requested)
    for (bool lower : {false,true})
    for (bool full : {false,true}) {
        auto actual = choose(level, requested, lower, full);
        int floor = level >= 20 && requested >= 2 ? 2 : 0;
        int expected = requested;
        if (lower && expected > std::max(1,floor)) --expected;
        assert(actual.front() == expected);
        assert(actual.back() == (full ? expected : floor));
        for (int quality : actual) assert(quality >= floor && quality <= requested);
        ++tests;
    }
    std::cout << tests << " actual-source quality-selection cases passed\n";
}
"""
with tempfile.TemporaryDirectory(prefix="wov-gear-test-") as temp:
    cpp = Path(temp) / "quality.cpp"
    exe = Path(temp) / "quality-test"
    cpp.write_text(program)
    subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
