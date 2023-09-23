from datetime import datetime
from sqlalchemy import text
from app.models import ReportStatus, Result
from app import app, db
import pytz, uuid, ast
from datetime import datetime


# function used to convert time from "HH:MM:SS" format to number of seconds (epoch format)
def time_to_epoch(time_str, store_timezone):
    # Parse the time string into a datetime object
    time_obj = datetime.strptime(time_str, "%H:%M:%S")

    # Convert the time to UTC (using store's timezone information)
    utc_time = store_timezone.localize(time_obj).astimezone(pytz.utc)

    # Calculate and return the Unix epoch time in seconds
    epoch_time = int(utc_time.timestamp())
    return epoch_time


# for a time interval, list of times in the interval, and the corresponding status at each time,
# generate the list of intervals when the status is active
def interpolation(interval_: list, times_: list, statuses_: list) -> list:
    # we create list times that has the interval endpoints included in the list, making it a complete list of times
    times = [interval_[0]]
    times.extend(times_)
    times.append(interval_[1])

    # we assume the initial state of the store same as the state at the first poll in the interval
    # we assume the final state of the store same as the state at the last poll in the interval
    statuses = [statuses_[0]]
    statuses.extend(statuses_)
    statuses.append(statuses_[len(statuses_) - 1])

    active_intervals_after_interpolation = []
    i = 0
    n = len(times)
    # Algorithm:
    # if at t1 the store was active and next at t2 it became inactive, or vice versa,
    # then we interpolate and assume that the state changed in the middle time of t1 and t2
    # if the state remained same, we say that the state reminined same throughout the time between t1 and t2 
    while i < n:
        if statuses[i] == 0:
            i += 1
            continue
        startval = 0
        if i == 0:
            startval = times[i]
        else:
            startval = (times[i] + times[i - 1]) // 2
        j = i
        while j < n and statuses[j] == 1:
            j += 1
        endval = 0
        if j == n:
            endval = times[n - 1]
        else:
            endval = (times[j] + times[j - 1]) // 2
        active_intervals_after_interpolation.append([startval, endval])
        i = j + 1
    return active_intervals_after_interpolation
       
       
# return the number of seconds after start_time that occur in the sorted intervals
def accumulate_from_date(start_time: int, intervals: list) -> int:
    uptime = 0
    i = 0
    n = len(intervals)
    while i < n and start_time > intervals[i][1]:
        i += 1
    if i == n:
        return uptime
    if start_time >= intervals[i][0] and start_time <= intervals[i][1]:
        uptime += intervals[i][1] - start_time
        i += 1
    while i < n:
        uptime += intervals[i][1] - intervals[i][0]
        i += 1
    return uptime

# function used to calculate the uptime for past 1 hour, 24 hours (day), and 24*7 hours (week) from curtime
def calculate_uptimes(curtime: int, intervals: list) -> list:
    uptime_hour = accumulate_from_date(curtime - 60 * 60, intervals)
    uptime_day = accumulate_from_date(curtime - 24 * 60 * 60, intervals)
    uptime_week = accumulate_from_date(curtime - 24 * 7 * 60 * 60, intervals)
    return [uptime_hour, uptime_day, uptime_week]

# function used to generate a report_id and create an entry for that report_id in the ReportStatus table
def generate_report_id(current_time: int) -> str:
    report_id = ""
    try:
        with app.app_context():
            report_id = str(uuid.uuid4())
            report_status = ReportStatus(
                report_id=report_id, status="Running", created_date=current_time
            )
            db.session.add(report_status)
            db.session.commit()
        return report_id
    except Exception as e:
        db.session.rollback()
        print("Error inserting data : ", e)
    finally:
        db.session.close()
        return report_id

# get all the storestatus data from the store_status table in the DB
def get_store_ids_data() -> list:
    with app.app_context():
        with db.engine.connect() as connection:
            store_ids_data = connection.execute(
                text(
                    """
                    SELECT store_id, timestamp_utc, status
                    FROM store_status
                    ORDER BY store_id, timestamp_utc
                    """
                )
            )
    return list(list(x for x in obj) for obj in store_ids_data)

# function to get the business hours data from the business_hours table in DB
def get_business_hours_data():
    with app.app_context():
        with db.engine.connect() as connection:
            return connection.execute(
                text(
                    """
                    SELECT store_id, day_of_week, start_time_utc, end_time_utc 
                    FROM business_hours 
                    ORDER BY store_id, day_of_week, start_time_utc
                    """
                )
            )


# function to create the dict to store the business hours of all the stores
def get_business_hours_hash(business_hours_data, unique_store_ids:dict) -> dict:
    business_hours_hash = {}
    for res in business_hours_data:
        store_id = res[0]
        day_of_week = res[1]
        if store_id not in business_hours_hash:
            # create a new object if not yet created
            business_hours_hash[store_id] = {str(i): [] for i in range(7)}
        business_hours_hash[store_id][day_of_week].append([res[2], res[3]])
    # If for any id, business hours is not specified, we assume its operational 24*7
    for id in unique_store_ids:
        if id not in business_hours_hash:
            business_hours_hash[id] = {str(i): [[0, 86400]] for i in range(7)}
    # business hours hash for any store_id and for any weekday contains time intervals in relative seconds format, means in epoch type
    return business_hours_hash

