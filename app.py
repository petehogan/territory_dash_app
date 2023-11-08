import dash_leaflet as dl
from dash import Dash, html, Output, Input, State, dcc, dash_table
import dash_leaflet.express as dlx
import pandas as pd
from dash_extensions.javascript import Namespace
from dash import Dash, html
import numpy as np
import geopandas as gp
from shapely.geometry import Point,Polygon
import plotly.express as px
from flask_caching import Cache
import os 

def find_geo(d):
    """Extract point coordinates from geojson returned by edit control"""
    res = []
    try:
        for v in d['features']:
            if v['geometry']['type'] == 'Polygon':
                res.append(v['geometry']['coordinates'])
        return res
    except:
        return None

def dict_to_gpd(ex):
    """converts a geojson returned from edit_control as a dict to a geopandas dataframe """
    extracted_coords = [i['geometry']['coordinates'] for i in ex['features']]
    extracted_features =[ i['properties'] for i in ex['features']]
    for i,k in enumerate(extracted_features):
        k['coords'] = Point(extracted_coords[i])
    return gp.GeoDataFrame(extracted_features, geometry = 'coords')

def dict_to_pd(ex):
    """converts a geojson returned from edit_control as a dict to a pandas dataframe """
    extracted_coords = [i['geometry']['coordinates'] for i in ex['features']]
    extracted_features =[ i['properties'] for i in ex['features']]
    temp_df = pd.DataFrame(extracted_features)
    lats = []
    longs = []
    for i,k in enumerate(extracted_features):
        longs.append(extracted_coords[i][0])
        lats.append(extracted_coords[i][1])
    temp_df['BillingLatitude'] = lats
    temp_df['BillingLongitude'] = longs
    return temp_df

def read_og_df():
    """read in original data so that you can add rows back to the geojson once it has been trimmed by select territories """
    if os.path.isfile('assets/randdata_.csv'):
        df = pd.read_csv("assets/randdata_.csv")  # randomized data, created elsewhere
        df = df[~df['ExternalName'].isna()]
        new_row = pd.DataFrame([dict(zip(df.columns,[0 if x!= 'ExternalName' else 'New' for x in df.columns]))])
        df = pd.concat([df,new_row], ignore_index = True)
        df['category'] = df['ExternalName'].apply(lambda x: cat_terr_map[x])
        df = df[['BillingLatitude', 'BillingLongitude', 'BillingPostalCode','Consortium_Sales_Total', 'TA_Sales_Total','ExternalName',color_prop]]  # drop irrelevant columns
        df = df.dropna()
        return df


colorscale = ["#ff0000","#ff1700","#ff2e00","#ff4500","#ff5c00","#ff7300","#ff8a00","#ffa100","#ffb800","#ffcf00","#ffe500","#fffc00","#ebff00","#d4ff00",
"#bdff00","#a6ff00","#8fff00","#78ff00","#61ff00","#4aff00","#33ff00","#1cff00","#05ff00","#00ed12","#00d629","#00bf40","#00a857","#00916e","#007a85","#00639c","#004db3","#0036c9","#001fe0","#0008f7"] # 33 colors

chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"  # js lib used for colors
color_prop = 'category'
#####
#################### SET UP STARTING DATA ######################################
df = pd.read_csv("assets/randdata_.csv")  # data from https://simplemaps.com/data/us-cities
df = df[~df['ExternalName'].isna()]
new_row = pd.DataFrame([dict(zip(df.columns,[0 if x!= 'ExternalName' else 'New' for x in df.columns]))])
df = pd.concat([df,new_row], ignore_index = True)
category, uniques = pd.factorize(df['ExternalName'])
cat_terr_map = dict(zip(uniques,list(range(len(uniques)))))
df['category'] = category
df = df[['BillingLatitude', 'BillingLongitude', 'BillingPostalCode','Consortium_Sales_Total','TA_Sales_Total','ExternalName', color_prop]]
df = df.dropna()
dicts = df.to_dict('records')
for item in dicts:
    item["tooltip"] = f"Consortium_Sales: {item['Consortium_Sales_Total']} , TA Sales: {item['TA_Sales_Total']}, ZIP: {item['BillingPostalCode']}, External: ({item['ExternalName']})" # bind tooltip
