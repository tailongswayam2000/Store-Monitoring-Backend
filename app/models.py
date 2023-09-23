from app import db

# Table to store the Store Status data from storestatus.csv
class StoreStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.String(50))
    timestamp_utc = db.Column(db.Integer)
    status = db.Column(db.String(50))

# table to store the status of the reports
class ReportStatus(db.Model):
    report_id = db.Column(db.String(50), primary_key=True)
    status = db.Column(db.String(50))
    created_date = db.Column(db.Integer)

# table to store the results of all the reports
class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(50))
    store_id = db.Column(db.String(50))
    uptime_last_hour = db.Column(db.Integer)
    uptime_last_day = db.Column(db.Integer)
    uptime_last_week = db.Column(db.Integer)
    downtime_last_hour = db.Column(db.Integer)
    downtime_last_day = db.Column(db.Integer)
    downtime_last_week = db.Column(db.Integer)

# table to store the business hours data from businesshours.csv
class BusinessHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.String(50))
    day_of_week = db.Column(db.String(50))
    start_time_utc = db.Column(db.Integer)
    end_time_utc = db.Column(db.Integer)

# table to store the store timezones data from storetimezones.csv
class StoreTimezones(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.String(50))
    timezone_str = db.Column(db.String(255))
