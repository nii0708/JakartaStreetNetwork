import streamlit as st
import pickle
import pandas as pd
import geopandas as gpd
import folium 
from shapely.geometry import Point
import osmnx as ox

# turn response caching off
ox.config(use_cache=False)

# turn it back on and turn on/off logging to your console
ox.config(use_cache=True, log_console=False)

st.set_page_config(layout="wide")
st.title('JAKARTA STREET NETWORK RESILIENCE')
url = "https://open.substack.com/pub/multiworldsmanifolds/p/how-resilient-is-the-jakarta-transportation"
st.subheader("For full article check this [link](%s)" % url)
st.divider()

def count_proximity(gdf,
                  gdf_reference,
                  treatment,
                  n=100,
                  buffer=500, 
                  ):
    gdf1 = gdf_reference.to_crs(epsg=3857)  # Project to Mercator (meters)
    gdf2 = gdf.to_crs(epsg=3857)  # Project to Mercator (meters)

    gdf1_buffer = gdf1.copy()
    gdf1_buffer['geometry'] = gdf1.geometry.buffer(buffer)  
    
    gdf2['within_500m'] = gdf2.geometry.apply(lambda x: gdf1_buffer.geometry.contains(x).any())

    prox = gdf2.sort_values(by=f't_{treatment}',ascending=False).head(n)['within_500m'].sum()

    return prox


def treatment():
    def plot_top_n_intersection(gdf,treatment,num_rank):
        gdf = gdf.sort_values(by=treatment,ascending=False).iloc[:num_rank]
        gdf['rank'] = [i for i in range(1,num_rank+1)]
        
        m = folium.Map(location=[gdf.geometry.y.mean(), gdf.geometry.x.mean()], zoom_start=11)
        
        #plot the data
        my_map = gdf.explore(marker_kwds={'radius':10},
                    m = m,
                    popup='rank',
                    tooltip=['rank', treatment],
                    column='rank',
                    cmap='winter',)

        #plot the marker
        for _, row in gdf.iterrows():
            folium.Marker(
                location=[row['y'], row['x']],  # Latitude, Longitude
                icon=folium.DivIcon(html=f"""<div style="font-size: 10px; color: black;">{row['rank']}</div>""")
            ).add_to(my_map)
        return my_map,m

    # Using object notation
    n_close = st.sidebar.selectbox(
        "How many intersections will you close?",
        ([i for i in range(41)])
    )

    top_n = st.sidebar.select_slider(
        "show number of top intersections",
        options=[i for i in range(1,101)],
    )
    
    st.sidebar.text('show 500 m buffer area from')
    selected_layers = [
            layer
            for layer in ['police station', 'fire station']
            if st.sidebar.checkbox(layer, False)
        ]
    
    #progress bar start
    progress_bar = st.sidebar.progress(0, 'loading the data')
    if 'gdf' not in st.session_state:
        st.session_state.gdf = gpd.read_file('./assets/graph_data_1.shp')
    gdf = st.session_state.gdf
    
    progress_bar.progress(0.3, text='loading the data')
    if 'police' not in st.session_state:
        st.session_state.police = gpd.read_file('./assets/police.shp')
    police = st.session_state.police
    
    progress_bar.progress(0.3, text='loading the data')
    if 'fire' not in st.session_state:
        st.session_state.fire = gpd.read_file('./assets/fire_station.shp')
    fire = st.session_state.fire
    #progress bar end
    progress_bar.empty()

    my_map,m = plot_top_n_intersection(gdf,f't_{n_close}',top_n)

    if selected_layers:
        for selected_layer in selected_layers:
                #add the second GeoDataFrame to the same map
                if selected_layer == 'police station':
                    folium_layer2 = police.explore(
                                m=m,
                                column='name',
                                tooltip="name",
                                marker_type='circle',
                                marker_kwds={'radius':500},
                                style_kwds={'color':'black',
                                            'fill':True,
                                            'fillOpacity':0.1
                                    },
                                legend=False
                                )
                    st.sidebar.write(f':blue[In treatment {n_close}, there are {count_proximity(gdf,police,n_close,top_n)}\
                        intersections within police station buffer zones out of {top_n} intersections]')
                if selected_layer == 'fire station':
                    folium_layer3 = fire.explore(
                                m=m,
                                column='name',
                                tooltip="name",
                                marker_type='circle',
                                marker_kwds={'radius':500},
                                style_kwds={'color':'red',
                                            'fill':True,
                                            'fillOpacity':0.1
                                    },
                                legend=False
                                )
                    st.sidebar.write(f':red[In treatment {n_close}, there are {count_proximity(gdf,fire,n_close,top_n)}\
                        intersections within fire station buffer zones out of {top_n} intersections]')
        folium.LayerControl().add_to(m)
    # if selected_layers:

    # else:
    #         st.error("Please choose at least one layer above.")

    st.components.v1.html(m._repr_html_() , height=600)

    
def jakarta_betweeness_centrality():
    def plot_betweeness_centrality(gdf,treatment):

        #plot the data
        my_map = gdf[gdf[treatment].notna()][['node','y','x',treatment,'geometry']].explore(marker_kwds={'radius':3},
                    popup=treatment,
                    column=treatment,
                    cmap='plasma',)
        # folium.TileLayer('cartodbpositron').add_to(my_map)

        return my_map
    
    

    # Using object notation
    n_close = st.sidebar.selectbox(
        "How many intersections will you close?",
        ([i for i in range(41)])
    )



    if 'gdf' not in st.session_state:
        st.session_state.gdf = gpd.read_file('./assets/graph_data_1.shp')
    gdf = st.session_state.gdf



    #with st.sidebar.button("Update map"):
    my_map = plot_betweeness_centrality(gdf,f't_{n_close}')

    st.components.v1.html(my_map._repr_html_() , height=600)

def intro():
    st.header("How to test the network resilience on disturbance?")

    st.image("assets/treatment.png", caption="treatment illustration",width=800)
    st.write("Imagine how a blockage would be translated in the network. If a blockage occurs at an intersection, \
        all roads directly connected to that intersection would become inaccessible via that intersection. \
        This treatment translates to removing that particular intersection (node) from the network (graph) and called elimination test. \
            We choose the most important intersection by using betweenness centrality")
    st.divider()
    st.write("In the sidebar, select 'Jakarta Betweenness Centrality' to display the betweenness centrality of each intersection, \
        and choose 'Treatment' to show up to the top 100 intersections and their proximity to police and fire stations.")

page_names_to_funcs = {
    "Home Page": intro,
    "Treatment": treatment,
    "Jakarta Betweeness Centrality":jakarta_betweeness_centrality}

demo_name = st.sidebar.selectbox("Choose a demo", page_names_to_funcs.keys())
page_names_to_funcs[demo_name]()