geojson = dlx.dicts_to_geojson(dicts, lon="BillingLongitude", lat = "BillingLatitude")
geobuf = dlx.geojson_to_geobuf(geojson)
############################################################
################ COLOR BAR AND OTHER JS CRAP ###############
vmax = df[color_prop].max()
ctg = np.unique(category)
ctg = list(uniques)


colorbar = dlx.categorical_colorbar(categories=ctg, colorscale=colorscale, width=1500, height=30, position="bottomleft")

# Create geojson.
ns = Namespace("dashExtensions", "default")
gj = dl.GeoJSON(data=geojson, id="geojson_l", #format="geobuf",
                     zoomToBounds=False,  # when true, zooms to bounds when data changes
                     options=dict(pointToLayer=ns("function1")),  # how to draw points
                     superClusterOptions=dict(radius=50),   # adjust cluster size
                     hideout=dict(colorProp=color_prop, circleOptions=dict(fillOpacity=1, stroke=False, radius=5),
                                  min=0, max=vmax, colorscale=colorscale))
#################################################################################
#starting point for data table
tbl_df = pd.DataFrame(df.groupby('ExternalName')[['Consortium_Sales_Total','TA_Sales_Total']].sum().reset_index())
#################################################################################
#################################################################################
app = Dash(__name__, external_scripts=[chroma], prevent_initial_callbacks=True)#, compress=False, assets_folder='assets')
app.title = "Consortium Sales Totals by Territory"
#below commented out for local deployment

# cache = Cache(app.server, config={                                                      
#     # try 'filesystem' if you don't want to setup redis                                 
#     'CACHE_TYPE': 'filesystem',                                                         
#     'CACHE_DIR': '/tmp'                                                                 
# })                                                                                      
#app.config.suppress_callback_exceptions = True                                          
server = app.server                                                                     
#TIMEOUT = 60

app.layout = html.Div([
    dcc.Dropdown(df.ExternalName.unique(), placeholder = 'Select territories to examine' ,multi = True, id = 'en_select'), 
    dl.Map([ #colorbar
        dl.TileLayer(), gj,dl.FeatureGroup([
            dl.EditControl(id="edit_control")
            ]),
    ], center = [40,-80], style={'width': '90%', 'height': '80vh', 'margin': "auto", "display": "inline-block"}, id="map")
    ,dcc.Dropdown(ctg, 0, id='demo-dropdown', placeholder = 'Select territory to edit')
    ,dash_table.DataTable(data = tbl_df.to_dict('records'),columns =[{"name": i, "id": i} for i in tbl_df.columns],id = 'tbl') 
    ,html.Button('Download Territory Allocations', id = 'btn_csv_1')
    ,dcc.Download(id = 'download-territory-csv')
 ])


@app.callback(
    Output('geojson_l','data'),
    Output('tbl','data'),
    Output('tbl','columns'),
    Input('en_select','value'),
    Input('edit_control','geojson'),
    State('geojson_l','data'),
    State('demo-dropdown','value'),
    )

#commented out for local deployment
#@cache.memoize(timeout=TIMEOUT)

