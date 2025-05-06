import os.path as osp
import warnings
import numpy as np
import torch
import torch.nn.functional as F
import torch_geometric
import torch_geometric.transforms as T
from torch_geometric.nn import HGTConv, Linear, MLP
from torch_geometric.utils import to_networkx
from torch_geometric.transforms import RandomLinkSplit, ToUndirected
from torch_geometric.loader import LinkNeighborLoader
from tqdm import tqdm
import networkx as nx
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, precision_recall_curve, auc, matthews_corrcoef
from swigg_db_local import SWGDatasetLocal

class SWG(torch.nn.Module):
    def __init__(self, hidden_channels, num_heads, num_layers, node_types, mlp_hidden_layers, mlp_dropout, data):
        super().__init__()

        self.lin_dict = torch.nn.ModuleDict()
        for node_type in node_types:
            self.lin_dict[node_type] = Linear(data.x_dict[node_type].size(-1), hidden_channels)

        self.convs = torch.nn.ModuleList()
        for _ in range(num_layers):
            conv = HGTConv(hidden_channels, hidden_channels, data.metadata(),
                           num_heads)
            self.convs.append(conv)

        #self.lin = Linear(hidden_channels, out_channels)
        self.mlp = MLP(mlp_hidden_layers, dropout=mlp_dropout, norm=None)

    def forward(self, x_dict, edge_index_dict, tr_edge_label_index):
        x_dict = {
            node_type: self.lin_dict[node_type](x).relu_()
            for node_type, x in x_dict.items()
        }
        for conv in self.convs:
            x_dict = conv(x_dict, edge_index_dict)

        row, col = tr_edge_label_index
        z = torch.cat([x_dict['restaurant'][row], x_dict['customer'][col]], dim=-1)

        return self.mlp(z).view(-1), x_dict
        #return self.lin(x_dict['restaurant'])

def metrics(prob_pred, binary_pred, ground_truth):
    f1 = f1_score(ground_truth, binary_pred)

    _precision, _recall, thresholds = precision_recall_curve(ground_truth, prob_pred)
    pr_auc = auc(_recall, _precision)

    acc = accuracy_score(ground_truth, binary_pred)

    precision = precision_score(ground_truth, binary_pred)
    recall = recall_score(ground_truth, binary_pred)

    mcc= matthews_corrcoef(ground_truth, binary_pred)

    metric_list = [precision, recall, f1, pr_auc, acc, mcc]

    return [float(m) for m in metric_list]

def create_loader(train_data, val_data, test_data):
    train_loader = LinkNeighborLoader(
        train_data, num_neighbors=[4],
        neg_sampling_ratio=5, shuffle=True,
        edge_label=train_data['restaurant', 'to', 'customer'].edge_label,
        edge_label_index=(('restaurant', 'to', 'customer'),
            train_data['restaurant', 'to', 'customer'].edge_label_index),
            batch_size=2,
        )

    val_loader = LinkNeighborLoader(
        val_data, num_neighbors=[4],
        neg_sampling_ratio=5, shuffle=True,
        edge_label=train_data['restaurant', 'to', 'customer'].edge_label,
        edge_label_index=(('restaurant', 'to', 'customer'),
            train_data['restaurant', 'to', 'customer'].edge_label_index),
            batch_size=2,
        )

    test_loader = LinkNeighborLoader(
        test_data, num_neighbors=[4],
        neg_sampling_ratio=5, shuffle=True,
        edge_label=train_data['restaurant', 'to', 'customer'].edge_label,
        edge_label_index=(('restaurant', 'to', 'customer'),
            train_data['restaurant', 'to', 'customer'].edge_label_index),
            batch_size=2,
        )
    return train_loader, val_loader, test_loader

@torch.no_grad()
def init_model(model, loader):
    batch = next(iter(loader))
    print(f"batch:{batch}")
    batch = batch.to('cpu')
    model(batch.x_dict, batch.edge_index_dict, batch[('restaurant', 'to', 'customer')].edge_label_index)

