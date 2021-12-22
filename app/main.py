import atexit
import base64
import io
import random
import time
from datetime import datetime
from io import BytesIO

import plotly
import plotly.express as px
import flask
import json
import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler
from flask import render_template, redirect, url_for, request, Response
import pandas as pd

mydb = mysql.connector.connect(
	host="172.21.0.2",
	user="test",
	#password="password",
	database="car_stats"
)

app = flask.Flask(__name__, static_url_path='',
				  static_folder='static',
				  template_folder='template')
app.config["DEBUG"] = True
mycursor = mydb.cursor()

# Global mapping variables
voltage_graph = 0
voltage_graphs = []
voltage_cutoff_time = ""
voltage_interval_limit = 200
earliest = ""
latest = ""


# Post route to submit voltage to SQL db
@app.route('/voltage/<voltage>', methods=['GET', 'POST'])
def post_voltage(voltage):
	sql = "INSERT INTO voltage (voltage, car_id) VALUES (%s, %s)"
	if voltage.isnumeric():
		val = (voltage, "01")
		print(mycursor.execute(sql, val))
		return "Success"
	return "Invalid request"


# Get the chunks of time series data from the SQL db
def get_voltage_chunks():
	global earliest
	global latest
	id = []
	voltage = []
	car_id = []
	timestamp = []
	sql = "SELECT id,voltage,car_id,timestamp FROM voltage"
	if voltage_cutoff_time != "":
		sql += " WHERE timestamp >= %s;"
		mycursor.execute(sql, (datetime.strptime(voltage_cutoff_time, '%Y-%m-%dT%H:%M'),))
	else:
		mycursor.execute(sql + ";")

	# Go through rows returned from db
	for i in mycursor:
		id.append(i[0])
		voltage.append(i[1])
		car_id.append(i[2])
		timestamp.append(i[3])

	chunks = []
	cur_chunk = pd.DataFrame(columns=["timestamp", "id", "car_id", "voltage", 'voltage_avg'])
	cur_chunk.voltage_avg = 0

	# Save params for web display
	earliest = timestamp[0]
	latest = timestamp[-1]

	# Iterate through the entries and transfer them into the dataframe
	# The voltage interval limit defines the maximum time between readings to separate
	# the results into individual instances
	for i in range(1, len(timestamp)):
		if (timestamp[i] - timestamp[i - 1]).total_seconds() > voltage_interval_limit and i > 1:
			cur_chunk['voltage_avg'] = cur_chunk['voltage'].rolling(30).mean()
			chunks.append(cur_chunk)
			cur_chunk = cur_chunk[0:0]
		if i == len(timestamp):
			chunks.append(cur_chunk)

		cur_chunk = cur_chunk.append({"timestamp": timestamp[i],
									  "id": id[i],
									  "car_id": car_id[i],
									  "voltage": voltage[i]},
									 ignore_index=True)
	return chunks


# Generate HTML graphs with plotly
def generate_voltage_chart():
	global voltage_graph
	global voltage_graphs
	chunks = get_voltage_chunks()
	voltage_graphs.clear()
	for i in range(0, len(chunks)):
		fig = px.line(chunks[i],
					  x='timestamp',
					  y=['voltage', 'voltage_avg'])

		graph_json = plotly.io.to_html(fig,
									   include_plotlyjs=False,
									   full_html=False,
									   default_height=370,
									   default_width="68%")  # json.dumps(fig,cls=plotly.utils.PlotlyJSONEncoder)

		voltage_graphs.append(graph_json)


# Display the homepage
@app.route("/")
def homepage():
	return render_template("index.html",
						   title="Voltage Chart Test",
						   voltage_graphs=voltage_graphs,
						   latest=latest,
						   earliest=earliest,
						   voltage_cutoff_time=voltage_cutoff_time)


# Basically a cron job, also runs the job once before adding it
def schedule_function(function, delay_seconds):
	function()
	scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': 2}, timezone='UTC')
	scheduler.add_job(func=function, trigger="interval", seconds=delay_seconds)
	scheduler.start()

	# Shut down the scheduler when exiting the app
	atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
	schedule_function(generate_voltage_chart, 15)
	app.run(host='0.0.0.0', port=5000)
