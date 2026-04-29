from dataclasses import dataclass

from app.modules.pricing.application.forecasting import ProphetRow


@dataclass(frozen=True)
class TimeSeriesFold:
    indice: int
    train: list[ProphetRow]
    test: list[ProphetRow]


def construir_folds_temporales(
    dataset: list[ProphetRow],
    min_train_size: int,
    test_size: int,
    step_size: int = 1,
) -> list[TimeSeriesFold]:
    if min_train_size < 1:
        raise ValueError("min_train_size debe ser mayor a 0")
    if test_size < 1:
        raise ValueError("test_size debe ser mayor a 0")
    if step_size < 1:
        raise ValueError("step_size debe ser mayor a 0")
    if len(dataset) < min_train_size + test_size:
        raise ValueError("No hay suficientes puntos para construir folds temporales")

    dataset_ordenado = sorted(dataset, key=lambda fila: fila.ds)
    folds: list[TimeSeriesFold] = []
    indice = 1
    train_fin = min_train_size

    while train_fin + test_size <= len(dataset_ordenado):
        folds.append(
            TimeSeriesFold(
                indice=indice,
                train=dataset_ordenado[:train_fin],
                test=dataset_ordenado[train_fin : train_fin + test_size],
            )
        )
        indice += 1
        train_fin += step_size

    return folds
