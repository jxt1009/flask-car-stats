from datetime import datetime, timedelta

import flask
import pymysql
from flask import render_template
import pandas as pd

conn = pymysql.connect(host="0.0.0.0",
					   port=3306,
					   user="test",
					   database="car_stats",
					   port=3308)


app = flask.Flask(__name__, static_url_path='',
				  static_folder='static',
				  template_folder='template')

app.config["DEBUG"] = True

# Global mapping variables
voltage_graphs = pd.DataFrame()
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
	params = ((datetime.utcnow()-timedelta(minutes=200)).strftime('%Y-%m-%dT%H:%M'),datetime.utcnow().strftime('%Y-%m-%dT%H:%M'),)

	db_results = pd.read_sql(sql=sql,con=conn,params=params)

	db_results = db_results.sort_values(by="timestamp")
	db_results['voltage'] = db_results['voltage'].apply(lambda x: x * ((R1+R2)/R2))
	db_results['timestamp'] = db_results['timestamp']
	db_results['voltage_avg'] = db_results['voltage'].expanding().mean()

	db_results.append(db_results.iloc[-1],ignore_index=True)
	return db_results

# Display the homepage
@app.route("/")
def homepage():
	return render_template("index.html", title="Voltage Chart Test")


@app.route("/voltage-chart")
def get_voltage_chart():
	return get_voltage_chunks().to_json(orient="records")


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000)
