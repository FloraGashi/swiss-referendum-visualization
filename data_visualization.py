import streamlit as st
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
from pyaxis import pyaxis
import matplotlib.patches as mpatches
import base64
import seaborn as sns
import plotly.graph_objects as go
from pathlib import Path

DATA_PATH = Path(r"C:\Users\flora\Desktop\HSLU\Semester 3\Data Visualization\Project\data")
GEOJSON_FILE = DATA_PATH / "swissBOUNDARIES3D_1_3_TLM_KANTONSGEBIET.geojson"
VOTATIONS_RESULTS_FILE = DATA_PATH / "px-x-1703030000_100.px"
VOTATIONS_YES_NO_FILE = DATA_PATH / "px-x-1703010000_102.px"
ENCODING = 'ISO-8859-2'
KEYWORDS = ['Militär', 'Atom', 'Covid', 'Ausländer']
GRAPH_COLORS = ['#1DA5E1', '#226B22', '#F23A29', '#533CA6', '#73175A']

def load_geojson(file_path):
    """Load and return a GeoDataFrame from a GeoJSON file."""
    gdf = gpd.read_file(file_path)
    return gdf.to_crs(epsg=4326)

def load_votations_data(file_path):
    """Load and return votations data as a DataFrame."""
    file_path_str = str(file_path)
    px_data = pyaxis.parse(file_path_str, encoding=ENCODING)
    return px_data['DATA']

def get_image_as_base64(path):
    """Encodes an image file to a base64 string"""
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return encoded_string

def configure_matplotlib():
    """Sets the font and the font size"""
    plt.rcParams['font.family'] = 'Century Gothic'
    plt.rcParams['font.size'] = 10

def convert_column_numeric(dataframe,*columns):
    """Convert the column content into numeric."""
    for name in columns:
        dataframe[name] = pd.to_numeric(dataframe[name], errors='coerce')
    return dataframe

def preprocess_votations_data(votations_results, keywords):
    """Processes votations data to filter and analyze 
    participation based on specified keywords."""
    filtered_votations = votations_results[votations_results['Vorlage'].str.contains('|'.join(keywords), case=False, na=False)]

    # filter for rows where the 'Ergebnis' column is 'Beteiligung in %' and convert the 'DATA' column to numeric
    beteiligung_columns = filtered_votations[filtered_votations['Ergebnis'] == 'Beteiligung in %']
    beteiligung_columns['DATA'] = pd.to_numeric(beteiligung_columns['DATA'], errors='coerce')

    beteiligung_columns['Jahr'] = pd.to_datetime(beteiligung_columns['Datum']).dt.year

    average_participation_by_theme = beteiligung_columns.groupby('Vorlage')['DATA'].mean().reset_index()
    average_participation_by_theme.columns = ['Thema', 'Durchschnittliche Beteiligung in %']

    # prepare a DataFrame to store results
    result_df = pd.DataFrame({
        'Thema': keywords,
        'Durchschnittliche Beteiligung in %': [average_participation_by_theme[average_participation_by_theme['Thema'].str.contains(keyword, case=False, na=False)]['Durchschnittliche Beteiligung in %'].mean() for keyword in keywords]
    })

    # calculate the average participation rate by canton
    average_participation_by_canton = beteiligung_columns.groupby('Kanton')['DATA'].mean().reset_index()
    average_participation_by_canton.columns = ['Kanton', 'Durchschnittliche Beteiligung in %']

    # convert the 'DATA' column to numeric and drop any rows with NaN values
    votations_results['DATA'] = pd.to_numeric(votations_results['DATA'], errors='coerce')
    votations_results = votations_results.dropna(subset=['DATA'])

    # group by both 'Vorlage' and 'Kanton' and calculate the mean participation rate
    average_participation_by_theme_kanton = beteiligung_columns.groupby(['Vorlage', 'Kanton'])['DATA'].mean().reset_index()
    average_participation_by_theme_kanton.columns = ['Thema', 'Kanton', 'Durchschnittliche Beteiligung in %']

    unique_kantone = average_participation_by_theme_kanton['Kanton'].unique()

    # concatenate data for each keyword to the results DataFrame
    result_df = pd.DataFrame({
        'Kanton': [],
        'Thema': [],
        'Durchschnittliche Beteiligung in %': []
    })

    for keyword in keywords:
        theme_data = average_participation_by_theme_kanton[average_participation_by_theme_kanton['Thema'].str.contains(keyword, case=False, na=False)]

        result_df = pd.concat([result_df, pd.DataFrame({
            'Kanton': unique_kantone,
            'Thema': [keyword] * len(unique_kantone),
            'Durchschnittliche Beteiligung in %': [theme_data[theme_data['Kanton'] == kanton]['Durchschnittliche Beteiligung in %'].mean() for kanton in unique_kantone]
        })])

    return result_df


