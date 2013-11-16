# -*- coding: utf-8 -*-

import sys
import os
import datetime

from sqlalchemy import create_engine, Column, Integer, String, Unicode, Boolean, ForeignKey, Date, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.schema import Index
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import object_session

with open(os.path.join(os.path.dirname(__file__), 'dbauth')) as fdbauth:
    db = create_engine(fdbauth.read().strip(), echo=False)
Session = sessionmaker(db)
Base = declarative_base(db)

create_all = Base.metadata.create_all
drop_all = Base.metadata.drop_all

MOMENTS = [('colazione', datetime.time(0)),
           ('pranzo', datetime.time(11)),
           ('cena', datetime.time(15))]

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)

    def get_statement(self, phase):
        try:
            statement = object_session(self).query(Statement). \
                filter(Statement.phase == phase). \
                filter(Statement.user == self).one()
        except NoResultFound:
            statement = Statement()
            statement.user = self
            statement.phase = phase
            statement.value = None

        return statement

    def get_pretty_name(self):
        return self.username.replace('@UZ.SNS.IT', '')

    @classmethod
    def get_from_username(cls, session, username):
        try:
            user = session.query(User).filter(User.username == username).one()
        except NoResultFound:
            user = User()
            user.username = username
            user.enabled = True
            session.add(user)

        return user

class Phase(Base):
    __tablename__ = 'phases'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    moment = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('date', 'moment'),
        )

    def get_statements(self):
        return object_session(self).query(Statement).filter(Statement.phase == self).all()

    @classmethod
    def get_current(cls, session, when=None):
        if when is None:
            when = datetime.datetime.now()
        moment = None
        for mom_idx, (mom_name, mom_time) in enumerate(MOMENTS):
            if mom_time <= when.time():
                moment = mom_idx
        try:
            phase = session.query(Phase).filter(Phase.date == when.date()). \
                filter(Phase.moment == moment).one()
        except NoResultFound:
            phase = Phase()
            phase.date = when.date()
            phase.moment = moment
            session.add(phase)

        return phase

class Statement(Base):
    __tablename__ = 'statements'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    phase_id = Column(Integer, ForeignKey(Phase.id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    value = Column(Unicode, nullable=False)

    user = relationship(User)
    phase = relationship(Phase)
