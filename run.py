import atexit
import base64
import io
import random
import time
from datetime import datetime, timedelta
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
	host="10.0.0.147",
	user="jtoper",
	database="car_stats",
	password=""
)

app = flask.Flask(__name__, static_url_path='',
				  static_folder='static',
				  template_folder='template')
app.config["DEBUG"] = True
mydb.autocommit = False
mycursor = mydb.cursor(buffered=True)

# Global mapping variables
voltage_graph = 0
voltage_graphs = []
voltage_cutoff_time = 10
voltage_interval_limit = 200
voltage_cutoff_name = "10m"
voltage_scaling_factor = 15/2.961
earliest = ""
latest = ""


# Post route to submit voltage to SQL db
@app.route('/voltage/<voltage>', methods=['GET'])
def post_voltage(voltage):
	sql = "INSERT INTO voltage (voltage, car_id) VALUES (%s, %s)"
	val = (voltage, "01")
	mycursor.execute(sql, val)
	return "Success"


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
		mycursor.execute(sql, (str(datetime.now() - timedelta(minutes=voltage_cutoff_time)),))
	else:
		mycursor.execute(sql)

	# Go through rows returned from db
	for i in mycursor:
		id.append(i[0])
		voltage.append(i[1]*voltage_scaling_factor)
		car_id.append(i[2])
		timestamp.append(i[3])

	if len(timestamp) == 0:
		return []

	chunks = []
	cur_chunk = pd.DataFrame(columns=["timestamp", "id", "car_id", "voltage", 'voltage_avg'])
	cur_chunk.voltage_avg = 0

	# Save params for web display
	latest = timestamp[0].strftime("%m/%d/%Y %I:%M %p")
	earliest = timestamp[-1].strftime("%m/%d/%Y %I:%M %p")
	if timestamp[0].strftime("%m/%d/%Y") == timestamp[-1].strftime("%m/%d/%Y"):
		latest = timestamp[0].strftime("%I:%M %p")


	# Iterate through the entries and transfer them into the dataframe
	# The voltage interval limit defines the maximum time between readings to separate
	# the results into individual instances
	for index in range(1, len(timestamp)):
		i = len(timestamp) - index
		cur_chunk = cur_chunk.append({"timestamp": timestamp[i],
									  "id": id[i],
									  "car_id": car_id[i],
									  "voltage": voltage[i]},
									 ignore_index=True)
	cur_chunk['voltage_avg'] = cur_chunk['voltage'].expanding().mean()

	chunks.append(cur_chunk)

	return chunks


# Generate HTML graphs with plotly
def generate_voltage_chart():
	global voltage_graph
	global voltage_graphs
	chunks = get_voltage_chunks()
	voltage_graphs.clear()
	for i in range(0, len(chunks)):
		avg_voltage ="Avg Voltage: "+str(chunks[i].voltage.mean())[:6]+"v"
		fig = px.line(chunks[i], x='timestamp', y=['voltage', 'voltage_avg'], title=avg_voltage)
		graph_json = plotly.io.to_html(fig,include_plotlyjs=False, full_html=False, default_height=450, default_width=1000)
		voltage_graphs.append(graph_json)

def prune_sql():
	sql = "DELETE FROM voltage WHERE timestamp < %s"
	mycursor.execute(sql,(datetime.now() - timedelta(hours=12),))
	if mycursor.rowcount > 0:
		mycursor.commit()

@app.route('/adjust-cutoff/', methods=['POST'])
def adjust_voltage_cutoff():
	global voltage_cutoff_time, voltage_cutoff_name
	if request.method == 'POST':
		form_data = request.form
		cutoff = form_data["hour-select"]
		minute_cutoff = None
		if cutoff != "":
			voltage_cutoff_name = cutoff
			if cutoff == "5m":
				minute_cutoff = 5
			if cutoff == "10m":
				minute_cutoff = 10
			if cutoff == "30m":
				minute_cutoff = 30
			if cutoff == "1":
				minute_cutoff = 60
			if cutoff == "2":
				minute_cutoff = 120
			if cutoff == "4":
				minute_cutoff = 4*60
			if cutoff == "8":
				minute_cutoff = 8*60
			if cutoff == "12":
				minute_cutoff = 12*60
			voltage_cutoff_time = minute_cutoff
		generate_voltage_chart()
	return redirect(url_for('homepage'))


# Display the homepage
@app.route("/")
def homepage():
	return render_template("index.html",
						   title="Voltage Chart Test",
						   voltage_graphs=voltage_graphs,
						   latest=latest,
						   earliest=earliest,
						   cutoff=voltage_cutoff_name)


@app.route("/get-charts")
def get_charts():
	global voltage_graphs
	return Response(voltage_graphs)

# Basically a cron job, also runs the job once before adding it
def schedule_function(function, delay_seconds):
	function()
	scheduler = BackgroundScheduler(
		{'apscheduler.job_defaults.max_instances': 2}, timezone='UTC')
	scheduler.add_job(func=function, trigger="interval", seconds=delay_seconds)
	scheduler.start()

	# Shut down the scheduler when exiting the app
	atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
	schedule_function(generate_voltage_chart, 10)
	schedule_function(prune_sql, 1*60*60)
	app.run(host='0.0.0.0', port=80)
