from swigg_ml_local import SWG 
from swigg_db_local import SWGDatasetLocal

def load_data(data, restaurant_id):


	data[('restaurant', 'to', 'customer')].edge_index = edge_index
	data[('customer', 'to', 'restaurant')].edge_index = torch.stack([edge_index[1], edge_index[0]])

	return data


def generate_prediction(data):

    model = SWG(hidden_channels=64, num_heads=2, num_layers=2,
                node_types=['restaurant', 'area', 'customer'],
                mlp_hidden_layers=[128, 64, 32, 1], mlp_dropout=0.4,
                data=data)
    model = load_state_dict(torch.load('./restaurant_fl/swg_state_global.pth'))
    print(f'Loaded model weights')


def main():
	data = SWGDataset(path, 0, force_reload=True)
	generate_prediction(data)