def prepare_data(votations_results, votations_yes_no):
    """Prepares the data for plotting by parsing dates and filtering for specific criteria."""
    # add date column
    votations_results[['Datum', 'Vorlage']] = votations_results['Datum und Vorlage'].str.split(' ', n=1, expand=True)
    votations_results.drop('Datum und Vorlage', axis=1, inplace=True)

    # add year, month and day columns
    votations_results[['Jahr', 'Monat', 'Tag']] = votations_results['Datum'].str.split('-', n=2, expand=True)

    # filter data for Switzerland's participation percentage
    votations_percentage = votations_results.loc[(votations_results.Kanton == 'Schweiz') & (votations_results.Ergebnis == 'Beteiligung in %')]
    votations_percentage = convert_column_numeric(votations_percentage, 'DATA', 'Jahr', 'Monat', 'Tag')
    votations_percentage = votations_percentage.drop(columns=['Ergebnis'], axis=1)
    votations_percentage = votations_percentage.rename(columns={"DATA": "Beteiligung"})

    years_range_low = 1880
    years_range_high = 2024
    participation_to_plot = votations_percentage.loc[(votations_percentage.Jahr >= years_range_low) &
                                                    (votations_percentage.Jahr < years_range_high)]

    foreigners = participation_to_plot.loc[participation_to_plot.Vorlage.str.contains('Ausländ')]
    atom = participation_to_plot.loc[participation_to_plot.Vorlage.str.contains('Atom')]
    military = participation_to_plot.loc[participation_to_plot.Vorlage.str.contains('Militär')]
    covid = participation_to_plot.loc[participation_to_plot.Vorlage.str.contains('Covid')]
    topics_list = [foreigners, military, atom, covid]

    # simplify naming of index columns
    votations_yes_no = votations_yes_no.rename(columns={'Kanton': 'Kanton', 'Periode': 'Years', 'Abstimmungsvorlage (Typ)':
        'Type', 'Abstimmungsvorlage (angenommen / verworfen)': 'Results', 'DATA': 'Data'})

    # split year from labels "Periode:" and "Jahr"
    votations_yes_no[['Label', "Year"]] = votations_yes_no['Years'].str.split(': ', n=1, expand=True)
    votations_yes_no.drop('Years', axis=1, inplace=True)

    labels_to_delete = ['Periode', 'Jahrzehnt']
    votations_yes_no = votations_yes_no[~votations_yes_no['Label'].str.startswith(tuple(labels_to_delete))]

    votations_yes_no.drop('Label', axis=1, inplace=True)

    # convert years to integer
    votations_yes_no['Data'] = pd.to_numeric(votations_yes_no['Data'], errors='coerce') #.astype(int)
    votations_yes_no['Year'] = pd.to_numeric(votations_yes_no['Year'], errors='coerce')#.astype(int)

    types_list = [item for item in votations_yes_no.Type.unique()]

    def total_votation_per_type(type):
        """This function takes a valid type of the votations_yes_no dataframe as argument.
        Returns the dataframe with total number votations per year, for this type for Switzerland."""
        dataframe = votations_yes_no.loc[(votations_yes_no['Results'] == 'Total') & (votations_yes_no['Kanton'] ==
                                                                                    'Schweiz') & (votations_yes_no['Type'] == type)]
        return dataframe

    # create relative values
    yes_no_to_plot = total_votation_per_type(types_list[5])
    yes_no_to_plot = yes_no_to_plot.loc[(yes_no_to_plot.Year > years_range_low) & ( yes_no_to_plot.Year <
                                                                                    years_range_high)]

    # add column with relative number of votations/year (%)
    yes_no_to_plot['Data_relative'] = yes_no_to_plot.loc[:, 'Data']
    yes_no_to_plot.Data_relative = yes_no_to_plot.Data_relative / 16 * 100

    return votations_results, yes_no_to_plot, participation_to_plot, topics_list


