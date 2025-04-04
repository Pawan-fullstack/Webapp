import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import numpy as np
from streamlit_option_menu import option_menu
import home
import auth
import login, signup
import os

# Initialize auth system
auth.init_auth()

# Define the URL structure and headers for HTTP requests
BASE_URL = "https://www.screener.in/company/{symbol}/"

# Function to download and parse HTML content
def download_and_parse(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup

# Function to pivot and prepare dataframe for display
def prepare_growth_display(df, metric_prefix):
    # Filter dataframe for relevant metrics
    growth_df = df[df['Metric'].str.contains(metric_prefix)]
    # Pivot dataframe to get periods as columns
    growth_df = growth_df.pivot(index='Metric', columns='Period', values='Value').reset_index()
    # Clean up the dataframe for better display
    growth_df.set_index('Metric', inplace=True)  # set 'Metric' as the new index
    return growth_df

# To find specific roce% value from table
def find_specific_roce(df, metric_name):
    try:
        # Find the row that contains the metric name (e.g., "ROCE %")
        metric_row = df[df['Metric'].str.contains(metric_name)]
        if not metric_row.empty:
            # Get the fifth last column's name
            # Assuming that the last few columns are always the dates we are interested in
            period = metric_row.columns[-5]  # Change the index as needed (-5 for fifth from the last)
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
    # Find the section containing the profit & loss statement
    profit_loss_section = parsed.find('section', {'id': 'profit-loss'})
    tables = profit_loss_section.find_all('table', class_='ranges-table')
    # Initialize list to store all data
    data = []
    # Iterate through each table and extract data
    for table in tables:
        # Fetch the header (growth type)
        header = table.find('th').text.strip()
        # Find all rows within the table
        rows = table.find_all('tr')[1:]  # Skip the first header row
        for row in rows:
            # Get the period and the percentage values
            period = row.find_all('td')[0].text.strip()
            value = row.find_all('td')[1].text.strip()
            data.append([header, period, value])
    # Convert to a pandas dataframe
    df = pd.DataFrame(data, columns=['Metric', 'Period', 'Value'])

    return df
    
# Function to find specific financial metrics from parsed HTML
def find_metric(parsed, html_tag, attribute_type, attribute_value):
    metric_tag = parsed.find(html_tag, {attribute_type: attribute_value})
    return metric_tag.text.strip() if metric_tag else 'Data not available'

# To find 'EPS in Rs'
def find_specific_eps(df, date):
    eps_row = df[df['Metric'].str.contains('EPS')]
    if not eps_row.empty and date in eps_row.columns:
        return eps_row[date].values[0]
    return None

def plot_growth_chart(df, title):
    # Ensure periods are in the desired order
    period_order = ['TTM:', '3 Years:', '5 Years:', '10 Years:']
    df['Period'] = pd.Categorical(df['Period'], categories=period_order, ordered=True)

    # Convert percentage strings to numbers for plotting
    df['Value'] = df['Value'].str.rstrip('%').astype(float)

    # Create the horizontal bar chart
    fig = px.bar(df, y='Period', x='Value', orientation='h', title=title, text='Value')
    fig.update_layout(xaxis_title='Growth (%)', yaxis_title='', yaxis=dict(categoryorder='total ascending'))
    fig.update_traces(textposition='outside')
    return fig

TAX_RATE = 0.25

# Function to calculate the intrinsic P/E ratio based on DCF analysis
def dcf_intrinsic_pe(eps, growth_rate, high_growth_period, fade_period, terminal_growth_rate, coc):
    eps = float(eps)
    growth_rate = float(growth_rate) / 100
    terminal_growth_rate = float(terminal_growth_rate) / 100
    coc = float(coc) / 100

    # Time array for the high growth and fade periods
    high_growth_years = np.arange(1, high_growth_period + 1)
    fade_years = np.arange(1, fade_period + 1)

    # High growth value calculation
    high_growth_values = eps * (1 + growth_rate) ** high_growth_years / (1 + coc) ** high_growth_years
    high_growth_value = np.sum(high_growth_values)

    # Fade period value calculation
    fade_growth_rates = growth_rate - (fade_years / fade_period) * (growth_rate - terminal_growth_rate)
    fade_values = eps * (1 + fade_growth_rates) ** (high_growth_years[-1] + fade_years) / (1 + coc) ** (high_growth_years[-1] + fade_years)
    fade_value = np.sum(fade_values)

    # Terminal value calculation
    terminal_value = (eps * (1 + terminal_growth_rate) ** (high_growth_period + fade_period + 1)) / (coc - terminal_growth_rate)
    terminal_value_discounted = terminal_value / (1 + coc) ** (high_growth_period + fade_period)

    # Intrinsic value calculation
    intrinsic_value = (high_growth_value + fade_value + terminal_value_discounted) * (1 - TAX_RATE)
    intrinsic_pe = intrinsic_value / eps

    return intrinsic_pe

def calculate_overvaluation(current_pe, fy23_pe, intrinsic_pe):
    lower_pe = min(float(current_pe), float(fy23_pe))
    overvaluation = (lower_pe / intrinsic_pe - 1) * 100
    return overvaluation

## Page Configuration ##
st.set_page_config(
    page_title="Stock Analy",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

## Authentication Check ##
def check_authentication():
    if not auth.is_authenticated():
        st.warning("Please login to access this feature")
        st.stop()

## Main App Logic ##
def main():
    # Initialize database on first run
    if not os.path.exists('users.db'):
        auth.create_users_table()
    
    # Handle URL routing
    path = st.experimental_get_query_params().get('page', ['home'])[0]
    
    # Sidebar Navigation
    with st.sidebar:
        app = option_menu(
            menu_title='Stock Analy',
            options=['Home', 'Account', 'Login', 'Signup'],
            icons=['house-fill', 'person-circle', 'trophy-fill', 'chat-fill', 'info-circle', 'box-arrow-in-right', 'person-plus'],
            menu_icon='chat-text-fill',
            default_index=0,
            styles={
                "container": {"padding": "5!important", "background-color": 'black'},
                "icon": {"color": "white", "font-size": "23px"}, 
                "nav-link": {"color": "white", "font-size": "20px", "text-align": "left", "margin": "0px", "--hover-color": "blue"},
                "nav-link-selected": {"background-color": "#02ab21"},
            }
        )
        
        # Display login status
        if auth.is_authenticated():
            st.success(f"Logged in as {st.session_state['username']}")
            if st.button("Logout"):
                auth.logout()
                st.experimental_rerun()
    
    # Page routing
    if app == 'Home':
        home.app()
    elif app == 'Login':
        login.app()
    elif app == 'Signup':
        signup.app()

    # After navigation, show stock analysis tool
    if auth.is_authenticated() and app not in ['Login', 'Signup']:
        st.header("Stock Analysis Tool")
        run_stock_analysis()

def run_stock_analysis():
    # Main input
    symbol_input = st.text_input("Enter Company Symbol", "TataSteel")

    # Sliders for DCF calculation parameters
    coc = st.slider('Cost of Capital (CoC) (%)', 8, 16, step=1, value=12)  # Default set to 12%
    roce_input = st.slider('Return on Capital Employed (RoCE) (%)', 10, 100, step=10, value=50)  # Default set to 50%
    growth_during_high_growth = st.slider('Growth during high growth period (%)', 8, 20, step=2, value=12)  # Default set to 12%
    high_growth_period = st.slider('High growth period (years)', 10, 25, step=2, value=14)  # Default set to 14 years
    fade_period = st.select_slider('Fade period (years)', options=[5, 10, 15, 20], value=10)  # Default set to 10 years
    terminal_growth_rate = st.select_slider('Terminal growth rate (%)', options=[0, 1, 2, 3, 4, 5, 6, 7, 7.5], value=5)  # Default set to 5%

    # Process data when button is clicked
    if st.button('Show Data'):
        url = BASE_URL.format(symbol=symbol_input)
        parsed_html = download_and_parse(url)

        quarters_df = get_table(parsed_html, 'quarters')
        profit_loss_df = get_table(parsed_html, 'profit-loss')
        profit_loss_additional_df = get_profit_loss_additional(parsed_html)
        balance_sheet_df = get_table(parsed_html, 'balance-sheet')
        cash_flow_df = get_table(parsed_html, 'cash-flow')
        ratios_df = get_table(parsed_html, 'ratios')
        shareholding_df = get_table(parsed_html, 'shareholding')
        
        # Fetch key metrics
        stock_symbol = find_metric(parsed_html, 'h1', 'class', 'h2 shrink-text')

        current_pe = None
        pe_elements = parsed_html.find_all('li', class_='flex flex-space-between')
        for li in pe_elements:
            if 'Stock P/E' in li.text:
                number_span = li.find('span', class_='number')
                if number_span:
                    current_pe = number_span.text.strip()
                    break

        current_price = None
        price_elements = parsed_html.find_all('li', class_='flex flex-space-between')
        for li in price_elements:
            if 'Current Price' in li.text:  
                number_span = li.find('span', class_='number')
                if number_span:
                    current_price = number_span.text.strip()
                    break

        epsvalue = find_specific_eps(profit_loss_df, 'Mar 2024')
        rocevalue = find_specific_roce(ratios_df, 'ROCE %')

        if current_price and epsvalue and epsvalue != 'EPS value not found':
            try:
                fy23_pe = float(current_price.replace(',', '')) / float(epsvalue)
                fy23_pe_calc = f"{fy23_pe:.2f}"
            except ValueError:
                fy23_pe_calc = "Error in calculation"
        else:
            fy23_pe_calc = "Data not available for calculation"
        
        sales_growth_df = profit_loss_additional_df[profit_loss_additional_df['Metric'].str.contains('Compounded Sales Growth')].reset_index()
        profit_growth_df = profit_loss_additional_df[profit_loss_additional_df['Metric'].str.contains('Compounded Profit Growth')].reset_index()
        
        # Preparing dataframes for display
        prepared_sales_growth = prepare_growth_display(profit_loss_additional_df, 'Compounded Sales Growth')
        prepared_profit_growth = prepare_growth_display(profit_loss_additional_df, 'Compounded Profit Growth')
        sales_growth_chart = plot_growth_chart(sales_growth_df, "Compounded Sales Growth")
        profit_growth_chart = plot_growth_chart(profit_growth_df, "Compounded Profit Growth")

        # Calculate intrinsic values
        if epsvalue and current_price:
            epsvalue = float(epsvalue.replace(',', ''))
            current_price = float(current_price.replace(',', ''))
            fy23_pe = current_price / epsvalue
            intrinsic_pe = dcf_intrinsic_pe(epsvalue, growth_during_high_growth, high_growth_period, fade_period, terminal_growth_rate, coc)
            overvaluation = calculate_overvaluation(current_pe, fy23_pe, intrinsic_pe)
            
        else:
            st.error("Financial data is incomplete or missing.")
            return

        # Display results in two columns
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"Stock Symbol: {stock_symbol}")
            st.write(f"Current P/E Ratio: {current_pe}")
            st.write(f"Current Price: {current_price}")
            st.write(f"EPS: {epsvalue}")
            st.write(f"FY23 PE: {fy23_pe_calc}")
            st.write(f"5 Year Median Pre-Tax RoCE %: {rocevalue}")
        
        with col2:
            st.write(f"Intrinsic P/E calculated: {intrinsic_pe:.2f}")
            
            # Color-code the overvaluation
            if overvaluation > 20:
                st.error(f"Overvaluation: {overvaluation:.2f}% (Significantly overvalued)")
            elif overvaluation > 0:
                st.warning(f"Overvaluation: {overvaluation:.2f}% (Moderately overvalued)")
            else:
                st.success(f"Undervaluation: {abs(overvaluation):.2f}% (Potentially undervalued)")
        
        # Show growth tables and charts
        st.subheader("Growth Analysis")
        col3, col4 = st.columns(2)
        
        with col3:
            st.table(prepared_sales_growth)
            st.plotly_chart(sales_growth_chart, use_container_width=True)
        
        with col4:
            st.table(prepared_profit_growth)
            st.plotly_chart(profit_growth_chart, use_container_width=True)

if __name__ == "__main__":
    main()
