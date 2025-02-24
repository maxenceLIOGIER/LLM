from sqlalchemy import insert, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, select
from typing import Any

import uuid

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()


class Origin(Base):
    __tablename__ = "origin"
    id_origin = Column(
        String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    origin = Column(String, nullable=True)


class Status(Base):
    __tablename__ = "status"
    id_status = Column(
        String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    status = Column(String, nullable=True)


class Prompt(Base):
    __tablename__ = "prompt"
    id_prompt = Column(
        String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    session_id = Column(String, nullable=False)
    id_origin = Column(String, ForeignKey("origin.id_origin"), nullable=True)
    prompt = Column(String, nullable=True)
    response = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=True, default=datetime.now)


class Log(Base):
    __tablename__ = "log"
    id_log = Column(
        String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    timestamp = Column(String, nullable=False)
    id_prompt = Column(String, ForeignKey("prompt.id_prompt"), nullable=False)
    id_status = Column(String, ForeignKey("status.id_status"), nullable=False)
    id_origin = Column(String, ForeignKey("origin.id_origin"), nullable=False)


class Database:
    def __init__(self, db_path: str):
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)  # Load all tables

    def insert(self, table: str, data: dict[str, Any]) -> bool:
        """
        Inserts a row into the specified table.

        :param table: str.
        :param data: Dictionary of column names and values.
        :return: True if insertion is successful, otherwise False.

        clés pour enregistrer dans la table prompt:
            - session_id
            - origin
            - prompt
            - response

        clés pour enregistrer dans la table log :
            - timestamp
            - prompt
            - status
        """
        if not data:
            erreur = "Error: No data provided for insertion."
            return erreur, False

        table_obj = self.metadata.tables.get(table)
        if table_obj is None:
            erreur = f"Error: Table '{table}' does not exist."
            return erreur, False

        try:
            with self.Session() as session:
                if table == "prompt":
                    statement = select(Origin).where(Origin.origin == data["origin"])
                    id_origin = session.scalar(statement=statement)
                    if not id_origin:
                        insert_origin = insert(Origin).values(
                            id_origin=str(uuid.uuid4()), origin=data["origin"]
                        )
                        session.execute(statement=insert_origin)
                        session.commit()
                    id_origin = session.scalar(statement=statement).id_origin
                    insert_prompt = insert(Prompt).values(
                        id_prompt=str(uuid.uuid4()),
                        session_id=data["session_id"],
                        id_origin=id_origin,
                        prompt=data["prompt"],
                        response=data["response"],
                    )
                    session.execute(insert_prompt)
                    session.commit()
                    return id_prompt, True
                if table == "log":
                    statement = select(Status).where(Status.status == data["status"])
                    id_status = session.scalar(statement=statement)
                    if not id_status:
                        insert_status = insert(Status).values(
                            id_status=str(uuid.uuid4()), status=data["status"]
                        )
                        session.execute(insert_status)
                        session.commit()
                    id_status = session.scalar(statement).id_status
                    statement = select(Prompt).where(Prompt.prompt == data["prompt"])
                    prompt = session.scalar(statement)
                    if not prompt:
                        raise "Le prompt demandé n'existe pas."

                    id_prompt = prompt.id_prompt
                    id_origin = prompt.id_origin
                    insert_log = insert(Log).values(
                        id_log=str(uuid.uuid4()),
                        timestamp=data["timestamp"],
                        id_prompt=id_prompt,
                        id_status=id_status,
                        id_origin=id_origin,
                    )
                    session.execute(insert_log)
                    session.commit()
                    return id_status, True
        except Exception as e:
            erreur = f"Error inserting into table '{table}': {e}"
            return erreur, False
