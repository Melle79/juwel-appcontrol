"""Den Tagesverlauf eines Lichtprofils zur aktuellen Uhrzeit auswerten.

Warum das noetig ist: Das Geraet meldet seine Kanalwerte nicht laufend.
Beobachtet an echter Hardware standen sie vier Tage unveraendert auf dem
Tagesplateau, waehrend das Becken nachts dunkel war - die Cloud bekommt
Zwischenwerte offenbar nur bei aktiver App-Verbindung. Im Automatikbetrieb
ist deshalb das Profil die verlaessliche Quelle, nicht der gemeldete Wert.
"""

from __future__ import annotations

from typing import Any

CHANNELS = ("red", "green", "blue", "white")
MINUTES_PER_DAY = 24 * 60


def _points(preset: dict[str, Any] | None) -> list[tuple[int, dict[str, float]]]:
    """Zeitpunkte als (Minute ab Mitternacht, Kanalwerte in Prozent)."""
    punkte: list[tuple[int, dict[str, float]]] = []
    for event in (preset or {}).get("timeEvents") or []:
        try:
            minute = int(event.get("time"))
        except (TypeError, ValueError):
            continue
        werte = event.get("value")
        if not isinstance(werte, dict):
            continue
        punkte.append(
            (minute % MINUTES_PER_DAY,
             {c: float(werte.get(c) or 0) for c in CHANNELS})
        )
    punkte.sort(key=lambda p: p[0])
    return punkte


def values_at(preset: dict[str, Any] | None, minute_of_day: int) -> dict[str, float] | None:
    """Kanalwerte in Prozent zur gegebenen Minute, linear zwischen den Punkten.

    Vor dem ersten und nach dem letzten Zeitpunkt wird ueber Mitternacht
    hinweg interpoliert - der Tag ist ein Kreis.
    """
    punkte = _points(preset)
    if not punkte:
        return None
    if len(punkte) == 1:
        return dict(punkte[0][1])

    minute = int(minute_of_day) % MINUTES_PER_DAY
    vorher = naechster = None
    for i, (m, _) in enumerate(punkte):
        if m <= minute:
            vorher = i
        if m >= minute and naechster is None:
            naechster = i
    if vorher is None:                      # vor dem ersten Punkt
        vorher = len(punkte) - 1
    if naechster is None:                   # nach dem letzten Punkt
        naechster = 0

    m_a, werte_a = punkte[vorher]
    m_b, werte_b = punkte[naechster]
    if vorher == naechster or m_a == m_b:
        return dict(werte_a)

    spanne = (m_b - m_a) % MINUTES_PER_DAY or MINUTES_PER_DAY
    fortschritt = ((minute - m_a) % MINUTES_PER_DAY) / spanne
    return {
        c: werte_a[c] + (werte_b[c] - werte_a[c]) * fortschritt
        for c in CHANNELS
    }
