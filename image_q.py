import dateutil
import pymysql as sql
import pandas as pd
from bokeh.io import curdoc
from bokeh.layouts import row, widgetbox, column
from bokeh.models import ColumnDataSource, Button, TextInput, Div
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.plotting import figure
from dateutil.parser import parser
import os
from datetime import datetime, timedelta
import time

#sdb connection
db_connection = sql.connect(host=os.getenv("HOST"), db=os.getenv('DATABASE1'), user= os.getenv('USER'), password=os.getenv('PASSWORD'))
sdb_con=sql.connect(host= os.getenv("HOST") , database=os.getenv('DATABASE2'), user= os.getenv('USER') , password=os.getenv('PASSWORD'))

#setting date format to be used on the x axis of the plot
date_formatter = DatetimeTickFormatter(days=['%e %b %Y'], months=['%e %b %Y'], years=['%e %b %Y'])

#date input fields
#calculated to be used for timestamp
time_offset = 2082844800
#default values
dat=datetime.now()-timedelta(days=7)
text_input =TextInput(value=dat.strftime("%Y-%m-%d"), title="start date:", placeholder="YYYY-MM-DD")
text_input2 =TextInput(value=datetime.now().strftime("%Y-%m-%d"), title="end date:", placeholder="YYYY-MM-DD")
average_input=TextInput(value="10", title="binning interval (minutes):",placeholder="enter minutes")

#ColumDataSource object where bokeh data to be ploted is stored
mean_source1 = ColumnDataSource()
median_source1=ColumnDataSource()

mean_source = ColumnDataSource()
median_source=ColumnDataSource()

difference_source=ColumnDataSource()
difference_source1=ColumnDataSource()

#widgetbox
error_message=Div(text='', style={"color": "red"})
success_message=Div(text="", style={"color": "green"})

button_1 = Button(label="search",width=200, height=150, sizing_mode='scale_both')

wb = widgetbox(error_message,success_message, button_1)
TOOLS="pan,wheel_zoom,box_zoom,reset,box_select,lasso_select,save"


