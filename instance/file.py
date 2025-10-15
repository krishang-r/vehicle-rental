from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///rental.db')
Session = sessionmaker(bind=engine)
session = Session()

# Vehicle model
class Vehicle(Base):
    __tablename__ = 'vehicle'
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(String)
    type = Column(String)
    make = Column(String)
    model = Column(String)
    year = Column(Integer)
    color = Column(String)
    seating_capacity = Column(Integer)
    rent_per_day = Column(Integer)
    availability = Column(String)

# Update all vehicles to available
vehicles = session.query(Vehicle).all()
for v in vehicles:
    v.availability = "Available"
session.commit()

print(f"Updated {len(vehicles)} vehicles to 'Available'")