def train_local(model, loader, epoch):        
    optimizer = torch.optim.Adam([
        dict(params=model.convs.parameters(), weight_decay=0.001, lr=0.005),
        dict(params=model.mlp.parameters(), weight_decay=0.001, lr=0.005),
    ])
    
    model.train()

    total_examples = total_loss = 0
    num_batches = len(loader)
    pbar = tqdm(enumerate(loader), total=num_batches, desc=f'Epoch {epoch}')

    try:
        for batch_idx, batch in pbar:
            optimizer.zero_grad()
            batch = batch.to("cpu")

            try:
                out, _ = model(batch.x_dict,
                        batch.edge_index_dict,
                        batch[('restaurant', 'to', 'customer')].edge_label_index
                )
            except RuntimeError as e:
                print(f"Error in model forward pass: {str(e)}")
                continue
            true_label = batch[('restaurant', 'to', 'customer')].edge_label
            true_label_size = len(true_label)

            pos_weight = torch.tensor([100]).to('cpu')
            loss = F.binary_cross_entropy_with_logits(out, true_label, pos_weight=pos_weight)
            loss.backward()

            optimizer.step()
            total_examples += true_label_size
            total_loss += float(loss) * true_label_size

            pbar.set_postfix({'loss': f'{loss.item():.4f}'})

    except Exception as e:
        print(f"Training error occurred: {str(e)}")
        raise e

    avg_loss = total_loss / total_examples
    return round(avg_loss, 4)

@torch.no_grad()
def test_local(model, loader, epoch):
    model.eval()

    total_examples = total_loss = 0
    total_precision = total_recall = total_f1 = total_pr_auc = total_acc = total_mcc = 0
    num_batches = len(loader)

    pbar = tqdm(enumerate(loader), total=num_batches, desc=f'Evaluation Epoch {epoch}')

    try:
        for batch_idx, batch in pbar:
            try:
                pred, _ = model(
                    batch.x_dict,
                    batch.edge_index_dict,
                    batch[('restaurant', 'to', 'customer')].edge_label_index,
                )
            except RuntimeError as e:
                print(f"Error in model forward pass: {str(e)}")
                continue

            #print(f"pred:{pred}")
            pred.cpu()
            true_label = batch[('restaurant', 'to', 'customer')].edge_label.cpu()
            true_label_size = len(true_label)
            #print(f"true_label:{true_label}")
            #print(f"true_label_size:{true_label_size}")

            pos_weight = torch.tensor([100]).to('cpu')
            ts_loss = F.binary_cross_entropy_with_logits(pred, true_label, pos_weight=pos_weight)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                binary_pred = np.where(pred.numpy() > 0.0, 1, 0)
                prob_pred = torch.sigmoid(pred).numpy()

            total_examples += true_label_size
            total_loss += float(ts_loss) * true_label_size

            metric = metrics(prob_pred, binary_pred, true_label)
            total_precision += float(metric[0]) * true_label_size
            total_recall += float(metric[1]) * true_label_size
            total_f1 += float(metric[2]) * true_label_size
            total_pr_auc += float(metric[3]) * true_label_size
            total_acc += float(metric[4]) * true_label_size
            total_mcc += float(metric[5]) * true_label_size

            pbar.set_postfix({
                'loss': f'{ts_loss:.4f}',
                'f1': f'{metric[2]:.4f}'
            })

    except Exception as e:
        print(f"Evaluation error occurred: {str(e)}")
        raise e

    metric = {
        'loss': round(total_loss/total_examples, 4),
        'precision': round(total_precision/total_examples, 4),
        'recall': round(total_recall/total_examples, 4),
        'f1': round(total_f1/total_examples, 4),
        'pr_auc': round(total_pr_auc/total_examples, 4),
        'acc': round(total_acc/total_examples, 4),
        'mcc': round(total_mcc/total_examples, 4)
    }
    return metric

def main():
    path = osp.join(osp.dirname(osp.realpath(__file__)), '')
    dataset = SWGDatasetLocal(path, 0, force_reload=True)

    print(f"dataset:{dataset.data}")
    transform = RandomLinkSplit(
        num_val=0.1,
        num_test=0.2,
        neg_sampling_ratio=0.0,
        edge_types=[('restaurant', 'to', 'customer'),
                    ],
        rev_edge_types=[('customer', 'to', 'restaurant'),
                    ],
    )

    train_data, val_data, test_data = transform(dataset.data)

    train_loader, val_loader, test_loader = create_loader(train_data, val_data, test_data)

    model = SWG(hidden_channels=64, num_heads=2, num_layers=2,
                node_types=['restaurant', 'area', 'customer'],
                mlp_hidden_layers=[128, 64, 32, 1], mlp_dropout=0.4,
                data=dataset.data)

    init_model(model, train_loader)
    model.to('cpu')

    for epoch in range(1, 2):
        train_local(model, train_loader, epoch)
        test_local(model, test_loader, epoch)

if __name__ == "__main__":
    main()