from mage_ai.data_preparation.decorators import data_exporter
import sys
sys.path.append('/home/scripts')
from transform_load import transform_and_load


@data_exporter
def transform_and_load_data(data, *args, **kwargs):
    return transform_and_load()
