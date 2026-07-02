from scripts.extract_load import extract_and_load

if "data_loader" not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_data(*args, **kwargs):
    return extract_and_load()
