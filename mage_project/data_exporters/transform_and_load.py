from mage_ai.data_preparation.decorators import data_exporter
from scripts.transform_load import transform_and_load


@data_exporter
def export_data(data, *args, **kwargs):
    return transform_and_load()