def plot_overall_participation(yes_no_to_plot, participation_to_plot, graph_colors):
    """ Plot the overall participation trend over time for different initiatives."""
    fig, ax = plt.subplots(figsize=(8,6))
    ax.set_title('Popular votations', loc='center', fontdict={'fontname': 'Century Gothic', 'size': 16}, pad=25)
    
    # setup the grid, ticks and params
    ax.grid(True, which='major', color='lightgrey', linestyle='-', linewidth=0.5)
    ax.tick_params(axis='x', labelsize=12, labelcolor='#646464', direction='out', length=6, width=0.5)
    ax.tick_params(axis='y', labelsize=12, labelcolor='#646464', direction='out', length=6, width=0.5)
 
    ax.spines['bottom'].set_linewidth(2)
    ax.spines['left'].set_linewidth(2)
    ax.spines['bottom'].set_color('darkgrey')
    ax.spines['left'].set_color('darkgrey')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # set the limits for the x and y axes
    ax.set_ylim(bottom=0, top=100)
    ax.set_xlim(left=1880, right=2030)
    xlabel = ax.set_xlabel("Year", loc='center')
    ylabel = ax.set_ylabel("% of participation")
    xlabel.set_fontname('Century Gothic')
    xlabel.set_size(12)
    ylabel.set_fontname('Century Gothic')
    ylabel.set_size(12)
    
    yes_no_to_plot = yes_no_to_plot.sort_values('Year')
    ax.scatter(participation_to_plot.Jahr, participation_to_plot.Beteiligung, marker='.', color='lightgrey')
    moving_average = participation_to_plot.Beteiligung.rolling(window=25).mean()
    ax.plot(participation_to_plot.Jahr, moving_average, color=graph_colors[2])

    moving_average2 = yes_no_to_plot.Data_relative.rolling(window=25).mean()
    ax.plot(yes_no_to_plot.Year, moving_average2, color=graph_colors[0])
    
    participation_patch = mpatches.Patch(color=graph_colors[2], label='Participation average')
    number_votation_patch = mpatches.Patch(color=graph_colors[0], label='Relative number of popular initiatives')
    ax.legend(handles=[participation_patch, number_votation_patch], loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0., frameon=False, prop={'family': 'Century Gothic', 'size': 10})

    # highlight significant historical periods
    ax.axvspan(1914, 1918, facecolor='lightgrey', alpha=0.3)
    ax.axvspan(1939, 1945, facecolor='lightgrey', alpha=0.3)
    ax.axvspan(1971, 1972, facecolor='lightgrey', alpha=0.3)
    ax.axvspan(2019, 2022, facecolor='lightgrey', alpha=0.3)

    # annotate significant events
    ax.annotate("World War I", xy=(0.22, 1.01), xycoords='axes fraction', xytext=(0, 5),
                textcoords='offset points', ha='center', va='bottom', fontsize=10)
    ax.annotate("World War II", xy=(0.4, 1.01), xycoords='axes fraction', xytext=(0, 5),
                textcoords='offset points', ha='center', va='bottom', fontsize=10)
    ax.annotate("Women's suffrage", xy=(0.6, 1.01), xycoords='axes fraction', xytext=(0, 5),
                textcoords='offset points', ha='center', va='bottom', fontsize=10)
    ax.annotate("Covid crisis", xy=(0.93, 1.01), xycoords='axes fraction', xytext=(0, 5),
                textcoords='offset points', ha='center', va='bottom', fontsize=10)

    plt.subplots_adjust(top=0.85)
    st.pyplot(fig)

    return moving_average


def plot_each_topics_participation(participation_to_plot, moving_average, topics_list, graph_colors, topics_titles):
    configure_matplotlib()
    fig, axs = plt.subplots(2,2, figsize=(12,10), sharex=True, sharey=True)

    # adjust spacing at the top of the figure and between subplots
    fig.subplots_adjust(top=0.85, hspace=0.3)
    fig.suptitle('Participation', fontname='Century Gothic', fontsize=14)

    # define tick ranges for the x and y axes
    x_ticks = range(1880, 2030, 20)
    y_ticks = range(0, 101, 25)

    k = 0
    ax = axs[0, 0] 
    last_point = topics_list[k].iloc[-2]  
    x, y = last_point['Jahr'], last_point['Beteiligung']
    y_offset = 10
    y_offset_for_grey_line = 37
    annotation_text = "Participation to each \npopular initiative \nabout foreigners" 

    ax.text(x, y + y_offset, annotation_text, color=graph_colors[k], fontsize=10, fontname='Century Gothic', 
            verticalalignment='center', horizontalalignment='left', transform=ax.transData)

    x_positions = {
        "World War I": 0.20,
        "World War II": 0.40,
        "Women's suffrage": 0.68,
        "Covid crisis": 0.95
    }

    for event, x_pos in x_positions.items():
        axs[0, 0].annotate(event, xy=(x_pos, 0.98), xycoords="axes fraction", 
                            xytext=(0, 10), textcoords='offset points', 
                            ha='center', va='bottom', fontsize=10)

    for i in range(2):
        for j in range(2):
            ax = axs[i, j]

            ax.axvspan(1914, 1918, facecolor='lightgrey', alpha=0.3)
            ax.axvspan(1939, 1945, facecolor='lightgrey', alpha=0.3)
            ax.axvspan(1971, 1973, facecolor='lightgrey', alpha=0.3)
            ax.axvspan(2019, 2022, facecolor='lightgrey', alpha=0.3)
            
            ax.plot(participation_to_plot.Jahr, moving_average, color="grey", linewidth=1, alpha=0.7)
            ax.scatter(topics_list[k].Jahr, topics_list[k].Beteiligung, color=graph_colors[k], s=40, alpha=0.7, zorder=99)
            ax.plot(topics_list[k].Jahr, topics_list[k].Beteiligung, color=graph_colors[k], linewidth=2, alpha=0.7, zorder=99)

            # set the grid, spines and ticks configurations
            ax.grid(color="#D5D5D5", linestyle="-", linewidth=0.5)
            ax.spines['bottom'].set_linewidth(2)
            ax.spines['left'].set_linewidth(2)
            ax.spines['bottom'].set_color('darkgrey')
            ax.spines['left'].set_color('darkgrey')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.set_xticks(x_ticks)
            ax.set_yticks(y_ticks)

            ax.tick_params(axis='x', which='both', labelsize=10, labelcolor='#646464', direction='out', length=6, width=0.5, labelbottom=True)
            ax.tick_params(axis='y', which='both', labelsize=10, labelcolor='#646464', direction='out', length=6, width=0.5, labelleft=True)

             # only for the first subplot, added an annotation for the grey line
            if k == 0:
                grey_line_label = "Average participation \nof all popular initiatives"
                
                ax.text(x, y - y_offset_for_grey_line, grey_line_label, color='grey', fontsize=10, fontname='Century Gothic', 
            verticalalignment='center', horizontalalignment='left', transform=ax.transData)
            ax.set_title(topics_titles[k], fontsize=12, pad=30)
            ax.grid(True, which='major', color='lightgrey', linestyle='-', linewidth=0.5)

            k += 1
    
    st.pyplot(fig)


