import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    MetaData, Column, Integer, String, Float, Boolean, ForeignKey, DateTime,
    or_)
from sqlalchemy.orm import sessionmaker, relationship

from settings import config as cfg


engine = sqlalchemy.create_engine(
    f"mysql+pymysql://"
    f"test:XzXQDNqgTiAu3gw6ILfN3xAUVIZCybKa"
    f"@{cfg.DATABASE_HOST}/myfund_test?charset=utf8&",
    echo=False, pool_pre_ping=True
)
meta = MetaData(bind=engine, reflect=True)

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()
Base.metadata.create_all(engine)


def select(table_name):
    table = meta.tables[table_name]
    with engine.begin() as connect:
        result = connect.execute(sqlalchemy.select([table])).fetchall()
    return result


class TelegramUsers(Base):
    __tablename__ = "telegram_users"

    id = Column(Integer, primary_key=True)
    ts_add = Column(Integer)
    ts_update = Column(Integer)
    telegram_id = Column(Integer)
    partner_id = Column(Integer, ForeignKey('partners.id'))
    referrer_id = Column(Integer)
    username = Column(String(50))
    first_name = Column(String(50))
    last_name = Column(String(50))

    partner = relationship("Partners", back_populates="user")

    def __repr__(self):
        output = (
            f"<TelegramUsers(id='{self.id}', "
            f"username='{self.username}', "
            f"telegram_id='{self.telegram_id}, "
            f"partner_id='{self.partner_id}, "
            f"referrer_id='{self.referrer_id}')>"
        )
        return output


class Partners(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True)
    priv = Column(String(12))
    ts_add = Column(Integer)
    ts_update = Column(Integer)
    active = Column(Integer)
    username = Column(String(32))
    password = Column(String(32))
    show_token_stat = Column(Integer)
    telegram_id = Column(Integer)
    tel_num = Column(String(12))
    first_name = Column(String(50))
    token_count = Column(Float)
    last_name = Column(String(50))
    referrer_id = Column(Integer)
    telegram_user = Column(String(50))
    email = Column(String(100))

    def __repr__(self):
        output = (
            f"<PartnersEvent(id='{self.id}', "
            f"last_name='{self.last_name}', "
            f"telegram_id='{self.telegram_id}')>"
        )
        return output


class PartnersWallet(Base):
    __tablename__ = "partners_wallet"

    id = Column(Integer,  primary_key=True)
    partner_id = Column(Integer, ForeignKey('partners.id'))
    currency = Column(String(10))
    addr = Column(String(150))
    autopay = Column(String(20))
    ts_add = Column(Integer)

    partner = relationship("Partners", back_populates="wallets")

    def __repr__(self):
        return f"<PartnersWallet(id='{self.id}', " \
               f"partner_id='{self.partner_id}', " \
               f"currency='{self.currency}', " \
               f"addr='{self.addr}', " \
               f"autopay={self.autopay})>"


class WalletsEvent(Base):
    __tablename__ = "wallets_event"

    id = Column(Integer,  primary_key=True)
    ts_add = Column(Integer)
    partner_id = Column(Integer)
    wallet_id = Column(Integer, ForeignKey('partners_wallet.id'))
    amount = Column(Float)
    status = Column(String(20))
    source_name = Column(String(20))
    source_id = Column(Integer)

    wallet = relationship("PartnersWallet", back_populates="events")

    def __repr__(self):
        return f"<PartnersWallet(id='{self.id}', " \
               f"wallet_id='{self.wallet_id}', " \
               f"partner_id='{self.partner_id}', " \
               f"status='{self.status}', " \
               f"amount='{self.amount}')>"


class WithdrawalTicket(Base):
    __tablename__ = 'withdrawal_ticket'

    id = Column(Integer, primary_key=True)
    partner_id = Column(Integer)
    src = Column(String(10))
    dst = Column(String(10))
    src_count = Column(Float)
    dst_count = Column(Float)
    rate = Column(Float)
    address = Column(String(200))
    status = Column(String(20))
    ts_create = Column(Integer)
    ts_update = Column(Integer)

    def __repr__(self):
        output = (
            f"<WithdrawalTicket(id='{self.id}', "
            f"partner_id='{self.partner_id}', "
            f"src='{self.src}', "
            f"dst='{self.dst}', "
            f"src_count='{self.src_count}', "
            f"dst_count='{self.dst_count}', "
            f"rate='{self.rate}', "
            f"status='{self.status}')>"
        )
        return output


