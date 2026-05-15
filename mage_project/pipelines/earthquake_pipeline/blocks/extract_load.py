from mage_ai.data_preparation.decorators import data_loader
from scripts.extract_load import extract_and_load


@data_loader
def load_data(*args, **kwargs):
    return extract_and_load()
