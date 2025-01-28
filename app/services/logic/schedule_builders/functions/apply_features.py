from typing import Type

from app.services.logic.schedule_builders.algorithm import Algorithm


def apply_features(base_class: Type, *features: Type) -> Type["Algorithm"]:
    def combined_init(self, *args, **kwargs):
        # Inicializa apenas o __init__ do base_class
        base_class.__init__(self, *args, **kwargs)
        # Executa lógica adicional para cada mixin, se necessário
        for mixin in features:
            init = getattr(mixin, "__init__", None)
            if init is not None and init is not base_class.__init__:
                init(self)

    # Cria a nova classe combinada
    combined_class = type(
        "CombinedAlgorithm",
        (*features, base_class),
        {"__init__": combined_init},  # Define um único __init__
    )
    return combined_class  # type: ignore
