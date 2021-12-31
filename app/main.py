import sys
import flask
import pymysql
from flask import render_template
import pandas as pd

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
	conn = get_connection()
	sql = "INSERT INTO voltage (voltage, car_id) VALUES (%s, %s)"
	val = (voltage, "01")
	cursor = conn.cursor()
	cursor.execute(sql, val)
	if conn.affected_rows() > 0:
		conn.commit()
		conn.close()
		return "Success"
	else:
		conn.close()
		return "Error"

def get_connection():
	return pymysql.connect(host="10.0.0.147",
						   port=3308,
						   user="test",
						   password="root",
						   database="car_stats")

# Get the chunks of time series data from the SQL db
def get_voltage_chunks(view_time):
	conn = get_connection()
	sql = "SELECT id,voltage,car_id,timestamp FROM voltage order by id desc limit %(view_time)s;"

	if view_time is None:
		view_time = 60
	else:
		view_time = int(view_time)

	db_results = pd.read_sql(sql=sql, con=conn, params={"view_time": view_time})
	db_results['voltage'] = db_results.voltage.apply(lambda x: x * ((R2 + R1) / R2))
	db_results['voltage_avg'] = db_results.voltage.expanding().mean()
	conn.close()

	return db_results


# Display the homepage
@app.route("/")
def homepage():
	return render_template("index.html", title="Voltage Chart Test", chart_title="12V Battery Charge Status")


@app.route("/voltage-chart")
@app.route("/voltage-chart/<view_time>")
def get_voltage_chart(view_time=None):
	chunks = get_voltage_chunks(view_time)
	json_output = chunks.to_json(orient="records")

	return json_output


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, threaded=True)