def plot_violin(participation_to_plot, topics_list, topics_titles, graph_colors):
    """Plots a violin plot for participation data for different topics. The violin plot
    shows the distribution and density of the participation percentages."""

    # preparing the military data by filtering and dropping NaN values
    military = participation_to_plot.loc[participation_to_plot.Vorlage.str.contains('Militär')]
    military = military.dropna()
    fig, axs = plt.subplots(figsize=(10,10), ncols=2, nrows=2, sharex='all', sharey='all')
    fig.suptitle('Participation density',fontsize=14)
    fig.subplots_adjust(wspace=0)

    axs = axs.flatten()
    
    # looping through each topic to create individual violin plots
    for i, topic in enumerate(topics_list):
        ax = axs[i]
        ax.grid(False)
        ax.set_frame_on(False)
        ax.set_ylim(bottom=0, top=100)
        ax.get_xaxis().set_visible(False)

        # creating the background violin plot for the general participation data
        part1 = ax.violinplot(participation_to_plot.dropna().Beteiligung, showmeans=False, showmedians=False,
                              showextrema=False)
        for pc in part1['bodies']:
            pc.set_facecolor('lightgrey')

        # creating the foreground violin plot for the specific topic's participation data
        part2 = ax.violinplot(topic.Beteiligung, showmeans=False, showmedians=False, showextrema=False)
        for pc in part2['bodies']:
            pc.set_facecolor(graph_colors[i])

        # adding scatter points to the violin plot for individual data points
        x_value = [1 for x in range(len(topic.Beteiligung))]
        ax.scatter(x_value, topic.Beteiligung, color=graph_colors[i])

        ax.set_title(topics_titles[i], y=-0.1, fontsize=12)

        if i == 0:
            ax.text(1, 20, "Overall Initiatives", color='grey', fontsize=11, ha='right')

    plt.tight_layout(pad=1.0)
    return st.pyplot(fig)

def plot_heatmap(votations_results, topics_titles):
    """Creates a heatmap visualization to display the margin of 'Yes' votes
    for different political topics in Switzerland."""
    results_ja = votations_results.loc[(votations_results.Kanton == 'Schweiz') & (votations_results.Ergebnis == 'Ja in %')]
    results_ja = convert_column_numeric(results_ja, 'DATA', 'Jahr', 'Monat', 'Tag')

     # calculating the margin of 'Yes' votes from 50%
    results_ja['difference'] = results_ja.DATA -50

    # filtering results for each topic and storing them in a list
    foreigners_results_ja = results_ja.loc[results_ja.Vorlage.str.contains('Ausländ')]
    atom_results_ja = results_ja.loc[results_ja.Vorlage.str.contains('Atom')]
    military_results_ja = results_ja.loc[results_ja.Vorlage.str.contains('Militär')]
    covid_results_ja = results_ja.loc[results_ja.Vorlage.str.contains('Covid')]
    topics_list_ja = [foreigners_results_ja, military_results_ja, atom_results_ja, covid_results_ja]

    for topic in topics_list_ja:
        topic.set_index('Vorlage', inplace=True)

    configure_matplotlib()
    fig, ax = plt.subplots(1,4, figsize=(8,4), sharex=True)
    fig.suptitle('Margin percentage per initiative', fontsize=9)
    fig.subplots_adjust(wspace=0)

    color = sns.light_palette("#0042C3", as_cmap=True)

    i_topic = 0
    for i in range(4):
        topic = topics_list_ja[i_topic]

        # sorting the values by the absolute difference and setting up the heatmap
        topic = topic[['difference']].abs().sort_values(by="difference", ascending=True)
        im = sns.heatmap(ax=ax[i], data=topic,  vmin=0, vmax=5, annot=False, linewidths=0.1,
                        yticklabels=False, xticklabels=False, cbar=False, cmap=color)
        ax[i].get_yaxis().set_visible(False)
        ax[i].set_xlabel(topics_titles[i],fontsize=8, fontname='Century Gothic', loc='center')

        i_topic += 1
    cbar = fig.colorbar(ax[3].collections[0], location='right', shrink=1,  ticks=[0, 2.5, 5])
    cbar.ax.set_yticklabels(['Tight', '2.5%', '>5% Clear'], fontsize=8, fontname='Century Gothic')
    cbar.ax.invert_yaxis()
    
    st.pyplot(fig)


