from flask import jsonify, send_file
from app.helper import *
import threading
from app import app
from app.backgroundTask import background_task
import csv
import io


# Create a route for triggering the report generation
@app.route("/trigger_report", methods=["POST"])
def trigger_report():
    current_time = 1674650603  # Mocked time for datetime.now().timestamp()

    # generate a uuid for report_id
    report_id = generate_report_id(current_time)

    # create a thread that does the background processing for the creation of the report
    thread = threading.Thread(
        target=background_task,
        kwargs={"current_time": current_time, "report_id": report_id},
    )
    # start the thread
    thread.start()

    # Return the report id
    return jsonify({"report_id": report_id}), 202


# Create a route for getting the report status or the CSV report
@app.route("/get_report/<report_id>", methods=["GET"])
def get_report(report_id):
    try:
        # get the status of the report
        report_status = get_report_status(report_id)
        report_status = [i for i in report_status][0][0]
        
        # if status is Running, return the "Running" message
        if report_status == "Running":
            return jsonify({"status": "Running"})
        
        # if status is "Completed", get the data for the report_id
        report_data = get_report_data(report_id)
        # Create a CSV from the report_data
        output = io.StringIO()
        csv_writer = csv.writer(output)
        csv_writer.writerows(report_data)
        # Send the CSV data as a downloadable attachment
        return (
            send_file(
                io.BytesIO(output.getvalue().encode("utf-8")),
                as_attachment=True,
                download_name=f"{report_id}_report.csv",
                mimetype="text/csv",
            ),
            200,
        )
    except Exception as e:
        print(e)
        return jsonify({"error": "could not fetch"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
