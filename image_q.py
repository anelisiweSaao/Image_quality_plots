import dateutil
import pymysql as sql
import pandas as pd
from bokeh.io import curdoc
from bokeh.layouts import row, widgetbox, column
from bokeh.models import HoverTool, ColumnDataSource, Button, TextInput, Div
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.plotting import figure
from dateutil.parser import parser
import os
from datetime import datetime

#sdb connection
db_connection = sql.connect(host=os.getenv("HOST"), db=os.getenv('DATABASE1'), user= os.getenv('USER'), password=os.getenv('PASSWORD'))
sdb_con=sql.connect(host= os.getenv("HOST") , database=os.getenv('DATABASE2'), user= os.getenv('USER') , password=os.getenv('PASSWORD'))

#setting date format to be used on the x axis of the plot
date_formatter = DatetimeTickFormatter(days=['%e %b %Y'], months=['%e %b %Y'], years=['%e %b %Y'])

#date input fields
#calculated to be used for timestamp
time_offset = 2082844800
#default values
text_input =TextInput(value="2017-11-20", title="start date:", placeholder="YYYY-MM-DD")
text_input2 =TextInput(value=datetime.now().strftime("%Y-%m-%d"), title="end date:", placeholder="YYYY-MM-DD")
average_input=TextInput(value="10", title="enter average:")


#ColumDataSource object where bokeh data to be ploted is stored
mean_source1 = ColumnDataSource()
median_source1=ColumnDataSource()

mean_source = ColumnDataSource()
median_source=ColumnDataSource()

difference_source=ColumnDataSource()

#widgetbox
error_message=Div(text='', style={"color": "red"})
success_message=Div(text="", style={"color": "green"})

button_1 = Button(label="search",width=200, height=150, sizing_mode='scale_both')

wb = widgetbox( error_message,success_message, button_1)
TOOLS="pan,wheel_zoom,box_zoom,reset,box_select,lasso_select,save"


#function to be called when onclick button is used
def update():
    global mean_source1,mean_source, error_message,median_source1,median_source,success_message, difference_source

    try:
        error_message.text = ""

        success_message.text = ""

        first = dateutil.parser.parse(text_input.value)
        print(" first time b4 the timestamp",first)
        first_timestamp= first.timestamp() + time_offset


        second = dateutil.parser.parse(text_input2.value)
        print(" second time b4 the timestamp", second)
        second_timestamp= second.timestamp() + time_offset


        if second > first or first == second:
            success_message.text = ''


        elif first > second or second > datetime.now():
            error_message.text = '<b>Please enter the correct dates</b>'

            return False

        #query data in mysql database
        sql1 = 'SELECT  str_to_date(datetime,"%Y-%m-%d %H:%i:%s") AS datetime, seeing  from seeing ' \
               '    where datetime >= str_to_date("{start_date}","%Y-%m-%d ")' \
               '    and datetime <= str_to_date("{end_date}","%Y-%m-%d ") '\
            .format(start_date=str(first), end_date=str(second))

        sql2 = 'select _timestamp_,ee50,fwhm,timestamp from tpc_guidance_status__timestamp where timestamp >= {start_date}' \
               '   and timestamp<= {end_date} and guidance_available="T"  ' \
               ' order by _timestamp_'\
            .format(start_date=str(first_timestamp), end_date=str(second_timestamp))

        success_message.text = '<b>loading......</b>'

        df2 = pd.read_sql(sql2, con=sdb_con)
        df1 = pd.read_sql(sql1, con=db_connection)

        #time for calcalating mean and average
        df2.index = df2["_timestamp_"]
        df1.index=df1['datetime']

        #for external seeing
        mean1 = df1[['seeing']].mean()
        mean1_all = df1.resample(str(average_input.value)+'T').mean()
        source1 = ColumnDataSource(mean1_all)
        mean_source1.data=source1.data
        #print("this is for external", mean1_all)

        median1=df1[['seeing']].median()
        median1_all=df1.resample(str(average_input.value)+'T').median()
        source=ColumnDataSource(median1_all)
        median_source1=source.data


        #calculate mean for fwhm
        mean = df2[['fwhm','ee50']].mean()
        mean_all = df2.resample(str(average_input.value)+'T').mean()
        source3 = ColumnDataSource(mean_all)
        mean_source.data = source3.data

        #calculate median for fwhm
        median = df2[['fwhm','ee50']].median()
        median_all = df2.resample(str(average_input.value)+'T').median()
        source4=ColumnDataSource(median_all)
        median_source.data = source4.data

        dataframes=[mean1_all,mean_all]
        add_dataframes=pd.concat(dataframes)
        add_dataframes.index.name = '_timestamp_'
        add_dataframes['difference']=add_dataframes['seeing']-add_dataframes['fwhm']

        #print("this difference",add_dataframes.difference,index=False)
        #difference_source.data=add_dataframes.data
        success_message.text = '<b>done</b>'

        print("button clicked")
    except Exception as error:

        error_message.text ='<b>The date entered is incorrect</b>'

def callback():
    # set a variable indicating a paqe reload

    update()
    #success_message.text='<b>done</b>'

button_1.on_click(callback)
update()

#plot labels
p = figure(title="internal vs external seeing (at given minutes of average and median ) ", x_axis_type='datetime'
           , x_axis_label='datetime', y_axis_label='seeing',plot_width=1000, plot_height=500,tools=TOOLS)#ols=[TOOLS, hover]

#layout to be shown on screen
layout_=column(row(text_input,text_input2,average_input,width=1500),wb,p)

#plots
#plots for external seeing
p.circle(source=mean_source1, x='datetime',y='seeing', legend="external_average" ,fill_color="white",color='green')
p.line(source=median_source1, x='datetime',y='seeing', legend="external_median" ,color='blue')

#plots showing median and mean for ee50 and fwhm
p.circle(source=mean_source, x='_timestamp_', y='ee50', legend='ee50_average')
p.circle(source=mean_source, x='_timestamp_', y='fwhm', legend='fwhm_average', color='red', fill_color='white')

p.line(source=median_source, x='_timestamp_', y='ee50', legend='ee50_median', color='green')
p.line(source=median_source, x='_timestamp_', y='fwhm', legend='fwhm_median', color='orange')

#for difference
#p.line(source=difference_source, x='_timestamp_', y='difference', legend='difference', color='orange')

#legends on the plot
p.xaxis.formatter = date_formatter
p.legend.location = "top_left"
p.legend.click_policy="hide"

#show the results
curdoc().add_root(layout_)

