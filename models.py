from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from db import Base


class PortMap(Base):
    __tablename__ = "port_maps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    port_prefix = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Carrier(Base):
    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    equipment_interchange_receipts = relationship(
        "EquipmentInterchangeReceipt",
        back_populates="carrier",
        cascade="all, delete-orphan",
    )


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tin_number = Column(String(64), nullable=False, unique=True)
    customer_name = Column(String(255), unique=True)
    customer_vat_number = Column(String(64))
    email = Column(String(255), nullable=False)
    region = Column(String(255), nullable=False)
    city = Column(String(255), nullable=False)
    business_type = Column(String(255), nullable=False)
    primary_contact = Column(String(255))
    secondary_contact = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    equipment_interchange_receipts = relationship(
        "EquipmentInterchangeReceipt",
        back_populates="customer",
        cascade="all, delete-orphan",
    )


class Depot(Base):
    __tablename__ = "depots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    eir_number_start = Column(Float)
    eir_number_end = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    containers = relationship("Container", back_populates="depot", cascade="all, delete-orphan")
    equipment_interchange_receipts = relationship(
        "EquipmentInterchangeReceipt",
        back_populates="depot",
        cascade="all, delete-orphan",
    )


class Container(Base):
    __tablename__ = "containers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_number = Column(String(255), nullable=False, unique=True)
    size = Column(String(50))
    container_type = Column(String(50))
    container_status = Column(String(50))
    depot_id = Column(Integer, ForeignKey("depots.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    depot = relationship("Depot", back_populates="containers")
    equipment_interchange_receipts = relationship(
        "EquipmentInterchangeReceipt",
        back_populates="container",
        cascade="all, delete-orphan",
    )


class Booking(Base):
    """
    Minimal Booking model to satisfy the foreign key reference from
    EquipmentInterchangeReceipt. Extend as needed.
    """

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    equipment_interchange_receipts = relationship(
        "EquipmentInterchangeReceipt",
        back_populates="booking",
        cascade="all, delete-orphan",
    )


class EquipmentInterchangeReceipt(Base):
    __tablename__ = "equipment_interchange_receipts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eir_number = Column(Integer, nullable=False, unique=True)

    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    depot_id = Column(Integer, ForeignKey("depots.id"), nullable=True)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=True)

    truck_number = Column(String(255), nullable=False)
    trailer_number = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=False)
    driver = Column(String(255), nullable=False)
    status = Column(String(50))
    seal_number = Column(String(255))
    sale_status = Column(String(50))
    depot_date = Column(DateTime)
    reservation_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    booking = relationship("Booking", back_populates="equipment_interchange_receipts")
    container = relationship("Container", back_populates="equipment_interchange_receipts")
    customer = relationship("Customer", back_populates="equipment_interchange_receipts")
    depot = relationship("Depot", back_populates="equipment_interchange_receipts")
    carrier = relationship("Carrier", back_populates="equipment_interchange_receipts")



