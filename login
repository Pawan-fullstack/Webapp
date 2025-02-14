import streamlit as st
import pickle
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import numpy as np
import streamlit_authenticator as stauth

# define the url structure and headers for http requests
BASE_URL = "https://www.screener.in/company/{symbol}/"


# function to download and parse html content
def download_and_parse(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup 

# function to pivot and prepare dataframe for display
def prepare_growth_display(df, metric_prefix):
    # filter dataframe for relevant metrics
    growth_df = df[df['Metric'].str.contains(metric_prefix)]
    # pivot dataframe to get periods as columns
    growth_df = growth_df.pivot(index='Metric', columns='Period', values='Value').reset_index()
    # clean up the dataframe for better display
    growth_df.set_index('Metric', inplace=True)  # set 'Metric' as the new index
    return growth_df

# to find specific roce% value from table
def find_specific_roce(df, metric_name):
    try:
        # find the row that contains the metric name (e.g., "ROCE %")
        metric_row = df[df['Metric'].str.contains(metric_name)]
        if not metric_row.empty:
            # get the fifth last column's name
            # assuming that the last few columns are always the dates we are interested in
            period = metric_row.columns[-5]  # change the index as needed (-5 for fifth from the last)
            return metric_row[period].values[0]
    except Exception as e:
        return f"Error fetching data: {str(e)}"
    return "Data not available"

def get_table(parsed, table_id):
    results = parsed.find('section', {'id': table_id})
    table = results.find('table', class_='data-table')
    headers = [header.text.strip() for header in table.find_all('th')[1:]]
    df_rows=[]
    for row in table.find_all('tr')[1:]:
        df_row=[]
        for cell in row.find_all('td'):
            df_row.append(cell.text.strip())
        df_rows.append(df_row)
    return pd.DataFrame(df_rows, columns=['Metric'] + headers)

def get_profit_loss_additional(parsed):
    # find the section containing the profit & loss statement
    profit_loss_section = parsed.find('section', {'id': 'profit-loss'})
    tables = profit_loss_section.find_all('table', class_='ranges-table')
    # initialize list to store all data
    data = []
    # iterate through each table and extract data
    for table in tables:
        # fetch the header (growth type)
        header = table.find('th').text.strip()
        # find all rows within the table
        rows = table.find_all('tr')[1:]  # skip the first header row
        for row in rows:
            # get the period and the percentage values
            period = row.find_all('td')[0].text.strip()
            value = row.find_all('td')[1].text.strip()
            data.append([header, period, value])
    # convert to a pandas dataframe
    df = pd.DataFrame(data, columns=['Metric', 'Period', 'Value'])

    return df
    
# function to find specific financial metrics from parsed html
def find_metric(parsed, html_tag, attribute_type, attribute_value):
    metric_tag = parsed.find(html_tag, {attribute_type: attribute_value})
    return metric_tag.text.strip() if metric_tag else 'Data not available'

# to find 'EPS in Rs'
def find_specific_eps(df, date):
    eps_row = df[df['Metric'].str.contains('EPS')]
    if not eps_row.empty and date in eps_row.columns:
        return eps_row[date].values[0]
    return None

def plot_growth_chart(df, title):
    # ensure periods are in the desired order
    period_order = ['TTM:', '3 Years:', '5 Years:', '10 Years:']
    df['Period'] = pd.Categorical(df['Period'], categories=period_order, ordered=True)

    # convert percentage strings to numbers for plotting
    df['Value'] = df['Value'].str.rstrip('%').astype(float)

    # create the horizontal bar chart
    fig = px.bar(df, y='Period', x='Value', orientation='h', title=title, text='Value')
    fig.update_layout(xaxis_title='Growth (%)', yaxis_title='', yaxis=dict(categoryorder='total ascending'))
    fig.update_traces(textposition='outside')
    return fig

TAX_RATE = 0.25

# function to calculate the intrinsic P/E ratio based on DCF analysis
def dcf_intrinsic_pe(eps, growth_rate, high_growth_period, fade_period, terminal_growth_rate, coc):
    eps = float(eps)
    growth_rate = float(growth_rate) / 100
    terminal_growth_rate = float(terminal_growth_rate) / 100
    coc = float(coc) / 100

    # time array for the high growth and fade periods
    high_growth_years = np.arange(1, high_growth_period + 1)
    fade_years = np.arange(1, fade_period + 1)

    # high growth value calculation
    high_growth_values = eps * (1 + growth_rate) ** high_growth_years / (1 + coc) ** high_growth_years
    high_growth_value = np.sum(high_growth_values)

    # fade period value calculation
    fade_growth_rates = growth_rate - (fade_years / fade_period) * (growth_rate - terminal_growth_rate)
    fade_values = eps * (1 + fade_growth_rates) ** (high_growth_years[-1] + fade_years) / (1 + coc) ** (high_growth_years[-1] + fade_years)
    fade_value = np.sum(fade_values)

    # terminal value calculation
    terminal_value = (eps * (1 + terminal_growth_rate) ** (high_growth_period + fade_period + 1)) / (coc - terminal_growth_rate)
    terminal_value_discounted = terminal_value / (1 + coc) ** (high_growth_period + fade_period)

    # intrinsic value calculation
    intrinsic_value = (high_growth_value + fade_value + terminal_value_discounted) * (1 - TAX_RATE)
    intrinsic_pe = intrinsic_value / eps

    return intrinsic_pe

def calculate_overvaluation(current_pe, fy23_pe, intrinsic_pe):
    lower_pe = min(float(current_pe), float(fy23_pe))
    overvaluation = (lower_pe / intrinsic_pe - 1) * 100
    return overvaluation

st.title('Hello User')  

names = ["Peter Parker", "Rebecca Miller"]
usernames = ["pparker", "rmiller"]

file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names,usernames,hashed_passwords,"sales_dashboard", "abcdef", cookie_expiry_days=20)

name, authetication_status ,username = authenticator.login("Login","main")



if authetication_status== False:
    st.error("Username / password is incorrect")

if authetication_status== None:
    st.warning("Please enter Username and password ")

authenticator.logout("Logout","sidebar")
st.sidebar(f"Welcome{name}") 