def plot_bubble_chart(data):
    """Plots the Bubbles for how many times the topics reoccured in the initiatives."""
    bubble_colors = ['rgb(179, 200, 178)','rgb(182, 217, 235)', 'rgb(236, 186, 181)', 'rgb(193, 186, 217)']

    fig = go.Figure()

    x_coordinate = 0
    y_coordinate = 0

    for index, row in data.iterrows():
        # adjusted the x-coordinate for subsequent bubbles to prevent overlap
        if index != 0: 
            x_coordinate += data.iloc[index - 1]['DisplaySize'] / 2 + row['DisplaySize'] / 2 + 10

        fig.add_trace(go.Scatter(
            x=[x_coordinate],
            y=[y_coordinate],
            mode='markers',
            marker=dict(
                size=row['DisplaySize'],
                sizemode='diameter',
                sizeref=0.0001,
                color=bubble_colors[index], 
            ),
            hoverinfo='none',
            text=str(row['Frequency']),
            textposition='middle center',
            textfont=dict(family='Century Gothic', size=row['TextSize'], color='white'),
            showlegend=False,
        ))

        fig.add_annotation(
            x=x_coordinate,
            y=y_coordinate,
            text=str(row['Frequency']),
            font=dict(family='Century Gothic', size=row['TextSize'], color='black'),
            showarrow=False,
        )

        # calculate yshift to place the keyword below the bubble
        yshift = -row['DisplaySize'] / 2 - 10  

        fig.add_annotation(
            x=x_coordinate,
            y=y_coordinate,
            text=row['Keyword'],
            font=dict(family='Century Gothic', size=16, color='black'),
            showarrow=False,
            xshift=0,
            yshift=yshift,
        )

    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')
    fig.update_layout(width=700, height=500)
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False)
    st.plotly_chart(fig)

def plot_maps(result_df, gdf):
    """Displays maps for different themes (Military, Foreigners, Atom, Covid)
    showing the average participation in votations per county in Switzerland."""

    # standardize canton names in the result dataframe to match the GeoDataFrame
    result_df['Kanton'] = result_df['Kanton'].replace({
        'Bern / Berne': 'Bern',
        'Fribourg / Freiburg': 'Fribourg',
        'Genčve': 'Genève',
        'Graubünden / Grigioni / Grischun': 'Graubünden',
        'Neuchâtel': 'Neuchâtel',
        'Valais / Wallis': 'Valais',
        'Vaud': 'Vaud'
    })

    # merge the votations data with the geographical data on the canton name
    merged_df = gdf.merge(result_df, left_on='NAME', right_on='Kanton', how='left')

    # fill any missing values for average participation with the overall mean
    result_df['Durchschnittliche Beteiligung in %'] = result_df['Durchschnittliche Beteiligung in %'].fillna(result_df['Durchschnittliche Beteiligung in %'].mean())

    keywords = ['Militär', 'Ausländer', 'Atom', 'Covid']
    
    cmaps = [plt.cm.Greens, plt.cm.Blues, plt.cm.Reds, plt.cm.Purples] 
   
    fig, axs = plt.subplots(nrows=2, ncols=2, figsize=(26, 32)) 
    axs = axs.flatten()

    norm = plt.Normalize(vmin=result_df['Durchschnittliche Beteiligung in %'].min(), 
                         vmax=result_df['Durchschnittliche Beteiligung in %'].max())

    texts_for_keywords = {
        'Militär': 'Military',
        'Atom': 'Atom',
        'Covid': 'Covid',
        'Ausländer': 'Foreigners'
    }   

    for ax, keyword, cmap in zip(axs, keywords, cmaps):
        # get the data for the current theme and remove any duplicate cantons
        keyword_data = merged_df[merged_df['Thema'] == keyword].drop_duplicates(subset=['Kanton'])

        # sort the data by participation percentage for legend labeling
        keyword_data_sorted = keyword_data.sort_values(by='Durchschnittliche Beteiligung in %', ascending=False)
        text_to_display = texts_for_keywords.get(keyword, "Default text if keyword not found")

        gdf.plot(ax=ax, color='lightgrey', edgecolor='black', linewidth=0.4)
        keyword_data_sorted.plot(ax=ax, column='Durchschnittliche Beteiligung in %', cmap=cmap, linewidth=0.8, edgecolor='lightgray', legend=False)

        legend_labels = [f"{row['Kanton']}: {row['Durchschnittliche Beteiligung in %']:.1f}%" for index, row in keyword_data_sorted.iterrows()]
        patches = [mpatches.Patch(color=cmap(norm(value)), label=label) for value, label in zip(keyword_data_sorted['Durchschnittliche Beteiligung in %'], legend_labels)]
        ax.text(0.02, 0.95, text_to_display, transform=ax.transAxes, fontsize=25)
        ax.legend(handles=patches, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=22)
        ax.set_axis_off()

    plt.tight_layout(pad=2.0)
    st.pyplot(fig)
    st.write("\n")  


