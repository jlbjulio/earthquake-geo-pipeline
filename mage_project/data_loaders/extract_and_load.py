import sys
sys.path.append('/home/scripts')
from extract_load import extract_and_load


@data_loader
def load_data(*args, **kwargs):
    return extract_and_load()