def everything_everywhere(selected_territories,edit_control,data,editing_territory):
    """respond to various inputs from edit control. Special cases for selecting territories, selecting editable territory, drawing a polygon and doing nothing."""
    coords = find_geo(edit_control)
    res = dict_to_pd(data)
    if not edit_control['features'] and selected_territories:
        #case when only you have selected a subset of territories but you have not yet drawn any polygons 
        res = read_og_df()

        df_ = res[res['ExternalName'].isin(selected_territories)].copy()
        tbl_df_ = pd.DataFrame(df_.groupby('ExternalName')[['Consortium_Sales_Total','TA_Sales_Total']].sum().reset_index())

        df_ = res[res['ExternalName'].isin(selected_territories)].copy()
        df_.iscopy = False
        dicts = df_.to_dict('records')
        for item in dicts:
            item["tooltip"] = f"Consortium_Sales: {item['Consortium_Sales_Total']} , TA Sales: {item['TA_Sales_Total']}, ZIP: {item['BillingPostalCode']}, External: ({item['ExternalName']})" # bind tooltip
        geojson = dlx.dicts_to_geojson(dicts, lon="BillingLongitude", lat = "BillingLatitude")  # convert to geojson        
        return geojson, tbl_df_.to_dict('records'),[{"name": i, "id": i} for i in tbl_df_.columns]

    if selected_territories and coords and editing_territory:
        # do all three; change whats selected, then compute intersection
        #edit df to reflect selection
        df_ = res[res['ExternalName'].isin(selected_territories)].copy()
        df_.iscopy = False
        # now compute intersection
        bounding_boxes = [Polygon(x[0]) for x in coords]
        gpd_ = gp.GeoDataFrame(df_, geometry =gp.points_from_xy(df_.BillingLongitude,df_.BillingLatitude))
        intersections = []
        for bounding_box in bounding_boxes:
            intersection = gpd_.intersects(gp.GeoSeries(bounding_box).unary_union)
            intersections.append(intersection)
        intersection = np.array(intersections).any(0)
        df_.loc[intersection,'ExternalName'] = editing_territory
        df_.loc[intersection,'category'] = cat_terr_map[editing_territory]
        #now compute the resulting table by groupby stuff
        tbl_df_ = pd.DataFrame(df_.groupby('ExternalName')[['Consortium_Sales_Total','TA_Sales_Total']].sum().reset_index())
        #convert resulant geojson to geojson
        dicts = df_.to_dict('records')
        for item in dicts:
            item["tooltip"] = f"Consortium_Sales: {item['Consortium_Sales_Total']} , TA Sales: {item['TA_Sales_Total']}, ZIP: {item['BillingPostalCode']}, External: ({item['ExternalName']})" # bind tooltip
        geojson = dlx.dicts_to_geojson(dicts, lon="BillingLongitude", lat = "BillingLatitude")  # convert to geojson
        return geojson, tbl_df_.to_dict('records'),[{"name": i, "id": i} for i in tbl_df_.columns]   

    if (selected_territories and not coords) or (selected_territories and not editing_territory):
        # selected territories but either there is a poly and no specified new terr, or there is a specified new terr and no poly, so we will simply update table and plot to reflect this 
        df_ = res[res['ExternalName'].isin(selected_territories)].copy()
        df_.iscopy = False
        dicts = df_.to_dict('records')
        for item in dicts:
            item["tooltip"] = f"Consortium_Sales: {item['Consortium_Sales_Total']} , TA Sales: {item['TA_Sales_Total']}, ZIP: {item['BillingPostalCode']}, External: ({item['ExternalName']})" # bind tooltip
        geojson = dlx.dicts_to_geojson(dicts, lon="BillingLongitude", lat = "BillingLatitude")  # convert to geojson

        tbl_df_ = tbl_df[tbl_df['ExternalName'].isin(selected_territories)]
        return geojson, tbl_df_.to_dict('records'),[{"name": i, "id": i} for i in tbl_df_.columns]  
    
    else:
        # nothing has happened so return the table and the geojson as they were
        return data, tbl_df.to_dict('records'),[{"name": i, "id": i} for i in tbl_df.columns]  



@app.callback(
    Output('download-territory-csv','data'),
    Input('btn_csv_1','n_clicks'),
    State('geojson_l','data'),
    prevent_inital_callback = True,
)
def gen_terri_output(n_clicks,data):
    """send the data created by edit control to a csv"""
    if n_clicks == 2:
        props = []
        for v in data['features']:
            props.append(v['properties'])
            res = pd.DataFrame(props)
        return dcc.send_data_frame(res.to_csv,'territories.csv')
    else:
            return None

if __name__ == '__main__':
    #app.run_server(host='0.0.0.0', port=8080, debug=None) #remote deployment
    app.run_server()