# OGame mine payback calculator

`ogame.py` ranks your next economy upgrades in OGame by how fast they pay for
themselves, and plans a build order from that. It covers metal, crystal and
deuterium mines, Plasma Technology and Astrophysics (new colonies).

## Usage

```sh
python3 ogame.py              # reads empire.json next to the script
python3 ogame.py other.json   # reads another empire file
```

You only need Python 3; there are no dependencies.

The script prints two tables:

1. **Daily production:** your empire's current metal, crystal and deuterium
   per day, plus the total in MSE.

   *Note: Dueterium production does not take into account the amount deducted from fusion reactors*
   
2. **Build order:** a plan for the next `plan_steps` upgrades. It picks the
   best upgrade, applies it to a copy of your empire, ranks again, and so on.
   Choosing Astrophysics adds a new planet with no mines, and that planet's
   build-up is planned with everything else. Steps in a row on the same planet
   are grouped onto one line.
   - **PAYBACK:** the payback of the step (for a grouped line, of its last
     and slowest step, shown with `≤`).
   - **SAVE:** how many days of your whole empire's production that line costs.

## How payback is calculated

```
payback = upgrade cost / extra hourly production
```

Both sides are converted to metal standard units (MSE) with your `trade_ratio`.

- **Mines:** the cost of one level against that planet's extra production.
  The production model includes slot bonuses, temperature (deuterium), plasma,
  crawlers, player and alliance class, officers, and lifeform bonuses.
- **Plasma Technology:** the research cost against the extra plasma production
  on all planets.
- **Astrophysics:** the research cost plus the cost of building a new colony's
  mines up to your current average levels, against the average production of
  one of your planets.

Energy is ignored: no energy cost and no reduced production from low energy.
Mines are upgraded one level at a time, each charged at its own price.

## empire.json

All keys are documented at the top of `ogame.py`. The main ones:

| Key | Meaning |
|---|---|
| `eco_speed` | Economy speed of the universe |
| `player_class`, `alliance_class` | e.g. `"collector"`, `"trader"` |
| `geologist`, `all_staff` | Officers |
| `trade_ratio` | Trade rate `[metal, crystal, deut]` |
| `plasma_tech`, `astro_tech` | Current research levels |
| `crawler_percent` | `1.5` for 150% overload (Collector only) |
| `lf_global_prod` | Lifeform production bonus `[metal, crystal, deut]` |
| `lf_class_bonus`, `lf_crawler_bonus` | Lifeform boosts to class and crawler bonuses |
| `lf_plasma_cost_reduction` | Lifeform discount on Plasma Tech research, e.g. `0.1487` |
| `mine_cost_reduction` | Mine cost discount, e.g. `0.03` (Mineral Research Centre) |
| `planets` | Each planet's `name`, `pos`, `max_temp`, `mines` `[metal, crystal, deut]` |
| `plan_steps` | Number of upgrades the build order plans |
| `new_planet` | Assumed `pos` and `max_temp` of new colonies |

Enter lifeform values as the totals the game shows. They already include the
lifeform level bonus, so the script doesn't apply it again.

Update each planet's `mines` after you upgrade, then run the script again.
