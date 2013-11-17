# -*- coding: utf-8 -*-

import sys
import os
import datetime

from sqlalchemy import create_engine, Column, Integer, String, Unicode, Boolean, DateTime, ForeignKey, Date, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref, aliased
from sqlalchemy.schema import Index
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import object_session
from sqlalchemy.sql.expression import desc, func, and_, alias

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

    def add_statement(self, phase, time, value):
        statement = Statement()
        statement.user = self
        statement.phase = phase
        statement.time = time
        statement.value = value
        object_session(self).add(statement)

    def get_last_statement(self, phase):
        try:
            return object_session(self).query(Statement). \
                filter(Statement.phase == phase). \
                filter(Statement.user == self). \
                order_by(desc(Statement.time)). \
                limit(1).one()
        except NoResultFound:
            return None

    def get_statements_num(self, phase):
        return object_session(self).query(Statement). \
            filter(Statement.phase == phase). \
            filter(Statement.user == self).count()

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
    __table_args__ = (
        UniqueConstraint('date', 'moment'),
        )

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    moment = Column(Integer, nullable=False)

    def get_statements(self):
        # FIXME - Fix the following code and use it instead of the bad hack
        #inner_max_time = func.max(Statement.time).alias()
        #inner_statement = aliased(Statement)
        #max_query = object_session(self).query(inner_statement, inner_max_time).group_by(inner_statement.user).subquery()
        #outer_statement = aliased(Statement)
        #print >> sys.stderr, max_query.c
        #return object_session(self).query(outer_statement).join((max_query, max_query.c.inner_max_time == outer_statement.time))

        statements = object_session(self).query(Statement).filter(Statement.phase == self).all()
        users = {}
        for statement in statements:
            if statement.user.username not in users:
                users[statement.user.username] = (datetime.datetime.fromtimestamp(0), None)
            if statement.time >= users[statement.user.username][0]:
                users[statement.user.username] = (statement.time, statement)
        return sorted(filter(lambda x: x.value is not None, map(lambda (x, y): y, users.itervalues())), key=lambda x: x.time)

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
    __table_args__ = (
        UniqueConstraint('user_id', 'phase_id', 'time'),
        )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    phase_id = Column(Integer, ForeignKey(Phase.id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    time = Column(DateTime, nullable=False)
    value = Column(Unicode, nullable=True)

    user = relationship(User)
    phase = relationship(Phase)