#  function to get a list of time intervals since past 7 days when any store was expected to be open
def get_expected_active_intervals(business_hours_hash:dict, unique_store_ids:dict, current_time:int) -> dict:
    expected_active_intervals = {id: [] for id in unique_store_ids}
    start_time = current_time - 24 * 8 * 60 * 60
    weekday = str(datetime.fromtimestamp(start_time).weekday())

    for id in unique_store_ids:
        # base_time represents the midnight time of the date 8 days before current_time
        base_time = int(
            datetime.fromtimestamp(start_time)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
        )
        active_intervals_for_store = []
        # run a loop for all the past 8 days from current_time
        for _ in range(8):
            # intervals stores business hours of the store having store_id=id on weekday
            intervals = business_hours_hash[id][weekday]
            for interval in intervals:
                # generate an interval having absolute epoch time
                temp = [int(i) + base_time for i in interval]
                active_intervals_for_store.append(temp)
            # increment the base time and weekday by 1 day
            base_time += 60 * 60 * 24
            weekday = str((int(weekday) + 1) % 7)
        # update the expected_active_intervals for the id
        expected_active_intervals[id] = active_intervals_for_store
    return expected_active_intervals

# function responsible for generating the data for the report and updating it in the results table in the DB
def generate_report(report_id: str, store_ids_data: list, expected_active_intervals: dict, current_time: int) -> None:
    # stores the results to be inserted into the DB
    db_results = []

    # we iterate over all store status entries
    # since the entries are sorted acc to the store_id, all the store_ids occur together
    # we keep on accumulating the data for a store id in store_obj
    # once we encounter a new id, we update the store_obj into the DB and reinitialize the store_obj 
    store_obj = {}
    # cur_id is the variable that stores the store_id we are currently working on
    cur_id = ""

    # this is done so that the last store_obj also gets saved, otherwise we would have to save the last store_obj separately after the iterations end
    # we can technically append any dummy data
    store_ids_data.append(store_ids_data[0])

    # iterate over every entry in store_ids_data
    for index, entry in enumerate(store_ids_data):
        store_id = entry[0]
        timestamp = int(entry[1])
        status = entry[2]
        # business slots is the list of active intervals for the store in past 8 days
        business_slots = expected_active_intervals[store_id]

        # if store_id is not cur_id, means we have encountered new store_id and we need to save the data in store_obj to the DB
        if store_id != cur_id:
            # we dont move forward if this the first iteration itself
            if cur_id != '':
                # active_intervals stores the actual intervals when the store was found to be active after interpolation
                active_intervals = []
                for interval_str, intervals in store_obj.items():
                    interval = ast.literal_eval(interval_str)
                    active_intervals.extend(
                        interpolation(interval, intervals[0], intervals[1])
                    )
                # calculate the expected uptimes, actual uptimes, then downtime = expected_uptime - actual_uptime
                expected_uptimes = calculate_uptimes(current_time, expected_active_intervals[cur_id])
                actual_uptimes = calculate_uptimes(current_time, active_intervals)
                actual_downtimes = [(expected_uptimes[i] - actual_uptimes[i]) for i in range(3)]
                # create Result object
                result = Result(
                    report_id=report_id,
                    store_id=cur_id,
                    uptime_last_hour=actual_uptimes[0],
                    uptime_last_day=actual_uptimes[1],
                    uptime_last_week=actual_uptimes[2],
                    downtime_last_hour=actual_downtimes[0],
                    downtime_last_day=actual_downtimes[1],
                    downtime_last_week=actual_downtimes[2],
                )
                # append the result object in the list of objects to append to the DB at the last
                db_results.append(result)
            # refresh the cur_id and store_obj to fresh values
            cur_id = store_id
            store_obj = {}

        # iterate over all the business slots
        for business_slot in business_slots:
            # check if the timestamp lies within this business slot
            if timestamp >= int(business_slot[0]) and timestamp <= int(business_slot[1]):
                interval = str([int(i) for i in business_slot])
                if interval not in store_obj:
                    # for each interval, the store_obj stores the poll times in first list and the corresponding status in the second list
                    store_obj[interval] = [[], []]
                store_obj[interval][0].append(timestamp)
                if status == "active":
                    store_obj[interval][1].append(1)
                else:
                    store_obj[interval][1].append(0)
    # At the last, add all the db_results to the DB
    with app.app_context():
        for result in db_results:
            db.session.add(result)
        db.session.commit()
        with db.engine.connect() as connection:
            connection.execute(
                text(
                    f"""
                    UPDATE report_status
                    SET status = "Completed"
                    WHERE report_id = "{report_id}";
                    commit;
                    """
                )
            )

# # 
# def get_report(report_id):
#     with app.app_context():
#         with db.engine.connect() as connection:
#             connection.execute(
#                 text(
#                     f"""
#                     SELECT 
#                     WHERE report_id = "{report_id}";
#                     commit;
#                     """
#                 )
#             )

# function to get the results for a report_id
def get_report_data(report_id: str) -> list:
    with app.app_context():
        with db.engine.connect() as connection:
            report_data = connection.execute(
                text(
                    f"""
                    SELECT store_id, uptime_last_hour, uptime_last_day, uptime_last_week, downtime_last_hour, downtime_last_day, downtime_last_week
                    FROM result 
                    WHERE report_id = '{report_id}'
                    """
                )
            )
            data = [[e for e in data] for data in report_data]
            # convert hour data into minutes and other data into hours
            for val in data:
                val[1] /= 60
                val[2] /= 3600
                val[3] /= 3600
                val[4] /= 60
                val[5] /= 3600
                val[6] /= 3600
            return data

# Get the status of the report_id, used for polling the status of the report
def get_report_status(report_id: str):
    with app.app_context():
        with db.engine.connect() as connection:
            return connection.execute(
                text(
                    f"""
                SELECT status
                FROM report_status
                WHERE report_id = '{report_id}'
                """
                )
            )
