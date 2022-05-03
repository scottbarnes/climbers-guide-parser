from .database import Base # type: ignore
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON # type:ignore
from sqlalchemy.orm import relationship # type: ignore


class PeakModel(Base):
    __tablename__ = 'peaks'
    id = Column(Integer, primary_key=True)
    aka = Column(JSON)
    created = Column(DateTime)
    description = Column(String)
    elevations = Column(JSON)
    gps_coordinates = Column(String)
    last_modified = Column(DateTime)
    location_description = Column(String)
    name = Column(String)
    peak_id = Column(String)
    region_slug = Column(String)
    slug = Column(String)
    utm_coordinates = Column(String)
    routes = relationship("RouteModel", backref="peaks")
    region_id = Column(Integer, ForeignKey('regions.id'))

    def __repr__(self):
        return f"<Peak(name={self.name}, routes={self.routes})>"


class RouteModel(Base):
    __tablename__ = 'routes'
    id = Column(Integer, primary_key=True)
    aka = Column(JSON)
    class_rating = Column(String)
    created = Column(DateTime)
    description = Column(String)
    last_modified = Column(DateTime)
    name = Column(String)
    peak_id = Column(Integer, ForeignKey('peaks.id'))
    route_id = Column(String)

    def __repr__(self):
        return f"<Route(name={self.name}, peak={self.peaks.name})>"


class PassModel(Base):
    __tablename__ = 'passes'
    id = Column(Integer, primary_key=True)
    aka = Column(JSON)
    class_rating = Column(String)
    created = Column(DateTime)
    description = Column(String)
    elevations = Column(JSON)
    last_modified = Column(DateTime)
    name = Column(String)
    pass_id = Column(String)
    region_slug = Column(String)
    slug = Column(String)
    region_id = Column(Integer, ForeignKey('regions.id'))

    def __repr__(self):
        return f"<Pass(name={self.name})>"


class RegionModel(Base):
    __tablename__ = 'regions'
    id = Column(Integer, primary_key=True)
    created = Column(DateTime)
    last_modified = Column(DateTime)
    name = Column(String)
    region_id = Column(String)
    slug = Column(String)
    peaks = relationship("PeakModel", backref="region")
    passes = relationship("PassModel", backref="region")

    def __repr__(self):
        return f"<Region(name={self.name})>"
