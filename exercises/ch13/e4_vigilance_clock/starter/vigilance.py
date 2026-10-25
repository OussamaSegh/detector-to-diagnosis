# SPDX-License-Identifier: MIT
"""Reporting clocks for a device incident in the EU and the US (see the README)."""
from datetime import date, timedelta

# TODO: one number is not enough: Article 87 has three clocks.
EU_DAYS = {"serious_incident": 15}

# TODO: check Article 86 for each class.
PSUR_MONTHS = {"IIa": 12, "IIb": 12, "III": 12}


def eu_deadline(aware: date, kind: str) -> date:
    return aware + timedelta(days=EU_DAYS.get(kind, 15))


def add_work_days(start: date, n: int, holidays=frozenset()) -> date:
    # TODO: work days are not calendar days.
    return start + timedelta(days=n)


def us_deadline(aware: date, kind: str, holidays=frozenset()) -> date:
    if kind == "five_day":
        return add_work_days(aware, 5, holidays)
    return aware + timedelta(days=30)


def psur_interval_months(device_class: str):
    return PSUR_MONTHS.get(device_class, 12)


def report_plan(aware: date, eu_kind, us_kind, holidays=frozenset()):
    plan = []
    if eu_kind:
        plan.append((eu_deadline(aware, eu_kind), "EU competent authority"))
    if us_kind:
        plan.append((us_deadline(aware, us_kind, holidays), "FDA"))
    return plan