class ExchangeEvents(Base):
    __tablename__ = 'exchange_events'

    id = Column(Integer, primary_key=True)
    partner_id = Column(Integer)
    src = Column(String(10))
    dst = Column(String(10))
    amount = Column(Float)
    autopay = Column(Boolean)
    status = Column(String(20))
    ts_add = Column(Integer)

    def __repr__(self):
        output = (
            f"<ExchangeEvents(id='{self.id}', "
            f"partner_id='{self.partner_id}', "
            f"src='{self.src}', "
            f"dst='{self.dst}', "
            f"amount='{self.amount}', "
            f"status='{self.status}')>"
        )
        return output


class GatewayEvents(Base):
    __tablename__ = 'gateway_events'

    id = Column(Integer, primary_key=True)
    currency = Column(String(50))
    event_name = Column(String(3))
    amount = Column(Float)
    address = Column(String(50))
    txid = Column(String(150))
    confirmed = Column(Boolean)
    ts_add = Column(Integer)

    def __repr__(self):
        output = (
            f"<GatewayEvents(id='{self.id}', "
            f"currency='{self.currency}', "
            f"confirmed='{self.confirmed}', "
            f"address='{self.address}', "
            f"amount='{self.amount}')>"
        )
        return output


class PartnersAddress(Base):
    __tablename__ = "partners_address"

    id = Column(Integer,  primary_key=True)
    partner_id = Column(Integer, ForeignKey('partners.id'))
    type = Column(String(50))
    addr = Column(String(200))
    testnet = Column(Boolean)

    partner = relationship("Partners", back_populates="addresses")

    def __repr__(self):
        return f"<PartnersAddress(partner_id='{self.partner_id}')>"


class PartnerEvents(Base):
    __tablename__ = 'partners_event'

    id = Column(Integer, primary_key=True)
    partner_id = Column(Integer)
    day = Column(String)
    event_name = Column(String)
    event_param = Column(Float)
    event_result = Column(Integer)


class FundHist(Base):
    __tablename__ = 'fund_hist'

    id = Column(Integer, primary_key=True)
    day = Column(String)
    sum_btc = Column(Float)
    sum_usd = Column(Float)
    sum_rub = Column(Float)
    token_usd = Column(Float)
    token_btc = Column(Float)
    token_rub = Column(Float)

    def __repr__(self):
        output = (
            f"<FundHist(id='{self.id}', "
            f"day='{self.day}', sum_usd={self.sum_usd}, "
            f"token_usd='{self.token_usd}')>"
        )
        return output


class CoinOutputHist(Base):
    __tablename__ = 'coin_output_hist'

    id = Column(Integer, primary_key=True)
    amount = Column(Float)
    tx_id = Column(String(120))
    time_output = Column(DateTime)
    currency = Column(String(10))


class CostPriceHist(Base):
    __tablename__ = 'cost_price_hist'

    id = Column(Integer, primary_key=True)
    day = Column(String(12))
    src = Column(String(12))
    dst = Column(String(12))
    cost = Column(Float)
    stock_id = Column(Integer)
    ts_create = Column(Integer)
    ts_update = Column(Integer)


def commit():
    session.commit()


def set_relationship():
    Partners.addresses = relationship(
        "PartnersAddress", order_by=PartnersAddress.partner_id,
        back_populates="partner")
    Partners.user = relationship(
        "TelegramUsers", order_by=TelegramUsers.partner_id,
        back_populates="partner")
    Partners.wallets = relationship(
        "PartnersWallet", order_by=PartnersWallet.partner_id,
        back_populates="partner")
    PartnersWallet.events = relationship(
        "WalletsEvent", order_by=WalletsEvent.wallet_id,
        back_populates="wallet")


set_relationship()
