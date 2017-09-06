from app import db
from sqlalchemy.dialects.postgresql import JSON


class Invalid(db.Model):
    __tablename__ = 'invalid'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String())

    def __init__(self, vin):
        self.vin = vin

    def __repr__(self):
        return '<id {}>'.format(self.id)


class Result(db.Model):
    __tablename__ = 'cars'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String())
    year = db.Column(db.Integer)
    # r_model = db.Column(db.Boolean)
    color = db.Column(db.String())
    stripe = db.Column(db.String())
    electronics = db.Column(db.Boolean)
    convenience = db.Column(db.Boolean)
    # painted_roof = db.Column(db.Boolean)
    build_date = db.Column(db.String())
    # price = db.Column(db.String())
    # dealer = db.Column(db.String())
    # address = db.Column(db.String())
    # phone = db.Column(db.String())
    # url = db.Column(db.String())

    def __init__(self, vin, year, color, build_date, stripe, electronics, convenience):
        # self.url = url
        self.vin = vin
        self.year = year
        # self.r_model = r_model
        self.color = color
        self.stripe = stripe
        self.electronics = electronics
        self.convenience = convenience
        # self.painted_roof = painted_roof
        self.build_date = build_date
        # self.price = price
        # self.dealer = dealer
        # self.address = address
        # self.phone = phone

    def __repr__(self):
        return '<id {}>'.format(self.id)
