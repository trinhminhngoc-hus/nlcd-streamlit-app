import ee
import streamlit as st
import importlib
from google.oauth2 import service_account
import geemap as geemap_package

geemap_package.basemaps = importlib.import_module("geemap.basemaps")
import geemap.foliumap as geemap

PROJECT_ID = "gee-ngoc-2025"

if "gcp_service_account" not in st.secrets:
    st.error("Thiếu [gcp_service_account] trong Streamlit Secrets.")
    st.stop()

service_account_info = dict(st.secrets["gcp_service_account"])

credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=[
        "https://www.googleapis.com/auth/earthengine",
        "https://www.googleapis.com/auth/cloud-platform",
    ],
)

try:
    ee.Initialize(
        credentials=credentials,
        project=PROJECT_ID,
    )
except Exception as error:
    st.error(f"Không khởi tạo được Earth Engine: {error}")
    st.stop()

def get_nlcd(year):
    dataset = ee.ImageCollection(
        "USGS/NLCD_RELEASES/2019_REL/NLCD"
    )

    image = (
        dataset
        .filter(ee.Filter.eq("system:index", str(year)))
        .first()
    )

    return image.select("landcover")


st.set_page_config(
    page_title="NLCD Land Cover",
    layout="wide",
)

st.header("National Land Cover Database (NLCD)")

control_col, map_col = st.columns([1, 3])

years = [
    "2001",
    "2004",
    "2006",
    "2008",
    "2011",
    "2013",
    "2016",
    "2019",
]

with control_col:
    selected_years = st.multiselect(
        "Select years",
        years,
        default=["2019"],
    )

    add_legend = st.checkbox(
        "Show legend",
        value=True,
    )

Map = geemap.Map(
    center=[40, -100],
    zoom=4,
)

for year in selected_years:
    Map.addLayer(
        get_nlcd(year),
        {},
        f"NLCD {year}",
    )

if add_legend:
    Map.add_legend(
        title="NLCD Land Cover",
        builtin_legend="NLCD",
    )

with map_col:
    Map.to_streamlit(height=650)
