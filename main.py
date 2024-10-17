from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# SQLite database setup
DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models for SQLAlchemy
class CustomerDB(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, index=True)
    phone = Column(String)

class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    total_price = Column(Float)
    status = Column(String, default="pending")

class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)

# Create tables in the database
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class Customer(BaseModel):
    name: str
    email: str
    phone: str

class Order(BaseModel):
    customer_id: int
    products: List[int]

class UpdateOrderStatus(BaseModel):
    status: str

class Payment(BaseModel):
    order_id: int
    amount: float
    payment_method: str

# 1. Create a Customer
@app.post("/customers/")
def create_customer(customer: Customer, db: Session = Depends(get_db)):
    new_customer = CustomerDB(**customer.dict())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

# 2. Get Customer Details
@app.get("/customers/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(CustomerDB).filter(CustomerDB.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

# 3. Place a New Order
@app.post("/orders/")
def place_order(order: Order, db: Session = Depends(get_db)):
    customer = db.query(CustomerDB).filter(CustomerDB.id == order.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    total_price = sum(db.query(ProductDB).filter(ProductDB.id == pid).first().price for pid in order.products)
    new_order = OrderDB(customer_id=order.customer_id, total_price=total_price)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

# 4. Update Order Status
@app.patch("/orders/{order_id}/status")
def update_order_status(order_id: int, order_status: UpdateOrderStatus, db: Session = Depends(get_db)):
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = order_status.status
    db.commit()
    return {"order_id": order_id, "status": order.status}

# 5. Make a Payment
@app.post("/payments/")
def make_payment(payment: Payment, db: Session = Depends(get_db)):
    order = db.query(OrderDB).filter(OrderDB.id == payment.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if payment.amount != order.total_price:
        raise HTTPException(status_code=400, detail="Payment amount does not match order total")

    return {"message": "Payment successful"}
