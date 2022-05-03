from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, DateTime # type:ignore
from sqlalchemy.ext.declarative import declarative_base # type:ignore
from sqlalchemy.orm import relationship, backref, sessionmaker, joinedload # type: ignore


SQLITE = 'sqlite'

class DB:
    DB_ENGINE = {
        SQLITE: 'sqlite:///{DATABASE}'
    }

    db_engine = None

    def __init__(self, dbtype, username='', password='', dbname=''):
        dbtype = dbtype.lower()

        if dbtype in self.DB_ENGINE.keys():
            engine_url = self.DB_ENGINE[dbtype].format(DATABASE=dbname)
            # self.db_engine = create_engine(engine_url, echo=True)
            self.db_engine = create_engine(engine_url)
            print(self.db_engine)
        else:
            print(f"DBType '{dbtype}' not found in DB_ENGINE")

    def create_db_engine(self):
        """ Create a database """
        return self.db_engine


Base = declarative_base()
