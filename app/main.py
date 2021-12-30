from datetime import datetime, timedelta
import sys
import flask
import pymysql
from flask import render_template
import pandas as pd

conn = pymysql.connect(host="10.0.0.147",
					   port=3308,
					   user="test",
					   password="root",
					   database="car_stats")


app = flask.Flask(__name__, static_url_path='',
				  static_folder='static',
				  template_folder='template')
if "dev" in sys.argv:
	app.config["DEBUG"] = True

# Global mapping variables
R1 = 8800
R2 = 2200


# Post route to submit voltage to SQL db
@app.route('/voltage/<voltage>', methods=['GET', 'POST'])
def post_voltage(voltage):
	sql = "INSERT INTO voltage (voltage, car_id) VALUES (%s, %s)"
	val = (voltage, "01")
	cursor = conn.cursor()
	cursor.execute(sql, val)
	if conn.affected_rows() > 0:
		conn.commit()
		return "Success"
	else:
		return "Error"


# Get the chunks of time series data from the SQL db
def get_voltage_chunks():
	sql = "SELECT id,voltage,car_id,timestamp FROM voltage"
	sql += " WHERE timestamp BETWEEN %s AND %s;"
	params = ((datetime.utcnow()-timedelta(minutes=60)).strftime('%Y-%m-%dT%H:%M'),
			  datetime.utcnow().strftime('%Y-%m-%dT%H:%M'),)

	db_results = pd.read_sql(sql=sql,con=conn,params=params)
	db_results['voltage'] = db_results.voltage.apply(lambda x: x * ((R2+R1)/R2))
	db_results['voltage_avg'] = db_results.voltage.expanding().mean()
	return db_results


# Display the homepage
@app.route("/")
def homepage():
	return render_template("index.html", title="Voltage Chart Test")


@app.route("/voltage-chart")
def get_voltage_chart():
	chunks = get_voltage_chunks()
	return chunks.to_json(orient="records")


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, threaded=True)
