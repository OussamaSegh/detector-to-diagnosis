# SPDX-License-Identifier: MIT
"""Reporting clocks for a device incident in the EU and the US.

EU: MDR Article 87 (serious incidents) and Article 86 (periodic safety update report).
US: 21 CFR 803 (medical device reporting by manufacturers).
A teaching model: the procedure of your quality system and your regulatory team decide
what is reported, by whom and when.
"""
from datetime import date, timedelta

# Days after the manufacturer becomes aware, MDR Article 87(3) to (5).
EU_DAYS = {
    "serious_public_health_threat": 2,
    "death_or_unanticipated_serious_deterioration": 10,
    "serious_incident": 15,
}

# PSUR at least every N months, MDR Article 86; class I has a PMS report instead (Article 85).
PSUR_MONTHS = {"IIa": 24, "IIb": 12, "III": 12}


# [snippet:clocks]
def eu_deadline(aware: date, kind: str) -> date:
    """The latest day for the report to the competent authority (calendar days)."""
    return aware + timedelta(days=EU_DAYS[kind])


def add_work_days(start: date, n: int, holidays=frozenset()) -> date:
    """The n-th work day after start: weekends and the given holidays do not count."""
    d = start
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in holidays:
            n -= 1
    return d


def us_deadline(aware: date, kind: str, holidays=frozenset()) -> date:
    """21 CFR 803.50: 30 calendar days; 803.53: 5 work days when remedial action is
    needed to prevent an unreasonable risk of substantial harm, or when FDA asks."""
    if kind == "malfunction_or_injury_or_death":
        return aware + timedelta(days=30)
    if kind == "five_day":
        return add_work_days(aware, 5, holidays)
    raise KeyError(kind)
# [/snippet:clocks]


def psur_interval_months(device_class: str):
    """None for class I: it has a post-market surveillance report, updated when necessary."""
    return PSUR_MONTHS.get(device_class)


def report_plan(aware: date, eu_kind: str | None, us_kind: str | None, holidays=frozenset()):
    """Every report that is due, earliest first, as (due date, jurisdiction)."""
    plan = []
    if eu_kind:
        plan.append((eu_deadline(aware, eu_kind), "EU competent authority"))
    if us_kind:
        plan.append((us_deadline(aware, us_kind, holidays), "FDA"))
    return sorted(plan)
