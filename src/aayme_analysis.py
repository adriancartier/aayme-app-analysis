'''Importing the required libraries.''' 

import pandas as pd
import re
from datetime import datetime
from dateutil.parser import parse
import json
import plotly.express as px
import os 
import folium

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

#Reading in the data
aayme_applications = pd.read_csv('../data/aayme_applications.csv')
aayme_applications['date'] = pd.to_datetime(aayme_applications['Date Created']).dt.date #Stripping the time from the date field
print('Date field has been modified')

def plot_app_submission(df):
    '''Plot timeseries of application submission using a generalised function'''
    esd = df.groupby('date', as_index=True).size()
    fig = px.line(esd, x=esd.index, y=esd.values, title="AAYME Applications", width=1800, height=600)
    fig.write_image("../images/app_submission_tsplot.png")
    print('Plots have been saved to your images directory')
    
plot_app_submission(aayme_applications)

'''
Only plot demographic information and spatial map based on qualified students 
'''
aayme_applications = aayme_applications.dropna(subset = ['Qualified'])
aayme_applications = aayme_applications[aayme_applications['Qualified'] ==  "Yes"] 
def plot_feature_stats(df, dimension):
    '''
    This function will provide pie charts with raw statistics (size) based on whatever dimension you
    care about
    '''
    esd = df.groupby(dimension, as_index=True).size()
    config = {'staticPlot': True}
    fig = px.pie(esd, values=esd.values, names=esd.index,hole = 0.3)
    fig.update_layout(uniformtext_minsize=9, uniformtext_mode='hide')
    #fig.show(config)
    file_name = dimension
    fig.write_image("../images/" + file_name + '.png')
    print('Pie graph for',dimension, 'has been saved')
    
plot_feature_stats(aayme_applications, 'Sex')
plot_feature_stats(aayme_applications, 'Current Grade Level')
plot_feature_stats(aayme_applications, 'Household Income')

'''
Creating a geospatial map of the application submission. This will be done be joining the county 
zip codes in the data with the US Census geoJSON zip codes
'''
aayme_applications['Actual Sch. Postal / Zip Code'] = aayme_applications['Actual Sch. Postal / Zip Code'].astype(int)
geo_group = aayme_applications.groupby('Actual Sch. Postal / Zip Code')
geo_agg = geo_group.agg({
                       'Entry Id': pd.Series.nunique,
                        })
geo_agg.rename(columns = {'Entry Id':'total_applications'}, inplace = True)
geo_agg.reset_index(inplace=True)
geo_agg['Actual Sch. Postal / Zip Code'] = geo_agg['Actual Sch. Postal / Zip Code'].astype(str)

# load GeoJSON
with open('../data/ms_mississippi_zip_codes_geo.min.json', 'r') as jsonFile:
    data = json.load(jsonFile)
tmp = data

# remove ZIP codes not in our dataset
geozips = []
for i in range(len(tmp['features'])):
    if tmp['features'][i]['properties']['ZCTA5CE10'] in list(geo_agg['Actual Sch. Postal / Zip Code'].unique()):
        geozips.append(tmp['features'][i])

# creating new JSON object
new_json = dict.fromkeys(['type','features'])
new_json['type'] = 'FeatureCollection'
new_json['features'] = geozips

# save JSON object as updated-file
open("updated-file.json", "w").write(
    json.dumps(new_json, sort_keys=True, indent=4, separators=(',', ': '))
)

def create_map(table, zips, mapped_feature, add_text = ''):
    '''
    table = main table/data frame we read from (pandas DataFrame)
    zips = column name where ZIP codes are (string)
    mapped_feature = column name for feature we want to visualize (string)
    add_text = any additional commentary to be added in the map legend (string)
    '''
    # reading of the updated GeoJSON file
    ms_geo = r'updated-file.json'
    # initiating a Folium map with Mississippi's longitude and latitude
    m = folium.Map(location = [33.000000, -90.000000], tiles = 'cartodbpositron', zoom_start = 11)
    # creating a choropleth map
    m.choropleth(
        geo_data = ms_geo,
        fill_opacity = 0.7,
        line_opacity = 0.2,
        data = table,
        # refers to which key within the GeoJSON to map the ZIP code to
        key_on = 'feature.properties.ZCTA5CE10',
        # first element contains location information, second element contains feature of interest
        columns = [zips, mapped_feature],
        fill_color = 'RdYlGn',
        text_color = 'white',
        legend_name = (' ').join(mapped_feature.split('_')).title() + ' ' + add_text + ' Across Mississippi'
    )
    folium.LayerControl().add_to(m)
    # save map with filename based on the feature of interest
    m.save(outfile = "../images/" + mapped_feature + '_map.html')
    


# Call the create_map function which writes the map to an html file
create_map(geo_agg, 'Actual Sch. Postal / Zip Code', 'total_applications') 
