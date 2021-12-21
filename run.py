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
import matplotlib
import matplotlib.pyplot as plt
import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler
from flask import render_template, redirect, url_for, request, Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd

matplotlib.use('Agg')

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
mycursor = mydb.cursor()

voltage_graph = 0
voltage_graphs = []
voltage_cutoff_time = ""
voltage_interval_limit = 200
earliest = ""
latest = ""


@app.route('/voltage/<voltage>', methods=['GET', 'POST'])
def post_voltage(voltage):
	sql = "INSERT INTO voltage (voltage, car_id) VALUES (%s, %s)"
	val = (voltage, "01")
	mycursor.execute(sql, val)
	return "Success"


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

	for i in mycursor:
		id.append(i[0])
		voltage.append(i[1])
		car_id.append(i[2])
		timestamp.append(i[3])
	chunks = []
	cur_chunk = pd.DataFrame(columns=["timestamp","id","car_id","voltage",'voltage_avg'])
	cur_chunk.voltage_avg = 0
	earliest = timestamp[0]
	latest = timestamp[-1]
	for i in range(1, len(timestamp)):
		if (timestamp[i] - timestamp[i - 1]).total_seconds() > voltage_interval_limit and i > 1:
			#print(cur_chunk)
			cur_chunk['voltage_avg'] = cur_chunk['voltage'].rolling(30).mean()
			chunks.append(cur_chunk)
			cur_chunk = cur_chunk[0:0]
		if i == len(timestamp):
			chunks.append(cur_chunk)

		cur_chunk=cur_chunk.append({"timestamp":timestamp[i],"id":id[i],"car_id":car_id[i],"voltage":voltage[i]}, ignore_index=True)
	return chunks


def generate_voltage_chart():
	global voltage_graph
	global voltage_graphs
	chunks = get_voltage_chunks()
	voltage_graphs.clear()
	for i in range(0, len(chunks)):
		fig=px.line(chunks[i],x='timestamp',y=['voltage','voltage_avg'])
		graph_json = plotly.io.to_html(fig,include_plotlyjs=False,full_html=False,default_height=370,default_width="60%")#json.dumps(fig,cls=plotly.utils.PlotlyJSONEncoder)
		voltage_graphs.append(graph_json)
		# plt.title("Period from "+chunks[i]["timestamp"][0].strftime("%d %b, %y %H:%M:%S") + ". Duration: " + str(chunks[i]["timestamp"][-1]-chunks[i]["timestamp"][0]))



@app.route("/voltage.png")
def voltage_png():
	return Response(voltage_graph)


@app.route("/voltage<value>.png")
def voltage_charts(value):
	return Response(voltage_graphs[value])


@app.route("/")
def homepage():
	return render_template("index.html",
						   title="Voltage Chart Test",
						   voltage_graphs=voltage_graphs,
						   latest=latest,
						   earliest=earliest,
						   voltage_cutoff_time=voltage_cutoff_time)


def schedule_function(function, delay):
	function()
	scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': 2},timezone='UTC')
	scheduler.add_job(func=function, trigger="interval", seconds=delay)
	scheduler.start()

	# Shut down the scheduler when exiting the app
	atexit.register(lambda: scheduler.shutdown())


@app.route('/adjust-cutoff/', methods=['POST', 'GET'])
def adjust_voltage_cutoff():
	global voltage_cutoff_time, voltage_interval_limit
	if request.method == 'POST':
		form_data = request.form
		cutoff = form_data["cutoff-time"]
		interval = form_data["interval-limit"]
		if cutoff != "":
			voltage_cutoff_time = cutoff
		if interval != '' and interval.isnumeric():
			voltage_interval_limit = int(interval)
		generate_voltage_chart()
	return redirect(url_for('homepage'))


if __name__ == '__main__':

	schedule_function(generate_voltage_chart, 5)
	app.run(host='0.0.0.0', port=80)
