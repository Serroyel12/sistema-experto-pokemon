from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List

FactBase = Dict[str, Any]


@dataclass
class Rule:
    name: str
    when: Callable[[FactBase], bool]   # condición
    then: Callable[[FactBase], None]  # acción
    explain: str                       # explicación en texto humano


@dataclass
class InferenceResult:
    facts: FactBase
    fired_rules: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)


def forward_chain(facts: FactBase, rules: List[Rule], max_loops: int = 20) -> InferenceResult:
    """
    Motor de encadenamiento hacia adelante muy simple:
    - Recorre las reglas
    - Si la condición es verdadera y la regla aún no se ha disparado, ejecuta la acción
      y guarda una explicación en la traza.
    - Repite mientras se disparen reglas nuevas o hasta max_loops.
    """
    fired = set()
    trace: List[str] = []

    for _ in range(max_loops):
        fired_any = False

        for r in rules:
            if r.name in fired:
                continue
            if r.when(facts):
                r.then(facts)
                fired.add(r.name)
                fired_any = True
                trace.append(f"[{r.name}] {r.explain}")

        if not fired_any:
            break

    return InferenceResult(
        facts=facts,
        fired_rules=list(fired),
        trace=trace
    )
