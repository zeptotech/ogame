import copy
import json
import math
import os
import sys

# ==============================================================================
#  YOUR EMPIRE DATA LIVES IN empire.json (next to this script)
#  Run:  python3 ogame.py              (uses empire.json)
#        python3 ogame.py other.json   (uses another file)
#
#  empire.json keys:
#   --- Universe & account ---
#   eco_speed               Economy speed of your universe (e.g. 1, 4, 8, 10)
#   player_class            "collector", "discoverer", "general" or "none"
#   alliance_class          "trader", "explorer", "warrior" or "none"
#   geologist               true if Geologist is active
#   all_staff               true if Commanding Staff is active (includes the Geologist)
#   trade_ratio             Your trade rate [metal, crystal, deut], e.g. [3.0, 2.0, 1.0]
#   --- Research ---
#   plasma_tech             Current Plasma Technology level
#   astro_tech              Current Astrophysics level
#   --- Crawlers ---
#   crawler_percent         1.0 = 100%, 1.5 = 150% overload (Collector only)
#   limit_crawlers_to_owned false = assume max crawlers; true = use each planet's "crawlers"
#   --- Lifeform bonuses (decimals, 0.0 if unused) ---
#   lf_global_prod          [metal, crystal, deut] production bonus, e.g. [0.12, 0.10, 0.08]
#   lf_class_bonus          LF boost to class bonuses, e.g. 0.15 for +15%
#   lf_crawler_bonus        LF boost to crawler production, e.g. 0.20 for +20%
#   lf_plasma_cost_reduction LF research discount on Plasma Tech cost, e.g. 0.1487 for -14.87%
#   --- Planets (update "mines" after each mine upgrade) ---
#   planets                 List of planets, each with:
#     name                  Any label
#     pos                   Slot in the system, 1-15 (metal/crystal slot bonus)
#     max_temp              Max temperature in °C (deut output)
#     mines                 [metal mine, crystal mine, deut synth] levels
#     crawlers              Crawlers on the planet (only used if limit_crawlers_to_owned)
#     lf_planet_prod        Optional planet LF building bonus [metal, crystal, deut]
#   --- Build order planner (optional) ---
#   plan_steps              How many single upgrades to plan ahead (default 150)
#   new_planet              Assumed {"pos", "max_temp"} of planets colonized after Astrophysics
#   --- Server constants (optional, only for custom universes) ---
#   miner_prod_bonus, miner_add_crawler, crawler_boost_per_unit, crawler_max_boost
# ==============================================================================
DEFAULTS = {
    "geologist": False,
    "all_staff": False,
    "trade_ratio": [3.0, 2.0, 1.0],
    "crawler_percent": 1.0,
    "limit_crawlers_to_owned": False,
    "lf_global_prod": [0.0, 0.0, 0.0],
    "lf_class_bonus": 0.0,
    "lf_crawler_bonus": 0.0,
    "lf_plasma_cost_reduction": 0.0,
    "plan_steps": 150,
    "new_planet": {"pos": 8, "max_temp": 50},
    # Server constants
    "miner_prod_bonus": 0.25,
    "miner_add_crawler": 0.50,
    "crawler_boost_per_unit": 0.0002,
    "crawler_max_boost": 0.50,
}
REQUIRED_KEYS = ["eco_speed", "player_class", "alliance_class", "plasma_tech", "astro_tech", "planets"]
REQUIRED_PLANET_KEYS = ["name", "pos", "max_temp", "mines"]

def load_config(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Empire file not found: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"{path} is not valid JSON (line {e.lineno}, column {e.colno}): {e.msg}")

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        sys.exit(f"{path} is missing: {', '.join(missing)}")
    if not data["planets"]:
        sys.exit(f"{path} has no planets")
    for i, p in enumerate(data["planets"], 1):
        missing = [k for k in REQUIRED_PLANET_KEYS if k not in p]
        if missing:
            sys.exit(f"Planet #{i} in {path} is missing: {', '.join(missing)}")
        if len(p["mines"]) != 3:
            sys.exit(f"Planet {p['name']}: mines must be [metal, crystal, deut]")
        if not 1 <= p["pos"] <= 15:
            sys.exit(f"Planet {p['name']}: pos must be between 1 and 15")
        p["mines"] = tuple(p["mines"])
        p.setdefault("crawlers", 0)
        p.setdefault("lf_planet_prod", [0.0, 0.0, 0.0])

    cfg = copy.deepcopy(DEFAULTS)
    cfg.update(data)
    return cfg