#function to be called when onclick button is used
def update():
    global mean_source1,mean_source, error_message,median_source1,median_source,success_message, difference_source1,difference_source, first,second
    try:
        error_message.text =""
        success_message.text =""

        try:
            first = dateutil.parser.parse((text_input.value)).replace(hour=12) #start at miday
            first_timestamp = first.timestamp() + time_offset

        except ValueError:
            raise ValueError("start date field is invalid")


        try:
            second = dateutil.parser.parse(text_input2.value).replace(hour=12)
            second_timestamp = second.timestamp() + time_offset
        except ValueError:
            raise ValueError("end date field is invalid")

        if second== first or first > second:
            raise TypeError("start date must be earlier than the end date ")

        try:
            input=int(average_input.value)
            if input > 0:
                success_message.text=""
            elif input <= 0:
                raise ValueError()

        except ValueError:
            raise ValueError("The binning interval must be a number greater than 0")

            # query data in mysql database
        sql1 = 'SELECT  str_to_date(datetime,"%Y-%m-%d %H:%i:%s") AS datetime, seeing  from seeing ' \
               '    where datetime >= str_to_date("{start_date}","%Y-%m-%d  %H:%i:%s")' \
               '    and datetime <= str_to_date("{end_date}","%Y-%m-%d %H:%i:%s") ' \
            .format(start_date=str(first), end_date=str(second))

        sql2 = 'select _timestamp_,ee50,fwhm,timestamp from tpc_guidance_status__timestamp where timestamp >= {start_date}' \
               '   and timestamp<= {end_date} and guidance_available="T"  ' \
               ' order by _timestamp_' \
            .format(start_date=str(first_timestamp), end_date=str(second_timestamp))

        success_message.text = '<b>loading......</b>'

        df2 = pd.read_sql(sql2, con=sdb_con)
        df1 = pd.read_sql(sql1, con=db_connection)
        print(df2)

        # seting index time for calcalating mean and average
        df2.index = df2["_timestamp_"]
        df1.index = df1['datetime']

        #df2_= df2.reset_index().set_in        dex("_timestamp_")
        #df1_ = df1.reset_index().set_index('datetime')

        print(df2.index)

        # for external seeing calculating median and mean
        mean1 = df1[['seeing']].mean()
        mean1_all = df1.resample(str(average_input.value) + 'T').mean()
        source1 = ColumnDataSource(mean1_all)
        mean_source1.data = source1.data
        print(mean1_all)

        median1 = df1[['seeing']].median()
        median1_all = df1.resample(str(average_input.value) + 'T').median()
        source = ColumnDataSource(median1_all)
        median_source1.data = source.data

        # calculate mean and median for fwhm,ee50
        mean = df2[['fwhm', 'ee50']].mean()
        mean_all = df2.resample(str(average_input.value) + 'T').mean()
        source3 = ColumnDataSource(mean_all)
        mean_source.data = source3.data

        median = df2[['fwhm', 'ee50']].median()
        median_all = df2.resample(str(average_input.value) + 'T').median()
        source4 = ColumnDataSource(median_all)
        median_source.data = source4.data

        # calculate difference for external seeing against fwhm and ee50
        dataframes = [mean1_all, mean_all]
        add_dataframes = pd.concat(dataframes, axis=1)
        add_dataframes.index.name = '_timestamp_'
        add_dataframes['difference1'] = add_dataframes['seeing'] - add_dataframes['fwhm']
        datasource = ColumnDataSource(add_dataframes)
        difference_source1.data = datasource.data

        # for difference with ee50
        add_dataframes['difference'] = add_dataframes['seeing'] - add_dataframes['ee50']
        datasource = ColumnDataSource(add_dataframes)
        difference_source.data = datasource.data

        success_message.text = '<b>done</b>'
        time.sleep(2)
        success_message.text = ''


    except ValueError as ve:
        #Raised when the built-in function for a data type has the valid type of arguments, but the arguments have invalid values specified.(end > start)
        error_message.text=str(ve)
        success_message.text = ""
    except  TypeError as te:
        #Raised when an operation or function is attempted that is invalid for the specified data type.(rong data in input field)
        error_message.text=str(te)
        success_message.text = ""

    except Exception as error:  # Base class for all exceptions(taking care for any error)
        error_message.text = str(error), " sorry something went rong"
        success_message.text = ""


button_1.on_click(update)
update()

#plot labels
p = figure(title=f"external vs internal seeing ({average_input.value} minute bins) ", x_axis_type='datetime'
           , x_axis_label='datetime', y_axis_label='seeing',plot_width=1000, plot_height=500,tools=TOOLS)
dif=figure(title=f'difference between average internal and external seeing ({average_input.value} minute bins)', x_axis_type='datetime',
           x_axis_label='datetime', y_axis_label='seeing',plot_width=1000, plot_height=500,tools=TOOLS)

#plots
#plots for external seeing
p.circle(source=mean_source1, x='datetime',y='seeing', legend="external average" ,fill_color="white",color='green')
p.line(source=median_source1, x='datetime',y='seeing', legend="external median" ,color='blue')

#plots showing median and mean for ee50 and fwhm
p.circle(source=mean_source, x='_timestamp_', y='ee50', legend='ee50 average')
p.circle(source=mean_source, x='_timestamp_', y='fwhm', legend='fwhm average', color='red', fill_color='white')

p.line(source=median_source, x='_timestamp_', y='ee50', legend='ee50 median', color='green')
p.line(source=median_source, x='_timestamp_', y='fwhm', legend='fwhm median', color='orange')

#for difference
dif.circle(source=difference_source1, x='_timestamp_', y='difference1', legend='fwhm difference', fill_color='blue')
dif.circle(source=difference_source, x='_timestamp_', y='difference', legend='ee50 difference', color='red')
#legends on the plot
p.xaxis.formatter = date_formatter

p.legend.location = "top_left"
p.legend.click_policy="hide"


dif.xaxis.formatter = date_formatter
dif.legend.click_policy="hide"
#layout to be shown on screen
layout_=column(row(text_input,text_input2,average_input,width=1500),wb,p,dif ,sizing_mode='fixed')

#show the results
curdoc().add_root(layout_)