import math

# ==============================================================================
#  UPDATE YOUR EMPIRE INFORMATION HERE (Only edit inside CONFIG)
# ==============================================================================
CONFIG = {
    # --- 1. UNIVERSE & ACCOUNT SETTINGS (Rarely change) ---
    "eco_speed": 10,                    # Your universe's economy speed (e.g., 1, 4, 8, 10)
    "player_class": "collector",       # "collector", "discoverer", "general", or "none"
    "alliance_class": "trader",        # "trader", "explorer", "warrior", or "none"
    "geologist": False,                 # True if Geologist is active, otherwise False
    "all_staff": False,                 # True if Commanding Staff is active, otherwise False
    "trade_ratio": (3.0, 2.0, 1.0),    # Your trade rate: (Metal, Crystal, Deuterium)

    # --- 2. RESEARCH LEVELS (Update whenever you finish a research) ---
    "plasma_tech": 18,                 # Current Plasma Technology level
    "astro_tech": 21,                  # Current Astrophysics level

    # --- 3. CRAWLER SETTINGS ---
    "crawler_percent": 1.5,            # 1.0 = 100%, 1.5 = 150% overload (Collector only)
    "limit_crawlers_to_owned": False,  # False = assume max crawlers; True = use "crawlers" count below

    # --- 4. LIFEFORM GLOBAL BONUSES (Optional - leave at 0.0 if unused) ---
    "lf_global_prod": (0.3367, 0.3568, 0.3651), # Global LF tech bonus as decimals: (Metal%, Crystal%, Deut%) e.g. (0.12, 0.10, 0.08)
    "lf_class_bonus": 0.0,             # Global LF character class boost as decimal (e.g. 0.15 for +15%)
    "lf_crawler_bonus": 0.0,           # LF bonus to crawler production as decimal (e.g. 0.20 for +20%)

    # --- 5. YOUR PLANETS (Update "mines" tuple whenever you upgrade a mine) ---
    # Format:
    #   "name":           Any label you want
    #   "pos":            Planet slot position in system (1 to 15) — affects Metal/Crystal slot bonus
    #   "max_temp":       Planet's max temperature in °C (shown in Overview) — affects Deut output
    #   "mines":          (Metal Mine Level, Crystal Mine Level, Deuterium Synth Level)
    #   "crawlers":       Number of crawlers on the planet (only used if limit_crawlers_to_owned is True)
    #   "lf_planet_prod": Optional planet-specific LF building bonus as decimals: (Metal%, Crystal%, Deut%)
    "planets": [
        {"name": "Planet 1",  "pos": 8, "max_temp": 33, "mines": (41, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 2",  "pos": 8, "max_temp": 48, "mines": (41, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 3",  "pos": 8, "max_temp": 59, "mines": (41, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 4",  "pos": 8, "max_temp": 47, "mines": (41, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 5",  "pos": 8, "max_temp": 38, "mines": (42, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 6",  "pos": 8, "max_temp": 57, "mines": (42, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 7",  "pos": 8, "max_temp": 66, "mines": (42, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 8",  "pos": 8, "max_temp": 67, "mines": (42, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 9",  "pos": 8, "max_temp": 36, "mines": (41, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 10", "pos": 8, "max_temp": 53, "mines": (41, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 11", "pos": 8, "max_temp": 69, "mines": (41, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
        {"name": "Planet 12", "pos": 8, "max_temp": 49, "mines": (41, 35, 37), "crawlers": 994, "lf_planet_prod": (0.0, 0.0, 0.0)},
    ],

    # --- 6. SERVER CONSTANTS (Do not change unless playing a custom/special universe) ---
    "miner_prod_bonus": 0.25,
    "miner_add_crawler": 0.50,
    "crawler_boost_per_unit": 0.0002,
    "crawler_max_boost": 0.50,
}

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

def research_cost(tech_id, lvl):
    if tech_id == 122:
        base, factor = (2000, 4000, 1000), 2.0
    elif tech_id == 124:
        base, factor = (4000, 8000, 4000), 1.75
    return tuple(math.floor(c * (factor ** (lvl - 1))) for c in base)

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

def roi_mine(tech_id, to_lvl, planet, cfg):
    curr_lvls = list(planet["mines"])
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

def roi_plasma(to_lvl, cfg):
    plasma = cfg["plasma_tech"]
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

    cost_mse = sum(to_mse(research_cost(122, lvl), trade_rate) for lvl in range(plasma + 1, to_lvl + 1))
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
                sec = roi_mine(tech_id, target_lvl, p, cfg)
                results.append((sec, f"{p['name']} (Pos {p['pos']}): {BUILDING_INFO[tech_id]['name']} {curr} -> {target_lvl}"))

    p_lvl = cfg["plasma_tech"]
    for step in range(1, 6):
        sec = roi_plasma(p_lvl + step, cfg)
        results.append((sec, f"Research: Plasma Tech {p_lvl} -> {p_lvl + step}"))

    astro = cfg["astro_tech"]
    start_step = 1 if (astro + 1) % 2 == 1 else 2
    for step in range(start_step, 11, 2):
        sec = roi_astro(astro + 1, astro + step, avg_mines, total_prod_mse, cfg)
        results.append((sec, f"Research: Astrophysics {astro} -> {astro + step}"))

    results.sort(key=lambda x: x[0])

    print(f"{'RANK':<5} {'UPGRADE':<44} {'PAYBACK':>12}")
    print("-" * 63)
    for rank, (sec, label) in enumerate(results[:20], 1):
        days = sec / 86400
        print(f"#{rank:<4} {label:<44} {days:>7.2f} days")


if __name__ == "__main__":
    get_best_roi(CONFIG)