# ==============================================================================
#  CALCULATION ENGINE (Do not edit below this line)
# ==============================================================================
METAL_POS_BONUS   = [1, 1, 1, 1, 1, 1.17, 1.23, 1.35, 1.23, 1.17, 1, 1, 1, 1, 1]
CRYSTAL_POS_BONUS = [1.4, 1.3, 1.2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
PLASMATECH_BONUS  = [0.01, 0.0066, 0.0033]

BUILDING_INFO = {
    1: {"name": "Metal Mine",   "base": (60, 15, 0),   "factor": 1.5},
    2: {"name": "Crystal Mine", "base": (48, 24, 0),   "factor": 1.6},
    3: {"name": "Deut Synth",   "base": (225, 75, 0),  "factor": 1.5},
}

def to_mse(res_tuple, trade_rate):
    return sum((x * trade_rate[0]) / trade_rate[i] for i, x in enumerate(res_tuple))

def building_cost(tech_id, lvl):
    b = BUILDING_INFO[tech_id]
    return tuple(math.floor(c * (b["factor"] ** (lvl - 1))) for c in b["base"])

def research_cost(tech_id, lvl, cost_reduction=0.0):
    if tech_id == 122:
        base, factor = (2000, 4000, 1000), 2.0
    elif tech_id == 124:
        base, factor = (4000, 8000, 4000), 1.75
    return tuple(math.floor(c * (factor ** (lvl - 1)) * (1 - cost_reduction)) for c in base)

def mines_production(tech_id, lvl, pos, max_temp, speed):
    if lvl <= 0:
        return 0
    base_prod = {1: 30, 2: 20, 3: 10}[tech_id]
    pos_bonus = 1.0
    if tech_id == 1:
        pos_bonus = METAL_POS_BONUS[pos - 1]
    elif tech_id == 2:
        pos_bonus = CRYSTAL_POS_BONUS[pos - 1]

    prod = base_prod * lvl * (1.1 ** lvl)
    if tech_id == 3:
        prod *= (1.44 - 0.004 * max_temp)
    return math.floor(prod * pos_bonus * speed)

def planet_hourly_prod(mine_lvls, planet, cfg, plasma_override=None):
    pos = planet["pos"]
    temp = planet["max_temp"]
    speed = cfg["eco_speed"]
    plasma_lvl = cfg["plasma_tech"] if plasma_override is None else plasma_override

    base_incoming = [30 * speed, 15 * speed, 0]
    plasma_bonus = [p * plasma_lvl for p in PLASMATECH_BONUS]

    is_miner = cfg["player_class"].lower() == "collector"
    is_trader = cfg["alliance_class"].lower() == "trader"
    crawler_pct = min(cfg["crawler_percent"], 1.5 if is_miner else 1.0)
    owned_crawlers = planet["crawlers"] if cfg["limit_crawlers_to_owned"] else 1_000_000

    mine_sum = sum(mine_lvls)
    max_crawlers = math.floor(mine_sum * 8 * (1.1 if cfg["geologist"] else 1.0))
    active_crawlers = min(max_crawlers, owned_crawlers)

    crawler_mult = cfg["crawler_boost_per_unit"] * (
        1 + cfg["miner_add_crawler"] * (1 + cfg["lf_class_bonus"]) if is_miner else 1.0
    ) * (1 + cfg["lf_crawler_bonus"])
    crawler_bonus = min(active_crawlers * crawler_pct * crawler_mult, cfg["crawler_max_boost"])

    lf_global = cfg["lf_global_prod"]
    lf_planet = planet.get("lf_planet_prod", (0.0, 0.0, 0.0))

    totals = []
    for i in range(3):
        m_prod = mines_production(i + 1, mine_lvls[i], pos, temp, speed)
        p_prod = m_prod * plasma_bonus[i]
        c_prod = m_prod * crawler_bonus
        class_prod = m_prod * (cfg["miner_prod_bonus"] * (1 + cfg["lf_class_bonus"]) if is_miner else 0.0)
        geo_prod = m_prod * (0.10 if cfg["geologist"] else 0.0)
        ally_prod = m_prod * (0.05 if is_trader else 0.0)
        staff_prod = m_prod * (0.02 if cfg["all_staff"] else 0.0)
        lf_g_prod = m_prod * lf_global[i]
        lf_p_prod = m_prod * lf_planet[i]

        totals.append(math.floor(
            m_prod + p_prod + c_prod + class_prod + geo_prod + ally_prod + staff_prod + lf_g_prod + lf_p_prod + base_incoming[i]
        ))
    return totals

def roi_mine(tech_id, to_lvl, planet, cfg, from_lvl=None):
    # from_lvl: level assumed already built (defaults to the planet's current level)
    curr_lvls = list(planet["mines"])
    if from_lvl is not None:
        curr_lvls[tech_id - 1] = from_lvl
    new_lvls = list(curr_lvls)
    new_lvls[tech_id - 1] = to_lvl

    curr_prod = planet_hourly_prod(curr_lvls, planet, cfg)
    new_prod = planet_hourly_prod(new_lvls, planet, cfg)
    prod_diff = [new_prod[i] - curr_prod[i] for i in range(3)]

    trade_rate = cfg["trade_ratio"]
    prod_diff_mse = to_mse(prod_diff, trade_rate)

    cost_mse = 0
    for lvl in range(curr_lvls[tech_id - 1] + 1, to_lvl + 1):
        cost_mse += to_mse(building_cost(tech_id, lvl), trade_rate)

    return (cost_mse * 3600) / prod_diff_mse

def roi_plasma(to_lvl, cfg, from_lvl=None):
    plasma = cfg["plasma_tech"] if from_lvl is None else from_lvl
    plasma_bonus = [p * (to_lvl - plasma) for p in PLASMATECH_BONUS]
    trade_rate = cfg["trade_ratio"]
    prod_diff_mse = 0

    for p in cfg["planets"]:
        diff = [
            mines_production(1, p["mines"][0], p["pos"], p["max_temp"], cfg["eco_speed"]) * plasma_bonus[0],
            mines_production(2, p["mines"][1], p["pos"], p["max_temp"], cfg["eco_speed"]) * plasma_bonus[1],
            mines_production(3, p["mines"][2], p["pos"], p["max_temp"], cfg["eco_speed"]) * plasma_bonus[2],
        ]
        prod_diff_mse += to_mse(diff, trade_rate)

    cost_mse = sum(to_mse(research_cost(122, lvl, cfg["lf_plasma_cost_reduction"]), trade_rate)
                   for lvl in range(plasma + 1, to_lvl + 1))
    return (cost_mse * 3600) / prod_diff_mse

def astro_planet_slots(lvl):
    # Astrophysics gives 1 extra planet slot at every odd level: slots = ceil(lvl / 2) + 1
    return (lvl + 1) // 2 + 1

def roi_astro(from_lvl, to_lvl, avg_mines, total_prod_mse, cfg):
    trade_rate = cfg["trade_ratio"]
    new_planets = astro_planet_slots(to_lvl) - astro_planet_slots(from_lvl - 1)
    num_planets = len(cfg["planets"])  # total_prod_mse is summed over these planets

    research_mse = sum(to_mse(research_cost(124, lvl), trade_rate) for lvl in range(from_lvl, to_lvl + 1))

    catchup_mse = 0
    for idx, tech_id in enumerate([1, 2, 3]):
        for lvl in range(1, int(avg_mines[idx]) + 1):
            catchup_mse += to_mse(building_cost(tech_id, lvl), trade_rate)

    total_cost_mse = research_mse + catchup_mse * new_planets
    prod_diff_mse = (total_prod_mse / num_planets) * new_planets
    return (total_cost_mse * 3600) / prod_diff_mse

def get_best_roi(cfg):
    results = []
    num_planets = len(cfg["planets"])
    avg_mines = [
        sum(p["mines"][i] for p in cfg["planets"]) / num_planets for i in range(3)
    ]
    total_prod = [0, 0, 0]
    for p in cfg["planets"]:
        hp = planet_hourly_prod(p["mines"], p, cfg)
        for i in range(3):
            total_prod[i] += hp[i]
    total_prod_mse = to_mse(total_prod, cfg["trade_ratio"])

    # Like the extension: check each mine up to (highest level of that mine on any planet) + 5
    max_mines = [max(p["mines"][i] for p in cfg["planets"]) for i in range(3)]
    for p in cfg["planets"]:
        for idx, tech_id in enumerate([1, 2, 3]):
            curr = p["mines"][idx]
            for target_lvl in range(curr + 1, max_mines[idx] + 6):
                # One level per row: payback of this level alone, assuming the previous levels are built
                sec = roi_mine(tech_id, target_lvl, p, cfg, from_lvl=target_lvl - 1)
                results.append((sec, f"{p['name']}: {BUILDING_INFO[tech_id]['name']} {target_lvl - 1} -> {target_lvl}"))

    p_lvl = cfg["plasma_tech"]
    for step in range(1, 6):
        sec = roi_plasma(p_lvl + step, cfg, from_lvl=p_lvl + step - 1)
        results.append((sec, f"Research: Plasma Tech {p_lvl + step - 1} -> {p_lvl + step}"))

    astro = cfg["astro_tech"]
    start_step = 1 if (astro + 1) % 2 == 1 else 2
    # One new planet slot per row: from the previous row's level to the next odd level
    prev_lvl = astro
    for step in range(start_step, 11, 2):
        to_lvl = astro + step
        sec = roi_astro(prev_lvl + 1, to_lvl, avg_mines, total_prod_mse, cfg)
        results.append((sec, f"Research: Astrophysics {prev_lvl} -> {to_lvl}"))
        prev_lvl = to_lvl

    results.sort(key=lambda x: x[0])

    print(f"{'RANK':<5} {'UPGRADE':<44} {'PAYBACK':>12}")
    print("-" * 63)
    for rank, (sec, label) in enumerate(results[:20], 1):
        days = sec / 86400
        print(f"#{rank:<4} {label:<44} {days:>7.2f} days")



# ==============================================================================
#  BUILD ORDER PLANNER
#  Repeatedly picks the upgrade with the shortest payback, applies it to a copy
#  of your empire, and re-ranks. Choosing Astrophysics adds a new planet with
#  empty mines, so its build-up is planned alongside your other upgrades.
# ==============================================================================
def empire_hourly_mse(cfg):
    total = [0, 0, 0]
    for p in cfg["planets"]:
        hp = planet_hourly_prod(p["mines"], p, cfg)
        total = [a + b for a, b in zip(total, hp)]
    return to_mse(total, cfg["trade_ratio"])

def next_options(cfg):
    """Every upgrade that can be done next: (payback_sec, cost_mse, action)."""
    trade_rate = cfg["trade_ratio"]
    options = []

    for pi, p in enumerate(cfg["planets"]):
        for tech_id in (1, 2, 3):
            lvl = p["mines"][tech_id - 1] + 1
            sec = roi_mine(tech_id, lvl, p, cfg)
            cost = to_mse(building_cost(tech_id, lvl), trade_rate)
            options.append((sec, cost, ("mine", pi, tech_id, lvl)))

    plasma_lvl = cfg["plasma_tech"] + 1
    options.append((roi_plasma(plasma_lvl, cfg),
                    to_mse(research_cost(122, plasma_lvl, cfg["lf_plasma_cost_reduction"]), trade_rate),
                    ("plasma", plasma_lvl)))

    astro = cfg["astro_tech"]
    astro_to = astro + 1 if (astro + 1) % 2 == 1 else astro + 2
    n = len(cfg["planets"])
    avg_mines = [sum(p["mines"][i] for p in cfg["planets"]) / n for i in range(3)]
    sec = roi_astro(astro + 1, astro_to, avg_mines, empire_hourly_mse(cfg), cfg)
    # Only the research is paid here; the new planet's mines are planned as separate steps
    cost = sum(to_mse(research_cost(124, lvl), trade_rate) for lvl in range(astro + 1, astro_to + 1))
    options.append((sec, cost, ("astro", astro_to)))
    return options

def apply_action(cfg, action):
    kind = action[0]
    if kind == "mine":
        _, pi, tech_id, lvl = action
        mines = list(cfg["planets"][pi]["mines"])
        mines[tech_id - 1] = lvl
        cfg["planets"][pi]["mines"] = tuple(mines)
    elif kind == "plasma":
        cfg["plasma_tech"] = action[1]
    elif kind == "astro":
        cfg["astro_tech"] = action[1]
        new_planet = cfg.get("new_planet", {"pos": 8, "max_temp": 50})
        cfg["_new_count"] = cfg.get("_new_count", 0) + 1
        cfg["planets"].append({
            "name": f"New Planet {cfg['_new_count']}",
            "pos": new_planet["pos"],
            "max_temp": new_planet["max_temp"],
            "mines": (0, 0, 0),
            "crawlers": 0,
            "lf_planet_prod": (0.0, 0.0, 0.0),
        })

def plan_build_order(cfg):
    state = copy.deepcopy(cfg)
    steps = []  # (step_no, action, payback_sec, save_days, label, planet_name)
    for step in range(1, cfg.get("plan_steps", 150) + 1):
        sec, cost, action = min(next_options(state), key=lambda o: o[0])
        # Days of total empire production needed to pay for this step
        save = cost / (empire_hourly_mse(state) * 24)
        if action[0] == "astro":
            label = f"Research: Astrophysics {state['astro_tech']} -> {action[1]} (colonize {len(state['planets']) + 1}th planet)"
        elif action[0] == "plasma":
            label = f"Research: Plasma Tech {action[1] - 1} -> {action[1]}"
        else:
            label = None
        planet_name = state["planets"][action[1]]["name"] if action[0] == "mine" else None
        steps.append((step, action, sec, save, label, planet_name))
        apply_action(state, action)

    # Group consecutive mine steps on the same planet into one line
    lines = []
    for step, action, sec, save, label, planet_name in steps:
        if action[0] == "mine":
            _, _, tech_id, lvl = action
            last = lines[-1] if lines else None
            if last and last["planet"] == planet_name:
                rng = last["ranges"].setdefault(tech_id, [lvl - 1, lvl])
                rng[1] = lvl
                last.update(end=step, sec=sec, save=last["save"] + save)
                continue
            lines.append({"planet": planet_name, "ranges": {tech_id: [lvl - 1, lvl]},
                          "start": step, "end": step, "sec": sec, "save": save})
        else:
            lines.append({"planet": None, "label": label, "start": step, "end": step, "sec": sec, "save": save})

    print(f"BUILD ORDER (next {len(steps)} upgrades, best payback first)")
    print(f"{'STEP':<9} {'UPGRADE':<80} {'PAYBACK':>12} {'SAVE':>11}")
    print("-" * 116)
    for ln in lines:
        steps_txt = f"{ln['start']}" if ln["start"] == ln["end"] else f"{ln['start']}-{ln['end']}"
        if ln["planet"] is None:
            text = ln["label"]
        else:
            parts = [f"{BUILDING_INFO[t]['name']} {a} -> {b}" for t, (a, b) in sorted(ln["ranges"].items())]
            text = f"{ln['planet']}: " + ", ".join(parts)
        payback = f"{ln['sec'] / 86400:.1f} days"
        if ln["start"] != ln["end"]:
            payback = "≤ " + payback
        print(f"{steps_txt:<9} {text:<80} {payback:>12} {format(ln['save'], '.1f') + ' days':>11}")

if __name__ == "__main__":
    default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "empire.json")
    cfg = load_config(sys.argv[1] if len(sys.argv) > 1 else default_path)
    get_best_roi(cfg)
    print()
    plan_build_order(cfg)
