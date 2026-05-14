from mage_ai.data_preparation.decorators import data_loader
import sys
sys.path.append('/home/scripts')
from extract_load import extract_and_load


@data_loader
def extract_and_load_data(*args, **kwargs):
    return extract_and_load()
