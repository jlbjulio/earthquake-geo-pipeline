import sys
sys.path.append('/home/scripts')
from transform_load import transform_and_load


@data_exporter
def export_data(data, *args, **kwargs):
    # data contains the output from the previous block (extract_and_load)
    # transform_and_load reads directly from raw_earthquakes in the database
    return transform_and_load()
