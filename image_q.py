import dateutil
import pymysql as sql
import pandas as pd
from bokeh.io import curdoc
from bokeh.layouts import row, widgetbox, column
from bokeh.models import HoverTool, ColumnDataSource, datetime, Button, TextInput, Div
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.plotting import figure
from dateutil.parser import parser
import os
import numpy as np
from datetime import timedelta,datetime
#sdb connection


db_connection = sql.connect(host=os.getenv("HOST"), db=os.getenv('DATABASE1'), user= os.getenv('USER'), password=os.getenv('PASSWORD'))
#print("env: ", os.environ['PASSWORD'])
#exit(0)
sdb_con=sql.connect(host= os.getenv("HOST") , database=os.getenv('DATABASE2'), user= os.getenv('USER') , password=os.getenv('PASSWORD'))

#setting date format to be used on the x axis of the plot
now=datetime.now()
date_formatter = DatetimeTickFormatter(days=['%e %b %Y'], months=['%e %b %Y'], years=['%e %b %Y'])

#date input fields
time_offset = 2082844800
text_input =TextInput(value="2017-09-20", title="start date:")
text_input2 =TextInput(value=datetime.now().strftime("%Y-%m-%d"), title="end date:")


#ColumDataSource object where bokeh data to be ploted is stored
source = ColumnDataSource()
mean_source = ColumnDataSource()
median_source=ColumnDataSource()



hover = HoverTool(tooltips=[
    ("index", "$index"),
    ("date", "@date"),
    ('date', '@date{%F}'),
    #("(x=date,y)", "($x=@date,$y)")

])

#widgetbox
error_message=Div(text='', style={"color": "red"})
button_1 = Button(label="search",width=200, height=150)
wb = widgetbox(error_message, button_1 )
TOOLS="crosshair,pan,wheel_zoom,box_zoom,reset,box_select,lasso_select"

#function to be called when oclick button is used
def callback():
    global source,mean_source, error_message,median_source


    try:
        first = dateutil.parser.parse(text_input.value)
        print(" first time b4 the timestamp",first)
        first_timestamp= first.timestamp() + time_offset
        second = dateutil.parser.parse(text_input2.value)
        print(" second time b4 the timestamp", second)
        second_timestamp=second.timestamp() + time_offset

        if second > first:
            error_message.text=''
        elif first > second:
            error_message.text = 'Please enter the correct dates'
        else:
            error_message.text ='please use format: YYYY-MM-DD'
    except ValueError:
        error_message.text ='enter the correct dates'

    sql1 = 'SELECT  str_to_date(datetime,"%Y-%m-%d %H:%i:%s") AS datetime, seeing  from seeing ' \
           '    where datetime >= str_to_date("{start_date}","%Y-%m-%d ")' \
           '    and datetime <= str_to_date("{end_date}","%Y-%m-%d ")' \
        .format(start_date=str(first), end_date=str(second))

    sql2 = 'select _timestamp_,ee50,fwhm from tpc_guidance_status__timestamp where timestamp>= {start_date}' \
           '     and timestamp<= {end_date} and guidance_available="T" order by _timestamp_'\
        .format(start_date=str(first_timestamp), end_date=str(second_timestamp))


    #print('A', datetime.now())
    df2 = pd.read_sql(sql2, con=sdb_con)
    #print('B', datetime.now())
    df1 = pd.read_sql(sql1, con=db_connection)
    source2 = ColumnDataSource(df1)
    source.data = source2.data






    df2.index = df2["_timestamp_"]
    mean = df2[['ee50', 'fwhm']].mean()
    mean_all = df2.resample("2T").mean()

    medienn = df2[['ee50', 'fwhm']].median()
    median_all = df2.resample("3T").median()




    source3=ColumnDataSource(mean_all)
    source4=ColumnDataSource(median_all)
    print("source3",source3.data)
    print(mean_all)
    print(mean)
    print(medienn)



    mean_source.data=source3.data

    median_source.data = source4.data
    print("                        ",median_source.data)

    print("callback clicked ")

button_1.on_click(callback)

callback()

print(mean_source.data)

#plot labels
p = figure(title="internal vs external seeing ", x_axis_type='datetime'
           , x_axis_label='datetime', y_axis_label='seeing',plot_width=1000, plot_height=500,tools=TOOLS)#tools=[TOOLS, hover]

#layout to be shown on screen
layout_=column(row(text_input,text_input2,width=1500),wb,p)

#plots
p.circle(source=source, x='datetime',y='seeing', legend="external" ,fill_color="white",color='green')
p.circle(source=mean_source, x='_timestamp_', y='ee50', legend='ee50_')
p.circle(source=mean_source, x='_timestamp_', y='fwhm', legend='fwhm_', color='red', fill_color='white')

p.line(source=median_source, x='_timestamp_', y='ee50', legend='ee50_median', color='green')
p.line(source=median_source, x='_timestamp_', y='fwhm', legend='fwhm_medien', color='orange')


p.xaxis.formatter = date_formatter
p.legend.location = "top_left"
p.legend.click_policy="hide"

#show the results
curdoc().add_root(layout_)

