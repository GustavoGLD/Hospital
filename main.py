import os

import pygad  # type: ignore
from loguru import logger
from sqlmodel import SQLModel

from app.models.schedule import Schedule
from app.services.cache.cache_in_dict import CacheInDict
from app.services.logic.schedule_builders.algorithm import Algorithm
from app.services.logic.schedule_optimizers.optimizer import Optimizer
from moonlogger import MoonLogger
from dotenv import load_dotenv

load_dotenv()


def setup_test_session():
    engine = create_engine("sqlite:///:memory:")  # Banco de dados em memória
    SQLModel.metadata.create_all(engine)  # Cria as tabelas
    return Session(engine)


from sqlmodel import select

from sqlmodel import create_engine, Session
from datetime import datetime


def get_engine():
    engine = create_engine(str(os.getenv("DB_URL")), echo=True)
    try:
        SQLModel.metadata.create_all(engine)
    except Exception:
        pass
    return engine


def main() -> Algorithm:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        try:
            logger.info("Limpando a tabela de agendamentos...")
            for row in session.exec(select(Schedule)).all():
                session.delete(row)
            session.commit()

            logger.info("Recolhendo dados do banco de dados...")
            cache = CacheInDict(session=session)

            logger.info("Executando o algoritmo...")
            optimizer = Optimizer(cache=cache)
            solution = optimizer.run()

            logger.info("Processando a solução...")
            algorithm = Algorithm(optimizer.solver.mobile_surgeries, cache, datetime.now())
            algorithm.execute(solution)
            algorithm.print_table()

            logger.info("Salvando os resultados no banco de dados...")

            session.add_all(algorithm.cache.get_table(Schedule))
            session.commit()
        except Exception as e:
            logger.error(f"Erro ao executar.")
            raise e
        else:
            logger.success(f"Análise de Desempenho. Tempo gasto: {MoonLogger.time_dict}")
            return algorithm


if __name__ == "__main__":
    main()