def main():
    """Main function of the Streamlit application.
    It loads data, processes it, and displays visualizations."""
    gdf = load_geojson(GEOJSON_FILE)
    votations_results = load_votations_data(VOTATIONS_RESULTS_FILE)
    votations_yes_no = load_votations_data(VOTATIONS_YES_NO_FILE)
    topics_titles = ['Foreigners', 'Military', 'Atom', 'Covid']
    votations_results, yes_no_to_plot, participation_to_plot, topics_list = prepare_data(votations_results, votations_yes_no)
    data = pd.DataFrame({
        'Keyword': ['Military', 'Foreigners', 'Atom', 'Covid'],
        'Frequency': [18, 15, 11, 3],
        'DisplaySize': [180, 150, 110, 30],
        'TextSize': [60, 50, 45, 12],
    })
    result_df = preprocess_votations_data(votations_results, KEYWORDS)

    st.markdown("<h1 style='font-family: Century Gothic ;text-align: center; color: brown;'>Swiss Popular Initiatives</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-family: Century Gothic ;text-align: center; color: black;'>The influence of the subject over participation rate</h3>", unsafe_allow_html=True)
    st.markdown("<h1 style='font-family:Lucida ;text-align: center;font-size: 12pt; color: darkgrey;'>By Flora Gashi & Sevan Sherbetjian</h1>", unsafe_allow_html=True)
    st.write('---')

    # introduction
    st.write("In Switzerland, voting is a big deal. It's not just about making laws; it's a way for everyone to have a say in our country's future. Several times a year, we get to vote on important issues.")
    st.markdown("<h3 style='font-family: Century Gothic ;text-align: left; font-size: 14pt; color: black;'>Without voters, there is no democracy.</h3>", unsafe_allow_html=True)
    st.write("Walking through the streets of our country, one can't help but notice numerous advertisements boldly displaying 'YES' or 'NO' in large letters. Political parties invest substantial resources in campaigns aimed at not only urging people to vote but also influencing them to align with their perspectives. These initiatives, depending on the subject at hand, can become fiercely contested, leading to strained relationships among friends and family members, and dominating public discourse. Despite the prominence of these campaigns, overall participation has been on a downward trend in recent years.")
    st.write("We wondered which role plays specific topics in the referendums. How much does a topic influence the participation rate? Looking at the general picture, participation varies differently across population. The most frequent voters are typically older folks and residents of German-speaking regions. They're pretty active when it comes to voting.")
    st.write("Moreover, there is evidence that voter turnout is influenced by perceptions of a fair system. Trust in the government and overall satisfaction can either encourage or discourage people from voting, similar to how confidence in good weather encourages outdoor activities. Also, when folks believe in their government and things are going smoothly, voting might not be on the top of their 'fun to-do' list!")
    st.write("But what about the contentious debates? Which topics stir the Swiss population to voice their opinions at the ballot box? To explore this, we've selected four controversial subjects and will examine their correlation with participation trends.")
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown("<h3 style='font-family: Century Gothic ;text-align: center; color: brown;'>The subjects</h3>", unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)

    # subjects
    image_width = "55px"
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div style='text-align: center'><img src='data:image/png;base64,{get_image_as_base64('img/panzer.png')}' width='{image_width}' style='display: block; margin-left: auto; margin-right: auto;'></div>", unsafe_allow_html=True)
        col1.markdown("<h2 style='font-family: Century Gothic; text-align: center; font-size: 15pt; color: black;'>Military</h2>", unsafe_allow_html=True)
        st.caption("The old guard always ready for a referendum on whether to buy new fighter jets or perhaps a vote on whether every citizen gets a Swiss Army knife at birth!")
       
    with col2:
        st.markdown(f"<div style='text-align: center'><img src='data:image/png;base64,{get_image_as_base64('img/globus.png')}' width='{image_width}' style='display: block; margin-left: auto; margin-right: auto;'></div>", unsafe_allow_html=True)
        col2.markdown("<h2 style='font-family: Century Gothic; text-align: center; font-size: 15pt; color: black;'>Foreigners</h2>", unsafe_allow_html=True)
        st.caption("The topic that's like the neighborhood's lively debate forum—always buzzing, always a hot topic at the dinner table.")

    with col3:
        st.markdown(f"<div style='text-align: center'><img src='data:image/png;base64,{get_image_as_base64('img/atom.png')}' width='{image_width}' style='display: block; margin-left: auto; margin-right: auto;'></div>", unsafe_allow_html=True)
        col3.markdown("<h2 style='font-family: Century Gothic; text-align: center; font-size: 15pt; color: black;'>Atom</h2>", unsafe_allow_html=True)
        st.caption("The intense debate club captain, constantly sparking conversations about energy—should we keep the lights on with nuclear power or just rely on the glow of a thousand Swiss watches?")

    with col4:
        st.markdown(f"<div style='text-align: center'><img src='data:image/png;base64,{get_image_as_base64('img/covid.png')}' width='{image_width}' style='display: block; margin-left: auto; margin-right: auto;'></div>", unsafe_allow_html=True)
        col4.markdown("<h2 style='font-family: Century Gothic; text-align: center; font-size: 15pt; color: black;'>Covid</h2>", unsafe_allow_html=True)
        st.caption("The new kid on the block, throwing a curveball into the mix with health policies that had everyone talking and voting on whether to wear masks.")

    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown("<h2 style='font-family: Century Gothic; text-align: left; font-size: 16pt; color: #646464;'>Below, you can observe that the average participation rate tends to decrease over time, while the average number of initiatives has significantly increased</h2>", unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)  

    # plot the participation
    moving_average =  plot_overall_participation(yes_no_to_plot, participation_to_plot, GRAPH_COLORS)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.write("However, this trend is not linear. Looking at each popular initiative (grey dots), we observe a wide variety in the participation… Are our spicy topics sparking the excitement?")
    st.write("Let’s dive into each topic separately. Against all odds, the 'foreigners' topic mostly aligns with the average of its time. It only gained regularity during the 80s. The initiative in 2016 led to increased participation (63%), possibly due to the inclusion of two buzzwords in the question: 'foreigners' and 'criminal.'")
    st.write("On the bottom left graph, we see that the atom subject did not trigger a significant rise in the participation rate. From the late 50s onwards, most initiatives align with the average. The topic peaked in 1962 when the question revolved around nuclear weapons.")
    st.write("Discussing weapons, in the top right graph, the 'military' exhibited a notably high participation rate at the beginning of the century. During this period, there was a pronounced surge in interest and involvement in this topic, surpassing the average. Why the sudden enthusiasm?")
    st.write("It's important to consider that only men had voting rights, and just before World War I, a significant 80% of them were potential soldiers. It's unsurprising that the level of engagement was elevated during this time. Could a similar dynamic explain the initially higher engagement with Covid initiatives (bottom right)? On both fronts, a substantial majority of voters are directly affected by the outcomes of the initiatives and likely hold strong opinions.")
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    
    # plot participation for each topic
    plot_each_topics_participation(participation_to_plot, moving_average, topics_list, GRAPH_COLORS, topics_titles)
    st.markdown('<br><br><br>', unsafe_allow_html=True)  

    st.write("On this additional view, we can better compare how the participation of a topic behaves compared to the overall initiatives. The “foreigners” and “atom” fit the trends, while military and Covid areas are slightly wider around 60%.")
    
    # plot the violin plot
    plot_violin(participation_to_plot, topics_list, topics_titles, GRAPH_COLORS)
    st.markdown('<br><br><br>', unsafe_allow_html=True) 
    st.markdown("<h2 style='font-family: Century Gothic; text-align: left; font-size: 16pt; color: #646464;'>However, the topic alone does not suffice to explain the participation. None of the topics consistently remained above or below the general trends. Could the frequency shed light on people’s motivation to vote?</h2>", unsafe_allow_html=True)

    st.markdown('<br><br><br>', unsafe_allow_html=True)  
    st.markdown('<br><br><br>', unsafe_allow_html=True)  
    st.markdown('<br><br><br>', unsafe_allow_html=True)  
    st.markdown('<br><br><br>', unsafe_allow_html=True)  
    st.markdown("<h2 style='font-family: Century Gothic; text-align: center; font-size: 20pt; color: #646464;'>Fun Fact: Did you know that Switzerland has enough bunkers to shelter its entire population in case of an emergency? But enough of that, let's continue our investigation...</h2>", unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)

    st.markdown("<h2 style='font-family: Century Gothic; text-align: left; font-size: 20pt; color: #646464;'>Reoccurence of the topics</h2>", unsafe_allow_html=True)

    st.write("Checking out initiatives since 1880, certain topics keeps resurrecting, just like zombies. But the veteran topic, the military, outvotes them all! The army has always played an important role in our country’s history, just like our neutrality. It’s no surprise that the subject keeps appearing in the initiatives. As we saw previously, the foreigners topic has been voted on more frequently over the years, with fluctuating participation. Younger than the military, the population has answered questions about it almost as often.")
    st.write("The atom is not far behind, with 11 initiatives. However, Covid, which has only existed since 2019, has already been voted on three times. Impressive, isn’t it?")
    
    # plot the bubble chart
    plot_bubble_chart(data)

    st.write("Our topics are hotly debated, so the results likely mirror the battle, don't they? Take a look at the heated outcomes we've illustrated below. The lighter the shade, the tighter the contest. May the best win!")  
    st.write("The foreigners debate on the top left was extremely close: rejected by less than 0.36% in 1982! This time, it was expected: the foreigner polarizes among voters the most. On the other hand, the results of Covid have not reflected vigorous fights so far.")
    
    # plot the heatmap
    plot_heatmap(votations_results, topics_titles)

    st.markdown('<br><br><br>', unsafe_allow_html=True)  
    st.markdown('<br><br><br>', unsafe_allow_html=True)  
    st.markdown("<h2 style='font-family: Century Gothic; text-align: center; font-size: 20pt; color: #646464;'>It's time for another Fact! Switzerland has a no-nonsense approach to nuclear safety. They once held a national referendum just to decide on a moratorium for new nuclear power plants. Talk about power to the people!</h2>", unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    
    st.markdown("<h2 style='font-family: Century Gothic; text-align: left; font-size: 20pt; color: #646464;'>Wait… don’t we forget about the “Röstigraben”? Are some topics more sensitive in certain places?</h2>", unsafe_allow_html=True)
    st.write("Picture this: Just three weeks after the Berlin Wall fell, Switzerland faced a groundbreaking choice. It was a pivotal moment 30 years ago when Swiss folks voted on whether to ditch their army. The driving force behind this audacious move? A group known as 'Switzerland Without an Army' or GSoA, born in 1982.")
    st.write("Here's the twist: On November 26, 1989, a whopping 35.6 percent of Swiss citizens got behind the plan—more than a million of them! But here's the real jaw-dropper: If you focused solely on Genf and Jura, Switzerland would've been an army-free paradise for three whole decades.")
    st.write("Aargau also stands out with a unique distinction. It's home to not one, not two, but three nuclear power plants! Beznau, Leibstadt, and Gösgen are the stars of Switzerland's nuclear energy scene, each contributing to the nation's power grid in its own way. Beznau, Switzerland's nuclear trailblazer, commenced operations in 1969, leading the way for clean energy. Leibstadt joined the ranks in 1984, while Gösgen, with its pressurized water reactor, has been a dependable source of power since 1979.")
    # plot the maps with the counties
    plot_maps(result_df, gdf)

    st.markdown("<h2 style='font-family: Century Gothic; text-align: left; font-size: 20pt; color: #646464;'>Well, we didn’t notice robust pattern tied to topics. Oh, and don’t get fooled by Schaffhausen, voting is mandatory there, which explains the constant higher participation.</h2>", unsafe_allow_html=True)
    
    st.markdown('<br><br><br>', unsafe_allow_html=True)  
    st.markdown('<br><br><br>', unsafe_allow_html=True) 
    st.markdown('<br><br><br>', unsafe_allow_html=True)   
    st.markdown("<h2 style='font-family: Century Gothic; text-align: center; font-size: 20pt; color: #646464;'>And to keep it interesting, here's another Fact.. In Switzerland, foreigners can be naturalized after 12 years of residence. That’s quite a commitment, almost like dating someone for a decade before popping the question!</h2>", unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)
    st.markdown('<br><br><br>', unsafe_allow_html=True)  
    st.markdown("<h2 style='font-family: Century Gothic; text-align: left; font-size: 20pt; color: #646464;'>Conclusion</h2>", unsafe_allow_html=True)
    st.write("We chose crispy topics to explore their impact on the participation rate and… we could not discern any significant overall connection. In deciphering higher participation rates, more frequent occurrences, or closer results, it became apparent that the nuances of the specific question provided more insights than the topic alone. It’s possible that other factors or their interplay, better explain why people opt for voting over spending time in the mountain, for few Sundays each year.")
    st.markdown('<br><br><br>', unsafe_allow_html=True)  
    st.write("---")
    st.markdown("<h2 style='font-family: Century Gothic; text-align: left; font-size: 14pt; color: #646464;'>Sources</h2>", unsafe_allow_html=True)
    st.write("Als die Schweiz ihrer Armee den Boden unter den Füssen wegzog - SWI swissinfo.ch")
    st.write("https://onlinelibrary.wiley.com/doi/pdf/10.1111/spsr.12116")
    st.write("https://www.swissinfo.ch/ger/politik/vor-30-jahren_als-die-schweiz-ihrer-armee-den-boden-unter-den-fuessen-wegzog/45349748")
    st.write("https://www.ag.ch/de/verwaltung/bvu/energie/energieversorgung/kernkraft")
    
    
if __name__ == "__main__":
    main()