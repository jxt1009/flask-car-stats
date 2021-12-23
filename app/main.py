import atexit
from datetime import datetime, timedelta

import plotly
import plotly.express as px
import flask
import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler
from flask import render_template, Response
import pandas as pd

mydb = mysql.connector.connect(
	host="10.0.0.147",
	user="test",
	port="3308",
	database="car_stats"
)

app = flask.Flask(__name__, static_url_path='',
				  static_folder='static',
				  template_folder='template')
app.config["DEBUG"] = True
mycursor = mydb.cursor(buffered=True)

# Global mapping variables
voltage_graph = 0
voltage_graphs = []
voltage_cutoff_time = ""
voltage_interval_limit = 200
voltage_scaling_factor = 15/2.951


# Post route to submit voltage to SQL db
@app.route('/voltage/<voltage>', methods=['GET', 'POST'])
def post_voltage(voltage):
	sql = "INSERT INTO voltage (voltage, car_id) VALUES (%s, %s)"
	val = (voltage, "01")
	mycursor.execute(sql, val)
	return "Success"


# Get the chunks of time series data from the SQL db
def get_voltage_chunks():
	minutes_offset = 30
	row_count = 0
	while row_count < 100:
		sql = "SELECT id,voltage,car_id,timestamp FROM voltage"
		sql += " WHERE timestamp BETWEEN %s AND %s;"
		mycursor.execute(sql, ((datetime.now()-timedelta(minutes=minutes_offset)).strftime('%Y-%m-%dT%H:%M'),datetime.now().strftime('%Y-%m-%dT%H:%M'),))
		minutes_offset += 30
		row_count = mycursor.rowcount

	# Go through rows returned from db
	db_results = pd.DataFrame(columns=["timestamp", "id", "car_id", "voltage", 'voltage_avg'])
	for i in mycursor:
		db_results = db_results.append({"timestamp": i[3],
									  "id":i[0],
									  "car_id": i[2],
									  "voltage": i[1] * voltage_scaling_factor},
									 ignore_index=True)
	db_results = db_results.sort_values(by="timestamp")
	db_results['voltage_avg'] = db_results['voltage'].expanding().mean()
	return [db_results]


# Generate HTML graphs with plotly
def generate_voltage_chart():
	global voltage_graph
	global voltage_graphs
	chunks = get_voltage_chunks()
	voltage_graphs.clear()
	for i in range(0, len(chunks)):
		voltage_avg = str(chunks[i]['voltage'].mean())[:4] +" volts avg"
		fig = px.line(chunks[i],
					  x='timestamp',
					  y=['voltage', 'voltage_avg'],
					  title=voltage_avg)

		graph_json = plotly.io.to_html(fig,
									   include_plotlyjs=False,
									   full_html=False,
									   default_height=450,
									   default_width=1000)
		voltage_graphs.append(graph_json)


# Display the homepage
@app.route("/")
def homepage():
	return render_template("index.html",
						   title="Voltage Chart Test",
						   voltage_graphs=voltage_graphs,
						   voltage_cutoff_time=voltage_cutoff_time)


# Basically a cron job, also runs the job once before adding it
def schedule_function(function, delay_seconds):
	function()
	scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': 1}, timezone='UTC')
	scheduler.add_job(func=function, trigger="interval", seconds=delay_seconds)
	scheduler.start()

	# Shut down the scheduler when exiting the app
	atexit.register(lambda: scheduler.shutdown())


@app.route("/voltage-chart")
def get_voltage_chart():
	html = ""
	for graph in voltage_graphs:
		html+=graph
	return Response(html)


if __name__ == '__main__':
	schedule_function(generate_voltage_chart, 15)
	app.run(host='0.0.0.0', port=5000)
